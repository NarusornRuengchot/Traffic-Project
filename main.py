import cv2
from ultralytics import YOLO

# 1. โหลดโมเดล YOLOv8n
model = YOLO("yolov8n.pt")

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
# ---------------------------------------------------------

while cap.isOpened():
    success, frame = cap.read()
    
    if not success:
        print("วิดีโอจบแล้ว หรือหาไฟล์ไม่พบ")
        break

    # 3. ตรวจจับและติดตามยานพาหนะ
    results = model.track(frame, classes=[2, 3, 5, 7], persist=True, tracker="bytetrack.yaml")
    annotated_frame = results[0].plot()

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
            
            offset = 15 

            # เช็คเงื่อนไขเมื่อรถวิ่งผ่านระดับเส้น LINE_Y
            if (LINE_Y - offset) < center_y < (LINE_Y + offset) and track_id not in counted_ids:
                counted_ids.add(track_id)
                
                # แยกนับตามตำแหน่งจุดกึ่งกลางของรถ (center_x) เปรียบเทียบกับจุดแบ่งเลน (MID_X)
                if center_x < MID_X:
                    inbound_count += 1   # อยู่ฝั่งซ้ายของจุดแบ่ง = ขาเข้า
                    # ให้เส้นฝั่งซ้ายกะพริบเป็นสีแดงสั้นๆ เมื่อนับรถได้
                    cv2.line(annotated_frame, INBOUND_START, INBOUND_END, (0, 0, 255), 5)
                else:
                    outbound_count += 1  # อยู่ฝั่งขวาของจุดแบ่ง = ขาออก
                    # ให้เส้นฝั่งขวากะพริบเป็นสีแดงสั้นๆ เมื่อนับรถได้
                    cv2.line(annotated_frame, OUTBOUND_START, OUTBOUND_END, (0, 0, 255), 5)

    # 5. แสดงผลสถิติแยกฝั่ง (สีข้อความตรงกับสีเส้น)
    cv2.putText(annotated_frame, f"Inbound (Left): {inbound_count}", (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
    
    cv2.putText(annotated_frame, f"Outbound (Right): {outbound_count}", (20, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 3)
    # ---------------------------------------------------------

    # 6. ย่อขนาดภาพก่อนแสดงผล เพื่อไม่ให้ล้นจอ
    resized_frame = cv2.resize(annotated_frame, (1024, 576)) 
    cv2.imshow("Smart Traffic Detection - YOLOv8", resized_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()