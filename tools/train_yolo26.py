"""
KU SRC Smart Traffic Analytics - YOLO26 Fine-Tuning Script
Leveraging Ultralytics YOLO26 NMS-Free architecture, STAL (Small-Target-Aware Label Assignment),
and MuSGD optimizer for enhanced motorcycle and vehicle detection.
"""

import os
import sys
from ultralytics import YOLO

# Configuration
BASE_MODEL = "yolo26s.pt"      # Options: yolo26n.pt (fastest), yolo26s.pt (balanced high accuracy)
DATASET_YAML = "Smart-Traffic-1/data.yaml"  # Path to your dataset data.yaml
EPOCHS = 50
IMGSZ = 640
BATCH = 16                     # Adjust to 8 if GPU memory is limited
PROJECT = "runs/detect"
NAME = "traffic_yolo26"

def train():
    if not os.path.exists(DATASET_YAML):
        print(f"⚠️ Dataset config not found at '{DATASET_YAML}'. Please update DATASET_YAML path.")
        return

    print("=" * 60)
    print("🚀 Starting YOLO26 Next-Gen Training Pipeline...")
    print(f"   Base Architecture: {BASE_MODEL}")
    print(f"   Dataset:           {DATASET_YAML}")
    print(f"   Epochs:            {EPOCHS} | Img Size: {IMGSZ} | Batch: {BATCH}")
    print("   Features:          NMS-Free Dual Head + STAL Small Target Optimization")
    print("=" * 60)

    # 1. Initialize YOLO26
    model = YOLO(BASE_MODEL)

    # 2. Train with optimized hyper-parameters
    results = model.train(
        data=DATASET_YAML,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        project=PROJECT,
        name=NAME,
        mosaic=0.5,             # Reduced mosaic so small motorcycles don't shrink too much
        close_mosaic=10,        # Turn off mosaic in final 10 epochs for natural frame tuning
        save=True,
        verbose=True
    )

    best_weight = os.path.join(PROJECT, NAME, "weights", "best.pt")
    if os.path.exists(best_weight):
        dest = os.path.join("models", "best_yolo26.pt")
        os.makedirs("models", exist_ok=True)
        import shutil
        shutil.copyfile(best_weight, dest)
        print(f"\n🎉 Training complete! Best YOLO26 model copied to: {dest}")
    else:
        print("\n✅ Training finished. Please check runs/detect for results.")

if __name__ == "__main__":
    train()
