import cv2
import os
import datetime
import numpy as np
import pandas as pd
import torch
from typing import Dict, List, Tuple, Optional, Any, Set
from ultralytics import YOLO

def resolve_model_path(model_name: str) -> str:
    """Find the exact model file or fallback variations."""
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

    # Search in root and models folder
    for directory in [".", "models"]:
        for cand in candidates:
            target = os.path.join(directory, cand) if directory != "." else cand
            if os.path.exists(target):
                return target

    # Fallback to any available .pt file
    for directory in [".", "models"]:
        if os.path.exists(directory):
            for f in os.listdir(directory):
                if f.endswith(".pt"):
                    return os.path.join(directory, f) if directory != "." else f

    return model_name


def get_traffic_level(density: float, stall_ratio: float = 0.0) -> Tuple[str, str, str]:
    """
    Evaluates traffic congestion level based on vehicle density and stall ratio.
    Returns: (Thai description, Emoji, English level name)
    """
    score = density * (1.0 + 0.2 * stall_ratio)

    if score <= 5.0:
        return "Smooth (คล่องตัว)", "🟢", "Smooth"
    elif score <= 12.0:
        return "Moderate (ปานกลาง)", "🟡", "Moderate"
    elif score <= 20.0:
        return "Congested (หนาแน่น)", "🟠", "Congested"
    else:
        return "Gridlock (หนาแน่นมาก)", "🔴", "Gridlock"


class AITrafficEngine:
    def __init__(
        self,
        model_name: str = "best.pt",
        conf_threshold: float = 0.25,
        img_size: int = 640,
        device: str = "cpu"
    ):
        self.conf_threshold: float = conf_threshold
        self.img_size: int = img_size
        self.device: str = device if (device != "cuda" or torch.cuda.is_available()) else "cpu"
        self.model_name: str = ""
        self.model: YOLO = None  # type: ignore
        self.class_map: Dict[str, int] = {}
        self.id_to_name: Dict[int, str] = {}
        self.selected_target_classes: List[str] = ["Car", "Motorcycle", "Bus", "Truck"]
        self.target_class_ids: List[int] = []

        # State tracking
        self.inbound_count: int = 0
        self.outbound_count: int = 0
        self.counted_ids: Set[int] = set()
        self.track_history: Dict[int, Tuple[int, int]] = {}
        self.prev_positions: Dict[int, Tuple[int, int]] = {}
        self.active_history: List[int] = []
        self.inbound_active_history: List[int] = []
        self.outbound_active_history: List[int] = []
        self.class_counts: Dict[str, int] = {"Car": 0, "Motorcycle": 0, "Bus": 0, "Truck": 0}
        self.events_log: List[Dict[str, Any]] = []
        self.flow_history: List[Dict[str, Any]] = []
        self.window_size: int = 30

        self.load_model(model_name)

    def load_model(self, model_name: str):
        """Loads a YOLO model weights file and dynamically initializes class maps from model metadata."""
        resolved = resolve_model_path(model_name)
        if not os.path.exists(resolved):
            fallback = "yolov11n.pt" if os.path.exists("yolov11n.pt") else "yolov8n.pt"
            if os.path.exists(fallback):
                resolved = fallback
            else:
                resolved = model_name

        self.model_name = os.path.basename(resolved)
        self.model = YOLO(resolved)

        # Dynamically inspect model.names from the loaded weights
        self.class_map = {}
        self.id_to_name = {}

        model_names = getattr(self.model, "names", None)
        if isinstance(model_names, dict):
            for cid, cname in model_names.items():
                name_clean = str(cname).strip().capitalize()
                # Normalize vehicle category names
                if name_clean.lower() in ["car", "automobile", "sedan", "suv", "van"]:
                    std_name = "Car"
                elif name_clean.lower() in ["motorcycle", "motorbike", "bike"]:
                    std_name = "Motorcycle"
                elif name_clean.lower() in ["bus"]:
                    std_name = "Bus"
                elif name_clean.lower() in ["truck"]:
                    std_name = "Truck"
                else:
                    std_name = name_clean

                self.id_to_name[int(cid)] = std_name
                self.class_map[std_name] = int(cid)

        # Fallback if names dict was incomplete
        if not self.class_map:
            if "best.pt" in self.model_name:
                self.class_map = {"Car": 0, "Motorcycle": 1, "Bus": 2, "Truck": 3}
                self.id_to_name = {0: "Car", 1: "Motorcycle", 2: "Bus", 3: "Truck"}
            else:
                self.class_map = {"Car": 2, "Motorcycle": 3, "Bus": 5, "Truck": 7}
                self.id_to_name = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}

        self.update_target_classes(self.selected_target_classes)

    def update_target_classes(self, classes_list: List[str]):
        """Updates which classes should be tracked and counted."""
        self.selected_target_classes = classes_list
        self.target_class_ids = [self.class_map[c] for c in classes_list if c in self.class_map]

    def reset_state(self):
        """Resets all counting and history counters for a fresh analysis run."""
        self.inbound_count = 0
        self.outbound_count = 0
        self.counted_ids.clear()
        self.track_history.clear()
        self.prev_positions.clear()
        self.active_history.clear()
        self.inbound_active_history.clear()
        self.outbound_active_history.clear()
        self.class_counts = {c: 0 for c in ["Car", "Motorcycle", "Bus", "Truck"]}
        self.events_log.clear()
        self.flow_history.clear()

    @staticmethod
    def get_available_models() -> List[Dict[str, Any]]:
        """Scans directory for available YOLO model files."""
        models = []
        seen = set()
        for directory in [".", "models"]:
            if not os.path.exists(directory):
                continue
            for f in sorted(os.listdir(directory)):
                if f.endswith(".pt") and f not in seen:
                    seen.add(f)
                    is_best = "best" in f.lower() or "custom" in f.lower()
                    label = f"🎯 Fine-Tuned Model ({f})" if is_best else f"⚡ YOLO Model: {f}"
                    models.append({
                        "name": f,
                        "label": label,
                        "path": os.path.join(directory, f) if directory != "." else f,
                        "type": "finetuned" if is_best else "standard"
                    })
        return models

    @staticmethod
    def get_available_devices() -> List[str]:
        """Returns available compute devices (CPU/CUDA)."""
        devices = ["cpu"]
        if torch.cuda.is_available():
            devices.insert(0, "cuda")
        return devices

    @staticmethod
    def get_video_info(video_path: str) -> Optional[Dict[str, Any]]:
        """Reads video metadata and returns dimensions, fps, and first frame."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        success, frame = cap.read()
        cap.release()

        if success:
            return {
                "width": width,
                "height": height,
                "fps": fps if fps > 0 else 30.0,
                "total_frames": total_frames,
                "first_frame": frame
            }
        return None

    @staticmethod
    def generate_calibration_preview(
        first_frame: np.ndarray,
        line_y_ratio: float = 0.50,
        mid_x_ratio: float = 0.45,
        swap_directions: bool = False
    ) -> np.ndarray:
        """Draws calibration lines and labels on the preview frame."""
        preview = first_frame.copy()
        height, width = preview.shape[:2]
        line_y = int(height * line_y_ratio)
        mid_x = int(width * mid_x_ratio)

        inbound_start, inbound_end = (0, line_y), (mid_x, line_y)
        outbound_start, outbound_end = (mid_x, line_y), (width, line_y)

        cv2.line(preview, inbound_start, inbound_end, (255, 255, 0), 4)      # Left: Cyan
        cv2.line(preview, outbound_start, outbound_end, (0, 165, 255), 4)   # Right: Orange
        cv2.circle(preview, (mid_x, line_y), 10, (0, 0, 255), -1)           # Divider: Red dot

        left_label = "Outbound Lane" if swap_directions else "Inbound Lane"
        right_label = "Inbound Lane" if swap_directions else "Outbound Lane"

        cv2.putText(preview, left_label, (20, max(25, line_y - 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.putText(preview, right_label, (mid_x + 20, max(25, line_y - 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

        return preview

    def process_frame(
        self,
        frame: np.ndarray,
        frame_idx: int,
        fps: float,
        start_datetime: datetime.datetime,
        line_y_ratio: float = 0.50,
        mid_x_ratio: float = 0.45,
        swap_directions: bool = False,
        img_size: int = 640,
        device: str = "cpu",
        tracker_cfg: str = "custom_tracker.yaml"
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Runs YOLO tracking on a frame, performs crossover counting,
        calculates stall ratio and rolling density, and annotates the frame.
        """
        self.img_size = img_size
        self.device = device if (device != "cuda" or torch.cuda.is_available()) else "cpu"

        height, width = frame.shape[:2]
        line_y = int(height * line_y_ratio)
        mid_x = int(width * mid_x_ratio)

        inbound_start, inbound_end = (0, line_y), (mid_x, line_y)
        outbound_start, outbound_end = (mid_x, line_y), (width, line_y)

        # Run YOLO tracking
        tracker_file = tracker_cfg if os.path.exists(tracker_cfg) else "bytetrack.yaml"
        if self.model is None:
            self.load_model(self.model_name or "best.pt")

        results = self.model.track(
            frame,
            imgsz=self.img_size,
            classes=self.target_class_ids,
            persist=True,
            tracker=tracker_file,
            device=self.device,
            conf=self.conf_threshold,
            verbose=False
        )

        annotated_frame = results[0].plot()

        # Render counting boundary lines
        cv2.line(annotated_frame, inbound_start, inbound_end, (255, 255, 0), 3)      # Left: Cyan
        cv2.line(annotated_frame, outbound_start, outbound_end, (0, 165, 255), 3)   # Right: Orange
        cv2.circle(annotated_frame, (mid_x, line_y), 6, (0, 0, 255), -1)            # Divider: Red dot

        # Calculate Active Vehicles & Stall Ratio safely
        boxes_obj = getattr(results[0], "boxes", None)
        has_boxes = False
        active_ids: List[int] = []
        boxes_xy: np.ndarray = np.empty((0, 4))
        class_indices: List[int] = []

        if boxes_obj is not None:
            box_ids = getattr(boxes_obj, "id", None)
            if box_ids is not None:
                has_boxes = True
                active_ids = box_ids.int().cpu().tolist()
                boxes_xy = boxes_obj.xyxy.cpu().numpy()
                cls_tensor = getattr(boxes_obj, "cls", None)
                if cls_tensor is not None:
                    class_indices = cls_tensor.int().cpu().tolist()

        active_count = len(active_ids)
        stall_count = 0
        current_positions: Dict[int, Tuple[int, int]] = {}
        inbound_active = 0
        outbound_active = 0

        if has_boxes:
            for bx, tid in zip(boxes_xy, active_ids):
                cx = int((bx[0] + bx[2]) / 2)
                cy = int((bx[1] + bx[3]) / 2)
                current_positions[tid] = (cx, cy)

                # Check stall
                if tid in self.prev_positions:
                    px, py = self.prev_positions[tid]
                    dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                    if dist < 5:
                        stall_count += 1

                # Check side density
                if cx < mid_x:
                    inbound_active += 1
                else:
                    outbound_active += 1

        self.prev_positions = current_positions
        stall_ratio = (stall_count / active_count) if active_count > 0 else 0.0

        # Update rolling averages
        self.active_history.append(active_count)
        self.inbound_active_history.append(inbound_active)
        self.outbound_active_history.append(outbound_active)
        if len(self.active_history) > self.window_size:
            self.active_history.pop(0)
            self.inbound_active_history.pop(0)
            self.outbound_active_history.pop(0)

        rolling_density = sum(self.active_history) / len(self.active_history) if self.active_history else 0.0
        rolling_inbound_density = sum(self.inbound_active_history) / len(self.inbound_active_history) if self.inbound_active_history else 0.0
        rolling_outbound_density = sum(self.outbound_active_history) / len(self.outbound_active_history) if self.outbound_active_history else 0.0

        lvl_th, emoji, lvl_en = get_traffic_level(rolling_density, stall_ratio)

        # Calculate Real-world time
        timestamp_sec = frame_idx / fps if fps > 0 else 0.0
        current_real_time = start_datetime + datetime.timedelta(seconds=timestamp_sec)
        real_time_str = current_real_time.strftime("%H:%M:%S")
        real_time_full_str = current_real_time.strftime("%Y-%m-%d %H:%M:%S")

        # Line crossover tracking
        new_events = []
        if has_boxes and class_indices:
            for box, track_id, class_idx in zip(boxes_xy, active_ids, class_indices):
                x1, y1, x2, y2 = box
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)

                if track_id in self.track_history:
                    prev_x, prev_y = self.track_history[track_id]

                    if (prev_y <= line_y <= center_y) or (center_y <= line_y <= prev_y):
                        if track_id not in self.counted_ids:
                            self.counted_ids.add(track_id)

                            if center_y != prev_y:
                                cross_x = prev_x + (center_x - prev_x) * (line_y - prev_y) / (center_y - prev_y)
                            else:
                                cross_x = center_x

                            class_name = self.id_to_name.get(class_idx, "Car")
                            left_is_inbound = not swap_directions

                            if cross_x < mid_x:
                                if left_is_inbound:
                                    self.inbound_count += 1
                                    direction = "Inbound"
                                else:
                                    self.outbound_count += 1
                                    direction = "Outbound"
                                cv2.line(annotated_frame, inbound_start, inbound_end, (0, 0, 255), 6)
                            else:
                                if left_is_inbound:
                                    self.outbound_count += 1
                                    direction = "Outbound"
                                else:
                                    self.inbound_count += 1
                                    direction = "Inbound"
                                cv2.line(annotated_frame, outbound_start, outbound_end, (0, 0, 255), 6)

                            if class_name in self.class_counts:
                                self.class_counts[class_name] += 1
                            else:
                                self.class_counts[class_name] = 1

                            event_data = {
                                "Timestamp (s)": round(timestamp_sec, 2),
                                "Real-world Time": real_time_full_str,
                                "Vehicle ID": track_id,
                                "Type": class_name,
                                "Direction": direction,
                                "Traffic Level": f"{emoji} {lvl_th}"
                            }
                            self.events_log.append(event_data)
                            new_events.append(event_data)

                self.track_history[track_id] = (center_x, center_y)

        # Dynamic HUD annotations
        left_label = "Outbound" if swap_directions else "Inbound"
        right_label = "Inbound" if swap_directions else "Outbound"
        left_count = self.outbound_count if swap_directions else self.inbound_count
        right_count = self.inbound_count if swap_directions else self.outbound_count

        cv2.putText(annotated_frame, f"{left_label}: {left_count}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
        cv2.putText(annotated_frame, f"{right_label}: {right_count}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)
        cv2.putText(annotated_frame, f"Time: {real_time_str}", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)

        color_map = {"Smooth": (0, 255, 0), "Moderate": (0, 255, 255), "Congested": (0, 165, 255), "Gridlock": (0, 0, 255)}
        cv2.putText(annotated_frame, f"Traffic: {lvl_en}", (20, 170), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color_map.get(lvl_en, (255, 255, 255)), 3)

        # Save flow history
        telemetry = {
            "time_sec": round(timestamp_sec, 1),
            "real_time": real_time_str,
            "real_time_full": real_time_full_str,
            "inbound_count": self.inbound_count,
            "outbound_count": self.outbound_count,
            "total_count": self.inbound_count + self.outbound_count,
            "active_vehicles": active_count,
            "inbound_active": round(rolling_inbound_density, 1),
            "outbound_active": round(rolling_outbound_density, 1),
            "stall_ratio": round(stall_ratio, 2),
            "density_score": round(rolling_density, 2),
            "traffic_level_th": lvl_th,
            "traffic_level_en": lvl_en,
            "traffic_level_emoji": emoji,
            "class_counts": self.class_counts.copy(),
            "new_events": new_events
        }

        self.flow_history.append(telemetry)
        return annotated_frame, telemetry

    def generate_summary_table(self, start_dt: datetime.datetime) -> List[Dict[str, Any]]:
        """Generates 10-second grouped interval summary data."""
        if not self.flow_history:
            return []

        df = pd.DataFrame(self.flow_history)
        if "time_sec" not in df.columns or "active_vehicles" not in df.columns:
            return []

        df["interval_sec"] = df["time_sec"].apply(lambda t: int(t // 10) * 10)
        df["interval_time"] = df["interval_sec"].apply(lambda t: (start_dt + datetime.timedelta(seconds=t)).strftime("%H:%M:%S"))

        summary = df.groupby("interval_time").agg(
            avg_active=("active_vehicles", "mean"),
            inbound_max=("inbound_count", "max"),
            inbound_min=("inbound_count", "min"),
            outbound_max=("outbound_count", "max"),
            outbound_min=("outbound_count", "min")
        ).reset_index()

        summary["inbound_passed"] = summary["inbound_max"] - summary["inbound_min"]
        summary["outbound_passed"] = summary["outbound_max"] - summary["outbound_min"]
        summary["level"] = summary["avg_active"].apply(lambda d: f"{get_traffic_level(d)[1]} {get_traffic_level(d)[0]}")
        summary["avg_active"] = summary["avg_active"].round(1)

        result = []
        for _, row in summary.iterrows():
            result.append({
                "time": row["interval_time"],
                "avg_vehicles": row["avg_active"],
                "traffic_level": row["level"],
                "inbound_flow": int(row["inbound_passed"]),
                "outbound_flow": int(row["outbound_passed"])
            })
        return result
