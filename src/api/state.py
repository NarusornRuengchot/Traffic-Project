import threading
from typing import Optional
from src.config.settings import settings
from src.core.traffic_pipeline import TrafficPipeline
from src.services.stream_worker import StreamWorker
from src.utils.file_helper import resolve_video_source

class AppState:
    """
    Centralized thread-safe runtime state management for the FastAPI application.
    Holds reference to global engine and currently active background stream worker.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AppState, cls).__new__(cls)
                cls._instance._init_state()
            return cls._instance

    def _init_state(self):
        self.global_engine = TrafficPipeline(model_name=settings.DEFAULT_MODEL)
        self.active_worker: Optional[StreamWorker] = None
        self._worker_lock = threading.Lock()

    def get_worker(self) -> Optional[StreamWorker]:
        with self._worker_lock:
            return self.active_worker

    def set_worker(self, worker: Optional[StreamWorker]):
        with self._worker_lock:
            self.active_worker = worker

    def resolve_video_path(self, video_path: str) -> str:
        """Finds exact video path in project root, uploads folder, or live webcam/RTSP stream."""
        if not video_path:
            return "webcam:0"
        return resolve_video_source(
            video_path,
            upload_dir=settings.UPLOAD_DIR,
            base_dir=settings.BASE_DIR
        )

app_state = AppState()
