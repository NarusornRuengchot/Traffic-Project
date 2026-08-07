import cv2
import tempfile
import streamlit as st
import pandas as pd
import torch
import os
import datetime
from ultralytics import YOLO

# ---------------------------------------------------------
# Web Page Layout Configuration & Theme Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="KU SRC Smart Traffic Dashboard",
    page_icon="🚗",
    layout="wide"
)

# ---------------------------------------------------------
# Dark / Light Mode State
# ---------------------------------------------------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True  # default: dark mode

# Toggle button in the top-right area
col_title_area, col_theme_btn = st.columns([10, 1])
with col_theme_btn:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️", help="Switch between Dark / Light mode", key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# Inject dynamic CSS based on current theme
if st.session_state.dark_mode:
    THEME_BG          = "#0F1117"
    THEME_CARD_BG     = "#1C1F2B"
    THEME_SIDEBAR_BG  = "#161822"
    THEME_TEXT        = "#E8ECF4"
    THEME_SUBTEXT     = "#A0A8BC"
    THEME_BORDER      = "#2E3348"
    THEME_ACCENT      = "#4F8EF7"
    THEME_HEADER_CLR  = "#7EB3FF"
    THEME_METRIC_CLR  = "#E8ECF4"
    THEME_BTN_BG      = "#2563EB"
    THEME_BTN_TEXT    = "#FFFFFF"
else:
    THEME_BG          = "#F0F4FF"
    THEME_CARD_BG     = "#FFFFFF"
    THEME_SIDEBAR_BG  = "#EEF2FF"
    THEME_TEXT        = "#1E293B"
    THEME_SUBTEXT     = "#4B5563"
    THEME_BORDER      = "#CBD5E1"
    THEME_ACCENT      = "#2563EB"
    THEME_HEADER_CLR  = "#1E3A8A"
    THEME_METRIC_CLR  = "#1E293B"
    THEME_BTN_BG      = "#3B82F6"
    THEME_BTN_TEXT    = "#FFFFFF"

st.markdown(f"""
    <style>
        /* ===== Global Background ===== */
        .stApp, .stApp > header {{
            background-color: {THEME_BG} !important;
        }}
        /* ===== Main Content Area ===== */
        section.main > div.block-container {{
            background-color: {THEME_BG};
            padding-top: 1rem;
        }}
        /* ===== Sidebar ===== */
        section[data-testid="stSidebar"] > div {{
            background-color: {THEME_SIDEBAR_BG} !important;
            border-right: 1px solid {THEME_BORDER};
        }}
        section[data-testid="stSidebar"] * {{
            color: {THEME_TEXT} !important;
        }}
        /* ===== Typography ===== */
        .main-header {{
            font-size: 2.2rem;
            font-weight: 700;
            color: {THEME_HEADER_CLR};
            margin-bottom: 0.1rem;
        }}
        .sub-header {{
            font-size: 1.1rem;
            color: {THEME_SUBTEXT};
            margin-bottom: 1.5rem;
        }}
        /* ===== Metric Cards ===== */
        div[data-testid="stMetricValue"] {{
            font-size: 2.5rem;
            font-weight: 800;
            color: {THEME_METRIC_CLR} !important;
        }}
        div[data-testid="stMetricLabel"] {{
            font-size: 1rem;
            font-weight: 600;
            color: {THEME_SUBTEXT} !important;
        }}
        div[data-testid="metric-container"] {{
            background-color: {THEME_CARD_BG};
            border: 1px solid {THEME_BORDER};
            border-radius: 12px;
            padding: 1rem 1.25rem;
        }}
        /* ===== General text ===== */
        p, h1, h2, h3, h4, h5, h6, label, .stMarkdown, .stText {{
            color: {THEME_TEXT} !important;
        }}
        /* ===== Info/Success/Warning boxes ===== */
        div[data-testid="stAlert"] {{
            background-color: {THEME_CARD_BG};
            border-color: {THEME_BORDER};
            color: {THEME_TEXT};
        }}
        /* ===== DataFrames ===== */
        div[data-testid="stDataFrame"] {{
            background-color: {THEME_CARD_BG};
            border-radius: 10px;
        }}
        /* ===== Buttons ===== */
        .stButton > button {{
            background-color: {THEME_BTN_BG};
            color: {THEME_BTN_TEXT};
            border: none;
            border-radius: 8px;
            transition: opacity 0.2s;
        }}
        .stButton > button:hover {{
            opacity: 0.85;
        }}
        /* ===== Progress bar ===== */
        div[data-testid="stProgress"] > div {{
            background-color: {THEME_ACCENT};
        }}
        /* ===== Expander ===== */
        details {{
            background-color: {THEME_CARD_BG};
            border: 1px solid {THEME_BORDER};
            border-radius: 10px;
        }}
        /* ===== selectbox / slider / radio track ===== */
        .stSelectbox > div > div,
        .stMultiSelect > div > div {{
            background-color: {THEME_CARD_BG};
            color: {THEME_TEXT};
            border-color: {THEME_BORDER};
        }}
    </style>
""", unsafe_allow_html=True)

with col_title_area:
    st.markdown('<div class="main-header">🚗 Kasetsart University Sriracha Campus</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time Vehicle Detection, Tracking &amp; Counting Dashboard (YOLOv11 / YOLOv8)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar Panel Configuration
# ---------------------------------------------------------
st.sidebar.header("📊 Dashboard Control Panel")

# 1. Data Source Section
st.sidebar.subheader("1. Video Source")
source_type = st.sidebar.radio(
    "Choose Video Source:",
    ["Use Local Sample Video (KUSRC_Traffic.MOV)", "Upload Custom Video File"]
)

video_path = None
if source_type == "Upload Custom Video File":
    uploaded_file = st.sidebar.file_uploader("Upload Traffic Video Clip", type=["mp4", "mov", "avi"])
    if uploaded_file is not None:
        # Save to temporary file for OpenCV access
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded_file.read())
        video_path = tfile.name
else:
    sample_file = "KUSRC_Traffic.MOV"
    if os.path.exists(sample_file):
        video_path = sample_file
    else:
        st.sidebar.error(f"Sample file '{sample_file}' was not found in the project workspace.")

# 2. Model Parameters
st.sidebar.subheader("2. Model Configuration")
model_version = st.sidebar.selectbox(
    "YOLO Architecture Version:",
    ["YOLOv11 (Newest)", "YOLOv8"],
    index=0,
    help="Choose between YOLOv11 (newer, more optimized) and YOLOv8."
)

if model_version == "YOLOv11 (Newest)":
    model_size = st.sidebar.selectbox(
        "YOLOv11 Model Size:",
        ["yolov11n.pt", "yolov11s.pt", "yolov11m.pt", "yolov11l.pt", "yolov11x.pt"],
        index=0,
        help="n: Nano (fastest), s: Small, m: Medium, l: Large, x: Extra-Large"
    )
else:
    model_size = st.sidebar.selectbox(
        "YOLOv8 Model Size:",
        ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"],
        index=0,
        help="n: Nano (fastest), s: Small, m: Medium, l: Large, x: Extra-Large"
    )

# Fine-tuned model option
if os.path.exists("best.pt"):
    use_finetuned = st.sidebar.checkbox(
        "🎯 ใช้โมเดลที่ Fine-tuned แล้ว (best.pt)",
        value=True,
        help="โมเดลที่เทรนเพิ่มเติมจาก Kaggle — แม่นยำกว่าสำหรับ bus, car, motorcycle, truck"
    )
    if use_finetuned:
        model_size = "best.pt"

conf_threshold = st.sidebar.slider(
    "Model Confidence Threshold:",
    min_value=0.10, max_value=1.00, value=0.25, step=0.05,
    help="Lower values detect more objects but may include false positives."
)

target_classes = st.sidebar.multiselect(
    "Detect & Count Classes:",
    ["Car", "Motorcycle", "Bus", "Truck"],
    default=["Car", "Motorcycle", "Bus", "Truck"]
)

# Device selection (CPU or CUDA GPU)
device_options = ["cpu"]
if torch.cuda.is_available():
    device_options.insert(0, "cuda")
device = st.sidebar.selectbox("Processing Engine:", device_options)

# 3. Performance Tuning
st.sidebar.subheader("3. Performance Tuning")
frame_skip = st.sidebar.slider(
    "Frame Skip Rate:",
    min_value=1, max_value=10, value=2, step=1,
    help="Processes every N-th frame. 1 processes all frames (slowest). Increase for CPU speedups."
)

img_size = st.sidebar.selectbox(
    "Inference Resolution (Image Size):",
    [640, 1280],
    index=0,
    help="640 is standard/fast. 1280 improves detection of small/distant vehicles but runs slower."
)

# 4. Calibration Section
st.sidebar.subheader("4. Detection Line Calibration")
line_y_percentage = st.sidebar.slider(
    "Line Height (Vertical %)", 
    min_value=0.1, max_value=0.9, value=0.50, step=0.05,
    help="Adjusts the height of the counting line on the screen."
)

mid_x_percentage = st.sidebar.slider(
    "Lane Divider (Horizontal %)", 
    min_value=0.1, max_value=0.9, value=0.45, step=0.05,
    help="Adjusts the split point dividing Left and Right traffic lanes."
)

# 4b. Direction Swap
st.sidebar.subheader("4b. Lane Direction")
swap_directions = st.sidebar.toggle(
    "🔄 สลับ Inbound ↔ Outbound",
    value=False,
    help="เปิดเพื่อสลับทิศทาง: ฝั่งซ้ายจะกลายเป็น Outbound และฝั่งขวาจะกลายเป็น Inbound"
)
if swap_directions:
    st.sidebar.info("🔄 โหมดสลับทิศทาง: ซ้าย = Outbound | ขวา = Inbound")
else:
    st.sidebar.info("➡️ โหมดปกติ: ซ้าย = Inbound | ขวา = Outbound")

# 5. Video Filming Time Configuration
st.sidebar.subheader("5. Video Filming Time")
enable_filming_time = st.sidebar.checkbox(
    "Specify Video Filming Time", 
    value=True,
    help="Enable to specify when this video was filmed to assess traffic level relative to real-world time."
)

if enable_filming_time:
    filming_date = st.sidebar.date_input("Filming Date", value=pd.Timestamp.now().date())
    filming_time = st.sidebar.time_input("Filming Start Time", value=datetime.time(8, 30))
    start_datetime = datetime.datetime.combine(filming_date, filming_time)
else:
    start_datetime = datetime.datetime.now()

# Class mappings — fine-tuned model ใช้ class index 0-3 (bus=0, car=1, motorcycle=2, truck=3)
# COCO model ใช้ index ปกติ (car=2, motorcycle=3, bus=5, truck=7)
if model_size == "best.pt":
    class_map = {"Car": 1, "Motorcycle": 2, "Bus": 0, "Truck": 3}
    coco_to_name = {1: "Car", 2: "Motorcycle", 0: "Bus", 3: "Truck"}
else:
    class_map = {"Car": 2, "Motorcycle": 3, "Bus": 5, "Truck": 7}
    coco_to_name = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}
selected_class_ids = [class_map[c] for c in target_classes]

def resolve_model_path(model_name):
    # Check if the file exists exactly as named
    if os.path.exists(model_name):
        return model_name
        
    # Check alternatives for YOLOv11 (with/without 'v' inside the name)
    if "yolov11" in model_name:
        alt_name = model_name.replace("yolov11", "yolo11")
        if os.path.exists(alt_name):
            return alt_name
    elif "yolo11" in model_name:
        alt_name = model_name.replace("yolo11", "yolov11")
        if os.path.exists(alt_name):
            return alt_name
            
    # Check alternatives for YOLOv8 (with/without 'v')
    if "yolov8" in model_name:
        alt_name = model_name.replace("yolov8", "yolo8")
        if os.path.exists(alt_name):
            return alt_name
    elif "yolo8" in model_name:
        alt_name = model_name.replace("yolo8", "yolov8")
        if os.path.exists(alt_name):
            return alt_name
            
    return model_name

# Persistent initialization of the model
@st.cache_resource
def load_yolo_model(model_name):
    resolved_name = resolve_model_path(model_name)
    return YOLO(resolved_name)

# Cache video metadata and the first frame for calibration preview
@st.cache_data
def get_video_metadata(vid_path):
    cap = cv2.VideoCapture(vid_path)
    if not cap.isOpened():
        return None
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    success, frame = cap.read()
    cap.release()
    if success:
        return {
            "width": width,
            "height": height,
            "fps": fps if fps > 0 else 30.0,
            "total_frames": total_frames,
            "first_frame": frame
        }
    return None

def get_traffic_level(density, stall_ratio=0.0):
    """
    ประเมินระดับการจราจรโดยพิจารณาทั้งจำนวนรถ และสัดส่วนรถที่หยุดนิ่ง
    density    : จำนวนรถเฉลี่ยบนจอ (rolling average)
    stall_ratio: สัดส่วน 0-1 ของรถที่แทบไม่ขยับ (0 = ทุกคันวิ่ง, 1 = หยุดหมด)
    """
    # stall_ratio เพิ่มคะแนนเล็กน้อย (0.2) เพื่อไม่ให้ Gridlock เร็วเกินไปจากรถหยุดรอระสั้นๆ
    score = density * (1.0 + 0.2 * stall_ratio)

    # Threshold ปรับเพื่อให้เหมาะถนน 4 เลนในมหาวิทยาลัย
    if score <= 5:
        return "Smooth (คล่องตัว)", "🟢", "Smooth"
    elif score <= 12:
        return "Moderate (ปานกลาง)", "🟡", "Moderate"
    elif score <= 20:
        return "Congested (หนาแน่น)", "🟠", "Congested"
    else:
        return "Gridlock (หนาแน่นมาก)", "🔴", "Gridlock"

def generate_traffic_summary_table(flow_history, start_dt):
    if not flow_history or start_dt is None:
        return None
    df = pd.DataFrame(flow_history)
    if "Time (s)" not in df.columns or "Active Vehicles" not in df.columns:
        return None
        
    df["Interval Time"] = df["Time (s)"].apply(lambda t: int(t // 10) * 10)
    df["Interval Real Time"] = df["Interval Time"].apply(lambda t: (start_dt + datetime.timedelta(seconds=t)).strftime("%H:%M:%S"))
    
    summary = df.groupby("Interval Real Time").agg(
        avg_active=("Active Vehicles", "mean"),
        inbound_max=("Inbound", "max"),
        inbound_min=("Inbound", "min"),
        outbound_max=("Outbound", "max"),
        outbound_min=("Outbound", "min"),
    ).reset_index()
    
    summary["Vehicles Passed (Inbound)"] = summary["inbound_max"] - summary["inbound_min"]
    summary["Vehicles Passed (Outbound)"] = summary["outbound_max"] - summary["outbound_min"]
    
    summary["Traffic Level"] = summary["avg_active"].apply(lambda d: f"{get_traffic_level(d)[1]} {get_traffic_level(d)[0]}")
    summary["Avg Vehicles on Screen"] = summary["avg_active"].round(1)
    
    return summary[["Interval Real Time", "Avg Vehicles on Screen", "Traffic Level", "Vehicles Passed (Inbound)", "Vehicles Passed (Outbound)"]].rename(
        columns={
            "Interval Real Time": "ช่วงเวลา (Time)",
            "Avg Vehicles on Screen": "ความหนาแน่นเฉลี่ย (Avg Vehicles)",
            "Traffic Level": "ระดับการจราจร (Traffic Level)",
            "Vehicles Passed (Inbound)": "จำนวนรถผ่านขาเข้า (Inbound Flow)",
            "Vehicles Passed (Outbound)": "จำนวนรถผ่านขาออก (Outbound Flow)"
        }
    )

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "processing" not in st.session_state:
    st.session_state.processing = False
if "inbound_count" not in st.session_state:
    st.session_state.inbound_count = 0
if "outbound_count" not in st.session_state:
    st.session_state.outbound_count = 0
if "counted_ids" not in st.session_state:
    st.session_state.counted_ids = set()
if "class_counts" not in st.session_state:
    st.session_state.class_counts = {c: 0 for c in class_map.keys()}
if "events_log" not in st.session_state:
    st.session_state.events_log = []
if "flow_history" not in st.session_state:
    st.session_state.flow_history = []
if "track_history" not in st.session_state:
    st.session_state.track_history = {}
if "active_vehicles_history" not in st.session_state:
    st.session_state.active_vehicles_history = []
if "start_datetime" not in st.session_state:
    st.session_state.start_datetime = None
# ประวัติพิกัดรถสำหรับคำนวณ stall ratio (ว่ารถวิ่งหรือหยุด)
if "prev_positions" not in st.session_state:
    st.session_state.prev_positions = {}
# ประวัติตำแหน่งรถแยกฝั่งเพื่อคำนวณ density ขาเข้า/ขาออก
if "inbound_active_history" not in st.session_state:
    st.session_state.inbound_active_history = []
if "outbound_active_history" not in st.session_state:
    st.session_state.outbound_active_history = []

# Load model
model = None
fallback_model = "yolov11n.pt" if ("yolov11" in model_size or "yolo11" in model_size) else "yolov8n.pt"
try:
    model = load_yolo_model(model_size)
except Exception as e:
    st.sidebar.warning(f"⚠️ Could not load '{model_size}'. Falling back to local '{fallback_model}'.")
    try:
        model = load_yolo_model(fallback_model)
    except Exception as e2:
        st.sidebar.error(f"❌ Critical Error: Failed to load fallback model '{fallback_model}'.")

if model is None:
    st.error(f"Failed to load any YOLO model. Please ensure '{fallback_model}' is present in the project directory.")
    st.stop()

# ---------------------------------------------------------
# Main Application Flow
# ---------------------------------------------------------
if video_path is not None:
    video_info = get_video_metadata(video_path)
    
    if video_info is None:
        st.error("Error reading the video clip. Please check the format and try again.")
    else:
        width = video_info["width"]
        height = video_info["height"]
        fps = video_info["fps"]
        total_frames = video_info["total_frames"]
        first_frame = video_info["first_frame"]
        
        # Calculate dynamic line coordinates
        LINE_Y = int(height * line_y_percentage)
        MID_X = int(width * mid_x_percentage)
        
        INBOUND_START, INBOUND_END = (0, LINE_Y), (MID_X, LINE_Y)
        OUTBOUND_START, OUTBOUND_END = (MID_X, LINE_Y), (width, LINE_Y)
        
        # Action Buttons Layout
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            start_clicked = st.button("▶️ Start Video Analysis", type="primary", use_container_width=True)
            if start_clicked:
                st.session_state.processing = True
                # Reset metrics for new run
                st.session_state.inbound_count = 0
                st.session_state.outbound_count = 0
                st.session_state.counted_ids = set()
                st.session_state.class_counts = {c: 0 for c in target_classes}
                st.session_state.events_log = []
                st.session_state.flow_history = []
                st.session_state.track_history = {}
                st.session_state.active_vehicles_history = []
                st.session_state.prev_positions = {}
                st.session_state.inbound_active_history = []
                st.session_state.outbound_active_history = []
                st.session_state.start_datetime = start_datetime
        with col_btn2:
            stop_clicked = st.button("⏹️ Stop / Pause Analysis", type="secondary", use_container_width=True)
            if stop_clicked:
                st.session_state.processing = False
        
        # If NOT currently processing, show static calibration preview
        if not st.session_state.processing:
            st.info("🔧 Review the detection boundaries overlay on the frame below. Adjust the sliders in the sidebar to realign the zones before starting analysis.")
            
            # Prepare preview frame overlay
            preview = first_frame.copy()
            cv2.line(preview, INBOUND_START, INBOUND_END, (255, 255, 0), 4)      # Inbound: Cyan
            cv2.line(preview, OUTBOUND_START, OUTBOUND_END, (0, 165, 255), 4)   # Outbound: Orange
            cv2.circle(preview, (MID_X, LINE_Y), 10, (0, 0, 255), -1)           # Midpoint: Red dot
            
            preview_rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
            st.image(preview_rgb, caption="Static Calibration Preview (First Frame of Video)", use_container_width=True)
            
            # If we have run logs from a previous run, display final stats
            if len(st.session_state.events_log) > 0:
                st.success(f"📈 Analysis ended/paused. Total Processed Count: {st.session_state.inbound_count + st.session_state.outbound_count} vehicles.")
                
                # Calculate final/average metrics
                df_flow_all = pd.DataFrame(st.session_state.flow_history)
                avg_density = df_flow_all["Active Vehicles"].mean() if not df_flow_all.empty else 0.0
                peak_density = df_flow_all["Active Vehicles"].max() if not df_flow_all.empty else 0
                avg_lvl, avg_emoji, _ = get_traffic_level(avg_density)
                peak_lvl, peak_emoji, _ = get_traffic_level(peak_density)
                
                # Metrics cards
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Final Inbound Traffic", st.session_state.inbound_count)
                col_m2.metric("Final Outbound Traffic", st.session_state.outbound_count)
                col_m3.metric("Average Congestion Level", f"{avg_emoji} {avg_lvl}", help=f"Peak level: {peak_emoji} {peak_lvl}")
                
                # Visual charts breakdown
                col_c1, col_c2 = st.columns([1, 1])
                with col_c1:
                    st.markdown("#### Final Class Distribution")
                    df_classes = pd.DataFrame({
                        "Vehicle Type": list(st.session_state.class_counts.keys()),
                        "Total Counted": list(st.session_state.class_counts.values())
                    })
                    st.bar_chart(df_classes.set_index("Vehicle Type"), use_container_width=True)
                with col_c2:
                    st.markdown("#### Cumulative Traffic Timeline (Real-world Time)")
                    df_flow = pd.DataFrame(st.session_state.flow_history).drop_duplicates(subset=["Real-world Time"], keep="last")
                    st.line_chart(df_flow.set_index("Real-world Time")[["Inbound", "Outbound", "Active Vehicles"]], use_container_width=True)
                
                # Grouped Traffic Summary Table
                st.markdown("### 📊 ตารางสรุปสภาพการจราจรตามช่วงเวลา (Traffic Congestion Summary by Time)")
                summary_df = generate_traffic_summary_table(st.session_state.flow_history, st.session_state.get("start_datetime", start_datetime))
                if summary_df is not None:
                    st.dataframe(summary_df, use_container_width=True)
                
                # CSV Export
                df_events = pd.DataFrame(st.session_state.events_log)
                csv_data = df_events.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Detailed CSV Tracking Log (includes Real-world Time)",
                    data=csv_data,
                    file_name="KU_SRC_traffic_report.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                with st.expander("📝 View Detailed Vehicle Detections Log"):
                    st.dataframe(df_events, use_container_width=True)
        
        # If PROCESSING, enter video streaming loop
        else:
            # Dynamic labels based on swap_directions
            if swap_directions:
                left_label  = "Outbound"
                right_label = "Inbound"
                left_emoji  = "🟠"
                right_emoji = "🔵"
            else:
                left_label  = "Inbound"
                right_label = "Outbound"
                left_emoji  = "🔵"
                right_emoji = "🟠"

            # Layout initialization
            col_m1, col_m2, col_m3 = st.columns(3)
            inbound_metric = col_m1.metric(f"{left_emoji} {left_label} Count (Left Lanes)", st.session_state.inbound_count)
            outbound_metric = col_m2.metric(f"{right_emoji} {right_label} Count (Right Lanes)", st.session_state.outbound_count)
            traffic_level_metric = col_m3.metric("Current Traffic Level", "🟢 Smooth (คล่องตัว)")
            # แถบแยก density ขาเข้า/ขาออก
            col_d1, col_d2 = st.columns(2)
            inbound_density_metric  = col_d1.metric(f"{left_emoji} {left_label} Density", "0 คัน")
            outbound_density_metric = col_d2.metric(f"{right_emoji} {right_label} Density", "0 คัน")
            
            col_stream, col_charts = st.columns([3, 2])
            with col_stream:
                st.markdown("### 🎥 Live Video Processing")
                frame_placeholder = st.empty()
                
            with col_charts:
                st.markdown("### 📈 Live Analytics Charts")
                class_chart_title = st.empty()
                class_chart_placeholder = st.empty()
                flow_chart_title = st.empty()
                flow_chart_placeholder = st.empty()
            
            # Progress bar setup
            progress_bar = st.progress(0.0)
            progress_text = st.empty()
            
            # Capture Setup
            cap = cv2.VideoCapture(video_path)
            frame_idx = 0
            
            while cap.isOpened() and st.session_state.processing:
                success, frame = cap.read()
                if not success:
                    st.session_state.processing = False
                    break
                
                frame_idx += 1
                
                # Perform Frame Skipping
                if frame_idx % frame_skip != 0:
                    continue
                
                # YOLO tracking pipeline
                results = model.track(
                    frame,
                    imgsz=img_size,
                    classes=selected_class_ids,
                    persist=True,
                    tracker="custom_tracker.yaml",
                    device=device,
                    conf=conf_threshold,
                    verbose=False
                )
                
                annotated_frame = results[0].plot()
                
                # Render counting boundary lines on output image
                cv2.line(annotated_frame, INBOUND_START, INBOUND_END, (255, 255, 0), 3)      # Cyan
                cv2.line(annotated_frame, OUTBOUND_START, OUTBOUND_END, (0, 165, 255), 3)   # Orange
                cv2.circle(annotated_frame, (MID_X, LINE_Y), 6, (0, 0, 255), -1)            # Red division dot
                
                # Calculate active count and traffic level
                active_ids = results[0].boxes.id.int().cpu().tolist() if results[0].boxes.id is not None else []
                active_count = len(active_ids)

                # --- คำนวณ stall_ratio: สัดส่วนรถที่หยุดนิ่ง (เคลื่อนที่น้อยกว่า 5px ระหว่างเฟรม) ---
                stall_count = 0
                current_positions = {}
                if results[0].boxes.id is not None:
                    boxes_xy = results[0].boxes.xyxy.cpu().numpy()
                    ids_now = results[0].boxes.id.int().cpu().tolist()
                    for bx, tid in zip(boxes_xy, ids_now):
                        cx = int((bx[0] + bx[2]) / 2)
                        cy = int((bx[1] + bx[3]) / 2)
                        current_positions[tid] = (cx, cy)
                        if tid in st.session_state.prev_positions:
                            px, py = st.session_state.prev_positions[tid]
                            dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                            if dist < 5:  # เคลื่อนที่น้อยกว่า 5px ถือว่าหยุด
                                stall_count += 1
                st.session_state.prev_positions = current_positions
                stall_ratio = (stall_count / active_count) if active_count > 0 else 0.0

                # --- คำนวณ density แยกขาเข้า/ขาออก ---
                inbound_active = 0
                outbound_active = 0
                if results[0].boxes.id is not None:
                    boxes_xy2 = results[0].boxes.xyxy.cpu().numpy()
                    ids_now2 = results[0].boxes.id.int().cpu().tolist()
                    for bx2, tid2 in zip(boxes_xy2, ids_now2):
                        cx2 = int((bx2[0] + bx2[2]) / 2)
                        if cx2 < MID_X:
                            inbound_active += 1
                        else:
                            outbound_active += 1

                # Rolling window ยาว 30 เฟรม เพื่อลด noise
                WINDOW = 30
                st.session_state.active_vehicles_history.append(active_count)
                st.session_state.inbound_active_history.append(inbound_active)
                st.session_state.outbound_active_history.append(outbound_active)
                if len(st.session_state.active_vehicles_history) > WINDOW:
                    st.session_state.active_vehicles_history.pop(0)
                    st.session_state.inbound_active_history.pop(0)
                    st.session_state.outbound_active_history.pop(0)
                rolling_density = sum(st.session_state.active_vehicles_history) / len(st.session_state.active_vehicles_history)
                rolling_inbound_density = sum(st.session_state.inbound_active_history) / len(st.session_state.inbound_active_history)
                rolling_outbound_density = sum(st.session_state.outbound_active_history) / len(st.session_state.outbound_active_history)

                lvl_th, emoji, lvl_en = get_traffic_level(rolling_density, stall_ratio)
                
                # Calculate times
                timestamp_sec = frame_idx / fps
                current_real_time = st.session_state.start_datetime + datetime.timedelta(seconds=timestamp_sec)
                real_time_str = current_real_time.strftime("%H:%M:%S")
                real_time_full_str = current_real_time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Track matching and line crossover engine
                if results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    track_ids = results[0].boxes.id.int().cpu().tolist()
                    classes = results[0].boxes.cls.int().cpu().tolist()
                    
                    for box, track_id, class_idx in zip(boxes, track_ids, classes):
                        x1, y1, x2, y2 = box
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                        
                        # Verify track history to inspect path intersection with LINE_Y
                        if track_id in st.session_state.track_history:
                            prev_x, prev_y = st.session_state.track_history[track_id]
                            
                            # Check if the path segment intersects the LINE_Y line
                            if (prev_y <= LINE_Y <= center_y) or (center_y <= LINE_Y <= prev_y):
                                if track_id not in st.session_state.counted_ids:
                                    st.session_state.counted_ids.add(track_id)
                                    
                                    # Linear interpolation to determine the exact crossover X coordinate
                                    if center_y != prev_y:
                                        cross_x = prev_x + (center_x - prev_x) * (LINE_Y - prev_y) / (center_y - prev_y)
                                    else:
                                        cross_x = center_x
                                        
                                    class_name = coco_to_name.get(class_idx, "Unknown")
                                    
                                    # Increment respective traffic lanes counter
                                    # swap_directions flips which side is Inbound vs Outbound
                                    left_is_inbound = not swap_directions  # True by default
                                    if cross_x < MID_X:
                                        # Left side
                                        if left_is_inbound:
                                            st.session_state.inbound_count += 1
                                            direction = "Inbound"
                                        else:
                                            st.session_state.outbound_count += 1
                                            direction = "Outbound"
                                        # Visual flash line for feedback
                                        cv2.line(annotated_frame, INBOUND_START, INBOUND_END, (0, 0, 255), 6)
                                    else:
                                        # Right side
                                        if left_is_inbound:
                                            st.session_state.outbound_count += 1
                                            direction = "Outbound"
                                        else:
                                            st.session_state.inbound_count += 1
                                            direction = "Inbound"
                                        # Visual flash line for feedback
                                        cv2.line(annotated_frame, OUTBOUND_START, OUTBOUND_END, (0, 0, 255), 6)
                                        
                                    if class_name in st.session_state.class_counts:
                                        st.session_state.class_counts[class_name] += 1
                                        
                                    # Log event record details
                                    st.session_state.events_log.append({
                                        "Timestamp (s)": round(timestamp_sec, 2),
                                        "Real-world Time": real_time_full_str,
                                        "Vehicle ID": track_id,
                                        "Type": class_name,
                                        "Direction": direction,
                                        "Traffic Level": f"{emoji} {lvl_th}"
                                    })
                        
                        # Update coordinate tracker history mapping
                        st.session_state.track_history[track_id] = (center_x, center_y)
                
                # Superimpose dynamic HUD statistics onto the frame itself
                # When swapped: left side = Outbound, right side = Inbound
                if swap_directions:
                    hud_left_label  = "Outbound"
                    hud_right_label = "Inbound"
                    hud_left_count  = st.session_state.outbound_count
                    hud_right_count = st.session_state.inbound_count
                else:
                    hud_left_label  = "Inbound"
                    hud_right_label = "Outbound"
                    hud_left_count  = st.session_state.inbound_count
                    hud_right_count = st.session_state.outbound_count

                cv2.putText(annotated_frame, f"{hud_left_label}: {hud_left_count}", (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
                cv2.putText(annotated_frame, f"{hud_right_label}: {hud_right_count}", (20, 90), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)
                cv2.putText(annotated_frame, f"Time: {real_time_str}", (20, 130), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
                
                # Level color coding — per-direction traffic levels
                _, in_emoji, in_lvl_en   = get_traffic_level(rolling_inbound_density,  stall_ratio)
                _, out_emoji, out_lvl_en = get_traffic_level(rolling_outbound_density, stall_ratio)

                # Map direction labels based on swap state
                if swap_directions:
                    hud_in_label  = hud_right_label   # Inbound = right side when swapped
                    hud_out_label = hud_left_label
                    hud_in_lvl    = out_lvl_en        # density is still computed per screen side
                    hud_out_lvl   = in_lvl_en
                else:
                    hud_in_label  = hud_left_label
                    hud_out_label = hud_right_label
                    hud_in_lvl    = in_lvl_en
                    hud_out_lvl   = out_lvl_en

                color_map = {"Smooth": (0, 255, 0), "Moderate": (0, 255, 255), "Congested": (0, 165, 255), "Gridlock": (0, 0, 255)}
                cv2.putText(annotated_frame, f"{hud_in_label}: {hud_in_lvl}",   (20, 170),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, color_map.get(hud_in_lvl,  (255,255,255)), 2)
                cv2.putText(annotated_frame, f"{hud_out_label}: {hud_out_lvl}", (20, 210),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, color_map.get(hud_out_lvl, (255,255,255)), 2)
                
                # Store timeline analytics data point
                st.session_state.flow_history.append({
                    "Time (s)": round(timestamp_sec, 1),
                    "Real-world Time": real_time_str,
                    "Inbound": st.session_state.inbound_count,
                    "Outbound": st.session_state.outbound_count,
                    "Active Vehicles": active_count,
                    "Inbound Active": round(rolling_inbound_density, 2),
                    "Outbound Active": round(rolling_outbound_density, 2),
                    "Stall Ratio": round(stall_ratio, 2),
                    "Traffic Level": f"{emoji} {lvl_th}",
                    "Density Score": round(rolling_density, 2)
                })
                
                # Real-time UI updates (labels adjust based on swap_directions)
                inbound_metric.metric(f"{left_emoji} {left_label} Count (Left Lanes)", st.session_state.inbound_count)
                outbound_metric.metric(f"{right_emoji} {right_label} Count (Right Lanes)", st.session_state.outbound_count)
                traffic_level_metric.metric("Current Traffic Level (Overall)", f"{emoji} {lvl_th}")

                # อัปเดต density card — แสดงระดับการจราจรแยกขาเข้า/ขาออก
                _, _in_emoji,  _in_lvl_th  = get_traffic_level(rolling_inbound_density,  stall_ratio)
                _, _out_emoji, _out_lvl_th = get_traffic_level(rolling_outbound_density, stall_ratio)
                inbound_density_metric.metric(
                    f"{left_emoji} {left_label} Traffic Level",
                    f"{_in_emoji} {_in_lvl_th}",
                    help=f"ระดับการจราจรฝั่ง{left_label} (rolling avg {WINDOW} เฟรม)"
                )
                outbound_density_metric.metric(
                    f"{right_emoji} {right_label} Traffic Level",
                    f"{_out_emoji} {_out_lvl_th}",
                    help=f"ระดับการจราจรฝั่ง{right_label} (rolling avg {WINDOW} เฟรม)"
                )
                
                # Push BGR -> RGB color converted frames live to Streamlit
                frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
                
                # Update Charts in right column
                df_classes_live = pd.DataFrame({
                    "Vehicle Type": list(st.session_state.class_counts.keys()),
                    "Count": list(st.session_state.class_counts.values())
                })
                class_chart_title.markdown("#### Vehicle Class Distribution")
                class_chart_placeholder.bar_chart(df_classes_live.set_index("Vehicle Type"), use_container_width=True)
                
                if len(st.session_state.flow_history) > 0:
                    df_flow_live = pd.DataFrame(st.session_state.flow_history).drop_duplicates(subset=["Real-world Time"], keep="last")
                    flow_chart_title.markdown("#### Cumulative Traffic Timeline")
                    flow_chart_placeholder.line_chart(df_flow_live.set_index("Real-world Time")[["Inbound", "Outbound", "Active Vehicles"]], use_container_width=True)
                
                # Update visual progress widgets
                progress_val = min(frame_idx / total_frames, 1.0)
                progress_bar.progress(progress_val)
                progress_text.text(f"Analyzing... {frame_idx}/{total_frames} frames ({int(progress_val * 100)}%)")
            
            cap.release()
            st.session_state.processing = False
            # Force rerun to cleanup stream display and display download actions screen
            st.rerun()

else:
    st.info("💡 Please choose your traffic data video file from the control panel sidebar to initiate the dashboard analysis engine.")
