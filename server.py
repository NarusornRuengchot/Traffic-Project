"""
KU SRC Smart Traffic Analytics - Main Server Application
Modular FastAPI entry point with WebSocket streaming, REST analytics API, and SPA serving.
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.config.settings import settings
from src.api.state import app_state

# Import routers
from src.api.routers.media import router as media_router
from src.api.routers.reports import router as reports_router
from src.api.routers.cctv import router as cctv_router
from src.api.routers.stream import router as stream_router

# Backward compatibility re-exports for existing tests & scripts
from src.api.routers.media import (
    get_models,
    get_videos,
    upload_video,
    get_calibration_preview,
    export_data,
)
from src.api.routers.reports import (
    get_peak_hours_report,
    get_history_report,
    get_report_dates,
    export_report_csv,
    get_incidents_report,
    get_speed_report,
)
from src.api.routers.cctv import test_cctv_endpoint
from src.api.routers.stream import websocket_stream_endpoint

# Expose legacy attributes
BASE_DIR = settings.BASE_DIR
FRONTEND_DIST = settings.FRONTEND_DIST
STATIC_DIR = settings.STATIC_DIR
UPLOAD_DIR = settings.UPLOAD_DIR
DEFAULT_MODEL = settings.DEFAULT_MODEL
global_engine = app_state.global_engine
resolve_video_path = app_state.resolve_video_path

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-time Vehicle Detection, Tracking, and Congestion Analytics API"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file mounts
if os.path.exists(os.path.join(settings.FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(settings.FRONTEND_DIST, "assets")), name="assets")
if os.path.exists(settings.STATIC_DIR):
    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Register Modular Routers
app.include_router(media_router)
app.include_router(reports_router)
app.include_router(cctv_router)
app.include_router(stream_router)

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves compiled React frontend SPA or fallback static page."""
    react_index = os.path.join(settings.FRONTEND_DIST, "index.html")
    if os.path.exists(react_index):
        return FileResponse(react_index)
    static_index = os.path.join(settings.STATIC_DIR, "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return HTMLResponse("<h2>KU SRC Traffic Dashboard is starting...</h2>")

if __name__ == "__main__":
    print(f"🚀 Starting KU SRC Smart Traffic Server on http://{settings.HOST}:{settings.PORT} ...")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
