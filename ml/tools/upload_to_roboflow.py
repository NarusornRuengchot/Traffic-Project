"""
สคริปต์อัปโหลดภาพและ Bounding Box ขึ้น Roboflow อัตโนมัติ
วิธีใช้งาน:
1. ติดตั้ง roboflow: pip install roboflow
2. ใส่ API_KEY และ PROJECT_ID ของคุณ
3. รันคำสั่ง: python upload_to_roboflow.py
"""
import os
from roboflow import Roboflow

# กำหนดข้อมูลโปรเจกต์ Roboflow ของคุณ
ROBOFLOW_API_KEY = "YOUR_API_KEY_HERE"
WORKSPACE_ID = "YOUR_WORKSPACE"
PROJECT_ID = "YOUR_PROJECT_NAME"

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset_motorcycles")

def upload():
    if ROBOFLOW_API_KEY == "YOUR_API_KEY_HERE":
        print("⚠️ กรุณาใส่ ROBOFLOW_API_KEY ของคุณในไฟล์ upload_to_roboflow.py ก่อนรัน")
        return

    rf = Roboflow(api_key=ROBOFLOW_API_KEY)
    project = rf.workspace(WORKSPACE_ID).project(PROJECT_ID)

    img_dir = os.path.join(DATASET_DIR, "images")
    lbl_dir = os.path.join(DATASET_DIR, "labels")

    image_files = [f for f in os.listdir(img_dir) if f.endswith(".jpg")]
    print(f"กำลังอัปโหลด {len(image_files)} ภาพขึ้น Roboflow...")

    for i, img_name in enumerate(image_files, 1):
        img_path = os.path.join(img_dir, img_name)
        lbl_name = img_name.replace(".jpg", ".txt")
        lbl_path = os.path.join(lbl_dir, lbl_name)

        if os.path.exists(lbl_path):
            project.upload(
                image_path=img_path,
                annotation_path=lbl_path,
                split="train"
            )
            print(f"[{i}/{len(image_files)}] อัปโหลดแล้ว: {img_name} + Bounding Box")
        else:
            project.upload(image_path=img_path, split="train")
            print(f"[{i}/{len(image_files)}] อัปโหลดเฉพาะภาพ: {img_name}")

    print("🎉 อัปโหลดขึ้น Roboflow เสร็จสิ้นเรียบร้อย!")

if __name__ == "__main__":
    upload()
