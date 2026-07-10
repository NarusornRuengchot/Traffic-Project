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
* **Python 3.9 - 3.12** installed (Python 3.12 is highly recommended. Python 3.13 requires C++ compiler tools to compile tracking dependencies like `lapx`, so setup might fail on 3.13 if they are missing).

### 🚀 Windows Auto-Setup (Easiest)
If you are on Windows, simply double-click the **`install.bat`** file in this folder (or run it via Command Prompt).
It will automatically:
1. Create a Python virtual environment (`venv`).
2. Upgrade `pip` to the latest version.
3. Install all required dependencies (including Streamlit, Ultralytics, PyTorch, etc.).
4. Report any potential issues.

---

### 💻 Manual Setup

#### 1. Clone the Repository
Clone this repository to your local computer:
```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd "Traffic Project"
```

#### 2. Set Up a Virtual Environment (Recommended)
Creating a virtual environment ensures that the dependencies do not conflict with your global Python setup.
* **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
  *(If you get an execution policy error, see the Troubleshooting section below).*
* **On macOS/Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

#### 3. Install Dependencies
Install all the required packages:
```bash
pip install -r requirements.txt
```

#### 4. Provide the Sample Video File
Since the sample video (`KUSRC_Traffic.MOV`) is very large (~201MB), it is ignored by Git and will not be pushed to GitHub. To run using this sample video:
1. Obtain the video file separately (e.g., from a shared OneDrive or Google Drive).
2. Place the video file `KUSRC_Traffic.MOV` directly into the root of this project directory.

*(Alternatively, you can run the Streamlit dashboard and upload your own traffic video via the sidebar panel).*

---

## 🚀 How to Run the App

You can choose to run the Web Dashboard or the Desktop Visualizer. First, make sure your virtual environment is active:

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

## 🛠️ VS Code & Windows Troubleshooting

If your friend is using **VS Code on Windows**, they are likely running into one of these common errors:

### 1. PowerShell Script Execution Policy Error (VS Code Terminal)
* **Symptom:** When running `.\venv\Scripts\Activate.ps1`, PowerShell shows a red error:
  `... cannot be loaded because running scripts is disabled on this system.`
* **Fix A (Recommended):** Use Command Prompt (`cmd`) terminal in VS Code instead of PowerShell, or simply run the command:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\venv\Scripts\Activate.ps1
  ```
* **Fix B:** In the VS Code terminal, select Python Interpreter:
  1. Press `Ctrl + Shift + P` (or `Cmd + Shift + P` on Mac) to open the Command Palette.
  2. Search for **"Python: Select Interpreter"**.
  3. Select the interpreter labeled **`venv`** (e.g., `.\venv\Scripts\python.exe`).
  4. Open a *new* terminal in VS Code; it will activate the virtual environment automatically.

### 2. `lapx` Installation Failures (Python Version / Build Tools)
* **Symptom:** `pip install -r requirements.txt` fails when compiling `lapx` with error `Microsoft Visual C++ 14.0 or greater is required`.
* **Why it happens:** The tracking algorithm ByteTrack/BoT-SORT needs `lapx`. If your friend is using Python 3.13, PyPI does not have a pre-built wheel for `lapx` yet, so it tries to compile it from source, which requires Visual Studio C++ compiler tools.
* **Fix A (Recommended):** Install **Python 3.12** instead of Python 3.13. Pre-built wheels for Python 3.12 are fully supported and will install instantly without needing any compilers.
* **Fix B:** Install **Microsoft C++ Build Tools** from [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and select the "Desktop development with C++" workload, then try installing again.

---

## 📁 Project Structure
```text
├── app.py                # Main Streamlit web dashboard interface
├── main.py               # Desktop-based OpenCV detection & tracking script
├── install.bat           # One-click Windows setup script (creates venv & installs deps)
├── requirements.txt      # List of dependencies
├── .gitignore            # Excludes large files (videos, YOLO weights, venv)
└── README.md             # Project documentation (this file)
```

