import unittest
import os
from src.core.vehicle_detector import VehicleDetector, _MODEL_CACHE
from src.core.traffic_pipeline import TrafficPipeline

class TestModelCacheAndPreview(unittest.TestCase):
    def test_model_cache_reuse(self):
        # First load
        detector1 = VehicleDetector(model_name="yolov11n.pt")
        model_inst1 = detector1.model
        self.assertIsNotNone(model_inst1)

        # Check in _MODEL_CACHE
        resolved = "yolov11n.pt"
        self.assertIn(resolved, _MODEL_CACHE)

        # Second load (must hit cache and reuse the exact same YOLO instance)
        detector2 = VehicleDetector(model_name="yolov11n.pt")
        model_inst2 = detector2.model
        self.assertIs(model_inst1, model_inst2, "Second load must return cached YOLO instance")

    def test_video_metadata_cache(self):
        video_path = os.path.join("uploads", "IMG_1357.MOV")
        if not os.path.exists(video_path):
            self.skipTest(f"Video {video_path} not found")

        # First call
        info1 = TrafficPipeline.get_video_info(video_path)
        self.assertIsNotNone(info1)

        # Cache check
        self.assertIn(video_path, TrafficPipeline._VIDEO_METADATA_CACHE)

        # Second call must return identical cached dict
        info2 = TrafficPipeline.get_video_info(video_path)
        self.assertIs(info1, info2, "Second call must return cached video info")

if __name__ == "__main__":
    unittest.main()
