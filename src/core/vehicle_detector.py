import os
import torch
from typing import Dict, List, Optional, Tuple, Any
from ultralytics import YOLO
from src.utils.file_helper import resolve_model_path

COCO_CLASS_MAP = {"Car": 2, "Motorcycle": 3, "Bus": 5, "Truck": 7}
COCO_ID_TO_NAME = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}

CUSTOM_CLASS_MAP = {"Car": 1, "Motorcycle": 2, "Bus": 0, "Truck": 3}
CUSTOM_ID_TO_NAME = {1: "Car", 2: "Motorcycle", 0: "Bus", 3: "Truck"}

class VehicleDetector:
    def __init__(
        self,
        model_name: str = "best.pt",
        conf_threshold: float = 0.25,
        img_size: int = 640,
        device: str = "cpu"
    ):
        self.conf_threshold = conf_threshold
        self.img_size = img_size
        self.device = self._auto_select_device(device)
        self.model_name = ""
        self.model: Optional[YOLO] = None
        self.class_map: Dict[str, int] = {}
        self.id_to_name: Dict[int, str] = {}
        self.selected_target_classes: List[str] = ["Car", "Motorcycle", "Bus", "Truck"]
        self.target_class_ids: List[int] = []

        self.load_model(model_name)

    @staticmethod
    def _auto_select_device(preferred: str = "cpu") -> str:
        if preferred == "cuda" and torch.cuda.is_available():
            return "cuda"
        if preferred == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return "cpu"

    @staticmethod
    def get_available_devices() -> List[str]:
        devices = ["cpu"]
        if torch.cuda.is_available():
            devices.insert(0, "cuda")
        return devices

    def load_model(self, model_name: str):
        resolved = resolve_model_path(model_name)
        self.model_name = os.path.basename(resolved)
        self.model = YOLO(resolved)

        if "best.pt" in self.model_name.lower():
            self.class_map = CUSTOM_CLASS_MAP.copy()
            self.id_to_name = CUSTOM_ID_TO_NAME.copy()
        else:
            self.class_map = COCO_CLASS_MAP.copy()
            self.id_to_name = COCO_ID_TO_NAME.copy()

        self.update_target_classes(self.selected_target_classes)

    def update_target_classes(self, classes_list: List[str]):
        self.selected_target_classes = classes_list
        self.target_class_ids = [
            self.class_map[c] for c in classes_list if c in self.class_map
        ]

    def set_confidence(self, conf: float):
        self.conf_threshold = max(0.01, min(1.0, conf))

    def set_img_size(self, img_size: int):
        self.img_size = img_size

    def set_device(self, device: str):
        self.device = self._auto_select_device(device)
