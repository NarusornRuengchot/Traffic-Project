import cv2
import os
import datetime
import numpy as np
import pandas as pd
import torch
from typing import Dict, List, Tuple, Optional, Any
from ultralytics import YOLO

def resolve_model_path(model_name: str) -> str:
    """Find the exact model file or fallback variations."""
    if os.path.exists(model_name):
        return model_name
        
    if "yolov11" in model_name:
        alt = model_name.replace("yolov11", "yolo11")
        if os.path.exists(alt):
            return alt
    elif "yolo11" in model_name:
        alt = model_name.replace("yolo11", "yolov11")
        if os.path.exists(alt):
            return alt
            
    if "yolov8" in model_name:
        alt = model_name.replace("yolov8", "yolo8")
        if os.path.exists(alt):
            return alt
    elif "yolo8" in model_name:
        alt = model_name.replace("yolo8", "yolov8")
        if os.path.exists(alt):
            return alt
            
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
    def __init__(self, model_name: str = "best.pt", conf_threshold: float = 0.25, img_size: int = 640, device: str = "cpu"):
        self.conf_threshold = conf_threshold
        self.img_size = img_size
        self.device = device
        self.model_name = ""
        self.model = None
        self.class_map = {}
        self.id_to_name = {}
        self.selected_target_classes = ["Car", "Motorcycle", "Bus", "Truck"]
        self.target_class_ids = []
        
        # State tracking
        self.inbound_count = 0
        self.outbound_count = 0
        self.counted_ids = set()
        self.track_history = {}
        self.prev_positions = {}
        self.active_history = []
        self.inbound_active_history = []
        self.outbound_active_history = []
        self.class_counts = {"Car": 0, "Motorcycle": 0, "Bus": 0, "Truck": 0}
        self.events_log = []
        self.flow_history = []
        self.window_size = 30
        
        self.load_model(model_name)

    def load_model(self, model_name: str):
        """Loads a YOLO model weights file and initializes class maps."""
        resolved = resolve_model_path(model_name)
        if not os.path.exists(resolved):
            fallback = "yolov11n.pt" if os.path.exists("yolov11n.pt") else "yolov8n.pt"
            if os.path.exists(fallback):
                resolved = fallback
            else:
                resolved = model_name

        self.model_name = os.path.basename(resolved)
        self.model = YOLO(resolved)

        # Setup class mappings based on model type
        if "best.pt" in self.model_name:
            self.class_map = {"Car": 1, "Motorcycle": 2, "Bus": 0, "Truck": 3}
            self.id_to_name = {1: "Car", 2: "Motorcycle", 0: "Bus", 3: "Truck"}
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
        if os.path.exists("best.pt"):
            models.append({"name": "best.pt", "label": "🎯 Fine-Tuned Model (best.pt)", "type": "finetuned"})
            
        for f in sorted(os.listdir(".")):
            if f.endswith(".pt") and f != "best.pt":
                models.append({"name": f, "label": f, "type": "standard"})
                
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
        fps = cap.get(cv2.CAP_PROP_FPS)
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
        LINE_Y = int(height * line_y_ratio)
        MID_X = int(width * mid_x_ratio)
        
        inbound_start, inbound_end = (0, LINE_Y), (MID_X, LINE_Y)
        outbound_start, outbound_end = (MID_X, LINE_Y), (width, LINE_Y)
        
        cv2.line(preview, inbound_start, inbound_end, (255, 255, 0), 4)      # Left: Cyan
        cv2.line(preview, outbound_start, outbound_end, (0, 165, 255), 4)   # Right: Orange
        cv2.circle(preview, (MID_X, LINE_Y), 10, (0, 0, 255), -1)           # Divider: Red dot
        
        left_label = "Outbound Lane" if swap_directions else "Inbound Lane"
        right_label = "Inbound Lane" if swap_directions else "Outbound Lane"
        
        cv2.putText(preview, left_label, (20, LINE_Y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.putText(preview, right_label, (MID_X + 20, LINE_Y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        
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
        self.device = device
        
        height, width = frame.shape[:2]
        LINE_Y = int(height * line_y_ratio)
        MID_X = int(width * mid_x_ratio)
        
        inbound_start, inbound_end = (0, LINE_Y), (MID_X, LINE_Y)
        outbound_start, outbound_end = (MID_X, LINE_Y), (width, LINE_Y)

        # Run YOLO tracking
        tracker_file = tracker_cfg if os.path.exists(tracker_cfg) else "bytetrack.yaml"
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
        cv2.circle(annotated_frame, (MID_X, LINE_Y), 6, (0, 0, 255), -1)            # Divider: Red dot

        # Calculate Active Vehicles & Stall Ratio
        active_ids = results[0].boxes.id.int().cpu().tolist() if results[0].boxes.id is not None else []
        active_count = len(active_ids)

        stall_count = 0
        current_positions = {}
        inbound_active = 0
        outbound_active = 0

        if results[0].boxes.id is not None:
            boxes_xy = results[0].boxes.xyxy.cpu().numpy()
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
                if cx < MID_X:
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
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            classes = results[0].boxes.cls.int().cpu().tolist()

            for box, track_id, class_idx in zip(boxes, track_ids, classes):
                x1, y1, x2, y2 = box
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)

                if track_id in self.track_history:
                    prev_x, prev_y = self.track_history[track_id]

                    if (prev_y <= LINE_Y <= center_y) or (center_y <= LINE_Y <= prev_y):
                        if track_id not in self.counted_ids:
                            self.counted_ids.add(track_id)

                            if center_y != prev_y:
                                cross_x = prev_x + (center_x - prev_x) * (LINE_Y - prev_y) / (center_y - prev_y)
                            else:
                                cross_x = center_x

                            class_name = self.id_to_name.get(class_idx, "Unknown")
                            left_is_inbound = not swap_directions

                            if cross_x < MID_X:
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

                            self.events_log.append({
                                "Timestamp (s)": round(timestamp_sec, 2),
                                "Real-world Time": real_time_full_str,
                                "Vehicle ID": track_id,
                                "Type": class_name,
                                "Direction": direction,
                                "Traffic Level": f"{emoji} {lvl_th}"
                            })

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
            "class_counts": self.class_counts.copy()
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
