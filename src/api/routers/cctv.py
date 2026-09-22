import os
from typing import Dict, Any
import cv2
from fastapi import APIRouter, Body
from src.api.state import app_state
from src.config.settings import settings

router = APIRouter(prefix="/api/cctv", tags=["CCTV & Live Streams"])

@router.post("/test")
async def test_cctv_endpoint(data: Dict[str, Any] = Body(...)):
    """Tests CCTV/RTSP connection with a fast timeout and returns connection status."""
    url = data.get("url", "").strip()
    if not url or url == "rtsp_stream":
        return {"success": False, "message": "กรุณาระบุ URL กล้องวงจรปิด (เช่น rtsp://admin:pass@192.168.1.100:554/stream1)"}

    resolved = app_state.resolve_video_path(url)
    if resolved.startswith("webcam:"):
        cam_idx = int(resolved.replace("webcam:", ""))
        cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(cam_idx)
    else:
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        cap = cv2.VideoCapture(
            resolved,
            cv2.CAP_FFMPEG,
            [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, settings.CCTV_TIMEOUT_MS, cv2.CAP_PROP_READ_TIMEOUT_MSEC, settings.CCTV_TIMEOUT_MS]
        )

    if not cap or not cap.isOpened():
        return {
            "success": False,
            "message": "❌ ไม่สามารถเชื่อมต่อกล้องได้: กล้องไม่ตอบสนอง กรุณาตรวจสอบ IP, Port, และรหัสผ่าน"
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
