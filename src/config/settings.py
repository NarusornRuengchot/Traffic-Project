import os
from typing import List

class Settings:
    """
    Centralized configuration settings for the KU SRC Smart Traffic server.
    """
    PROJECT_NAME: str = "KU SRC Smart Traffic Dashboard API"
    VERSION: str = "2.3.0"
    
    # Base filesystem paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    FRONTEND_DIST: str = os.path.join(BASE_DIR, "frontend", "dist")
    STATIC_DIR: str = os.path.join(BASE_DIR, "static")
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    
    # Server network settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: List[str] = ["*"]
    
    # Video & Stream defaults
    DEFAULT_MODEL: str = "best.pt" if os.path.exists(os.path.join(BASE_DIR, "best.pt")) else "yolov11n.pt"
    DEFAULT_CONF_THRESHOLD: float = 0.25
    DEFAULT_INFERENCE_SIZE: int = 480
    DEFAULT_STREAM_WIDTH: int = 960
    DEFAULT_JPEG_QUALITY: int = 65
    
    # Camera / CCTV timeouts (milliseconds)
    CCTV_TIMEOUT_MS: int = 4000

    def __init__(self):
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.DATA_DIR, exist_ok=True)

settings = Settings()
