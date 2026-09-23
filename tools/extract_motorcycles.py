import os
import cv2
import numpy as np
from ultralytics import YOLO

# ============================================================
# Script: สกัดภาพจากวิดีโอ + ทำ Auto-Bounding Box (มอเตอร์ไซค์ + คนขับ)
# ============================================================

VIDEO_PATH = "uploads/IMG_1357.MOV"
OUTPUT_DIR = os.path.join("data", "dataset_motorcycles") if os.path.exists(os.path.join("data", "dataset_motorcycles")) else "dataset_motorcycles"
TARGET_FRAMES = 50       # จำนวนภาพที่ต้องการ (30-50 ภาพ)
MIN_FRAME_GAP = 25       # เว้นระยะห่างระหว่างเฟรม (กันภาพซ้ำติดๆ กัน)

# คลาสเป้าหมายสำหรับ YOLO Dataset:
# 0: bus, 1: car, 2: motorbike (มอเตอร์ไซค์+คนขับ), 3: truck
CLASS_MAP = {
    "bus": 0,
    "car": 1,
    "motorbike": 2,
    "truck": 3
}

def box_overlap(box1, box2):
    """คำนวณการซ้อนทับกันระหว่างกรอบกล่อง 2 กล่อง [x1, y1, x2, y2]"""
    xA = max(box1[0], box2[0])
    yA = max(box1[1], box2[1])
    xB = min(box1[2], box2[2])
    yB = min(box1[3], box2[3])
    
    inter_area = max(0, xB - xA) * max(0, yB - yA)
    if inter_area <= 0:
        return 0.0
    
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    # คืนค่าสัดส่วนการทับซ้อนเทียบกับกล่องที่เล็กกว่า
    min_area = min(box1_area, box2_area)
    return inter_area / min_area if min_area > 0 else 0.0

def is_rider_on_bike(person_box, bike_box):
    """
    ตรวจสอบว่าคน (person) กำลังขี่มอเตอร์ไซค์ (bike) คันนี้อยู่หรือไม่:
    - มีการซ้อนทับกันในแนวแกน X (horizontal overlap)
    - ตำแหน่งตัวคนอยู่ด้านบนหรือเหลื่อมกับตัวรถ
    """
    p_x1, p_y1, p_x2, p_y2 = person_box
    b_x1, b_y1, b_x2, b_y2 = bike_box
    
    # คำนวณ horizontal overlap
    x_overlap = max(0, min(p_x2, b_x2) - max(p_x1, b_x1))
    p_width = p_x2 - p_x1
    
    if p_width <= 0:
        return False
        
    overlap_ratio = x_overlap / p_width
    
    # คนต้องอยู่ตำแหน่งบนหรือระดับเดียวกับมอเตอร์ไซค์ (ก้นคนต้องไม่ต่ำกว่าพื้นรถ)
    y_overlap = max(0, min(p_y2, b_y2) - max(p_y1, b_y1))
    
    return overlap_ratio > 0.35 and (y_overlap > 0 or p_y2 <= b_y2 + 20)

def main():
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ ไม่พบไฟล์วิดีโอ: {VIDEO_PATH}")
        return

    # สร้างโฟลเดอร์สำหรับเก็บชุดข้อมูล
    img_dir = os.path.join(OUTPUT_DIR, "images")
    lbl_dir = os.path.join(OUTPUT_DIR, "labels")
    prev_dir = os.path.join(OUTPUT_DIR, "preview")
    for d in [img_dir, lbl_dir, prev_dir]:
        os.makedirs(d, exist_ok=True)

    print("🚀 กำลังโหลดโมเดล YOLO เพื่อช่วย Auto-Annotate...")
    model = YOLO("yolov11n.pt") # ใช้ COCO model เพราะแยกคน (0) กับมอเตอร์ไซค์ (3) ได้ชัดเจน

    cap = cv2.VideoCapture(VIDEO_PATH)
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"🎬 เปิดวิดีโอ: {VIDEO_PATH} (ความยาว {total_video_frames} เฟรม)")

    saved_count = 0
    last_saved_frame = -MIN_FRAME_GAP
    frame_idx = 0

    while cap.isOpened() and saved_count < TARGET_FRAMES:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        # ตรวจสอบทุกๆ 5 เฟรม เพื่อความรวดเร็ว
        if frame_idx % 5 != 0:
            continue

        # เว้นระยะไม่ให้แคปภาพมอเตอร์ไซค์ติดกันเกินไป
        if frame_idx - last_saved_frame < MIN_FRAME_GAP:
            continue

        h, w = frame.shape[:2]

        # รันตรวจจับด้วย YOLO (imgsz=640 รวดเร็วบน CPU)
        results = model(frame, imgsz=640, conf=0.18, classes=[0, 2, 3, 5, 7], verbose=False)[0]

        if results.boxes is None or len(results.boxes) == 0:
            continue

        boxes = results.boxes.xyxy.cpu().numpy()
        classes = results.boxes.cls.cpu().numpy().astype(int)
        confs = results.boxes.conf.cpu().numpy()

        # แยกกล่องตามประเภท
        person_boxes = [b for b, c in zip(boxes, classes) if c == 0]
        moto_boxes   = [b for b, c in zip(boxes, classes) if c == 3]
        car_boxes    = [b for b, c in zip(boxes, classes) if c == 2]
        bus_boxes    = [b for b, c in zip(boxes, classes) if c == 5]
        truck_boxes  = [b for b, c in zip(boxes, classes) if c == 7]

        # ถ้าในเฟรมนี้ไม่มีมอเตอร์ไซค์เลย ให้ข้ามไป
        if len(moto_boxes) == 0:
            continue

        # รวมกล่อง "มอเตอร์ไซค์ + คนขับ" เป็นกรอบเดียวกัน
        merged_moto_boxes = []
        used_persons = set()

        for mb in moto_boxes:
            m_x1, m_y1, m_x2, m_y2 = mb
            # ค้นหาคนขี่ที่อยู่บนมอเตอร์ไซค์คันนี้
            for i, pb in enumerate(person_boxes):
                if i not in used_persons and is_rider_on_bike(pb, mb):
                    # รวมกล่องให้ครอบคลุมทั้งมอเตอร์ไซค์และคนขี่
                    m_x1 = min(m_x1, pb[0])
                    m_y1 = min(m_y1, pb[1])
                    m_x2 = max(m_x2, pb[2])
                    m_y2 = max(m_y2, pb[3])
                    used_persons.add(i)

            # ป้องกันกรณีจับคนขี่ไม่ติด: ขยายกรอบด้านบนขึ้นเล็กน้อย (12%) เพื่อให้ครอบคลุมหมวกกันน็อก/คนขี่
            height = m_y2 - m_y1
            m_y1 = max(0, m_y1 - (height * 0.12))

            merged_moto_boxes.append([m_x1, m_y1, m_x2, m_y2])

        # บันทึกไฟล์
        saved_count += 1
        last_saved_frame = frame_idx
        file_base = f"frame_{saved_count:03d}_{frame_idx}"
        img_file = os.path.join(img_dir, f"{file_base}.jpg")
        lbl_file = os.path.join(lbl_dir, f"{file_base}.txt")
        prev_file = os.path.join(prev_dir, f"{file_base}_preview.jpg")

        # 1. บันทึกภาพต้นฉบับ
        cv2.imwrite(img_file, frame)

        # 2. บันทึก Label ไฟล์ .txt ตามมาตรฐาน YOLO (Normalized x_center, y_center, width, height)
        # Class 0: bus, 1: car, 2: motorbike, 3: truck
        yolo_annotations = []
        preview_frame = frame.copy()

        def add_yolo_annotation(box, class_id, label_name, color):
            x1, y1, x2, y2 = box
            # Clip ให้อยู่ในขอบเขตภาพ
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h
            cx = (x1 + x2) / (2.0 * w)
            cy = (y1 + y2) / (2.0 * h)

            if bw > 0 and bh > 0:
                yolo_annotations.append(f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")
                # วาด Preview
                cv2.rectangle(preview_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(preview_frame, label_name, (int(x1), max(20, int(y1) - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # บันทึก มอเตอร์ไซค์ (Class 2)
        for mb in merged_moto_boxes:
            add_yolo_annotation(mb, CLASS_MAP["motorbike"], "motorbike (bike+rider)", (0, 255, 0))

        # บันทึก รถประเภทอื่นๆ ในเฟรมเดียวกันด้วย เพื่อให้ Dataset ครบถ้วน
        for cb in car_boxes:
            add_yolo_annotation(cb, CLASS_MAP["car"], "car", (255, 200, 0))
        for bb in bus_boxes:
            add_yolo_annotation(bb, CLASS_MAP["bus"], "bus", (0, 165, 255))
        for tb in truck_boxes:
            add_yolo_annotation(tb, CLASS_MAP["truck"], "truck", (0, 0, 255))

        with open(lbl_file, "w") as f:
            f.writelines(yolo_annotations)

        # บันทึกภาพ Preview ให้ผู้ใช้ดูการตีกรอบ
        cv2.imwrite(prev_file, preview_frame)

        print(f"[{saved_count}/{TARGET_FRAMES}] สกัดภาพเฟรมที่ {frame_idx} (พบมอเตอร์ไซค์ {len(merged_moto_boxes)} คัน)", flush=True)

    cap.release()

    # สร้าง data.yaml ไว้ให้พร้อมสำหรับเทรนหรือนำเข้า
    yaml_content = f"""path: {os.path.abspath(OUTPUT_DIR)}
train: images
val: images

nc: 4
names: ['bus', 'car', 'motorbike', 'truck']
"""
    with open(os.path.join(OUTPUT_DIR, "data.yaml"), "w") as f:
        f.write(yaml_content)

    print("\n" + "="*60)
    print(f"✅ สกัดภาพและทำ Auto-Bounding Box สำเร็จทั้งหมด {saved_count} ภาพ!")
    print(f"📁 โฟลเดอร์เก็บข้อมูล: {OUTPUT_DIR}")
    print(f"   ├─ images/  : ภาพต้นฉบับ .jpg สำหรับอัปโหลดเข้า Roboflow")
    print(f"   ├─ labels/  : ไฟล์พิกัดกล่อง .txt (ตีกรอบมอเตอร์ไซค์+คนขับ อัตโนมัติ)")
    print(f"   ├─ preview/ : ภาพตัวอย่างที่วาดกรอบเขียวให้ตรวจทานได้ทันที")
    print(f"   └─ data.yaml: ไฟล์คอนฟิกพร้อมใช้งาน")
    print("="*60)

if __name__ == "__main__":
    main()
