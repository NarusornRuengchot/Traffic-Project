"""
Benchmark Service for CCTV and Video Model Accuracy & Performance Evaluation.
Evaluates and compares YOLO models on identical CCTV/video frames:
- Mean Detection Confidence (%)
- Inference Latency (ms) and Effective FPS
- Detection Volume & Class Breakdown (Car, Motorcycle, Bus, Truck)
- Side-by-Side Annotated Visual Previews
"""
import os
import time
import base64
from typing import Dict, List, Tuple, Optional, Any
import cv2
import numpy as np

from src.core.vehicle_detector import VehicleDetector
from src.utils.file_helper import resolve_model_path, resolve_video_source
from src.config.settings import settings

MODEL_METADATA: Dict[str, Dict[str, str]] = {
    "best.pt": {
        "title": "Custom Traffic AI (Vehicle Specialized)",
        "tag": "🏆 Highest Precision",
        "description": "โมเดลที่ผ่านการเทรนเฉพาะทางสำหรับถนนไทย คัดกรองแม่นยำพิเศษ",
        "architecture": "YOLO Custom"
    },
    "best_finetuned_50f.pt": {
        "title": "Fine-Tuned 50 Frames",
        "tag": "🎯 Targeted Fine-Tuning",
        "description": "โมเดล Fine-tuned ด้วยชุดข้อมูลตัวอย่าง 50 เฟรม",
        "architecture": "YOLO Fine-Tuned"
    },
    "yolo26s.pt": {
        "title": "YOLO26 Small",
        "tag": "⚡ Next-Gen Balanced",
        "description": "สถาปัตยกรรม YOLO26 โมเดลขนาดเล็กที่มีความสมดุลสูง",
        "architecture": "YOLO26 Small"
    },
    "yolo26n.pt": {
        "title": "YOLO26 Nano",
        "tag": "🚀 Ultra-Fast Edge",
        "description": "สถาปัตยกรรม YOLO26 ขนาดกะทัดรัด ประมวลผลเร็วที่สุด",
        "architecture": "YOLO26 Nano"
    },
    "yolov11n.pt": {
        "title": "YOLO11 Nano",
        "tag": "📊 Baseline Reference",
        "description": "โมเดลมาตรฐาน COCO Baseline สำหรับเปรียบเทียบ",
        "architecture": "YOLO11 Nano"
    }
}

CLASS_COLORS = {
    "Car": (249, 115, 22),       # Orange
    "Motorcycle": (59, 130, 246), # Blue
    "Bus": (168, 85, 247),       # Purple
    "Truck": (234, 179, 8)       # Yellow
}

def capture_benchmark_frames(video_source: str, sample_count: int = 12) -> Tuple[List[np.ndarray], Dict[str, Any]]:
    """
    Captures a set of frames from CCTV, webcam, or video file for comparative benchmarking.
    """
    resolved = resolve_video_source(video_source)
    is_live = (
        resolved.startswith("webcam:")
        or resolved.isdigit()
        or resolved.startswith(("rtsp://", "http://", "https://"))
    )

    if resolved.startswith("webcam:") or resolved.isdigit():
        cam_idx = int(resolved.replace("webcam:", ""))
        cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(cam_idx)
    elif is_live:
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        cap = cv2.VideoCapture(
            resolved,
            cv2.CAP_FFMPEG,
            [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, settings.CCTV_TIMEOUT_MS, cv2.CAP_PROP_READ_TIMEOUT_MSEC, settings.CCTV_TIMEOUT_MS]
        )
    else:
        cap = cv2.VideoCapture(resolved)

    if not cap or not cap.isOpened():
        raise ValueError(f"ไม่สามารถเปิดการเชื่อมต่อวิดีโอหรือกล้อง CCTV ({video_source}) ได้ กรุณาตรวจสอบ URL หรือไฟล์วิดีโอ")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

    frames: List[np.ndarray] = []
    
    current_pos = min(30, total_frames // 4) if (not is_live and total_frames > 60) else 0
    if not is_live and current_pos > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

    step = 10 if not is_live else 1
    attempts = 0
    max_attempts = sample_count * 5

    while len(frames) < sample_count and attempts < max_attempts:
        ret, frame = cap.read()
        attempts += 1
        if not ret or frame is None:
            break

        # Resize if large (>960px) to maintain fair and efficient benchmark
        h, w = frame.shape[:2]
        if w > 960:
            scale = 960.0 / w
            frame = cv2.resize(frame, (960, int(h * scale)))

        frames.append(frame)

        if not is_live and step > 1:
            current_pos += step
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

    cap.release()

    if not frames:
        raise ValueError(f"ไม่สามารถอ่านเฟรมภาพจากกล้อง CCTV หรือวิดีโอ ({video_source}) ได้")

    meta = {
        "source": video_source,
        "is_live": is_live,
        "width": width,
        "height": height,
        "fps": round(float(fps), 1),
        "sampled_frames": len(frames)
    }
    return frames, meta


def annotate_preview_frame(frame: np.ndarray, boxes_xyxy: np.ndarray, confs: List[float], class_names: List[str], model_name: str, inference_ms: float) -> str:
    """
    Draws professional bounding boxes and HUD watermark on the frame, returns Base64 JPEG.
    """
    vis = frame.copy()
    h, w = vis.shape[:2]

    # Draw bounding boxes
    for box, conf, cname in zip(boxes_xyxy, confs, class_names):
        x1, y1, x2, y2 = map(int, box)
        color = CLASS_COLORS.get(cname, (16, 185, 129)) # BGR
        # OpenCV uses BGR
        bgr_color = (int(color[2]), int(color[1]), int(color[0]))

        # Box
        cv2.rectangle(vis, (x1, y1), (x2, y2), bgr_color, 2)

        # Label tag
        label = f"{cname} {int(conf * 100)}%"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        tag_y1 = max(0, y1 - th - 6)
        cv2.rectangle(vis, (x1, tag_y1), (x1 + tw + 8, tag_y1 + th + 6), bgr_color, -1)
        cv2.putText(vis, label, (x1 + 4, tag_y1 + th + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    # Top-right watermark HUD
    hud_text = f"{model_name} | {len(boxes_xyxy)} vehicles | {inference_ms:.1f}ms"
    (htw, hth), _ = cv2.getTextSize(hud_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    hud_x1 = w - htw - 20
    hud_y1 = 12
    cv2.rectangle(vis, (hud_x1 - 6, hud_y1 - 4), (w - 10, hud_y1 + hth + 8), (20, 24, 33), -1)
    cv2.rectangle(vis, (hud_x1 - 6, hud_y1 - 4), (w - 10, hud_y1 + hth + 8), (59, 130, 246), 1)
    cv2.putText(vis, hud_text, (hud_x1, hud_y1 + hth + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    # Encode to JPEG Base64
    _, buf = cv2.imencode(".jpg", vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode("utf-8")


def run_cctv_model_benchmark(
    video_source: str,
    models: Optional[List[str]] = None,
    sample_frames: int = 12,
    conf_threshold: float = 0.18,
    img_size: int = 480
) -> Dict[str, Any]:
    """
    Executes comparative accuracy and latency benchmark across specified models on identical CCTV frames.
    """
    available_model_files = [
        f for f in os.listdir("models") if f.endswith(".pt")
    ] if os.path.exists("models") else ["best.pt", "yolo26s.pt", "yolo26n.pt", "yolov11n.pt"]

    # Filter or default models
    if not models:
        models = ["best.pt", "yolo26s.pt", "yolo26n.pt", "yolov11n.pt"]
    
    # Filter to existing models
    valid_models = []
    for m in models:
        base_name = os.path.basename(m)
        resolved = resolve_model_path(base_name)
        if os.path.exists(resolved):
            valid_models.append(base_name)

    if not valid_models:
        valid_models = ["best.pt"]

    # 1. Capture identical frames from CCTV/Stream
    frames, source_meta = capture_benchmark_frames(video_source, sample_count=sample_frames)
    num_frames = len(frames)

    # Pick representative frame index (middle of sample)
    rep_frame_idx = num_frames // 2
    rep_frame = frames[rep_frame_idx]

    benchmark_results: List[Dict[str, Any]] = []

    for model_name in valid_models:
        try:
            detector = VehicleDetector(
                model_name=model_name,
                conf_threshold=conf_threshold,
                img_size=img_size,
                device="cpu"
            )
            # Warm up
            detector.warmup(img_size)

            total_inference_time = 0.0
            all_confidences: List[float] = []
            class_counts: Dict[str, int] = {"Car": 0, "Motorcycle": 0, "Bus": 0, "Truck": 0}
            class_conf_sums: Dict[str, float] = {"Car": 0.0, "Motorcycle": 0.0, "Bus": 0.0, "Truck": 0.0}

            rep_boxes = np.empty((0, 4))
            rep_confs = []
            rep_classes = []
            rep_ms = 0.0

            for idx, frame in enumerate(frames):
                t0 = time.perf_counter()
                results = detector.model(
                    frame,
                    imgsz=img_size,
                    classes=detector.target_class_ids,
                    device=detector.device,
                    conf=conf_threshold,
                    verbose=False
                )
                t1 = time.perf_counter()
                infer_ms = (t1 - t0) * 1000.0
                total_inference_time += infer_ms

                if results and len(results) > 0 and results[0].boxes is not None and len(results[0].boxes) > 0:
                    boxes = results[0].boxes
                    confs = boxes.conf.cpu().numpy().tolist()
                    classes = boxes.cls.int().cpu().numpy().tolist()
                    xyxy = boxes.xyxy.cpu().numpy()

                    all_confidences.extend(confs)

                    for c_id, conf in zip(classes, confs):
                        c_name = detector.id_to_name.get(c_id, "Vehicle")
                        if c_name in class_counts:
                            class_counts[c_name] += 1
                            class_conf_sums[c_name] += conf

                    if idx == rep_frame_idx:
                        rep_boxes = xyxy
                        rep_confs = confs
                        rep_classes = [detector.id_to_name.get(c, "Vehicle") for c in classes]
                        rep_ms = infer_ms

            avg_infer_ms = total_inference_time / max(1, num_frames)
            effective_fps = 1000.0 / avg_infer_ms if avg_infer_ms > 0 else 0.0
            total_detections = len(all_confidences)
            mean_conf = float(np.mean(all_confidences) * 100.0) if all_confidences else 0.0
            high_conf_count = sum(1 for c in all_confidences if c >= 0.60)
            high_conf_ratio = (high_conf_count / total_detections * 100.0) if total_detections > 0 else 0.0

            # Class breakdown
            class_breakdown = {}
            for c_name in ["Car", "Motorcycle", "Bus", "Truck"]:
                cnt = class_counts[c_name]
                c_mean = (class_conf_sums[c_name] / cnt * 100.0) if cnt > 0 else 0.0
                class_breakdown[c_name] = {
                    "count": cnt,
                    "avg_per_frame": round(cnt / max(1, num_frames), 1),
                    "mean_confidence": round(c_mean, 1)
                }

            # Generate annotated preview thumbnail
            preview_base64 = annotate_preview_frame(
                rep_frame,
                rep_boxes,
                rep_confs,
                rep_classes,
                model_name,
                rep_ms
            )

            # Model metadata
            meta = MODEL_METADATA.get(model_name, {
                "title": model_name,
                "tag": "Custom Model",
                "description": "โมเดลตรวจจับการจราจร",
                "architecture": "YOLO"
            })

            model_file_path = resolve_model_path(model_name)
            file_size_mb = round(os.path.getsize(model_file_path) / (1024 * 1024), 1) if os.path.exists(model_file_path) else 0.0

            benchmark_results.append({
                "model_name": model_name,
                "title": meta["title"],
                "tag": meta["tag"],
                "description": meta["description"],
                "architecture": meta["architecture"],
                "file_size_mb": file_size_mb,
                "mean_confidence": round(mean_conf, 1),
                "total_detections": total_detections,
                "avg_detections_per_frame": round(total_detections / max(1, num_frames), 1),
                "avg_inference_ms": round(avg_infer_ms, 1),
                "fps": round(effective_fps, 1),
                "high_conf_ratio": round(high_conf_ratio, 1),
                "class_breakdown": class_breakdown,
                "annotated_preview": preview_base64
            })

        except Exception as e:
            print(f"⚠️ Error benchmarking model {model_name}: {e}")
            benchmark_results.append({
                "model_name": model_name,
                "title": model_name,
                "error": str(e)
            })

    # Filter successful benchmarks
    success_results = [r for r in benchmark_results if "error" not in r]

    # Calculate Winners
    accuracy_winner = max(success_results, key=lambda x: x["mean_confidence"])["model_name"] if success_results else ""
    speed_winner = max(success_results, key=lambda x: x["fps"])["model_name"] if success_results else ""
    motorcycle_winner = max(
        success_results,
        key=lambda x: (x["class_breakdown"]["Motorcycle"]["count"], x["class_breakdown"]["Motorcycle"]["mean_confidence"])
    )["model_name"] if success_results else ""

    # Balanced recommendation
    # Balance score = (Mean Confidence * 0.5) + (min(100, FPS) * 0.5)
    def balance_score(res):
        return (res["mean_confidence"] * 0.6) + (min(100.0, res["fps"]) * 0.4)

    recommended_model = max(success_results, key=balance_score)["model_name"] if success_results else ""

    return {
        "status": "success",
        "video_source": video_source,
        "source_metadata": source_meta,
        "tested_models_count": len(valid_models),
        "results": benchmark_results,
        "winners": {
            "accuracy_winner": accuracy_winner,
            "speed_winner": speed_winner,
            "motorcycle_winner": motorcycle_winner,
            "recommended_model": recommended_model
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
