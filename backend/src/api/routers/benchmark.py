import os
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Body, HTTPException

from src.services.benchmark_service import run_cctv_model_benchmark, MODEL_METADATA
from src.utils.file_helper import list_available_models, list_available_videos

router = APIRouter(prefix="/api/benchmark", tags=["Model Benchmark & CCTV Comparison"])

@router.get("/presets")
async def get_benchmark_presets():
    """
    Returns available CCTV/video sources and model options for benchmarking.
    """
    videos = list_available_videos()
    models = list_available_models()

    cctv_presets = [
        {
            "id": "kusrc_cctv",
            "name": "🏫 KUSRC Campus CCTV (จำลองกล้องวงจรปิด มก.ศรีราชา)",
            "path": "IMG_1357.MOV",
            "type": "cctv_sim",
            "description": "ภาพการจราจรจริงถนนหน้ามหาวิทยาลัยเกษตรศาสตร์ ศรีราชา"
        },
        {
            "id": "webcam",
            "name": "💻 Local Webcam (webcam:0)",
            "path": "webcam:0",
            "type": "webcam",
            "description": "กล้องเว็บแคมเชื่อมต่อตรงกับเครื่องคอมพิวเตอร์"
        },
        {
            "id": "custom_rtsp",
            "name": "🌐 Custom RTSP / IP Camera Stream",
            "path": "rtsp://",
            "type": "rtsp",
            "description": "ระบุ URL สตรีมกล้องวงจรปิด RTSP / HLS จริงของคุณ"
        }
    ]

    return {
        "presets": cctv_presets,
        "available_videos": videos,
        "available_models": models,
        "model_metadata": MODEL_METADATA
    }


@router.post("/compare")
async def compare_models_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Executes a comprehensive accuracy and latency benchmark across specified models
    on frames from the given CCTV stream or video file.
    """
    video_source = payload.get("video_source", "IMG_1357.MOV")
    models = payload.get("models", ["best.pt", "yolo26s.pt", "yolo26n.pt", "yolov11n.pt"])
    sample_frames = int(payload.get("sample_frames", 10))
    sample_frames = max(3, min(30, sample_frames))
    conf_threshold = float(payload.get("conf_threshold", 0.18))
    img_size = int(payload.get("img_size", 480))

    try:
        benchmark_data = run_cctv_model_benchmark(
            video_source=video_source,
            models=models,
            sample_frames=sample_frames,
            conf_threshold=conf_threshold,
            img_size=img_size
        )
        return benchmark_data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการรัน Benchmark: {str(e)}")
