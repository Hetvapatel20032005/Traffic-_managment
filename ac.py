from ultralytics import YOLO
import cv2
import time
import torch

# --- GPU Check ---
device = 0 if torch.cuda.is_available() else 'cpu'
print(f"🚀 Running on: {torch.cuda.get_device_name(0) if device == 0 else 'CPU'}")

# 🛠️ CHANGE 1: Use 'yolov8x.pt' (The Most Powerful Model)
# Pehli baar run karne par ye download hoga (~130MB)
print("⏳ Loading The Beast (yolov8x)...")
model = YOLO('yolov8x.pt') 

video_path = "static/traffic1.mp4" 
cap = cv2.VideoCapture(video_path)

print(f"\n{'FRAME':<10} | {'OBJECTS':<10} | {'AVG CONFIDENCE':<15} | {'SPEED':<10}")
print("=" * 55)

frame_count = 0
total_conf = 0

# Hum thoda aage ke frames check karenge jahan gadiyan clear hon
cap.set(cv2.CAP_PROP_POS_FRAMES, 50) 

while frame_count < 10:
    ret, frame = cap.read()
    if not ret: break
    
    start_time = time.time()
    
    # 🛠️ CHANGE 2 & 3: High Res (1280) + High Confidence Filter (0.50)
    # conf=0.50 ka matlab: Sirf wahi dikhao jisme AI 50% se zyada sure hai
    results = model(frame, imgsz=1280, verbose=False, conf=0.50, device=device)
    
    end_time = time.time()
    
    for r in results:
        boxes = r.boxes
        count = len(boxes)
        
        if count > 0:
            # Average Confidence Calculation
            avg_conf = sum(boxes.conf.cpu().numpy()) / count
            speed_ms = (end_time - start_time) * 1000
            
            # Color coding for output
            conf_str = f"{avg_conf*100:.2f}%"
            
            print(f"{frame_count:<10} | {count:<10} | {conf_str:<15} | {speed_ms:.1f} ms")
            total_conf += avg_conf * 100
            
    frame_count += 1

print("=" * 55)
final_avg = total_conf / 10

print(f"\n✅ FINAL REPORT (OPTIMIZED):")
print(f"🎯 Model Used: YOLOv8 Extra Large (yolov8x)")
print(f"📺 Resolution: 1280p (HD Analysis)")
print(f"🔥 Average Accuracy/Confidence: {final_avg:.2f}%")

if final_avg > 80:
    print("🏆 STATUS: EXCELLENT PERFORMANCE")
else:
    print("⚠️ STATUS: GOOD (Try increasing conf threshold)")