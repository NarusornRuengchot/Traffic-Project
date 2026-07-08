import cv2
import tempfile
import streamlit as st
from ultralytics import YOLO

# ---------------------------------------------------------
# Web Page Layout Configuration
# ---------------------------------------------------------
st.set_page_config(page_title="KU SRC Smart Traffic Dashboard", layout="wide")
st.title("🚗 Kasetsart University Sriracha Campus - Traffic Analytics")
st.subheader("Real-time Vehicle Detection & Counting Suite (YOLOv11)")

# Sidebar Configuration for Uploads
st.sidebar.header("1. Data Source")
uploaded_file = st.sidebar.file_uploader("Upload Traffic Video Clip", type=["mp4", "mov", "avi"])

# Persistent initialization of the model
@st.cache_resource
def load_model():
    return YOLO("yolov11n.pt")

model = load_model()

# ---------------------------------------------------------
# Main Application Flow
# ---------------------------------------------------------
if uploaded_file is not None:
    # Save the uploaded file to a temporary location so OpenCV can read it
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    cap = cv2.VideoCapture(tfile.name)

    # Automatically extract video properties
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # ---------------------------------------------------------
    # 2. Interactive Line Calibration Sliders in Sidebar
    # ---------------------------------------------------------
    st.sidebar.header("2. Line Calibration")
    
    # Slider to adjust the horizontal level of the counting lines (Y-axis)
    line_y_percentage = st.sidebar.slider(
        "Line Height (Vertical Position)", 
        min_value=0.1, max_value=0.9, value=0.50, step=0.05,
        help="Adjusts how high or low the detection line sits on the screen."
    )
    LINE_Y = int(frame_height * line_y_percentage)

    # Slider to adjust the dividing point between Inbound and Outbound (X-axis)
    mid_x_percentage = st.sidebar.slider(
        "Lane Divider Split (Horizontal Position)", 
        min_value=0.1, max_value=0.9, value=0.45, step=0.05,
        help="Adjusts the split point between left and right traffic lanes."
    )
    MID_X = int(frame_width * mid_x_percentage)

    # Re-calculate dynamic line thresholds based on slider coordinates
    INBOUND_START, INBOUND_END = (0, LINE_Y), (MID_X, LINE_Y)
    OUTBOUND_START, OUTBOUND_END = (MID_X, LINE_Y), (frame_width, LINE_Y)

    # UI Layout: Create columns to display live analytics metric cards
    metric_col1, metric_col2 = st.columns(2)
    inbound_metric = metric_col1.metric(label="Inbound Traffic (Left Lanes)", value=0)
    outbound_metric = metric_col2.metric(label="Outbound Traffic (Right Lanes)", value=0)

    # Frame placeholder where the processed video stream will render live on screen
    frame_placeholder = st.empty()

    inbound_count = 0         
    outbound_count = 0        
    counted_ids = set()       

    # Processing Loop
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # YOLOv11 Tracking Pipeline on CPU
        results = model.track(frame, classes=[2, 3, 5, 7], persist=True, tracker="bytetrack.yaml", device='cpu', verbose=False)
        annotated_frame = results[0].plot()

        # Draw dynamic measurement bounds geometry based on slider inputs
        cv2.line(annotated_frame, INBOUND_START, INBOUND_END, (255, 255, 0), 3)  # Left: Cyan
        cv2.line(annotated_frame, OUTBOUND_START, OUTBOUND_END, (0, 165, 255), 3) # Right: Orange

        # Crossline Counting Logic Engine
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu() 
            track_ids = results[0].boxes.id.int().cpu().tolist() 

            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = box
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                offset = 15 

                if (LINE_Y - offset) < center_y < (LINE_Y + offset) and track_id not in counted_ids:
                    counted_ids.add(track_id)
                    
                    if center_x < MID_X:
                        inbound_count += 1
                        cv2.line(annotated_frame, INBOUND_START, INBOUND_END, (0, 0, 255), 5)
                    else:
                        outbound_count += 1
                        cv2.line(annotated_frame, OUTBOUND_START, OUTBOUND_END, (0, 0, 255), 5)

        # Update the live metrics numbers on the dashboard UI elements instantly
        inbound_metric.metric(label="Inbound Traffic (Left Lanes)", value=inbound_count)
        outbound_metric.metric(label="Outbound Traffic (Right Lanes)", value=outbound_count)

        # Draw standard statistical print overlays on video canvas frame
        cv2.putText(annotated_frame, f"Inbound: {inbound_count}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
        cv2.putText(annotated_frame, f"Outbound: {outbound_count}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)

        # Re-render frame from BGR matrix to RGB matrix for correct browser display colors
        frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        
        # Push the final frame matrix onto the browser's view layout
        frame_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)

    cap.release()
    st.success("Video processing sequence concluded successfully!")
else:
    st.info("Please use the Control Panel sidebar to drop your traffic clip into the workspace.")
