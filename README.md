# 🚗 KU SRC Smart Traffic Dashboard

Real-time Vehicle Detection, Tracking & Counting Dashboard for Kasetsart University Sriracha Campus (KU SRC) built with **YOLOv11** and **Streamlit**.

---

## 📊 Features
* **Real-time Vehicle Tracking:** Detects, tracks, and counts vehicles (Cars, Motorcycles, Buses, and Trucks).
* **Direction-based Counting:** Separate counting logic for **Inbound (Left)** and **Outbound (Right)** lanes.
* **Interactive Dashboard Panel:** Adjust YOLO configuration, confidence thresholds, and targeted classes dynamically from the sidebar.
* **Dual Interface Options:** Choose between the interactive Streamlit Web Dashboard or the lightweight OpenCV Desktop view.

---

## ⚙️ Getting Started

Follow these steps to set up and run the application on your local machine.

### Prerequisites
* **Python 3.9** or higher installed.

### 1. Clone the Repository
Clone this repository to your local computer:
```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd "Traffic Project"
```

### 2. Set Up a Virtual Environment (Recommended)
Creating a virtual environment ensures that the dependencies do not conflict with your global Python setup.
* **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
* **On macOS/Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install Dependencies
Install all the required packages:
```bash
pip install -r requirements.txt
```

### 4. Provide the Sample Video File
Since the sample video (`KUSRC_Traffic.MOV`) is very large (~201MB), it is ignored by Git and will not be pushed to GitHub. To run using this sample video:
1. Obtain the video file separately (e.g., from a shared OneDrive or Google Drive).
2. Place the video file `KUSRC_Traffic.MOV` directly into the root of this project directory.

*(Alternatively, you can run the Streamlit dashboard and upload your own traffic video via the sidebar panel).*

---

## 🚀 How to Run the App

You can choose to run the Web Dashboard or the Desktop Visualizer:

### Run the Streamlit Web Dashboard (Local Host Server)
Runs a local web server (usually at `http://localhost:8501`) with full metrics, graphs, and control panels.
```bash
python -m streamlit run app.py
```
> **Note:** The first time you run this, YOLO will automatically download the model weights (`yolov11n.pt`) from the internet.

### Run the OpenCV Desktop Visualizer
Runs the lightweight desktop script that displays the raw video frames with object-tracking bounding boxes directly in a desktop window:
```bash
python main.py
```

---

## 📁 Project Structure
```text
├── app.py                # Main Streamlit web dashboard interface
├── main.py               # Desktop-based OpenCV detection & tracking script
├── requirements.txt      # List of dependencies
├── .gitignore            # Excludes large files (videos, YOLO weights, venv)
└── README.md             # Project documentation (this file)
```
