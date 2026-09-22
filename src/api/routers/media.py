import base64
import datetime
import os
import shutil
import time
from typing import Dict, Any

import cv2
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Response

from src.config.settings import settings
from src.api.state import app_state
from src.core.traffic_pipeline import TrafficPipeline
from src.utils.file_helper import list_available_videos

router = APIRouter(tags=["Media & Calibration"])

@router.get("/api/models")
async def get_models():
    """Returns available YOLO models, computing devices, and currently active model."""
    worker = app_state.get_worker()
    current_model = worker.engine.model_name if worker else app_state.global_engine.model_name
    return {
        "models": TrafficPipeline.get_available_models(),
        "devices": TrafficPipeline.get_available_devices(),
        "current_model": current_model
    }

@router.get("/api/videos")
async def get_videos():
    """Returns list of all available videos in project and uploads directory."""
    return {"videos": list_available_videos(upload_dir=settings.UPLOAD_DIR, project_dir=settings.BASE_DIR)}

@router.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Uploads a video file to the server for analysis."""
    filename = file.filename or f"uploaded_{int(time.time())}.mp4"
    clean_name = os.path.basename(filename)
    dest_path = os.path.join(settings.UPLOAD_DIR, clean_name)

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

@router.get("/api/calibration/preview")
async def get_calibration_preview(
    video_path: str = Query(..., description="Path to video file"),
    line_y_ratio: float = Query(0.50),
    mid_x_ratio: float = Query(0.45),
    swap_directions: bool = Query(False)
):
    """Generates a tripwire calibration preview overlay for the first frame of a video."""
    resolved = app_state.resolve_video_path(video_path)
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

@router.get("/api/export")
async def export_data(format: str = Query("csv")):
    """Exports current session crossing telemetry as CSV or summary."""
    worker = app_state.get_worker()
    target_engine = worker.engine if (worker and worker.engine.events_log) else app_state.global_engine

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
