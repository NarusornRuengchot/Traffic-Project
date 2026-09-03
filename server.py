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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

from src.core.traffic_pipeline import TrafficPipeline
from src.core.analytics import evaluate_traffic_level
from src.utils.file_helper import resolve_model_path, list_available_models, list_available_videos, SUPPORTED_VIDEO_EXTENSIONS
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
    """Finds exact video path in project root or uploads folder."""
    if os.path.exists(video_path):
        return video_path

    cand = os.path.join(BASE_DIR, video_path)
    if os.path.exists(cand):
        return cand

    cand_up = os.path.join(UPLOAD_DIR, os.path.basename(video_path))
    if os.path.exists(cand_up):
        return cand_up

    # Fallback to first available video
    vids = list_available_videos(upload_dir=UPLOAD_DIR, project_dir=BASE_DIR)
    if vids:
        return vids[0]["path"]

    return video_path

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
                worker.load_video(resolved_vid)
                worker.reset()
                worker.start()
                await websocket.send_json({"type": "status", "playing": True})

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


