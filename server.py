import asyncio
import base64
import datetime
import json
import os
import shutil
import tempfile
import time
from typing import Dict, Any, Optional, List
import io

import cv2
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

from src.core.traffic_pipeline import TrafficPipeline
from src.core.analytics import evaluate_traffic_level
from src.utils.file_helper import (
    resolve_model_path,
    list_available_models,
    list_available_videos,
    resolve_video_source,
    SUPPORTED_VIDEO_EXTENSIONS
)
from src.services.stream_worker import StreamWorker

app = FastAPI(title="KU SRC Smart Traffic Dashboard API", version="2.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount frontend static assets
if os.path.exists(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

DEFAULT_MODEL = "best.pt" if os.path.exists("best.pt") else "yolov11n.pt"
global_engine = TrafficPipeline(model_name=DEFAULT_MODEL)
active_worker: Optional[StreamWorker] = None

def resolve_video_path(video_path: str) -> str:
    """Finds exact video path in project root, uploads folder, or live webcam/RTSP stream."""
    if not video_path:
        return "webcam:0"
    return resolve_video_source(video_path, upload_dir=UPLOAD_DIR, base_dir=BASE_DIR)

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    react_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(react_index):
        return FileResponse(react_index)
    static_index = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return HTMLResponse("<h2>KU SRC Traffic Dashboard is starting...</h2>")

@app.get("/api/models")
async def get_models():
    current_model = active_worker.engine.model_name if active_worker else global_engine.model_name
    return {
        "models": TrafficPipeline.get_available_models(),
        "devices": TrafficPipeline.get_available_devices(),
        "current_model": current_model
    }

@app.get("/api/videos")
async def get_videos():
    return {"videos": list_available_videos(upload_dir=UPLOAD_DIR, project_dir=BASE_DIR)}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    filename = file.filename or f"uploaded_{int(time.time())}.mp4"
    clean_name = os.path.basename(filename)
    dest_path = os.path.join(UPLOAD_DIR, clean_name)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "success": True,
        "video": {
            "id": clean_name,
            "name": f"📁 Uploaded: {clean_name}",
            "path": dest_path,
            "type": "uploaded"
        }
    }

@app.get("/api/calibration/preview")
async def get_calibration_preview(
    video_path: str = Query(..., description="Path to video file"),
    line_y_ratio: float = Query(0.50),
    mid_x_ratio: float = Query(0.45),
    swap_directions: bool = Query(False)
):
    resolved = resolve_video_path(video_path)
    if not os.path.exists(resolved):
        raise HTTPException(status_code=404, detail="Video file not found")

    v_info = TrafficPipeline.get_video_info(resolved)
    if not v_info or v_info.get("first_frame") is None:
        raise HTTPException(status_code=400, detail="Cannot read video first frame")

    preview = TrafficPipeline.generate_calibration_preview(
        first_frame=v_info["first_frame"],
        line_y_ratio=line_y_ratio,
        mid_x_ratio=mid_x_ratio,
        swap_directions=swap_directions
    )

    _, buffer = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    b64 = base64.b64encode(buffer).decode("utf-8")
    return {"preview": b64, "width": v_info["width"], "height": v_info["height"]}

@app.get("/api/export")
async def export_data(format: str = Query("csv")):
    # Extract live telemetry from active worker if currently streaming, else global engine
    target_engine = active_worker.engine if (active_worker and active_worker.engine.events_log) else global_engine

    if format == "summary":
        summary = target_engine.generate_summary_table(datetime.datetime.now())
        return {"summary": summary}

    # CSV Export of crossing events
    events = target_engine.events_log
    lines = ["Timestamp (s),Real-world Time,Vehicle ID,Type,Direction,Traffic Level"]
    for ev in events:
        lines.append(
            f"{ev.get('Timestamp (s)', '')},"
            f"{ev.get('Real-world Time', '')},"
            f"{ev.get('Vehicle ID', '')},"
            f"{ev.get('Type', '')},"
            f"{ev.get('Direction', '')},"
            f"\"{ev.get('Traffic Level', '')}\""
        )
    csv_str = "\n".join(lines)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=traffic_events.csv"}
    )

def _clean_param(param, default=None):
    if param is None or hasattr(param, "default") or str(param) in ("all", "All", "None", ""):
        return default
    return str(param)

@app.get("/api/reports/peak-hours")
async def get_peak_hours_report(date: Optional[str] = Query(None)):
    """Returns 24h hourly volume and peak-hours analytics for the selected date."""
    from src.database.db_manager import db_manager
    target_date = _clean_param(date)
    analytics = db_manager.get_peak_hours_analysis(target_date)
    return analytics

@app.get("/api/reports/history")
async def get_history_report(
    date: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query("All"),
    direction: Optional[str] = Query("All"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """Returns paginated vehicle crossing history with filters."""
    from src.database.db_manager import db_manager
    target_date = _clean_param(date)
    v_type = _clean_param(vehicle_type, default="All")
    dir_str = _clean_param(direction, default="All")
    p = 1 if hasattr(page, "default") else int(page)
    lim = 50 if hasattr(limit, "default") else int(limit)

    offset = (p - 1) * lim
    events, total = db_manager.get_events_history(
        limit=lim,
        offset=offset,
        target_date=target_date,
        vehicle_type=v_type,
        direction=dir_str
    )
    return {
        "events": events,
        "total": total,
        "page": p,
        "limit": lim,
        "total_pages": (total + lim - 1) // lim if total > 0 else 1
    }

@app.get("/api/reports/dates")
async def get_report_dates():
    """Returns list of distinct dates available in the database."""
    from src.database.db_manager import db_manager
    dates = db_manager.get_available_dates()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if today not in dates:
        dates.insert(0, today)
    return {"dates": dates}

@app.get("/api/reports/export")
async def export_report_csv(date: Optional[str] = Query(None)):
    """Generates downloadable CSV export from SQLite database."""
    from src.database.db_manager import db_manager
    target_date = _clean_param(date)
    csv_str = db_manager.export_csv(target_date)
    filename = f"traffic_report_{target_date or 'all'}.csv"
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/api/cctv/test")
async def test_cctv_endpoint(data: Dict[str, Any] = Body(...)):
    """Tests CCTV/RTSP connection with a fast 4-second timeout and returns connection status."""
    url = data.get("url", "").strip()
    if not url or url == "rtsp_stream":
        return {"success": False, "message": "กรุณาระบุ URL กล้องวงจรปิด (เช่น rtsp://admin:pass@192.168.1.100:554/stream1)"}

    resolved = resolve_video_path(url)
    if resolved.startswith("webcam:"):
        cam_idx = int(resolved.replace("webcam:", ""))
        cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(cam_idx)
    else:
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        cap = cv2.VideoCapture(
            resolved,
            cv2.CAP_FFMPEG,
            [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 4000]
        )

    if not cap or not cap.isOpened():
        return {
            "success": False,
            "message": f"❌ ไม่สามารถเชื่อมต่อกล้องได้: กล้องไม่ตอบสนอง กรุณาตรวจสอบ IP, Port, และรหัสผ่าน"
        }

    success, frame = cap.read()
    cap.release()
    if not success or frame is None:
        return {"success": False, "message": "⚠️ สตรีมเปิดได้แต่ไม่ได้รับภาพจากกล้อง"}

    h, w = frame.shape[:2]
    return {
        "success": True,
        "message": f"✅ เชื่อมต่อกล้องสำเร็จ! (ความละเอียด {w}x{h} px)",
        "width": w,
        "height": h
    }

# -------------------------------------------------------------
# Decoupled Real-Time WebSocket Streaming Endpoint
# -------------------------------------------------------------
@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    global active_worker
    await websocket.accept()

    worker = StreamWorker(
        engine=TrafficPipeline(model_name=DEFAULT_MODEL),
        target_width=960,
        inference_size=480,
        jpeg_quality=65
    )
    active_worker = worker

    async def frame_sender_loop():
        """Reads encoded frames from worker's bounded queue without blocking the asyncio loop."""
        while True:
            try:
                # Non-blocking check with small sleep to allow cooperative concurrency
                try:
                    packet = worker.frame_queue.get_nowait()
                except Exception:
                    await asyncio.sleep(0.01)
                    continue

                await websocket.send_json(packet)
            except WebSocketDisconnect:
                break
            except Exception as e:
                break

    sender_task = asyncio.create_task(frame_sender_loop())

    # Send initial status on connection
    await websocket.send_json({
        "type": "model_status",
        "status": "ready",
        "model": worker.engine.model_name
    })

    try:
        while True:
            raw_msg = await websocket.receive_text()
            data = json.loads(raw_msg)
            cmd = data.get("command")

            if cmd == "start":
                worker.update_config(data)
                vid_path = data.get("video_path", "KUSRC_Traffic.mov")
                resolved_vid = resolve_video_path(vid_path)

                # Validation: prevent empty or placeholder RTSP selection
                if resolved_vid == "rtsp_stream" or not str(resolved_vid).strip():
                    await websocket.send_json({
                        "type": "error",
                        "message": "⚠️ กรุณากรอก URL กล้อง CCTV (เช่น rtsp://admin:pass@192.168.1.100:554/stream1 หรือ http://...) ในช่องข้อความก่อนเริ่ม"
                    })
                    await websocket.send_json({"type": "status", "playing": False})
                    continue

                success = worker.load_video(resolved_vid)
                if not success:
                    error_msg = f"❌ ไม่สามารถเปิดสัญญาณภาพได้: {vid_path}"
                    if str(resolved_vid).startswith(("rtsp://", "http://", "https://")):
                        error_msg = (
                            f"❌ ไม่สามารถเชื่อมต่อกล้อง CCTV / RTSP ({vid_path}) ได้\n\n"
                            "สาเหตุที่พบบ่อย:\n"
                            "1. หมายเลข IP Address หรือ Port 554 ไม่ถูกต้อง หรือกล้องยังไม่ได้เปิด\n"
                            "2. ต้องใส่ Username/Password ของกล้อง (เช่น rtsp://admin:1234@192.168.1.100:554/...)\n"
                            "3. อุปกรณ์คอมพิวเตอร์ไม่ได้อยู่ในวง Wi-Fi / LAN เดียวกับกล้อง\n"
                            "4. หากเป็นหน้าเว็บหรือ YouTube จะเปิดตรงไม่ได้ ต้องเป็นสตรีม RTSP หรือ HTTP MJPEG"
                        )
                    elif str(resolved_vid).startswith("webcam:"):
                        error_msg = f"❌ ไม่สามารถเปิดกล้องเว็บแคม ({vid_path}) ได้ กรุณาตรวจสอบว่ามีโปรแกรมอื่นกำลังเปิดกล้องอยู่หรือไม่"

                    await websocket.send_json({
                        "type": "error",
                        "message": error_msg
                    })
                    await websocket.send_json({"type": "status", "playing": False})
                    continue

                worker.reset()
                worker.start()
                await websocket.send_json({"type": "status", "playing": True})

            elif cmd == "test_cctv":
                test_url = data.get("url", "").strip()
                resolved = resolve_video_path(test_url)
                if resolved == "rtsp_stream" or not resolved:
                    await websocket.send_json({
                        "type": "cctv_test_result",
                        "success": False,
                        "message": "กรุณากรอก URL ของกล้องก่อนทดสอบ"
                    })
                    continue

                if resolved.startswith("webcam:"):
                    cam_idx = int(resolved.replace("webcam:", ""))
                    cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(cam_idx)
                else:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
                    cap = cv2.VideoCapture(
                        resolved,
                        cv2.CAP_FFMPEG,
                        [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 4000]
                    )

                if not cap or not cap.isOpened():
                    await websocket.send_json({
                        "type": "cctv_test_result",
                        "success": False,
                        "message": f"❌ เชื่อมต่อไม่สำเร็จ: กล้อง {test_url} ไม่ตอบสนอง (ตรวจสอบ IP/Port/User/Pass)"
                    })
                else:
                    s_frame, t_frame = cap.read()
                    cap.release()
                    if s_frame and t_frame is not None:
                        h_t, w_t = t_frame.shape[:2]
                        await websocket.send_json({
                            "type": "cctv_test_result",
                            "success": True,
                            "message": f"✅ เชื่อมต่อกล้อง CCTV สำเร็จ! ความละเอียดภาพ {w_t}x{h_t} พร้อมใช้งาน",
                            "width": w_t,
                            "height": h_t
                        })
                    else:
                        await websocket.send_json({
                            "type": "cctv_test_result",
                            "success": False,
                            "message": "⚠️ เชื่อมต่อได้แต่ไม่ได้รับภาพจากกล้อง"
                        })

            elif cmd == "pause":
                worker.pause()
                await websocket.send_json({"type": "status", "playing": False})

            elif cmd == "resume":
                worker.resume()
                await websocket.send_json({"type": "status", "playing": True})

            elif cmd == "reset":
                worker.reset()
                await websocket.send_json({"type": "status", "reset": True})

            elif cmd == "get_preview":
                # Real-time calibration preview directly over WebSocket (prevents HTTP API spam)
                vid_path = data.get("video_path", "KUSRC_Traffic.mov")
                resolved_vid = resolve_video_path(vid_path)
                v_info = TrafficPipeline.get_video_info(resolved_vid)
                if v_info and v_info.get("first_frame") is not None:
                    preview = TrafficPipeline.generate_calibration_preview(
                        first_frame=v_info["first_frame"],
                        line_y_ratio=float(data.get("line_y_ratio", 0.50)),
                        mid_x_ratio=float(data.get("mid_x_ratio", 0.45)),
                        swap_directions=bool(data.get("swap_directions", False))
                    )
                    _, buffer = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    b64_prev = base64.b64encode(buffer).decode("utf-8")
                    await websocket.send_json({
                        "type": "preview",
                        "preview": b64_prev,
                        "width": v_info["width"],
                        "height": v_info["height"]
                    })

            elif cmd == "update_config":
                old_model = worker.engine.model_name
                new_model = data.get("model_name")
                if new_model and new_model != old_model:
                    await websocket.send_json({
                        "type": "model_status",
                        "status": "loading",
                        "model": new_model
                    })
                    worker.update_config(data)
                    await websocket.send_json({
                        "type": "model_status",
                        "status": "ready",
                        "model": worker.engine.model_name
                    })
                else:
                    worker.update_config(data)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        worker.stop()
        sender_task.cancel()
        if active_worker is worker:
            active_worker = None

if __name__ == "__main__":
    print("🚀 Starting KU SRC Smart Traffic Server on http://localhost:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)


