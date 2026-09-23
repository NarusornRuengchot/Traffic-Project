import unittest
import os
import asyncio
from src.services.benchmark_service import capture_benchmark_frames, run_cctv_model_benchmark
from src.api.routers.benchmark import get_benchmark_presets, compare_models_endpoint

class TestBenchmarkService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_video = os.path.join("uploads", "IMG_1357.MOV")
        if not os.path.exists(cls.test_video):
            cls.test_video = "IMG_1357.MOV"

    def test_get_benchmark_presets(self):
        """Tests that presets endpoint returns CCTV options and available models."""
        data = asyncio.run(get_benchmark_presets())
        self.assertIn("presets", data)
        self.assertIn("available_models", data)
        self.assertTrue(len(data["presets"]) >= 2)

    def test_capture_benchmark_frames(self):
        """Tests capturing sample frames from video source."""
        if not os.path.exists(self.test_video):
            self.skipTest(f"Video {self.test_video} not found")

        frames, meta = capture_benchmark_frames(self.test_video, sample_count=2)
        self.assertGreaterEqual(len(frames), 1)
        self.assertIn("width", meta)
        self.assertIn("height", meta)
        self.assertIn("fps", meta)
        self.assertEqual(meta["sampled_frames"], len(frames))

    def test_run_cctv_model_benchmark(self):
        """Tests comparative benchmark between two lightweight models."""
        if not os.path.exists(self.test_video):
            self.skipTest(f"Video {self.test_video} not found")

        models_to_test = ["yolo26n.pt", "yolov11n.pt"]
        result = run_cctv_model_benchmark(
            video_source=self.test_video,
            models=models_to_test,
            sample_frames=2,
            conf_threshold=0.18,
            img_size=320
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["results"]), 2)
        self.assertIn("winners", result)

        for res in result["results"]:
            self.assertIn("mean_confidence", res)
            self.assertIn("avg_inference_ms", res)
            self.assertIn("fps", res)
            self.assertIn("annotated_preview", res)
            self.assertIn("class_breakdown", res)
            self.assertTrue(len(res["annotated_preview"]) > 100)

        # Check winners structure
        self.assertIn("accuracy_winner", result["winners"])
        self.assertIn("speed_winner", result["winners"])
        self.assertIn("recommended_model", result["winners"])

    def test_api_benchmark_compare_endpoint(self):
        """Tests POST /api/benchmark/compare endpoint."""
        if not os.path.exists(self.test_video):
            self.skipTest(f"Video {self.test_video} not found")

        payload = {
            "video_source": self.test_video,
            "models": ["yolo26n.pt"],
            "sample_frames": 2,
            "conf_threshold": 0.18,
            "img_size": 320
        }
        data = asyncio.run(compare_models_endpoint(payload))
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["model_name"], "yolo26n.pt")

if __name__ == "__main__":
    unittest.main()
