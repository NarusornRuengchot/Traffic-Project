import cv2
import os
import sys
import argparse
import datetime
from ultralytics import YOLO
from src.utils.file_helper import resolve_model_path, resolve_video_source

# CLI Arguments support
parser = argparse.ArgumentParser(description="KU SRC Smart Traffic Analytics - Desktop Video Processor")
parser.add_argument("--model", type=str, default="best.pt", help="Model name (e.g., best.pt, yolo26s.pt, yolo26n.pt)")
parser.add_argument("--video", type=str, default="IMG_1357.MOV", help="Video path or webcam (e.g., uploads/IMG_1357.MOV, webcam:0)")
parser.add_argument("--size", type=int, default=640, help="Inference image resolution (default: 640)")
parser.add_argument("--conf", type=float, default=0.18, help="Confidence threshold (default: 0.18)")

# Parse args (ignore unrecognized for interactive terminal flexibility)
args, _ = parser.parse_known_args()

MODEL_NAME = args.model
MODEL_PATH = resolve_model_path(MODEL_NAME, search_dirs=["models", "."])
IMG_SIZE = args.size
CONF_THRESH = args.conf

print(f"🚀 Initializing Smart Traffic AI Engine...")
print(f"   Model: {MODEL_PATH} ({'YOLO26 Next-Gen' if '26' in MODEL_PATH else 'Custom Traffic Model'})")
print(f"   Resolution: {IMG_SIZE}px | Confidence: {int(CONF_THRESH * 100)}%")

model = YOLO(MODEL_PATH)


# 2. นำเข้าไฟล์วิดีโอ (ค้นหา KUSRC_Traffic.mov หรือไฟล์ในโฟลเดอร์ uploads อัตโนมัติ)
video_candidates = [
    "KUSRC_Traffic.mov",
    os.path.join("uploads", "IMG_1357.MOV"),
    "IMG_1357.MOV"
]
if os.path.exists("uploads"):
    for f in os.listdir("uploads"):
        if f.lower().endswith(('.mov', '.mp4', '.avi', '.mkv')):
            video_candidates.append(os.path.join("uploads", f))

video_path = next((p for p in video_candidates if os.path.exists(p)), None)

if not video_path:
    print("เกิดข้อผิดพลาด: ระบบไม่สามารถค้นหาไฟล์วิดีโอได้ (กรุณาวางไฟล์วิดีโอ .mov/.mp4 ไว้ในโฟลเดอร์โปรเจกต์ หรือในโฟลเดอร์ uploads)")
    exit()

print(f"กำลังเปิดไฟล์วิดีโอ: {video_path}")
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"เกิดข้อผิดพลาด: ระบบไม่สามารถเปิดไฟล์วิดีโอ '{video_path}' ได้")
    exit()

# ดึงค่าความกว้างและความสูงของวิดีโออัตโนมัติ
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) # [เพิ่มบรรทัดนี้]

# ---------------------------------------------------------
# การตั้งค่าเส้นสมมติแบบแยกฝั่งซ้าย-ขวา ชัดเจน
# ---------------------------------------------------------
MID_X = int(frame_width * 0.45)  # จุดแบ่งเลนตรงเกาะกลางถนน (40% ของความกว้างจอ)

# [ส่วนที่ต้องแก้] ให้ระบบตั้งเส้นไว้ที่กึ่งกลางจอพอดี (50% ของความสูงวิดีโอ)
LINE_Y = int(frame_height * 0.50) 

# เส้นฝั่งซ้าย (Inbound - ขาเข้า)
# ... (โค้ดส่วนอื่นคงเดิม) ...

INBOUND_START = (0, LINE_Y)
INBOUND_END = (MID_X, LINE_Y)

# เส้นฝั่งขวา (Outbound - ขาออก)
OUTBOUND_START = (MID_X, LINE_Y)
OUTBOUND_END = (frame_width, LINE_Y)

inbound_count = 0         # ตัวแปรเก็บจำนวนรถขาเข้า
outbound_count = 0        # ตัวแปรเก็บจำนวนรถขาออก
counted_ids = set()       # ชุดข้อมูลสำหรับเก็บ ID รถที่ถูกนับไปแล้ว
track_history = {}        # ประวัติพิกัดรถเพื่อใช้เช็คกรณีข้ามเส้นแบ่ง

# กำหนดเวลาเริ่มต้นในการถ่ายทำคลิปและตัวแปลคำนวณความหนาแน่น
start_datetime = datetime.datetime.now().replace(hour=8, minute=30, second=0, microsecond=0)
fps = cap.get(cv2.CAP_PROP_FPS)
if fps <= 0:
    fps = 30.0
frame_idx = 0
active_vehicles_history = []
inbound_active_history  = []   # ประวัติ density ขาเข้า
outbound_active_history = []   # ประวัติ density ขาออก
prev_positions          = {}   # ตำแหน่งเฟรมก่อนหน้า สำหรับหา stall_ratio
WINDOW = 30                    # rolling window size

def get_traffic_level(density, stall_ratio=0.0):
    """
    ประเมินระดับการจราจรตามทั้งปริมาณรถและการเคลื่อนตัว
    density    : จำนวนรถเฉลี่ยในจอ (rolling average)
    stall_ratio: 0-1 สัดส่วนรถที่แทบไม่ขยับ
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
# ---------------------------------------------------------

while cap.isOpened():
    success, frame = cap.read()
    
    if not success:
        print("วิดีโอจบแล้ว หรือหาไฟล์ไม่พบ")
        break

    frame_idx += 1
    # 3. ตรวจจับและติดตามยานพาหนะ
    # ถ้าใช้ fine-tuned model ให้ตรวจจับทุกคลาสของโมเดล ถ้าเป็น YOLO26/COCO ให้จับ car, motorcycle, bus, truck (2, 3, 5, 7)
    target_classes = None if ("best" in MODEL_PATH or "custom" in MODEL_PATH) else [2, 3, 5, 7]
    results = model.track(frame, imgsz=IMG_SIZE, classes=target_classes, persist=True, tracker="custom_tracker.yaml", device='cpu', conf=CONF_THRESH)

    annotated_frame = results[0].plot()

    # คำนวณความหนาแน่นและระดับการจราจร
    active_ids = results[0].boxes.id.int().cpu().tolist() if results[0].boxes.id is not None else []
    active_count = len(active_ids)

    # --- stall_ratio: วัดสัดส่วนรถที่แทบไม่เคลื่อน (<5px) ---
    stall_count = 0
    current_positions = {}
    if results[0].boxes.id is not None:
        bxs = results[0].boxes.xyxy.cpu().numpy()
        ids_now = results[0].boxes.id.int().cpu().tolist()
        for bx, tid in zip(bxs, ids_now):
            cx = int((bx[0] + bx[2]) / 2)
            cy = int((bx[1] + bx[3]) / 2)
            current_positions[tid] = (cx, cy)
            if tid in prev_positions:
                px, py = prev_positions[tid]
                if ((cx - px)**2 + (cy - py)**2) ** 0.5 < 5:
                    stall_count += 1
    prev_positions.clear()
    prev_positions.update(current_positions)
    stall_ratio = (stall_count / active_count) if active_count > 0 else 0.0

    # --- density แยกขาเข้า/ขาออก ---
    inbound_active = 0
    outbound_active = 0
    if results[0].boxes.id is not None:
        for bx2 in results[0].boxes.xyxy.cpu().numpy():
            cx2 = int((bx2[0] + bx2[2]) / 2)
            if cx2 < MID_X:
                inbound_active += 1
            else:
                outbound_active += 1

    active_vehicles_history.append(active_count)
    inbound_active_history.append(inbound_active)
    outbound_active_history.append(outbound_active)
    if len(active_vehicles_history) > WINDOW:
        active_vehicles_history.pop(0)
        inbound_active_history.pop(0)
        outbound_active_history.pop(0)
    rolling_density          = sum(active_vehicles_history)  / len(active_vehicles_history)
    rolling_inbound_density  = sum(inbound_active_history)   / len(inbound_active_history)
    rolling_outbound_density = sum(outbound_active_history)  / len(outbound_active_history)
    lvl_th, emoji, lvl_en = get_traffic_level(rolling_density, stall_ratio)

    # คำนวณเวลาจริงของเฟรม
    timestamp_sec = frame_idx / fps
    current_real_time = start_datetime + datetime.timedelta(seconds=timestamp_sec)
    real_time_str = current_real_time.strftime("%H:%M:%S")

    # 4. วาดเส้นสมมติแยกสีให้เห็นชัดเจนบนหน้าจอ
    cv2.line(annotated_frame, INBOUND_START, INBOUND_END, (255, 255, 0), 3)  # ฝั่งซ้าย: สีฟ้า (BGR)
    cv2.line(annotated_frame, OUTBOUND_START, OUTBOUND_END, (0, 165, 255), 3) # ฝั่งขวา: สีส้ม (BGR)

    # ---------------------------------------------------------
    # ตรรกะการนับจำนวนแยกฝั่งซ้าย-ขวา
    # ---------------------------------------------------------
    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu() 
        track_ids = results[0].boxes.id.int().cpu().tolist() 

        for box, track_id in zip(boxes, track_ids):
            x1, y1, x2, y2 = box
            
            # หาจุดกึ่งกลางของตัวรถ
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            
            # ตรวจสอบประวัติพิกัดรถเพื่อดูการข้ามเส้นสมมติ LINE_Y
            if track_id in track_history:
                prev_x, prev_y = track_history[track_id]
                
                # เช็คการเคลื่อนที่ข้ามเส้น LINE_Y ระหว่างเฟรมก่อนหน้าและเฟรมปัจจุบัน
                if (prev_y <= LINE_Y <= center_y) or (center_y <= LINE_Y <= prev_y):
                    if track_id not in counted_ids:
                        counted_ids.add(track_id)
                        
                        # คำนวณหาตำแหน่งแกน X ที่ข้ามเส้นโดยประมาณ
                        if center_y != prev_y:
                            cross_x = prev_x + (center_x - prev_x) * (LINE_Y - prev_y) / (center_y - prev_y)
                        else:
                            cross_x = center_x
                            
                        # แยกนับตามตำแหน่งจุดกึ่งกลางของรถ (cross_x) เปรียบเทียบกับจุดแบ่งเลน (MID_X)
                        if cross_x < MID_X:
                            inbound_count += 1   # อยู่ฝั่งซ้ายของจุดแบ่ง = ขาเข้า
                            print(f"[{real_time_str}] Vehicle ID {track_id} crossed INBOUND. Traffic Level: {emoji} {lvl_th}")
                            # ให้เส้นฝั่งซ้ายกะพริบเป็นสีแดงสั้นๆ เมื่อนับรถได้
                            cv2.line(annotated_frame, INBOUND_START, INBOUND_END, (0, 0, 255), 5)
                        else:
                            outbound_count += 1  # อยู่ฝั่งขวาของจุดแบ่ง = ขาออก
                            print(f"[{real_time_str}] Vehicle ID {track_id} crossed OUTBOUND. Traffic Level: {emoji} {lvl_th}")
                            # ให้เส้นฝั่งขวากะพริบเป็นสีแดงสั้นๆ เมื่อนับรถได้
                            cv2.line(annotated_frame, OUTBOUND_START, OUTBOUND_END, (0, 0, 255), 5)
            
            # อัปเดตประวัติพิกัด
            track_history[track_id] = (center_x, center_y)

    # 5. แสดงผลสถิติแยกฝั่ง (สีข้อความตรงกับสีเส้น)
    cv2.putText(annotated_frame, f"Inbound (Left): {inbound_count}", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
    cv2.putText(annotated_frame, f"Outbound (Right): {outbound_count}", (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)
    cv2.putText(annotated_frame, f"Time: {real_time_str}", (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
    color_map = {"Smooth": (0, 255, 0), "Moderate": (0, 255, 255), "Congested": (0, 165, 255), "Gridlock": (0, 0, 255)}
    text_color = color_map.get(lvl_en, (255, 255, 255))
    cv2.putText(annotated_frame, f"Traffic: {lvl_en}", (20, 170),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_color, 3)
    # แสดงระดับการจราจรแยกขาเข้า/ขาออก
    _, in_emoji, in_lvl_en  = get_traffic_level(rolling_inbound_density,  stall_ratio)
    _, out_emoji, out_lvl_en = get_traffic_level(rolling_outbound_density, stall_ratio)
    cv2.putText(annotated_frame, f"Inbound:  {in_lvl_en}",  (20, 210),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    cv2.putText(annotated_frame, f"Outbound: {out_lvl_en}", (20, 245),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
    # ---------------------------------------------------------

    # 6. ย่อขนาดภาพก่อนแสดงผล เพื่อไม่ให้ล้นจอ
    resized_frame = cv2.resize(annotated_frame, (1024, 576)) 
    cv2.imshow("Smart Traffic Detection ", resized_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()