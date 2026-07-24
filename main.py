import cv2
import os
import datetime
from ultralytics import YOLO

# ฟังก์ชันตรวจสอบชื่อไฟล์โมเดลเพื่อป้องกันข้อผิดพลาดกรณีพิมพ์ชื่อไฟล์สลับไปมาระหว่าง yolo11 และ yolov11
def resolve_model_path(model_path):
    if os.path.exists(model_path):
        return model_path
    
    # กรณี YOLOv11 (สลับระหว่างมี v และไม่มี v เช่น yolov11s.pt <-> yolo11s.pt)
    if "yolov11" in model_path:
        alt_path = model_path.replace("yolov11", "yolo11")
        if os.path.exists(alt_path):
            return alt_path
    elif "yolo11" in model_path:
        alt_path = model_path.replace("yolo11", "yolov11")
        if os.path.exists(alt_path):
            return alt_path
            
    # กรณี YOLOv8 (สลับระหว่างมี v และไม่มี v เช่น yolov8n.pt <-> yolo8n.pt)
    if "yolov8" in model_path:
        alt_path = model_path.replace("yolov8", "yolo8")
        if os.path.exists(alt_path):
            return alt_path
    elif "yolo8" in model_path:
        alt_path = model_path.replace("yolo8", "yolov8")
        if os.path.exists(alt_path):
            return alt_path
            
    return model_path

# เลือกรุ่นของโมเดลที่ต้องการทดสอบ (YOLO Model Configuration)
# สามารถเลือกใช้ได้ทั้ง YOLOv11 (แนะนำ) หรือเปลี่ยนเป็น YOLOv8 ได้ตามต้องการ
# ตัวอย่างโมเดล YOLOv11 ที่มีในโฟลเดอร์: "yolov11n.pt", "yolo11s.pt", "yolo11m.pt", "yolo11l.pt", "yolo11x.pt"
# ตัวอย่างโมเดล YOLOv8 ที่มีในโฟลเดอร์: "yolov8n.pt"
MODEL_PATH = resolve_model_path("yolov11n.pt")  # ระบบจะตรวจสอบและดึงไฟล์โมเดลที่ถูกต้องให้โดยอัตโนมัติ
IMG_SIZE = 1280             # ขนาดความละเอียดในตรวจจับ (640 = มาตรฐาน/เร็ว, 1280 = แม่นยำวัตถุขนาดเล็กแต่ช้าลง)

model = YOLO(MODEL_PATH)


# 2. นำเข้าไฟล์วิดีโอ 
cap = cv2.VideoCapture("KUSRC_Traffic.mov") 

if not cap.isOpened():
    print("เกิดข้อผิดพลาด: ระบบไม่สามารถค้นหาหรือเปิดไฟล์วิดีโอได้")
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

def get_traffic_level(density):
    if density <= 1.5:
        return "Smooth (คล่องตัว)", "🟢", "Smooth"
    elif density <= 4.0:
        return "Moderate (ปานกลาง)", "🟡", "Moderate"
    elif density <= 7.0:
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
   # เปลี่ยนจาก device=0 เป็น device='cpu' เพื่อไม่ให้โปรแกรม Error
    results = model.track(frame, imgsz=IMG_SIZE, classes=[2, 3, 5, 7], persist=True, tracker="custom_tracker.yaml", device='cpu', conf=0.15)

    annotated_frame = results[0].plot()

    # คำนวณความหนาแน่นและระดับการจราจร
    active_ids = results[0].boxes.id.int().cpu().tolist() if results[0].boxes.id is not None else []
    active_count = len(active_ids)
    active_vehicles_history.append(active_count)
    if len(active_vehicles_history) > 15:
        active_vehicles_history.pop(0)
    rolling_density = sum(active_vehicles_history) / len(active_vehicles_history)
    lvl_th, emoji, lvl_en = get_traffic_level(rolling_density)

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
    # ---------------------------------------------------------

    # 6. ย่อขนาดภาพก่อนแสดงผล เพื่อไม่ให้ล้นจอ
    resized_frame = cv2.resize(annotated_frame, (1024, 576)) 
    cv2.imshow("Smart Traffic Detection ", resized_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()