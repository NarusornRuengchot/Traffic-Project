import asyncio
import base64
import datetime
import json
import os
import shutil
import tempfile
import time
from typing import Dict, Any, Optional, List

import cv2
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from ai_engine import AITrafficEngine, get_traffic_level

app = FastAPI(title="KU SRC Smart Traffic WebSocket Service", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

DEFAULT_MODEL = "best.pt" if os.path.exists("best.pt") else "yolov11n.pt"
global_engine = AITrafficEngine(model_name=DEFAULT_MODEL)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>KU SRC Traffic Dashboard is loading...</h2>")


@app.get("/api/models")
async def list_models():
    return {
        "models": AITrafficEngine.get_available_models(),
        "devices": AITrafficEngine.get_available_devices(),
        "current_model": global_engine.model_name
    }


SUPPORTED_VIDEO_EXTENSIONS = (
    ".mov", ".mp4", ".avi", ".mkv", ".webm",
    ".m4v", ".wmv", ".flv", ".ts", ".3gp"
)


@app.get("/api/videos")
async def list_videos():
    videos = []
    seen_paths = set()

    # 1. Scan root project folder for all video files (.mov, .mp4, etc.)
    for f in sorted(os.listdir(".")):
        if os.path.isfile(f) and f.lower().endswith(SUPPORTED_VIDEO_EXTENSIONS):
            is_sample = "kusrc" in f.lower()
            label = f"KU SRC Sample Video ({f})" if is_sample else f"📹 Project Video: {f}"
            videos.append({
                "id": f,
                "name": label,
                "path": f,
                "type": "sample" if is_sample else "local"
            })
            seen_paths.add(os.path.abspath(f))

    # 2. Scan uploaded video files
    if os.path.exists(UPLOAD_DIR):
        for f in sorted(os.listdir(UPLOAD_DIR)):
            full_path = os.path.join(UPLOAD_DIR, f)
            if os.path.isfile(full_path) and f.lower().endswith(SUPPORTED_VIDEO_EXTENSIONS):
                if os.path.abspath(full_path) not in seen_paths:
                    videos.append({
                        "id": f,
                        "name": f"📁 Uploaded: {f}",
                        "path": full_path,
                        "type": "uploaded"
                    })
                    seen_paths.add(os.path.abspath(full_path))

    return {"videos": videos}


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
        
    safe_name = os.path.basename(file.filename)
    dest_path = os.path.join(UPLOAD_DIR, safe_name)
    
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"status": "success", "filename": safe_name, "path": dest_path}


@app.get("/api/video-preview")
async def get_calibration_preview(
    path: str,
    line_y: float = Query(0.50),
    mid_x: float = Query(0.45),
    swap: bool = Query(False)
):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Video not found")
        
    info = AITrafficEngine.get_video_info(path)
    if not info:
        raise HTTPException(status_code=400, detail="Could not read video")
        
    first_frame = info.pop("first_frame")
    preview = AITrafficEngine.generate_calibration_preview(
        first_frame,
        line_y_ratio=line_y,
        mid_x_ratio=mid_x,
        swap_directions=swap
    )
    
    _, buffer = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 80])
    preview_base64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")
    
    info["preview"] = preview_base64
    return info


@app.websocket("/ws/traffic")
async def websocket_traffic_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    session_engine = AITrafficEngine(model_name=global_engine.model_name)
    is_running = False
    is_paused = False
    run_lock = asyncio.Lock()
    stream_task: Optional[asyncio.Task] = None
    
    config = {
        "video_path": "KUSRC_Traffic.MOV" if os.path.exists("KUSRC_Traffic.MOV") else "KUSRC_Traffic.mov",
        "model_name": session_engine.model_name,
        "line_y_ratio": 0.50,
        "mid_x_ratio": 0.45,
        "swap_directions": False,
        "conf_threshold": 0.25,
        "frame_skip": 2,
        "img_size": 640,
        "device": "cpu",
        "target_classes": ["Car", "Motorcycle", "Bus", "Truck"],
        "start_datetime_str": datetime.datetime.now().strftime("%Y-%m-%d 08:30:00"),
        "jpeg_quality": 75
    }

    async def stream_worker():
        nonlocal is_running, is_paused
        
        video_path = config.get("video_path", "")
        if not os.path.exists(video_path):
            await websocket.send_json({"type": "error", "message": f"Video file not found: {video_path}"})
            is_running = False
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            await websocket.send_json({"type": "error", "message": "Failed to open video file"})
            is_running = False
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        try:
            start_dt = datetime.datetime.strptime(config["start_datetime_str"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            start_dt = datetime.datetime.now()

        session_engine.reset_state()
        session_engine.update_target_classes(config.get("target_classes", ["Car", "Motorcycle", "Bus", "Truck"]))
        
        frame_idx = 0
        last_yield_time = time.time()
        fps_timer_start = time.time()
        frames_processed_count = 0
        current_fps = 0.0
        
        await websocket.send_json({
            "type": "started",
            "total_frames": total_frames,
            "fps": fps,
            "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S")
        })

        try:
            while is_running and cap.isOpened():
                if is_paused:
                    await asyncio.sleep(0.1)
                    continue

                success, frame = cap.read()
                if not success:
                    break

                frame_idx += 1
                frame_skip = max(1, int(config.get("frame_skip", 2)))
                if frame_idx % frame_skip != 0:
                    continue

                frames_processed_count += 1
                now = time.time()
                # Compute real-time processing FPS every 5 frames
                if now - fps_timer_start >= 0.5:
                    current_fps = round(frames_processed_count / (now - fps_timer_start), 1)
                    fps_timer_start = now
                    frames_processed_count = 0

                # Run YOLO in worker thread
                annotated_frame, telemetry = await asyncio.to_thread(
                    session_engine.process_frame,
                    frame=frame,
                    frame_idx=frame_idx,
                    fps=fps,
                    start_datetime=start_dt,
                    line_y_ratio=float(config.get("line_y_ratio", 0.50)),
                    mid_x_ratio=float(config.get("mid_x_ratio", 0.45)),
                    swap_directions=bool(config.get("swap_directions", False)),
                    img_size=int(config.get("img_size", 640)),
                    device=str(config.get("device", "cpu"))
                )

                telemetry["frame_idx"] = frame_idx
                telemetry["total_frames"] = total_frames
                telemetry["progress_pct"] = round((frame_idx / total_frames) * 100, 1) if total_frames > 0 else 0.0
                telemetry["fps"] = current_fps if current_fps > 0 else round(fps, 1)

                jpeg_quality = int(config.get("jpeg_quality", 75))
                _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                frame_base64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")

                payload = {
                    "type": "frame",
                    "frame": frame_base64,
                    "telemetry": telemetry
                }

                await websocket.send_json(payload)

                target_frame_time = (1.0 / fps) * frame_skip
                elapsed = time.time() - last_yield_time
                if elapsed < target_frame_time:
                    await asyncio.sleep(target_frame_time - elapsed)
                else:
                    await asyncio.sleep(0.001)
                last_yield_time = time.time()

            summary_data = session_engine.generate_summary_table(start_dt)
            await websocket.send_json({
                "type": "finished",
                "total_inbound": session_engine.inbound_count,
                "total_outbound": session_engine.outbound_count,
                "total_vehicles": session_engine.inbound_count + session_engine.outbound_count,
                "class_counts": session_engine.class_counts,
                "summary_table": summary_data,
                "events_log": session_engine.events_log
            })

        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})
        finally:
            cap.release()
            is_running = False

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            action = msg.get("action", "")

            if action == "start":
                async with run_lock:
                    if is_running:
                        await websocket.send_json({"type": "warning", "message": "Analysis is already running."})
                        continue

                    if "config" in msg:
                        config.update(msg["config"])

                    req_model = config.get("model_name", DEFAULT_MODEL)
                    if session_engine.model_name != req_model:
                        session_engine.load_model(req_model)

                    session_engine.conf_threshold = float(config.get("conf_threshold", 0.25))
                    session_engine.img_size = int(config.get("img_size", 640))
                    session_engine.device = str(config.get("device", "cpu"))
                    if "target_classes" in config:
                        session_engine.update_target_classes(config["target_classes"])

                    is_running = True
                    is_paused = False
                    stream_task = asyncio.create_task(stream_worker())

            elif action == "pause":
                is_paused = not is_paused
                await websocket.send_json({"type": "paused", "is_paused": is_paused})

            elif action == "stop":
                is_running = False
                if stream_task and not stream_task.done():
                    stream_task.cancel()
                await websocket.send_json({"type": "stopped"})

            elif action == "update_config":
                new_cfg = msg.get("config", {})
                config.update(new_cfg)
                if "conf_threshold" in new_cfg:
                    session_engine.conf_threshold = float(new_cfg["conf_threshold"])
                if "img_size" in new_cfg:
                    session_engine.img_size = int(new_cfg["img_size"])
                if "device" in new_cfg:
                    session_engine.device = str(new_cfg["device"])
                if "target_classes" in new_cfg:
                    session_engine.update_target_classes(new_cfg["target_classes"])
                if "model_name" in new_cfg and new_cfg["model_name"] != session_engine.model_name:
                    session_engine.load_model(new_cfg["model_name"])
                await websocket.send_json({"type": "config_updated", "config": config})

            elif action == "ping":
                await websocket.send_json({"type": "pong", "time": time.time()})

    except WebSocketDisconnect:
        is_running = False
        if stream_task and not stream_task.done():
            stream_task.cancel()
    except Exception:
        is_running = False
        if stream_task and not stream_task.done():
            stream_task.cancel()


if __name__ == "__main__":
    print("🚀 Starting KU SRC Smart Traffic WebSocket Server on http://localhost:8000 ...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
