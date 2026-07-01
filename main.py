import cv2
from ultralytics import YOLO

# 1. โหลดโมเดล YOLOv8n
model = YOLO("yolov8n.pt")

# 2. นำเข้าไฟล์วิดีโอ
cap = cv2.VideoCapture("traffic_video.mov")

# ---------------------------------------------------------
# [ส่วนที่เพิ่มใหม่] การตั้งค่าเส้นสมมติและตัวแปรนับจำนวน
# ---------------------------------------------------------
# กำหนดพิกัดเส้นสมมติ (แกน X, แกน Y) 
# สมมติขีดเส้นขวางถนน โดยให้แกน Y อยู่ที่พิกัด 400 (ปรับค่านี้ได้ตามมุมกล้องวิดีโอของคุณ)
LINE_START = (0, 400)     # จุดเริ่มต้นเส้น (ซ้ายสุด)
LINE_END = (1280, 400)    # จุดสิ้นสุดเส้น (ขวาสุด)

vehicle_count = 0         # ตัวแปรเก็บยอดรวมรถที่วิ่งผ่าน
counted_ids = set()       # ชุดข้อมูล (Set) สำหรับเก็บ ID รถที่ถูกนับไปแล้ว จะได้ไม่นับซ้ำ
# ---------------------------------------------------------

while cap.isOpened():
    success, frame = cap.read()
    
    if not success:
        print("วิดีโอจบแล้ว หรือหาไฟล์ไม่พบ")
        break

    # 3. ให้ YOLOv8 ตรวจจับและ "ติดตาม" ยานพาหนะ (Object Tracking)
    # เปลี่ยนจากการใช้ model() ธรรมดา เป็น model.track() และใส่ persist=True เพื่อให้ระบบจำ ID รถได้
    results = model.track(frame, classes=[2, 3, 5, 7], persist=True, tracker="bytetrack.yaml")

    # 4. ให้ YOLO วาดกรอบสี่เหลี่ยมพร้อม ID รถ ทับลงบนภาพ
    annotated_frame = results[0].plot()

    # 5. วาดเส้นสมมติสีเขียว (BGR: 0, 255, 0) ลงบนวิดีโอ
    cv2.line(annotated_frame, LINE_START, LINE_END, (0, 255, 0), 2)

    # ---------------------------------------------------------
    # [ส่วนที่เพิ่มใหม่] ตรรกะการนับจำนวนเมื่อขับผ่านเส้น
    # ---------------------------------------------------------
    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu() # ดึงพิกัดกรอบรถทั้ง 4 มุม (x1, y1, x2, y2)
        track_ids = results[0].boxes.id.int().cpu().tolist() # ดึงหมายเลข ID ของรถแต่ละคัน

        for box, track_id in zip(boxes, track_ids):
            x1, y1, x2, y2 = box
            
            # หาจุดกึ่งกลางของตัวรถ (แนวตั้งแกน Y)
            center_y = int((y1 + y2) / 2)
            
            # ระยะความคลาดเคลื่อน (Offset) เนื่องจากเฟรมวิดีโออาจข้ามพิกัดไปบ้าง
            offset = 15 
            line_y = LINE_START[1] # ดึงค่าแกน Y ของเส้นสมมติมาใช้ (คือ 400)

            # เช็คเงื่อนไข: ถ้ารถวิ่งเข้ามาในระยะเส้นสมมติ และยังไม่เคยถูกนับ
            if (line_y - offset) < center_y < (line_y + offset) and track_id not in counted_ids:
                vehicle_count += 1
                counted_ids.add(track_id) # บันทึก ID นี้ว่านับแล้ว
                
                # เปลี่ยนสีเส้นเป็น "สีแดง" แวบหนึ่ง เมื่อมีการนับจำนวนเกิดขึ้น
                cv2.line(annotated_frame, LINE_START, LINE_END, (0, 0, 255), 4)

    # แสดงข้อความตัวเลขยอดรวมรถที่มุมซ้ายบนของจอ (สีขาว)
    cv2.putText(annotated_frame, f"Total Vehicles: {vehicle_count}", (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    # ---------------------------------------------------------

    # 6. แสดงผลวิดีโอ
    cv2.imshow("Smart Traffic Detection - YOLOv8", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()