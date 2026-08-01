"""
fine_tune_yolo.py
-----------------
Fine-tune YOLO model บน Roboflow dataset (YOLOv11 format)

วิธีใช้:
    1. แตกไฟล์ .zip จาก Roboflow ไว้ในโฟลเดอร์โปรเจกต์
    2. แก้ DATASET_YAML ด้านล่างให้ตรงกับ path ของ data.yaml
    3. รัน: python fine_tune_yolo.py
    4. โมเดลที่ fine-tune แล้วจะอยู่ใน runs/detect/traffic_finetune/weights/best.pt
    5. แก้ main.py ให้ใช้ best.pt แทน yolov11n.pt

หมายเหตุ: ไม่ต้องรัน convert_coco_to_yolo.py แล้ว
          เพราะ Roboflow แปลงเป็น YOLO format มาให้เรียบร้อยแล้ว
"""

import os
from ultralytics import YOLO

# ============================================================
# ตั้งค่า
# ============================================================

# Path ไปยัง data.yaml ที่ได้จาก Roboflow (แก้ชื่อโฟลเดอร์ให้ตรง)
# ตัวอย่าง: ถ้าแตกไฟล์แล้วได้โฟลเดอร์ชื่อ 'vehicles-coco-2'
DATASET_YAML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vehicles-coco-2", "data.yaml")

# โมเดล pretrained ที่จะใช้เป็น starting point
# ยิ่งใหญ่ = แม่นยำกว่า แต่ใช้เวลา train นานกว่า
BASE_MODEL = "yolo11s.pt"   # แนะนำ: n(เร็ว) / s(สมดุล) / m(แม่น)

# ============================================================
# Training hyperparameters
# ============================================================
EPOCHS      = 50        # จำนวนรอบ train (เพิ่มถ้า dataset ใหญ่)
IMGSZ       = 640       # ขนาดภาพ train
BATCH       = 8         # ลด batch size ถ้า RAM ไม่พอ (เช่น 4)
PATIENCE    = 10        # หยุด early ถ้า val loss ไม่ดีขึ้น N epochs
DEVICE      = "cpu"     # เปลี่ยนเป็น "0" ถ้ามี NVIDIA GPU
PROJECT     = "runs/detect"
NAME        = "traffic_finetune"
# ============================================================


def main():
    print("=" * 60)
    print("  YOLO Fine-tuning on Traffic Dataset")
    print("=" * 60)

    if not os.path.exists(DATASET_YAML):
        print(f"ไม่พบ dataset.yaml: {DATASET_YAML}")
        print("กรุณารัน convert_coco_to_yolo.py ก่อน")
        return

    print(f"Dataset : {DATASET_YAML}")
    print(f"Model   : {BASE_MODEL}")
    print(f"Epochs  : {EPOCHS}")
    print(f"Device  : {DEVICE}")
    print()

    # โหลด pretrained model
    model = YOLO(BASE_MODEL)

    # เริ่ม fine-tune
    results = model.train(
        data=DATASET_YAML,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        patience=PATIENCE,
        device=DEVICE,
        project=PROJECT,
        name=NAME,
        # Augmentation เพื่อป้องกัน overfitting
        flipud=0.0,     # ไม่พลิกบน-ล่าง (รถไม่ขับหัวลง)
        fliplr=0.5,     # พลิกซ้าย-ขวา 50%
        mosaic=1.0,     # mosaic augmentation
        # Freeze backbone ช่วยให้ train เร็วขึ้นบน CPU
        freeze=10,      # freeze 10 layers แรก (backbone)
    )

    # หา path โมเดลที่ดีที่สุด
    best_model_path = os.path.join(PROJECT, NAME, "weights", "best.pt")
    print("\n" + "=" * 60)
    print(f"Fine-tuning เสร็จสิ้น!")
    print(f"Best model: {best_model_path}")
    print()
    print("วิธีใช้โมเดลใหม่ใน main.py:")
    print(f'   MODEL_PATH = r"{best_model_path}"')
    print()
    print("วิธีใช้โมเดลใหม่ใน app.py (Streamlit):")
    print("   วางไฟล์ best.pt ไว้ในโฟลเดอร์โปรเจกต์")
    print("   แล้วเลือกในช่อง YOLO Model Size")
    print("=" * 60)

    # Validation ด้วย best model
    print("\nกำลัง Validate best model...")
    best_model = YOLO(best_model_path)
    metrics = best_model.val(data=DATASET_YAML, device=DEVICE)
    print(f"\nResults:")
    print(f"  mAP50     : {metrics.box.map50:.4f}")
    print(f"  mAP50-95  : {metrics.box.map:.4f}")
    print(f"  Precision : {metrics.box.p.mean():.4f}")
    print(f"  Recall    : {metrics.box.r.mean():.4f}")


if __name__ == "__main__":
    main()
