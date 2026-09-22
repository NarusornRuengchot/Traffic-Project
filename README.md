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
│   ├── core/                      # VehicleDetector, VehicleTracker, LaneCounter, Analytics, Pipeline
│   ├── visualizer/                # FrameAnnotator (Calibration & HUD Overlays)
│   ├── schema/                    # Telemetry & Configuration Dataclasses
│   └── utils/                     # Video & Model Discovery Helpers
│
├── server.py                      # 🚀 FastAPI WebSocket & REST Streaming Server
├── ai_engine.py                   # Backward-compatible Adapter
├── app.py                         # Streamlit Interface (Alternative Python UI)
├── main.py                        # Desktop OpenCV Window (Alternative Desktop UI)
├── requirements.txt
└── README.md
```

---

## ⚙️ Quick Start Guide

### 1. Install Dependencies
Make sure you have Python 3.9+ and Node.js 18+ installed:
```bash
# Install Python packages
pip install -r requirements.txt

# Install React dependencies (Optional if running pre-built dist)
cd frontend
npm install
npm run build
cd ..
```

### 2. Run the React Web Dashboard (Recommended)
Simply start the FastAPI backend:
```bash
python server.py
```
Open your browser and navigate to:
👉 **`http://localhost:8000`**

---

### 3. Alternative Interfaces
* **Streamlit Python Dashboard:**
  ```bash
  python -m streamlit run app.py
  ```
* **Desktop OpenCV Visualizer:**
  ```bash
  python main.py
  ```
