# 🚗 KU SRC Smart Traffic Analytics Dashboard (React + YOLOv11)

Real-time Vehicle Detection, Tracking, Bidirectional Counting & Congestion Analytics Dashboard for Kasetsart University Sriracha Campus (KU SRC) built with **YOLOv11**, **ByteTrack**, **FastAPI WebSocket**, and **React (Vite)**.

---

## 📊 Features & Capabilities
* **⚛️ Ultra-Fast React Dashboard:** Modern, responsive Web UI with Dark/Light theme, live SVG telemetry charts, and interactive Tripwire Calibration.
* **⚡ Full-Duplex WebSocket Streaming:** Zero-lag real-time video streaming with live vehicle counting and instant telemetry updates.
* **🚗 Multi-Class Vehicle Tracking:** Real-time tracking for Cars, Motorcycles, Buses, and Trucks using ByteTrack.
* **↔️ Bidirectional Tripwire Counting:** High-precision crossover mathematics for separate Inbound (เข้าเมือง) and Outbound (ออกเมือง) counting.
* **🚦 Intelligent Traffic Congestion Scoring:** Calculates rolling density score and stall ratio (Smooth, Moderate, Congested, Gridlock).
* **📁 Video Upload & Model Switcher:** Support for custom video uploads (.mp4, .mov) and dynamic YOLO model selection (`best.pt`, `yolov11n.pt`, etc.).
* **📋 Event Log & CSV Export:** Real-time table of crossing vehicles with search, filtering, and 1-click CSV download.
* **🔐 User Authentication:** Register / login with hashed passwords and token-based sessions (default admin: `admin` / `admin123`).
* **🏢 Business Dashboard:** Manage businesses and their CCTV cameras, with footfall, peak-hour and target KPIs.
* **⚖️ Model Benchmark:** Compare accuracy and speed of several YOLO models on the same video frames.
* **📱 Mobile-Friendly UI:** Bottom navigation layout for phones.

See [docs/walkthrough.md](docs/walkthrough.md) for details on the authentication, business, and mobile features.

---

## 🏗️ Architecture & Project Structure

```text
Traffic-Project/
├── frontend/                      # ⚛️ React 19 + Vite Web Application
│   ├── src/
│   │   ├── components/            # Header, MetricCards, VideoPlayer, ControlPanel, Charts, EventLogTable,
│   │   │                          # AuthModal, BusinessDashboard, ModelComparison, MobileBottomNav
│   │   ├── hooks/                 # useTrafficWebSocket (Real-time Stream & Commands)
│   │   ├── services/              # REST API Client
│   │   ├── App.jsx                # Dashboard Layout
│   │   └── index.css              # Modern Theme & Styling System
│   └── dist/                      # Production Build (served automatically by FastAPI)
│
├── backend/                       # 🐍 FastAPI server + AI engine (run everything from here)
│   ├── server.py                  # 🚀 FastAPI WebSocket & REST Streaming Server
│   ├── ai_engine.py               # Backward-compatible Adapter
│   ├── custom_tracker.yaml        # ByteTrack configuration
│   ├── requirements.txt
│   ├── src/                       # Modular Python Core Engine
│   │   ├── api/                   # FastAPI routers (stream, media, reports, cctv, auth, business, benchmark)
│   │   ├── config/                # Settings (paths, host/port, defaults)
│   │   ├── core/                  # VehicleDetector, VehicleTracker, LaneCounter, Analytics, Pipeline
│   │   ├── database/              # SQLite analytics, users & business data
│   │   ├── services/              # Stream worker, model benchmark service
│   │   ├── visualizer/            # FrameAnnotator (Calibration & HUD Overlays)
│   │   ├── schema/                # Telemetry & Configuration Dataclasses
│   │   └── utils/                 # Video & Model Discovery Helpers, password/token security
│   ├── tests/                     # 🧪 Automated Test Suite
│   ├── models/                    # 🧠 YOLO weights (best.pt, yolo26n.pt, yolo26s.pt, yolov11n.pt)
│   ├── data/                      # 📊 traffic_analytics.db
│   ├── uploads/                   # 🎬 Video files (e.g., IMG_1357.MOV)
│   └── legacy/                    # Alternative UIs: OpenCV main.py, old static/ page
│
├── ml/                            # 🧠 Model training (not needed at runtime)
│   ├── notebooks/                 # Colab / Kaggle fine-tuning notebooks
│   ├── tools/                     # Dataset conversion, extraction, training scripts
│   └── dataset_motorcycles/       # 50 auto-labeled motorcycle frames + data.yaml
│
├── scripts/
│   ├── install.bat                # 📦 Windows setup & dependency installer
│   ├── run_dashboard.bat          # 🪟 Windows quick start
│   └── run.sh                     # 🐧 Linux Cloud start script (FastAPI on custom port)
├── docs/                          # 📄 Feature walkthroughs
├── Dockerfile, docker-compose.yml
└── README.md
```

---

## ⚙️ Quick Start Guide

### 1. Install Dependencies
Make sure you have Python 3.9 - 3.12 and Node.js 18+ installed:
```bash
# Windows automatic setup
scripts\install.bat

# Or manual installation
pip install -r backend/requirements.txt

# Build the React frontend
cd frontend
npm install
npm run build
cd ..
```

### 2. Run the React Web Dashboard (Recommended)
Start the FastAPI backend **from inside `backend/`** (models, uploads and tracker config are resolved relative to it):
```bash
cd backend
python server.py
```
Or use the start scripts:
* Windows: double-click `scripts\run_dashboard.bat`
* Linux: `bash scripts/run.sh` (defaults to port 3047)

Open your browser and navigate to:
👉 **`http://localhost:8000`**

For frontend development with hot reload, run `npm run dev` in `frontend/` (port 5173) while the backend is running; it talks to `http://127.0.0.1:8000`.

### 3. Run Tests
```bash
cd backend
python -m unittest discover -s tests -t .
```

### 4. Alternative Desktop Interface (run from `backend/`)
* **Desktop OpenCV Visualizer:**
  ```bash
  python -m legacy.main
  ```
