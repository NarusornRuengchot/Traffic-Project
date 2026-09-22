from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import datetime

@dataclass
class TrafficLevel:
    thai_desc: str
    emoji: str
    english_name: str
    color_rgb: tuple
    color_hex: str

@dataclass
class DetectionBox:
    track_id: int
    class_id: int
    class_name: str
    bbox: List[float]  # [x1, y1, x2, y2]
    center: tuple       # (cx, cy)
    confidence: float

@dataclass
class VehicleEvent:
    timestamp_sec: float
    real_time: str
    vehicle_id: int
    vehicle_type: str
    direction: str
    traffic_level: str

@dataclass
class TelemetryFrame:
    time_sec: float
    real_time: str
    real_time_full: str
    inbound_count: int
    outbound_count: int
    total_count: int
    active_vehicles: int
    inbound_active: float
    outbound_active: float
    stall_ratio: float
    density_score: float
    traffic_level_th: str
    traffic_level_en: str
    traffic_level_emoji: str
    traffic_level_color: str
    class_counts: Dict[str, int] = field(default_factory=dict)

@dataclass
class CalibrationConfig:
    line_y_ratio: float = 0.50
    mid_x_ratio: float = 0.45
    swap_directions: bool = False
    conf_threshold: float = 0.25
    img_size: int = 640
    device: str = "cpu"
    tracker_cfg: str = "custom_tracker.yaml"
    target_classes: List[str] = field(default_factory=lambda: ["Car", "Motorcycle", "Bus", "Truck"])
