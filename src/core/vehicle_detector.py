import os
import torch
from typing import Dict, List, Optional, Tuple, Any
from ultralytics import YOLO
from src.utils.file_helper import resolve_model_path

COCO_CLASS_MAP = {"Car": 2, "Motorcycle": 3, "Bus": 5, "Truck": 7}
COCO_ID_TO_NAME = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}

CUSTOM_CLASS_MAP = {"Car": 1, "Motorcycle": 2, "Bus": 0, "Truck": 3}
CUSTOM_ID_TO_NAME = {1: "Car", 2: "Motorcycle", 0: "Bus", 3: "Truck"}

# In-memory model cache: maps resolved model path -> (YOLO instance, class_map, id_to_name)
_MODEL_CACHE: Dict[str, Tuple[YOLO, Dict[str, int], Dict[int, str]]] = {}

class VehicleDetector:
    def __init__(
        self,
        model_name: str = "best.pt",
        conf_threshold: float = 0.25,
        img_size: int = 640,
        device: str = "cpu"
    ):
        self.conf_threshold: float = conf_threshold
        self.img_size: int = img_size
        self.device: str = self._auto_select_device(device)
        self.model_name: str = ""
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
        if not os.path.exists(resolved):
            fallback = "yolov11n.pt" if os.path.exists("yolov11n.pt") else "yolov8n.pt"
            if os.path.exists(fallback):
                resolved = fallback
            else:
                resolved = model_name

        self.model_name = os.path.basename(resolved)

        # 1. Fast Cache Hit: Instant model switch (<1ms)
        if resolved in _MODEL_CACHE:
            cached_model, cached_class_map, cached_id_to_name = _MODEL_CACHE[resolved]
            self.model = cached_model
            self.class_map = cached_class_map.copy()
            self.id_to_name = cached_id_to_name.copy()
            self.update_target_classes(self.selected_target_classes)
            return

        # 2. Cache Miss: Load from disk
        try:
            self.model = YOLO(resolved)
        except Exception as e:
            print(f"⚠️ Error loading YOLO model '{resolved}': {e}. Attempting default yolov11n.pt fallback.")
            self.model = YOLO("yolov11n.pt")
            self.model_name = "yolov11n.pt"
            resolved = "yolov11n.pt"

        # Dynamically inspect model.names from model metadata
        self.class_map = {}
        self.id_to_name = {}

        model_names = getattr(self.model, "names", None)
        if isinstance(model_names, dict):
            for cid, cname in model_names.items():
                name_clean = str(cname).strip().capitalize()
                # Normalize vehicle category names
                if name_clean.lower() in ["car", "automobile", "sedan", "suv", "van"]:
                    std_name = "Car"
                elif name_clean.lower() in ["motorcycle", "motorbike", "bike", "scooter"]:
                    std_name = "Motorcycle"
                elif name_clean.lower() in ["bus"]:
                    std_name = "Bus"
                elif name_clean.lower() in ["truck"]:
                    std_name = "Truck"
                else:
                    std_name = name_clean

                self.id_to_name[int(cid)] = std_name
                self.class_map[std_name] = int(cid)

        # Fallback if names dict was incomplete or lacked target classes
        if not any(c in self.class_map for c in ["Car", "Motorcycle", "Bus", "Truck"]):
            if "best.pt" in self.model_name.lower() or "custom" in self.model_name.lower():
                self.class_map = CUSTOM_CLASS_MAP.copy()
                self.id_to_name = CUSTOM_ID_TO_NAME.copy()
            else:
                self.class_map = COCO_CLASS_MAP.copy()
                self.id_to_name = COCO_ID_TO_NAME.copy()

        # Cache the loaded model instance for instant future switching
        _MODEL_CACHE[resolved] = (self.model, self.class_map.copy(), self.id_to_name.copy())

        self.update_target_classes(self.selected_target_classes)

    def warmup(self, size: int = 320):
        """Runs a fast dummy inference to compile PyTorch kernels and prevent cold-start latency."""
        try:
            if self.model is not None:
                import numpy as np
                dummy = np.zeros((size, size, 3), dtype=np.uint8)
                self.model(dummy, imgsz=size, device=self.device, verbose=False)
        except Exception:
            pass

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

