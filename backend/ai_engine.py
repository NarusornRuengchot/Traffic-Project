"""
AI Traffic Engine (Backward-Compatible Facade / Adapter)
This module provides a drop-in backward-compatible interface to the modular
TrafficPipeline in `src.core.traffic_pipeline`.
"""
import os
import datetime
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from src.core.traffic_pipeline import TrafficPipeline
from src.core.analytics import evaluate_traffic_level
from src.utils.file_helper import resolve_model_path as _resolve_model_path

def resolve_model_path(model_name: str) -> str:
    """Find the exact model file or fallback variations."""
    return _resolve_model_path(model_name)

def get_traffic_level(density: float, stall_ratio: float = 0.0) -> Tuple[str, str, str]:
    """
    Evaluates traffic congestion level based on vehicle density and stall ratio.
    Returns: (Thai description, Emoji, English level name)
    """
    lvl = evaluate_traffic_level(density, stall_ratio)
    return f"{lvl.english_name} ({lvl.thai_desc})", lvl.emoji, lvl.english_name

class AITrafficEngine:
    """
    Backward-compatible adapter class wrapping TrafficPipeline.
    Preserves existing API surface for notebooks and external scripts.
    """
    def __init__(
        self,
        model_name: str = "best.pt",
        conf_threshold: float = 0.25,
        img_size: int = 640,
        device: str = "cpu"
    ):
        self._pipeline = TrafficPipeline(
            model_name=model_name,
            conf_threshold=conf_threshold,
            img_size=img_size,
            device=device
        )

    @property
    def model_name(self) -> str:
        return self._pipeline.model_name

    @property
    def model(self):
        return self._pipeline.detector.model

    @property
    def conf_threshold(self) -> float:
        return self._pipeline.detector.conf_threshold

    @conf_threshold.setter
    def conf_threshold(self, value: float):
        self._pipeline.detector.set_confidence(value)

    @property
    def img_size(self) -> int:
        return self._pipeline.detector.img_size

    @img_size.setter
    def img_size(self, value: int):
        self._pipeline.detector.set_img_size(value)

    @property
    def device(self) -> str:
        return self._pipeline.detector.device

    @device.setter
    def device(self, value: str):
        self._pipeline.detector.set_device(value)

    @property
    def class_map(self) -> Dict[str, int]:
        return self._pipeline.detector.class_map

    @property
    def id_to_name(self) -> Dict[int, str]:
        return self._pipeline.detector.id_to_name

    @property
    def selected_target_classes(self) -> List[str]:
        return self._pipeline.detector.selected_target_classes

    @property
    def target_class_ids(self) -> List[int]:
        return self._pipeline.detector.target_class_ids

    @property
    def inbound_count(self) -> int:
        return self._pipeline.inbound_count

    @property
    def outbound_count(self) -> int:
        return self._pipeline.outbound_count

    @property
    def class_counts(self) -> Dict[str, int]:
        return self._pipeline.class_counts

    @property
    def events_log(self) -> List[Dict[str, Any]]:
        return self._pipeline.events_log

    @property
    def flow_history(self) -> List[Dict[str, Any]]:
        return self._pipeline.flow_history

    def load_model(self, model_name: str):
        self._pipeline.load_model(model_name)

    def update_target_classes(self, classes_list: List[str]):
        self._pipeline.update_target_classes(classes_list)

    def reset_state(self):
        self._pipeline.reset_state()

    @staticmethod
    def get_available_models() -> List[Dict[str, Any]]:
        return TrafficPipeline.get_available_models()

    @staticmethod
    def get_available_devices() -> List[str]:
        return TrafficPipeline.get_available_devices()

    @staticmethod
    def get_video_info(video_path: str) -> Optional[Dict[str, Any]]:
        return TrafficPipeline.get_video_info(video_path)

    @staticmethod
    def generate_calibration_preview(
        first_frame: np.ndarray,
        line_y_ratio: float = 0.50,
        mid_x_ratio: float = 0.45,
        swap_directions: bool = False
    ) -> np.ndarray:
        return TrafficPipeline.generate_calibration_preview(
            first_frame=first_frame,
            line_y_ratio=line_y_ratio,
            mid_x_ratio=mid_x_ratio,
            swap_directions=swap_directions
        )

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
        return self._pipeline.process_frame(
            frame=frame,
            frame_idx=frame_idx,
            fps=fps,
            start_datetime=start_datetime,
            line_y_ratio=line_y_ratio,
            mid_x_ratio=mid_x_ratio,
            swap_directions=swap_directions,
            img_size=img_size,
            device=device,
            tracker_cfg=tracker_cfg
        )

    def generate_summary_table(self, start_dt: datetime.datetime) -> List[Dict[str, Any]]:
        return self._pipeline.generate_summary_table(start_dt)

