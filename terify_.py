import torch
import cv2
from ultralytics import YOLO

# 检查CUDA是否可用
print(f"CUDA is available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU device: {torch.cuda.get_device_name(0)}")

# 验证OpenCV
print(f"OpenCV version: {cv2.__version__}")

# 验证YOLO
model = YOLO("yolo11s.pt")
print("YOLO model loaded successfully")
