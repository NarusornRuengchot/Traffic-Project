import asyncio
import base64
import json
import os
import time
import cv2
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.state import app_state
from src.config.settings import settings
from src.core.traffic_pipeline import TrafficPipeline
from src.services.stream_worker import StreamWorker

router = APIRouter(tags=["WebSocket Stream"])

@router.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    """
    Decoupled Real-Time WebSocket Streaming Endpoint.
    Streams AI-annotated frames and live vehicle telemetry to the React client.
    """
    await websocket.accept()

    worker = StreamWorker(
        engine=TrafficPipeline(
            model_name=settings.DEFAULT_MODEL,
            device=settings.DEFAULT_DEVICE
        ),
        target_width=settings.DEFAULT_STREAM_WIDTH,
        inference_size=settings.DEFAULT_INFERENCE_SIZE,
        jpeg_quality=settings.DEFAULT_JPEG_QUALITY
    )
    app_state.set_worker(worker)

    async def frame_sender_loop():
        """Reads encoded frames from worker's bounded queue without blocking the asyncio loop."""
        while True:
            try:
                try:
                    packet = worker.frame_queue.get_nowait()
                except Exception:
                    await asyncio.sleep(0.01)
                    continue

                await websocket.send_json(packet)
            except WebSocketDisconnect:
                break
            except Exception:
                break

    sender_task = asyncio.create_task(frame_sender_loop())

    from src.utils.file_helper import list_available_videos
    # Push initial status and full resources directly over WebSocket
    # Eliminates the need for frontend to spam HTTP GET /api/models and /api/videos
    await websocket.send_json({
        "type": "init_resources",
        "models": TrafficPipeline.get_available_models(),
        "videos": list_available_videos(upload_dir=settings.UPLOAD_DIR, project_dir=settings.BASE_DIR),
        "devices": TrafficPipeline.get_available_devices(),
        "current_model": worker.engine.model_name,
        "default_model": settings.DEFAULT_MODEL
    })

    try:
        while True:
            raw_msg = await websocket.receive_text()
            data = json.loads(raw_msg)
            cmd = data.get("command")

            if cmd == "ping":
                await websocket.send_json({"type": "pong", "time": time.time()})

            elif cmd == "get_resources":
                await websocket.send_json({
                    "type": "init_resources",
                    "models": TrafficPipeline.get_available_models(),
                    "videos": list_available_videos(upload_dir=settings.UPLOAD_DIR, project_dir=settings.BASE_DIR),
                    "devices": TrafficPipeline.get_available_devices(),
                    "current_model": worker.engine.model_name,
                    "default_model": settings.DEFAULT_MODEL
                })

            elif cmd == "switch_model":
                new_model = data.get("model_name")
                if new_model:
                    await websocket.send_json({
                        "type": "model_status",
                        "status": "loading",
                        "model": new_model
                    })
                    try:
                        worker.engine.load_model(new_model)
                        await websocket.send_json({
                            "type": "model_status",
                            "status": "ready",
                            "model": worker.engine.model_name
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "model_status",
                            "status": "error",
                            "model": new_model,
                            "error": str(e)
                        })

            elif cmd == "start":
                worker.update_config(data)
                vid_path = data.get("video_path", "KUSRC_Traffic.mov")
                resolved_vid = app_state.resolve_video_path(vid_path)

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
                resolved = app_state.resolve_video_path(test_url)
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
                        [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, settings.CCTV_TIMEOUT_MS, cv2.CAP_PROP_READ_TIMEOUT_MSEC, settings.CCTV_TIMEOUT_MS]
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
                vid_path = data.get("video_path", "KUSRC_Traffic.mov")
                resolved_vid = app_state.resolve_video_path(vid_path)
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
        if app_state.get_worker() is worker:
            app_state.set_worker(None)
