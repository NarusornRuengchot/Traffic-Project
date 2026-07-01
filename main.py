import cv2
from ultralytics import YOLO

# 1. โหลดโมเดล YOLOv8n (n ย่อมาจาก nano คือขนาดเล็กสุด ทำงานไว เหมาะกับโน้ตบุ๊กทั่วไป)
# *หมายเหตุ: รันโค้ดครั้งแรก ระบบจะดาวน์โหลดไฟล์ yolov8n.pt ให้เองอัตโนมัติ*
model = YOLO("yolov8n.pt")

# 2. นำเข้าไฟล์วิดีโอ (เปลี่ยนชื่อไฟล์ให้ตรงกับวิดีโอที่คุณมี)
cap = cv2.VideoCapture("traffic_video.mov")

while cap.isOpened():
    # อ่านวิดีโอทีละเฟรม (ทีละภาพ)
    success, frame = cap.read()
    
    if not success:
        print("วิดีโอจบแล้ว หรือหาไฟล์ไม่พบ")
        break

    # 3. ให้ YOLOv8 ตรวจจับยานพาหนะในภาพ
    # ใช้ classes=[2, 3, 5, 7] เพื่อกรองเฉพาะ: รถยนต์(2), มอเตอร์ไซค์(3), รถบัส(5), รถบรรทุก(7)
    results = model(frame, classes=[2, 3, 5, 7])

    # 4. ให้ YOLO วาดกรอบสีสี่เหลี่ยม (Bounding Box) ทับลงบนภาพให้เลยอัตโนมัติ!
    annotated_frame = results[0].plot()

    # 5. แสดงผลวิดีโอที่ตีกรอบแล้วขึ้นมาบนหน้าจอ
    cv2.imshow("Smart Traffic Detection - YOLOv8", annotated_frame)

    # วงจรหยุดการทำงาน: กดปุ่ม 'q' ที่คีย์บอร์ดภาษาอังกฤษเพื่อปิดหน้าต่าง
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# คืนทรัพยากรให้ระบบเมื่อทำงานเสร็จ
cap.release()
cv2.destroyAllWindows()