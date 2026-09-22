import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import cv2
from src.services.stream_worker import StreamWorker
from src.core.traffic_pipeline import TrafficPipeline
from src.utils.file_helper import resolve_video_source

class TestLiveStream(unittest.TestCase):
    def test_resolve_video_source(self):
        self.assertEqual(resolve_video_source("webcam:0"), "webcam:0")
        self.assertEqual(resolve_video_source("0"), "0")
        self.assertEqual(resolve_video_source("rtsp://192.168.1.1:554/live"), "rtsp://192.168.1.1:554/live")
        self.assertEqual(resolve_video_source("http://192.168.1.1:8080/mjpeg"), "http://192.168.1.1:8080/mjpeg")

    def test_live_stream_worker_initialization(self):
        worker = StreamWorker(
            engine=TrafficPipeline(model_name="yolov11n.pt"),
            target_width=640,
            inference_size=320,
            max_queue_size=2
        )

        # Mock cv2.VideoCapture for live webcam test
        with patch("cv2.VideoCapture") as mock_cap_class:
            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.get.return_value = 30.0
            mock_cap_class.return_value = mock_cap

            # Load live webcam source
            loaded = worker.load_video("webcam:0")
            self.assertTrue(loaded)
            self.assertTrue(worker.is_live)
            self.assertEqual(worker.total_frames, 0)

            # Check that CAP_PROP_BUFFERSIZE was set to 1 for zero latency
            mock_cap.set.assert_called_with(cv2.CAP_PROP_BUFFERSIZE, 1)

            worker.stop()

if __name__ == "__main__":
    unittest.main()
