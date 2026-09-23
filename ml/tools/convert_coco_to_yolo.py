"""
convert_coco_to_yolo.py
-----------------------
แปลง dataset จาก MS COCO format -> YOLO format
แล้วสร้าง dataset.yaml สำหรับ fine-tune โมเดล YOLO

วิธีใช้:
    python convert_coco_to_yolo.py

โครงสร้าง dataset ที่ต้องมี (แก้ DATASET_ROOT ด้านล่าง):
    dataset/
    ├── images/
    │   ├── train/
    │   └── val/
    └── annotations/
        ├── instances_train.json
        └── instances_val.json
"""

import json
import os
import shutil
from pathlib import Path

# ============================================================
# ตั้งค่าตามโครงสร้าง dataset ของคุณ
# ============================================================

DATASET_ROOT = r"C:\path\to\your\dataset"   # << แก้ path ตรงนี้

# COCO category IDs ที่ต้องการ (ตรงกับ vehicle classes)
# COCO standard (1-indexed): car=3, motorcycle=4, bus=6, truck=8
# ถ้า dataset ของคุณใช้ category_id ต่างออกไป ให้แก้ตรงนี้
WANTED_CATEGORIES = {
    3: "car",
    4: "motorcycle",
    6: "bus",
    8: "truck",
}

# Output directory (จะสร้างให้อัตโนมัติ)
OUTPUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset_yolo")

# ============================================================


def coco_to_yolo(ann_json_path, images_dir, output_images_dir, output_labels_dir):
    os.makedirs(output_images_dir, exist_ok=True)
    os.makedirs(output_labels_dir, exist_ok=True)

    with open(ann_json_path, "r") as f:
        coco = json.load(f)

    # สร้าง mapping: category_id -> yolo class index (0-indexed)
    cat_id_to_yolo = {}
    yolo_idx = 0
    for cat in coco["categories"]:
        cid = cat["id"]
        if cid in WANTED_CATEGORIES:
            cat_id_to_yolo[cid] = yolo_idx
            yolo_idx += 1

    if not cat_id_to_yolo:
        print("  ไม่พบ category ที่ตรงกัน!")
        print(f"  Categories ที่มีใน JSON: {[c['name'] for c in coco['categories']]}")
        return 0

    print(f"  Category mapping: {cat_id_to_yolo}")

    img_id_to_info = {img["id"]: img for img in coco["images"]}

    img_annotations = {}
    for ann in coco["annotations"]:
        cid = ann["category_id"]
        if cid not in cat_id_to_yolo:
            continue
        iid = ann["image_id"]
        if iid not in img_annotations:
            img_annotations[iid] = []
        img_annotations[iid].append(ann)

    converted = 0
    skipped = 0

    for img_id, anns in img_annotations.items():
        img_info = img_id_to_info.get(img_id)
        if img_info is None:
            continue

        file_name = img_info["file_name"]
        img_w = img_info["width"]
        img_h = img_info["height"]

        src_img = os.path.join(images_dir, file_name)
        if not os.path.exists(src_img):
            src_img = os.path.join(images_dir, os.path.basename(file_name))
        if not os.path.exists(src_img):
            skipped += 1
            continue

        dst_img = os.path.join(output_images_dir, os.path.basename(file_name))
        if not os.path.exists(dst_img):
            shutil.copy2(src_img, dst_img)

        label_name = Path(os.path.basename(file_name)).stem + ".txt"
        label_path = os.path.join(output_labels_dir, label_name)

        yolo_lines = []
        for ann in anns:
            cls_idx = cat_id_to_yolo[ann["category_id"]]
            x_min, y_min, bw, bh = ann["bbox"]
            cx = max(0.0, min(1.0, (x_min + bw / 2) / img_w))
            cy = max(0.0, min(1.0, (y_min + bh / 2) / img_h))
            nw = max(0.0, min(1.0, bw / img_w))
            nh = max(0.0, min(1.0, bh / img_h))
            yolo_lines.append(f"{cls_idx} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        with open(label_path, "w") as lf:
            lf.write("\n".join(yolo_lines))

        converted += 1

    print(f"  แปลงสำเร็จ: {converted} ภาพ | ข้าม: {skipped} ภาพ")
    return converted


def create_dataset_yaml(output_root, class_names):
    yaml_content = f"""# dataset.yaml - Fine-tune YOLO on traffic dataset
# สร้างโดย convert_coco_to_yolo.py

path: {output_root}
train: images/train
val:   images/val

nc: {len(class_names)}
names: {class_names}
"""
    yaml_path = os.path.join(output_root, "dataset.yaml")
    with open(yaml_path, "w") as f:
        f.write(yaml_content)
    print(f"สร้าง dataset.yaml: {yaml_path}")
    return yaml_path


def main():
    print("=" * 60)
    print("  COCO -> YOLO Dataset Converter")
    print("=" * 60)

    dataset_root = Path(DATASET_ROOT)
    if not dataset_root.exists():
        print(f"ไม่พบ DATASET_ROOT: {DATASET_ROOT}")
        print("กรุณาแก้ตัวแปร DATASET_ROOT ในไฟล์นี้")
        return

    class_names = list(WANTED_CATEGORIES.values())
    print(f"Classes: {class_names}")
    print(f"Input : {DATASET_ROOT}")
    print(f"Output: {OUTPUT_ROOT}\n")

    print("กำลังแปลง train set...")
    coco_to_yolo(
        str(dataset_root / "annotations" / "instances_train.json"),
        str(dataset_root / "images" / "train"),
        os.path.join(OUTPUT_ROOT, "images", "train"),
        os.path.join(OUTPUT_ROOT, "labels", "train"),
    )

    print("กำลังแปลง val set...")
    coco_to_yolo(
        str(dataset_root / "annotations" / "instances_val.json"),
        str(dataset_root / "images" / "val"),
        os.path.join(OUTPUT_ROOT, "images", "val"),
        os.path.join(OUTPUT_ROOT, "labels", "val"),
    )

    create_dataset_yaml(OUTPUT_ROOT, class_names)

    print("\n" + "=" * 60)
    print("เสร็จสิ้น! ขั้นตอนถัดไป: รัน python fine_tune_yolo.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
