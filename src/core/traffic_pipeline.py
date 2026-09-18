import os
import cv2
import datetime
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from src.core.vehicle_detector import VehicleDetector
from src.core.vehicle_tracker import VehicleTracker
from src.core.lane_counter import LaneCounter
from src.core.analytics import TrafficAnalytics, evaluate_traffic_level
from src.core.speed_estimator import SpeedEstimator
from src.core.incident_detector import IncidentDetector
from src.visualizer.annotator import FrameAnnotator
from src.utils.file_helper import resolve_model_path, list_available_models, list_available_videos
from src.schema.telemetry import CalibrationConfig

class TrafficPipeline:
    """
    Unified modular AI Traffic pipeline combining detection, tracking,
    crossover counting, speed estimation, incident detection, congestion analytics, and HUD.
    """
    def __init__(
        self,
        model_name: str = "yolo11n.pt",
        conf_threshold: float = 0.25,
        img_size: int = 480,
        device: str = "cpu"
    ):

        self.detector = VehicleDetector(
            model_name=model_name,
            conf_threshold=conf_threshold,
            img_size=img_size,
            device=device
        )
        self.tracker = VehicleTracker()
        self.counter = LaneCounter()
        self.analytics = TrafficAnalytics()
        self.speed_estimator = SpeedEstimator()
        self.incident_detector = IncidentDetector()
        self.annotator = FrameAnnotator()

    @property
    def model_name(self) -> str:
        return self.detector.model_name

    @property
    def inbound_count(self) -> int:
        return self.counter.inbound_count

    @property
    def outbound_count(self) -> int:
        return self.counter.outbound_count

    @property
    def class_counts(self) -> Dict[str, int]:
        return self.counter.class_counts

    @property
    def events_log(self) -> List[Dict[str, Any]]:
        return self.counter.events_log

    @property
    def flow_history(self) -> List[Dict[str, Any]]:
        return self.analytics.flow_history

    def reset_state(self):
        self.tracker.reset()
        self.counter.reset()
        self.analytics.reset()
        self.speed_estimator.reset()
        self.incident_detector.reset()

    def load_model(self, model_name: str):
        self.detector.load_model(model_name)

    def update_target_classes(self, classes_list: List[str]):
        self.detector.update_target_classes(classes_list)

    @staticmethod
    def get_available_models() -> List[Dict[str, Any]]:
        return list_available_models()

    @staticmethod
    def get_available_devices() -> List[str]:
        return VehicleDetector.get_available_devices()

    _VIDEO_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_video_info(cls, video_path: str) -> Optional[Dict[str, Any]]:
        # Fast cache check: avoids repeated disk access and OpenCV decoding
        if video_path in cls._VIDEO_METADATA_CACHE:
            return cls._VIDEO_METADATA_CACHE[video_path]

        is_live = (
            str(video_path).startswith("webcam:")
            or str(video_path).isdigit()
            or str(video_path).startswith(("rtsp://", "http://", "https://"))
        )

        if is_live:
            if str(video_path).startswith("webcam:") or str(video_path).isdigit():
                cam_idx = int(str(video_path).replace("webcam:", ""))
                cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(cam_idx)
            else:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
                cap = cv2.VideoCapture(
                    video_path,
                    cv2.CAP_FFMPEG,
                    [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 4000]
                )

            if not cap or not cap.isOpened():
                return None

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
            fps = 30.0
            total_frames = 0
            success, frame = cap.read()
            cap.release()

            if success:
                info = {
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "total_frames": total_frames,
                    "first_frame": frame,
                    "is_live": True
                }
                return info
            return None
        else:
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
                info = {
                    "width": width,
                    "height": height,
                    "fps": fps if fps > 0 else 30.0,
                    "total_frames": total_frames,
                    "first_frame": frame,
                    "is_live": False
                }
                cls._VIDEO_METADATA_CACHE[video_path] = info
                return info
            return None

    @staticmethod
    def generate_calibration_preview(
        first_frame: np.ndarray,
        line_y_ratio: float = 0.50,
        mid_x_ratio: float = 0.45,
        swap_directions: bool = False
    ) -> np.ndarray:
        return FrameAnnotator.draw_calibration_lines(
            image=first_frame,
            line_y_ratio=line_y_ratio,
            mid_x_ratio=mid_x_ratio,
            swap_directions=swap_directions
        )

    def process_frame(
        self,
        frame: np.ndarray,
        frame_idx: int,
        fps: float,
        start_datetime: Optional[datetime.datetime] = None,
        line_y_ratio: float = 0.50,
        mid_x_ratio: float = 0.45,
        swap_directions: bool = False,
        img_size: int = 640,
        device: str = "cpu",
        tracker_cfg: str = "custom_tracker.yaml",
        speed_limit_kmh: float = 50.0,
        pixels_per_meter: float = 22.0
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Executes complete frame processing: detection, tracking, crossover math,
        speed estimation, incident detection, telemetry computation, and HUD annotation.
        """
        self.detector.set_img_size(img_size)
        self.detector.set_device(device)
        self.speed_estimator.set_calibration_scale(pixels_per_meter)
        self.incident_detector.set_speed_limit(speed_limit_kmh)

        height, width = frame.shape[:2]
        line_y = int(height * line_y_ratio)
        mid_x = int(width * mid_x_ratio)

        tracker_file = tracker_cfg if os.path.exists(tracker_cfg) else "bytetrack.yaml"

        # 1. Inference with Tracking
        results = self.detector.model.track(
            frame,
            imgsz=self.detector.img_size,
            classes=self.detector.target_class_ids,
            persist=True,
            tracker=tracker_file,
            device=self.detector.device,
            conf=self.detector.conf_threshold,
            verbose=False
        )

        annotated_frame = results[0].plot()

        # 2. Extract Active Detections
        has_boxes = results[0].boxes is not None and results[0].boxes.id is not None
        if has_boxes:
            active_ids = results[0].boxes.id.int().cpu().tolist()
            boxes_xyxy = results[0].boxes.xyxy.cpu().numpy()
            class_indices = results[0].boxes.cls.int().cpu().tolist()
        else:
            active_ids = []
            boxes_xyxy = np.empty((0, 4))
            class_indices = []

        # 3. Tracker update & Stall ratio
        active_count, stall_ratio, inbound_active, outbound_active, _ = self.tracker.update_positions(
            boxes_xyxy=boxes_xyxy,
            track_ids=active_ids,
            mid_x=mid_x,
            frame_idx=frame_idx
        )

        # 4. Centroids & Real-time Speed Estimation
        centroids = []
        for box in boxes_xyxy:
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)
            centroids.append((cx, cy))

        c_names = [self.detector.id_to_name.get(cls_id, "Vehicle") for cls_id in class_indices]

        speeds_map: Dict[int, float] = {}
        speeds_list: List[float] = []
        for tid, pt in zip(active_ids, centroids):
            sp = self.speed_estimator.update(tid, pt, frame_idx, fps)
            speeds_map[tid] = sp
            speeds_list.append(sp)

        self.speed_estimator.prune_lost_tracks(active_ids)

        moving_speeds = [s for s in speeds_list if s > 2.0]
        avg_speed = round(float(np.mean(moving_speeds)), 1) if moving_speeds else (
            round(float(np.mean(speeds_list)), 1) if speeds_list else 0.0
        )

        # 5. Rolling Density & Congestion level
        rolling_density, rolling_inbound, rolling_outbound = self.analytics.update_rolling_stats(
            active_count=active_count,
            inbound_active=inbound_active,
            outbound_active=outbound_active
        )
        traffic_level = evaluate_traffic_level(rolling_density, stall_ratio)

        # 6. Real-world Timestamps
        timestamp_sec = frame_idx / fps if fps > 0 else 0.0
        if start_datetime is None:
            current_real_time = datetime.datetime.now()
        else:
            current_real_time = start_datetime + datetime.timedelta(seconds=timestamp_sec)
        real_time_str = current_real_time.strftime("%H:%M:%S")
        real_time_full_str = current_real_time.strftime("%Y-%m-%d %H:%M:%S")

        # 7. Incident & Anomaly Detection
        new_incidents = self.incident_detector.check_incidents(
            track_ids=active_ids,
            centroids=centroids,
            speeds=speeds_list,
            class_names=c_names,
            mid_x=mid_x,
            swap_directions=swap_directions,
            current_time_sec=timestamp_sec,
            real_time_str=real_time_str,
            fps=fps
        )
        incident_ids = {inc["vehicle_id"] for inc in self.incident_detector.active_incidents}

        # 8. Tripwire Counting with Speed
        new_events, triggered_lines = self.counter.check_crossovers(
            boxes_xyxy=boxes_xyxy,
            track_ids=active_ids,
            class_ids=class_indices,
            id_to_name=self.detector.id_to_name,
            track_history=self.tracker.track_history,
            line_y=line_y,
            mid_x=mid_x,
            swap_directions=swap_directions,
            timestamp_sec=timestamp_sec,
            real_time_full_str=real_time_full_str,
            traffic_level_str=f"{traffic_level.emoji} {traffic_level.thai_desc}",
            frame_width=width,
            speeds=speeds_map
        )

        # 9. Draw Visual Overlays, Badges & HUD
        annotated_frame = FrameAnnotator.draw_vehicle_badges(
            frame=annotated_frame,
            boxes_xyxy=boxes_xyxy,
            track_ids=active_ids,
            speeds=speeds_map,
            speed_limit_kmh=speed_limit_kmh,
            incident_vehicle_ids=incident_ids
        )

        inbound_color = (0, 0, 255) if ((0, line_y), (mid_x, line_y)) in triggered_lines else (255, 255, 0)
        outbound_color = (0, 0, 255) if ((mid_x, line_y), (width, line_y)) in triggered_lines else (0, 165, 255)

        annotated_frame = FrameAnnotator.draw_calibration_lines(
            image=annotated_frame,
            line_y_ratio=line_y_ratio,
            mid_x_ratio=mid_x_ratio,
            swap_directions=swap_directions,
            inbound_color=inbound_color,
            outbound_color=outbound_color
        )

        annotated_frame = FrameAnnotator.draw_hud(
            frame=annotated_frame,
            inbound_count=self.counter.inbound_count,
            outbound_count=self.counter.outbound_count,
            real_time_str=real_time_str,
            traffic_level_en=traffic_level.english_name,
            traffic_level_color=traffic_level.color_rgb,
            swap_directions=swap_directions,
            avg_speed=avg_speed,
            incident_count=len(self.incident_detector.active_incidents)
        )

        # 10. Build Telemetry Data Dictionary
        telemetry = {
            "time_sec": round(timestamp_sec, 1),
            "real_time": real_time_str,
            "real_time_full": real_time_full_str,
            "inbound_count": self.counter.inbound_count,
            "outbound_count": self.counter.outbound_count,
            "total_count": self.counter.inbound_count + self.counter.outbound_count,
            "active_vehicles": active_count,
            "inbound_active": round(rolling_inbound, 1),
            "outbound_active": round(rolling_outbound, 1),
            "stall_ratio": round(stall_ratio, 2),
            "density_score": round(rolling_density, 2),
            "avg_speed_kmh": avg_speed,
            "traffic_level_th": traffic_level.thai_desc,
            "traffic_level_en": traffic_level.english_name,
            "traffic_level_emoji": traffic_level.emoji,
            "traffic_level_color": traffic_level.color_hex,
            "class_counts": self.counter.class_counts.copy(),
            "new_events": new_events,
            "new_incidents": new_incidents,
            "active_incidents": self.incident_detector.active_incidents[-5:]
        }

        self.analytics.record_telemetry(telemetry)
        return annotated_frame, telemetry

    def generate_summary_table(self, start_dt: datetime.datetime, interval_seconds: int = 10) -> List[Dict[str, Any]]:
        return self.analytics.generate_summary_table(start_dt, interval_seconds)
