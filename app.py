import cv2
import tempfile
import streamlit as st
import pandas as pd
import torch
import os
from ultralytics import YOLO

# ---------------------------------------------------------
# Web Page Layout Configuration & Theme Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="KU SRC Smart Traffic Dashboard",
    page_icon="🚗",
    layout="wide"
)

# Custom CSS for rich dashboard styling
st.markdown("""
    <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1E3A8A;
            margin-bottom: 0.1rem;
        }
        .sub-header {
            font-size: 1.1rem;
            color: #4B5563;
            margin-bottom: 2rem;
        }
        div[data-testid="stMetricValue"] {
            font-size: 2.5rem;
            font-weight: 800;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 1rem;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🚗 Kasetsart University Sriracha Campus</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Real-time Vehicle Detection, Tracking & Counting Dashboard (YOLOv11)</div>', unsafe_allow_html=True)

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
model_size = st.sidebar.selectbox(
    "YOLOv11 Model Version:",
    ["yolov11n.pt", "yolov11s.pt", "yolov11m.pt"],
    index=0,
    help="Nano (fastest), Small (balanced), Medium (highest accuracy but slower)."
)

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
    help="Adjusts the split point dividing Left (Inbound) and Right (Outbound) traffic lanes."
)

# Class mappings to COCO index mappings
class_map = {"Car": 2, "Motorcycle": 3, "Bus": 5, "Truck": 7}
coco_to_name = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}
selected_class_ids = [class_map[c] for c in target_classes]

# Persistent initialization of the model
@st.cache_resource
def load_yolo_model(model_name):
    return YOLO(model_name)

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

# Load model
model = None
try:
    model = load_yolo_model(model_size)
except Exception as e:
    st.sidebar.warning(f"⚠️ Could not load '{model_size}'. Falling back to local 'yolov11n.pt'.")
    try:
        model = load_yolo_model("yolov11n.pt")
    except Exception as e2:
        st.sidebar.error(f"❌ Critical Error: Failed to load fallback model 'yolov11n.pt'.")

if model is None:
    st.error("Failed to load any YOLOv11 model. Please ensure 'yolov11n.pt' is present in the project directory.")
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
                
                # Metrics cards
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("Final Inbound Traffic", st.session_state.inbound_count)
                col_m2.metric("Final Outbound Traffic", st.session_state.outbound_count)
                
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
                    st.markdown("#### Cumulative Traffic Timeline")
                    df_flow = pd.DataFrame(st.session_state.flow_history).drop_duplicates(subset=["Time (s)"], keep="last")
                    st.line_chart(df_flow.set_index("Time (s)"), use_container_width=True)
                
                # CSV Export
                df_events = pd.DataFrame(st.session_state.events_log)
                csv_data = df_events.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Detailed CSV Tracking Log",
                    data=csv_data,
                    file_name="KU_SRC_traffic_report.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                with st.expander("📝 View Detailed Vehicle Detections Log"):
                    st.dataframe(df_events, use_container_width=True)
        
        # If PROCESSING, enter video streaming loop
        else:
            # Layout initialization
            col_m1, col_m2 = st.columns(2)
            inbound_metric = col_m1.metric("Inbound Count (Left Lanes)", st.session_state.inbound_count)
            outbound_metric = col_m2.metric("Outbound Count (Right Lanes)", st.session_state.outbound_count)
            
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
                    classes=selected_class_ids,
                    persist=True,
                    tracker="bytetrack.yaml",
                    device=device,
                    conf=conf_threshold,
                    verbose=False
                )
                
                annotated_frame = results[0].plot()
                
                # Render counting boundary lines on output image
                cv2.line(annotated_frame, INBOUND_START, INBOUND_END, (255, 255, 0), 3)      # Cyan
                cv2.line(annotated_frame, OUTBOUND_START, OUTBOUND_END, (0, 165, 255), 3)   # Orange
                cv2.circle(annotated_frame, (MID_X, LINE_Y), 6, (0, 0, 255), -1)            # Red division dot
                
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
                                    timestamp_sec = frame_idx / fps
                                    
                                    # Increment respective traffic lanes counter
                                    if cross_x < MID_X:
                                        st.session_state.inbound_count += 1
                                        direction = "Inbound"
                                        # Visual flash line for feedback
                                        cv2.line(annotated_frame, INBOUND_START, INBOUND_END, (0, 0, 255), 6)
                                    else:
                                        st.session_state.outbound_count += 1
                                        direction = "Outbound"
                                        # Visual flash line for feedback
                                        cv2.line(annotated_frame, OUTBOUND_START, OUTBOUND_END, (0, 0, 255), 6)
                                        
                                    if class_name in st.session_state.class_counts:
                                        st.session_state.class_counts[class_name] += 1
                                        
                                    # Log event record details
                                    st.session_state.events_log.append({
                                        "Timestamp (s)": round(timestamp_sec, 2),
                                        "Vehicle ID": track_id,
                                        "Type": class_name,
                                        "Direction": direction
                                    })
                        
                        # Update coordinate tracker history mapping
                        st.session_state.track_history[track_id] = (center_x, center_y)
                
                # Superimpose dynamic HUD statistics onto the frame itself
                cv2.putText(annotated_frame, f"Inbound: {st.session_state.inbound_count}", (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
                cv2.putText(annotated_frame, f"Outbound: {st.session_state.outbound_count}", (20, 90), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)
                
                # Store timeline analytics data point
                current_time = frame_idx / fps
                st.session_state.flow_history.append({
                    "Time (s)": round(current_time, 1),
                    "Inbound": st.session_state.inbound_count,
                    "Outbound": st.session_state.outbound_count
                })
                
                # Real-time UI updates
                inbound_metric.metric("Inbound Count (Left Lanes)", st.session_state.inbound_count)
                outbound_metric.metric("Outbound Count (Right Lanes)", st.session_state.outbound_count)
                
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
                    df_flow_live = pd.DataFrame(st.session_state.flow_history).drop_duplicates(subset=["Time (s)"], keep="last")
                    flow_chart_title.markdown("#### Cumulative Traffic Timeline")
                    flow_chart_placeholder.line_chart(df_flow_live.set_index("Time (s)"), use_container_width=True)
                
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
