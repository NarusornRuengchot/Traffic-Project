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
seminar/
├── frontend/                      # ⚛️ React 19 + Vite Web Application
│   ├── src/
│   │   ├── components/            # Header, MetricCards, VideoPlayer, ControlPanel, Charts, EventLogTable
│   │   ├── hooks/                 # useTrafficWebSocket (Real-time Stream & Commands)
│   │   ├── services/              # REST API Client
│   │   ├── App.jsx                # Dashboard Layout
│   │   └── index.css              # Modern Theme & Styling System
│   └── dist/                      # Production Build (served automatically by FastAPI)
│
├── src/                           # 🐍 Modular Python Core Engine
│   ├── api/                       # REST & WebSocket route handlers
│   ├── config/                    # Environment & configuration settings
│   ├── core/                      # VehicleDetector, VehicleTracker, LaneCounter, Analytics, Pipeline
│   ├── database/                  # SQLite analytics & incident logging
│   ├── services/                  # StreamWorker background tasks
│   ├── utils/                     # Video & Model Discovery Helpers
│   └── visualizer/                # FrameAnnotator (Calibration & HUD Overlays)
│
├── models/                        # 🧠 YOLO Weights (best.pt, yolo26n.pt, yolo26s.pt, yolov11n.pt)
├── data/                          # 📊 SQLite database & datasets
│   ├── traffic_analytics.db
│   └── dataset_motorcycles/       # 50 auto-labeled motorcycle frames + data.yaml
│
├── uploads/                       # 🎬 Video files (e.g., IMG_1357.MOV)
├── tools/                         # 🛠️ Training & fine-tuning utilities
│   ├── notebooks/                 # Colab & Kaggle fine-tuning notebooks
│   ├── train_yolo26.py
│   ├── extract_motorcycles.py
│   └── upload_to_roboflow.py
│
├── tests/                         # 🧪 Automated Test Suite (27 test cases)
├── server.py                      # 🚀 FastAPI WebSocket & REST Streaming Server
├── main.py                        # 🖥️ Desktop OpenCV Window (Alternative Desktop UI)
├── ai_engine.py                   # 🔄 Backward-compatible Adapter
├── run.sh                         # 🐧 Linux Cloud start script (FastAPI on custom port)
├── run_dashboard.bat              # 🪟 Windows quick start batch script
├── install.bat                    # 📦 Windows setup & dependency installer
├── requirements.txt
└── README.md
```

---

## ⚙️ Quick Start Guide

### 1. Install Dependencies
Make sure you have Python 3.9 - 3.12 and Node.js 18+ installed:
```bash
# Windows automatic setup
install.bat

# Or manual installation
pip install -r requirements.txt
```

### 2. Run the React Web Dashboard (Recommended)
On Windows:
```cmd
run_dashboard.bat
```
Or run Python directly:
```bash
python server.py
```
Open your browser and navigate to:
👉 **`http://localhost:8000`**

### 3. Alternative Desktop Interface
* **Desktop OpenCV Visualizer:**
  ```bash
  python main.py
  ```

