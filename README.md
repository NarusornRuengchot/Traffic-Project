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

---

## 🏗️ Architecture & Project Structure

```text
Traffic-Project/
├── frontend/                      # ⚛️ React 19 + Vite Web Application
│   ├── src/
│   │   ├── components/            # Header, MetricCards, VideoPlayer, ControlPanel, Charts, EventLogTable
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
│   │   ├── api/                   # FastAPI routers & shared state
│   │   ├── config/                # Settings (paths, host/port, defaults)
│   │   ├── core/                  # VehicleDetector, VehicleTracker, LaneCounter, Analytics, Pipeline
│   │   ├── database/              # SQLite analytics store
│   │   ├── services/              # Stream worker
│   │   ├── visualizer/            # FrameAnnotator (Calibration & HUD Overlays)
│   │   ├── schema/                # Telemetry & Configuration Dataclasses
│   │   └── utils/                 # Video & Model Discovery Helpers
│   ├── tests/
│   ├── models/                    # YOLO weights (*.pt)
│   ├── data/                      # traffic_analytics.db
│   ├── uploads/                   # Uploaded videos
│   └── legacy/                    # Alternative/old UIs: Streamlit app.py, OpenCV main.py, static/, MySQL database.py
│
├── ml/                            # 🧠 Model training (not needed at runtime)
│   ├── notebooks/                 # Colab / Kaggle fine-tuning notebooks
│   ├── tools/                     # Dataset conversion, extraction, training scripts
│   ├── dataset_motorcycles/
│   └── preview_motorcycles/
│
├── scripts/                       # install.bat, run_dashboard.bat
├── Dockerfile, docker-compose.yml
└── README.md
```

---

## ⚙️ Quick Start Guide

### 1. Install Dependencies
Make sure you have Python 3.9+ and Node.js 18+ installed:
```bash
# Install Python packages
pip install -r backend/requirements.txt

# Install React dependencies (Optional if running pre-built dist)
cd frontend
npm install
npm run build
cd ..
```

### 2. Run the React Web Dashboard (Recommended)
Start the FastAPI backend **from inside `backend/`** (models and tracker config are resolved relative to it):
```bash
cd backend
python server.py
```
Or on Windows just double-click `scripts/run_dashboard.bat`.
Open your browser and navigate to:
👉 **`http://localhost:8000`**

---

For frontend development with hot reload, run `npm run dev` in `frontend/` (port 5173) while the backend is running; it talks to `http://127.0.0.1:8000`.

### 3. Run Tests
```bash
cd backend
python -m unittest discover -s tests -t .
```

### 4. Legacy Interfaces (run from `backend/`)
* **Streamlit Python Dashboard:**
  ```bash
  python -m streamlit run legacy/app.py
  ```
* **Desktop OpenCV Visualizer:**
  ```bash
  python -m legacy.main
  ```
