import asyncio
import base64
import datetime
import os
import queue
import threading
import time
from typing import Dict, Any, Optional, List, Tuple
import cv2

from src.core.traffic_pipeline import TrafficPipeline

class StreamWorker:
    """
    Dedicated background worker thread for video decoding, AI tracking,
    and frame encoding. Decouples heavy computer vision workload from the
    asyncio WebSocket event loop to prevent server freezes and lag.
    """
    def __init__(
        self,
        engine: Optional[TrafficPipeline] = None,
        target_width: int = 960,
        inference_size: int = 480,
        jpeg_quality: int = 65,
        max_queue_size: int = 2
    ):
        self.engine: TrafficPipeline = engine if engine is not None else TrafficPipeline()
        self.target_width = target_width
        self.inference_size = inference_size
        self.jpeg_quality = jpeg_quality

        # Streaming state flags
        self._is_running = threading.Event()
        self._is_paused = threading.Event()
        self._stop_requested = threading.Event()
        self._lock = threading.Lock()

        # Video source state
        self.video_path: Optional[str] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.fps: float = 30.0
        self.total_frames: int = 0
        self.current_frame_idx: int = 0
        self.start_dt: datetime.datetime = datetime.datetime.now()
        self.is_live: bool = False

        # Thread synchronization
        self._thread: Optional[threading.Thread] = None
        self._is_running = threading.Event()
        self._is_paused = threading.Event()
        self._stop_requested = threading.Event()
        self._lock = threading.Lock()

        # Calibration & detection parameters
        self.line_y_ratio: float = 0.50
        self.mid_x_ratio: float = 0.45
        self.swap_directions: bool = False
        self.conf_threshold: float = 0.25

        # Bounded frame buffer with drop-oldest policy (prevents WebSocket lag)
        self.frame_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.last_telemetry: Optional[Dict[str, Any]] = None

    @property
    def is_playing(self) -> bool:
        return self._is_running.is_set() and not self._is_paused.is_set()

    @property
    def is_paused(self) -> bool:
        return self._is_paused.is_set()

    def load_video(self, video_path: str) -> bool:
        """
        Loads video file or connects to real-time live video feed (Webcam, RTSP, IP Camera).
        """
        with self._lock:
            if self.cap is not None:
                self.cap.release()
                self.cap = None

            self.video_path = str(video_path)
            self.is_live = (
                self.video_path.startswith("webcam:")
                or self.video_path.isdigit()
                or self.video_path.startswith(("rtsp://", "http://", "https://"))
            )

            if self.is_live:
                if self.video_path.startswith("webcam:") or self.video_path.isdigit():
                    cam_idx = int(self.video_path.replace("webcam:", ""))
                    self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(cam_idx)
                else:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
                    self.cap = cv2.VideoCapture(
                        self.video_path,
                        cv2.CAP_FFMPEG,
                        [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 4000]
                    )

                if not self.cap or not self.cap.isOpened():
                    print(f"❌ Failed to open live video source: {video_path}")
                    return False

                # Crucial for true real-time zero latency: set internal buffer to 1 frame
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
                self.total_frames = 0
                self.current_frame_idx = 0
                self.start_dt = datetime.datetime.now()
                print(f"🔴 Connected to REAL-TIME LIVE STREAM: {video_path} (FPS: {self.fps})")
                return True
            else:
                if not os.path.exists(video_path):
                    print(f"❌ Video not found: {video_path}")
                    return False

                self.cap = cv2.VideoCapture(video_path)
                if self.cap.isOpened():
                    self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
                    self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.current_frame_idx = 0
                    self.start_dt = datetime.datetime.now()
                    print(f"🎬 Loaded video: {video_path} (FPS: {self.fps}, Frames: {self.total_frames})")
                    return True
                else:
                    print(f"❌ OpenCV failed to open video: {video_path}")
                    return False

    def start(self):
        """Starts or restarts the background stream processing thread."""
        self._stop_requested.clear()
        self._is_paused.clear()
        self._is_running.set()

        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="StreamWorkerThread")
            self._thread.start()

    def pause(self):
        self._is_paused.set()

    def resume(self):
        self._is_paused.clear()

    def reset(self):
        with self._lock:
            self.engine.reset_state()
            if not self.is_live and self.cap is not None and self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame_idx = 0
            # Drain queue
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break

    def update_config(self, cfg: Dict[str, Any]):
        with self._lock:
            if "model_name" in cfg and cfg["model_name"] != self.engine.model_name:
                self.engine.load_model(cfg["model_name"])
            if "conf_threshold" in cfg:
                self.conf_threshold = float(cfg["conf_threshold"])
                self.engine.detector.set_confidence(self.conf_threshold)
            if "line_y_ratio" in cfg:
                self.line_y_ratio = float(cfg["line_y_ratio"])
            if "mid_x_ratio" in cfg:
                self.mid_x_ratio = float(cfg["mid_x_ratio"])
            if "swap_directions" in cfg:
                self.swap_directions = bool(cfg["swap_directions"])
            if "target_classes" in cfg:
                self.engine.update_target_classes(cfg["target_classes"])

    def stop(self):
        """Signals the worker thread to terminate and cleans up."""
        self._stop_requested.set()
        self._is_running.clear()
        self._is_paused.clear()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

        with self._lock:
            if self.cap is not None:
                self.cap.release()
                self.cap = None

    def _worker_loop(self):
        """Continuous frame processing loop running in background thread."""
        frame_interval = 1.0 / self.fps if self.fps > 0 else 0.033

        while not self._stop_requested.is_set():
            if not self._is_running.is_set() or self._is_paused.is_set():
                time.sleep(0.04)
                continue

            loop_start = time.perf_counter()

            with self._lock:
                if self.cap is None or not self.cap.isOpened():
                    time.sleep(0.05)
                    continue

                success, frame = self.cap.read()
                if not success:
                    if self.is_live:
                        # Real-time camera brief dropout/reconnect buffer
                        time.sleep(0.04)
                        continue
                    else:
                        # Video ended -> loop seamlessly
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        self.current_frame_idx = 0
                        success, frame = self.cap.read()
                        if not success:
                            self._is_running.clear()
                            time.sleep(0.05)
                            continue

                self.current_frame_idx += 1
                curr_idx = self.current_frame_idx
                line_y = self.line_y_ratio
                mid_x = self.mid_x_ratio
                swap_dir = self.swap_directions

            # Optimal image resize for web delivery
            h, w = frame.shape[:2]
            if w != self.target_width:
                scale = self.target_width / float(w)
                frame = cv2.resize(frame, (self.target_width, int(h * scale)), interpolation=cv2.INTER_LINEAR)

            # Heavy AI pipeline execution
            try:
                cur_start_dt = None if self.is_live else self.start_dt
                annotated_frame, telemetry = self.engine.process_frame(
                    frame=frame,
                    frame_idx=curr_idx,
                    fps=self.fps,
                    start_datetime=cur_start_dt,
                    line_y_ratio=line_y,
                    mid_x_ratio=mid_x,
                    swap_directions=swap_dir,
                    img_size=self.inference_size
                )
                telemetry["is_live"] = self.is_live
            except Exception as err:
                print(f"⚠️ Error during frame inference: {err}")
                time.sleep(0.03)
                continue

            # Fast JPEG compression
            success_enc, buffer = cv2.imencode(
                ".jpg",
                annotated_frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
            )
            if not success_enc:
                continue

            b64_frame = base64.b64encode(buffer).decode("utf-8")
            self.last_telemetry = telemetry

            packet = {
                "type": "frame",
                "image": b64_frame,
                "telemetry": telemetry
            }

            # Non-blocking bounded push (drops oldest frame if WebSocket is lagging)
            try:
                self.frame_queue.put_nowait(packet)
            except queue.Full:
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self.frame_queue.put_nowait(packet)
                except queue.Full:
                    pass

            # Frame rate throttle
            if not self.is_live:
                elapsed = time.perf_counter() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
            else:
                # Live cameras are paced by camera hardware -> yield tiny slice
                time.sleep(0.001)

    def get_events_log(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.engine.events_log)

    def generate_summary(self, start_dt: datetime.datetime) -> List[Dict[str, Any]]:
        with self._lock:
            return self.engine.generate_summary_table(start_dt)
