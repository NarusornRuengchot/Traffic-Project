import os
from typing import List, Dict, Any, Tuple

SUPPORTED_VIDEO_EXTENSIONS = (
    ".mov", ".mp4", ".avi", ".mkv", ".webm",
    ".m4v", ".wmv", ".flv", ".ts", ".3gp"
)

def resolve_model_path(model_name: str, search_dirs: List[str] = None) -> str:
    """Finds the model file in current dir or search dirs, checking fallback naming variants."""
    if search_dirs is None:
        search_dirs = [".", "models"]

    # Check direct path first
    if os.path.exists(model_name):
        return model_name

    candidates = [model_name]
    if "yolov11" in model_name:
        candidates.append(model_name.replace("yolov11", "yolo11"))
    elif "yolo11" in model_name:
        candidates.append(model_name.replace("yolo11", "yolov11"))

    if "yolov8" in model_name:
        candidates.append(model_name.replace("yolov8", "yolo8"))
    elif "yolo8" in model_name:
        candidates.append(model_name.replace("yolo8", "yolov8"))

    for directory in search_dirs:
        for cand in candidates:
            target = os.path.join(directory, cand) if directory != "." else cand
            if os.path.exists(target):
                return target

    # Fallback to any existing .pt file
    for directory in search_dirs:
        if os.path.exists(directory):
            for f in os.listdir(directory):
                if f.endswith(".pt"):
                    return os.path.join(directory, f) if directory != "." else f

    return model_name

def list_available_models(search_dirs: List[str] = None) -> List[Dict[str, Any]]:
    """Scans directories for YOLO model weights."""
    if search_dirs is None:
        search_dirs = [".", "models"]

    models = []
    seen = set()

    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
        for f in sorted(os.listdir(directory)):
            if f.endswith(".pt") and f not in seen:
                seen.add(f)
                is_finetuned = "best" in f.lower() or "custom" in f.lower()
                label = f"🎯 Fine-Tuned Model ({f})" if is_finetuned else f"⚡ YOLO Model: {f}"
                models.append({
                    "name": f,
                    "label": label,
                    "path": os.path.join(directory, f) if directory != "." else f,
                    "type": "finetuned" if is_finetuned else "standard"
                })

    return models

def resolve_video_source(source_path: str, upload_dir: str = "uploads", base_dir: str = ".") -> str:
    """Resolves a video source, handling live webcam, RTSP/HTTP streams, and local files."""
    if not source_path:
        return ""

    # Live Webcam: "webcam:0", "webcam:1", "0", "1"
    if str(source_path).startswith("webcam:") or str(source_path).isdigit():
        return str(source_path)

    # Live RTSP / HTTP Camera Stream
    if str(source_path).startswith(("rtsp://", "http://", "https://")):
        return str(source_path)

    # Check direct file path
    if os.path.exists(source_path):
        return source_path

    # Check project base dir
    cand_base = os.path.join(base_dir, source_path)
    if os.path.exists(cand_base):
        return cand_base

    # Check uploads directory
    cand_up = os.path.join(upload_dir, os.path.basename(source_path))
    if os.path.exists(cand_up):
        return cand_up

    return source_path

def list_available_videos(upload_dir: str = "uploads", project_dir: str = ".") -> List[Dict[str, Any]]:
    """Scans and returns all available videos and real-time live sources (webcam, RTSP)."""
    videos = []
    seen_paths = set()

    # 1. Real-time Live Sources (Webcam & IP Camera)
    videos.append({
        "id": "webcam:0",
        "name": "🔴 📷 Live Webcam (Camera 0 - Real-time)",
        "path": "webcam:0",
        "type": "live"
    })
    videos.append({
        "id": "rtsp_stream",
        "name": "🔴 🌐 Live RTSP / IP Camera (CCTV Stream)",
        "path": "rtsp_stream",
        "type": "live"
    })

    # 2. Project directory sample and local videos
    if os.path.exists(project_dir):
        for f in sorted(os.listdir(project_dir)):
            if os.path.isfile(f) and f.lower().endswith(SUPPORTED_VIDEO_EXTENSIONS):
                abs_p = os.path.abspath(f)
                if abs_p not in seen_paths:
                    is_sample = "kusrc" in f.lower()
                    label = f"🚗 KU SRC Sample Video ({f})" if is_sample else f"📹 Project Video: {f}"
                    videos.append({
                        "id": f,
                        "name": label,
                        "path": f,
                        "type": "sample" if is_sample else "local"
                    })
                    seen_paths.add(abs_p)

    # 3. Uploaded directory
    if os.path.exists(upload_dir):
        for f in sorted(os.listdir(upload_dir)):
            full_path = os.path.join(upload_dir, f)
            if os.path.isfile(full_path) and f.lower().endswith(SUPPORTED_VIDEO_EXTENSIONS):
                abs_p = os.path.abspath(full_path)
                if abs_p not in seen_paths:
                    videos.append({
                        "id": f,
                        "name": f"📁 Uploaded: {f}",
                        "path": full_path,
                        "type": "uploaded"
                    })
                    seen_paths.add(abs_p)

    return videos
