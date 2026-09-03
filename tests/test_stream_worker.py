import unittest
import time
import os
from src.services.stream_worker import StreamWorker
from src.core.traffic_pipeline import TrafficPipeline

class TestStreamWorker(unittest.TestCase):
    def test_worker_lifecycle(self):
        video_path = os.path.join("uploads", "IMG_1357.MOV")
        if not os.path.exists(video_path):
            self.skipTest(f"Video {video_path} not found")

        worker = StreamWorker(
            engine=TrafficPipeline(model_name="yolov11n.pt"),
            target_width=640,
            inference_size=320,
            max_queue_size=2
        )

        loaded = worker.load_video(video_path)
        self.assertTrue(loaded)
        self.assertGreater(worker.total_frames, 0)

        # Start worker
        worker.start()
        self.assertTrue(worker.is_playing)

        # Wait for first processed frame (allowing time for initial model warmup on CPU)
        packet = worker.frame_queue.get(timeout=30.0)
        self.assertEqual(packet["type"], "frame")
        self.assertIn("image", packet)
        self.assertIn("telemetry", packet)

        # Test pause
        worker.pause()
        self.assertTrue(worker.is_paused)

        # Test stop
        worker.stop()
        self.assertFalse(worker.is_playing)
        self.assertIsNone(worker.cap)

if __name__ == "__main__":
    unittest.main()
