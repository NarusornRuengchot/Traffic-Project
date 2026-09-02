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

app = FastAPI(title="KU SRC Smart Traffic Dashboard API", version="2.2.0")

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
    return {
        "models": TrafficPipeline.get_available_models(),
        "devices": TrafficPipeline.get_available_devices(),
        "current_model": global_engine.model_name
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
    if not os.path.exists(video_path):
        # Check in base dir
        cand = os.path.join(BASE_DIR, video_path)
        if os.path.exists(cand):
            video_path = cand
        else:
            raise HTTPException(status_code=404, detail="Video file not found")

    v_info = TrafficPipeline.get_video_info(video_path)
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
    if format == "summary":
        summary = global_engine.generate_summary_table(datetime.datetime.now())
        return {"summary": summary}

    # CSV Export of events
    events = global_engine.events_log
    lines = ["Timestamp (s),Real-world Time,Vehicle ID,Type,Direction,Traffic Level"]
    for ev in events:
        lines.append(f"{ev.get('Timestamp (s)', '')},{ev.get('Real-world Time', '')},{ev.get('Vehicle ID', '')},{ev.get('Type', '')},{ev.get('Direction', '')},\"{ev.get('Traffic Level', '')}\"")
    csv_str = "\n".join(lines)
    return Response(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=traffic_events.csv"})

# -------------------------------------------------------------
# Real-Time WebSocket Streaming Session Handler
# -------------------------------------------------------------
class StreamSession:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.engine = TrafficPipeline(model_name=DEFAULT_MODEL)
        self.is_playing = False
        self.is_paused = False
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_path = ""
        self.conf_threshold = 0.25
        self.line_y_ratio = 0.50
        self.mid_x_ratio = 0.45
        self.swap_directions = False
        self.target_classes = ["Car", "Motorcycle", "Bus", "Truck"]
        self.start_dt = datetime.datetime.now()
        self.fps = 30.0
        self.total_frames = 0
        self.current_frame_idx = 0

    def load_video(self, video_path: str):
        if self.cap is not None:
            self.cap.release()

        resolved = video_path
        if not os.path.exists(resolved):
            cand = os.path.join(BASE_DIR, video_path)
            if os.path.exists(cand):
                resolved = cand
            else:
                cand_up = os.path.join(UPLOAD_DIR, os.path.basename(video_path))
                if os.path.exists(cand_up):
                    resolved = cand_up

        # Fallback to any available video if target video not found
        if not os.path.exists(resolved):
            vids = list_available_videos(upload_dir=UPLOAD_DIR, project_dir=BASE_DIR)
            if vids:
                resolved = vids[0]["path"]

        self.cap = cv2.VideoCapture(resolved)
        if self.cap.isOpened():
            self.video_path = resolved
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.current_frame_idx = 0
            print(f"🎬 Successfully loaded video: {resolved} (FPS: {self.fps}, Frames: {self.total_frames})")
        else:
            print(f"❌ Could not open video: {resolved}")


    def update_config(self, cfg: Dict[str, Any]):
        if "model_name" in cfg and cfg["model_name"] != self.engine.model_name:
            self.engine.load_model(cfg["model_name"])
        if "conf_threshold" in cfg:
            self.conf_threshold = float(cfg["conf_threshold"])
            self.engine.detector.set_confidence(self.conf_threshold)
        if "line_y_ratio" in cfg:
            self.line_y_ratio = float(cfg["line_y_ratio"])
        if "mid_x_ratio" in cfg:
            self.mid_x_ratio = float(cfg["mid_x_ratio"])
        if "swap_directions" in cfg:
            self.swap_directions = bool(cfg["swap_directions"])
        if "target_classes" in cfg:
            self.target_classes = cfg["target_classes"]
            self.engine.update_target_classes(self.target_classes)

    def close(self):
        self.is_playing = False
        if self.cap is not None:
            self.cap.release()

@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = StreamSession(websocket)

    async def stream_loop():
        while True:
            try:
                if not session.is_playing or session.is_paused:
                    await asyncio.sleep(0.05)
                    continue

                if session.cap is None or not session.cap.isOpened():
                    session.is_playing = False
                    await websocket.send_json({"type": "status", "playing": False, "ended": True})
                    await asyncio.sleep(0.1)
                    continue

                success, frame = session.cap.read()
                if not success:
                    # Video ended -> loop video
                    session.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    session.current_frame_idx = 0
                    success, frame = session.cap.read()
                    if not success:
                        session.is_playing = False
                        await websocket.send_json({"type": "status", "playing": False, "ended": True})
                        await asyncio.sleep(0.1)
                        continue

                session.current_frame_idx += 1

                # Resize frame to optimal 960px width for silky-smooth web streaming & low CPU load
                h, w = frame.shape[:2]
                target_w = 960
                if w != target_w:
                    scale = target_w / float(w)
                    frame = cv2.resize(frame, (target_w, int(h * scale)), interpolation=cv2.INTER_LINEAR)

                # Run AI Pipeline with optimized 480px inference size
                annotated_frame, telemetry = session.engine.process_frame(
                    frame=frame,
                    frame_idx=session.current_frame_idx,
                    fps=session.fps,
                    start_datetime=session.start_dt,
                    line_y_ratio=session.line_y_ratio,
                    mid_x_ratio=session.mid_x_ratio,
                    swap_directions=session.swap_directions,
                    img_size=480
                )

                # Turbo JPEG Encoding (quality 60 is sharp & transfers in <2ms)
                _, buffer = cv2.imencode(".jpg", annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                b64_frame = base64.b64encode(buffer).decode("utf-8")

                # Send full packet
                await websocket.send_json({
                    "type": "frame",
                    "image": b64_frame,
                    "telemetry": telemetry
                })

                # Minimal sleep to prevent event loop starvation
                await asyncio.sleep(0.001)


            except Exception as e:
                print(f"⚠️ Error in stream_loop: {e}")
                await asyncio.sleep(0.05)

    stream_task = asyncio.create_task(stream_loop())


    try:
        while True:
            raw_msg = await websocket.receive_text()
            data = json.loads(raw_msg)
            cmd = data.get("command")

            if cmd == "start":
                session.update_config(data)
                vid = data.get("video_path", "KUSRC_Traffic.mov")
                session.load_video(vid)
                session.engine.reset_state()
                session.is_playing = True
                session.is_paused = False
                await websocket.send_json({"type": "status", "playing": True})

            elif cmd == "pause":
                session.is_paused = True
                await websocket.send_json({"type": "status", "playing": False})

            elif cmd == "resume":
                session.is_paused = False
                await websocket.send_json({"type": "status", "playing": True})

            elif cmd == "reset":
                session.engine.reset_state()
                if session.cap is not None:
                    session.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    session.current_frame_idx = 0
                await websocket.send_json({"type": "status", "reset": True})

            elif cmd == "update_config":
                session.update_config(data)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        session.close()
        stream_task.cancel()

if __name__ == "__main__":
    print("🚀 Starting KU SRC Smart Traffic Server on http://localhost:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

