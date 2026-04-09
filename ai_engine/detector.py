from ultralytics import YOLO
import cv2
import torch
import numpy as np
import threading  # 👈 Thread collision fix karne ke liye

class TrafficDetector:
    def __init__(self):
        # --- GPU CHECK ---
        if torch.cuda.is_available():
            self.device = 0 
            print(f"✅ GPU ACTIVE: {torch.cuda.get_device_name(0)}")
        else:
            self.device = 'cpu'
            print("⚠️ GPU Not Found!")

        # Model Load (Small is best for speed/accuracy balance)
        self.model = YOLO('yolov8s.pt') 
        
        # Mapping
        self.class_map = { 1: "bicycle", 2: "car", 3: "motorbike", 5: "bus", 7: "truck" }
        self.vehicle_weights = { "bicycle": 0.2, "motorbike": 0.5, "car": 1.0, "bus": 3.0, "truck": 2.5 }

        # ⚙️ SIMPLE SETTINGS (Yahan change karo)
        # -------------------------------------------------
        # 1. Service Lane kis taraf hai? (True = Right side, False = Left side)
        self.SERVICE_ON_RIGHT = True 
        
        # 2. Main Road kitni chaudi hai? (0.70 matlab 70% Main Road, 30% Service Lane)
        self.SPLIT_RATIO = 0.70 
        # -------------------------------------------------

        # 👇 THREAD LOCK & PRE-WARM LOGIC (Crash Fix) 👇
        self.lock = threading.Lock()
        print("🔥 Pre-warming AI Model to prevent thread collisions...")
        # Dummy frame bhej kar model ko pehle hi ready kar rahe hain
        dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model(dummy_frame, device=self.device, verbose=False)
        print("✅ Model Pre-warmed & Locked!")
        # 👆 ------------------------------------------------ 👆

    def process_frame(self, frame, only_emergency=False):
        # 1. Frame Size Nikalo (Automatic)
        height, width, _ = frame.shape
        
        # 2. Divider Line Calculate karo
        if self.SERVICE_ON_RIGHT:
            # Agar Right me service lane hai, to Line 70% pe banegi
            limit_x = int(width * self.SPLIT_RATIO)
        else:
            # Agar Left me service lane hai, to Line 30% pe banegi
            limit_x = int(width * (1 - self.SPLIT_RATIO))

        # 3. Detection (👇 WITH THREAD LOCK 👇)
        with self.lock:
            # Is block ke andar ek baar mein sirf ek camera allow hoga!
            results = self.model(frame, imgsz=640, stream=True, verbose=False, conf=0.3, device=self.device)
        
        counts = {"car": 0, "motorbike": 0, "bus": 0, "truck": 0, "bicycle": 0}
        total_pcu = 0.0
        emergency_detected = False
        processed_frame = frame

        # --- DRAW CLEAN DIVIDER LINE ---
        # Yellow Line
        cv2.line(processed_frame, (limit_x, 0), (limit_x, height), (0, 255, 255), 2)
        
        # Labels lagao taaki pata chale kaunsa zone kya hai
        if self.SERVICE_ON_RIGHT:
            cv2.putText(processed_frame, "MAIN ROAD", (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(processed_frame, "SERVICE LANE", (limit_x + 10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        else:
            cv2.putText(processed_frame, "SERVICE LANE", (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            cv2.putText(processed_frame, "MAIN ROAD", (limit_x + 10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls = int(box.cls[0])
                if cls in self.class_map:
                    label = self.class_map[cls]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # 📍 Center Point check karo
                    cx = (x1 + x2) // 2

                    # 🧠 LOGIC: Check Zone
                    in_service_zone = False
                    
                    if self.SERVICE_ON_RIGHT:
                        if cx > limit_x: in_service_zone = True  # Line ke Right side
                    else:
                        if cx < limit_x: in_service_zone = True  # Line ke Left side

                    # 🛑 FILTER LOGIC
                    # Agar Service Zone me hai aur Heavy Vehicle nahi hai -> IGNORE
                    should_ignore = False
                    
                    if in_service_zone or only_emergency:
                        if label not in ["bus", "truck"]:
                            should_ignore = True
                    
                    if should_ignore:
                        # Grey Box (Ignored Vehicle) - Thoda transparent dikhate hain
                        overlay = processed_frame.copy()
                        cv2.rectangle(overlay, (x1, y1), (x2, y2), (128, 128, 128), -1)
                        cv2.addWeighted(overlay, 0.3, processed_frame, 0.7, 0, processed_frame)
                        continue 

                    # --- Valid Detection ---
                    if label in counts: counts[label] += 1
                    total_pcu += self.vehicle_weights.get(label, 1.0)

                    # Colors
                    color = (0, 255, 0)
                    if label in ["motorbike", "bicycle"]: color = (255, 255, 0)
                    elif label in ["bus", "truck"]: color = (0, 165, 255)
                    
                    # Emergency
                    if label == "bus": 
                        emergency_detected = True
                        color = (0, 0, 255)
                        cv2.putText(processed_frame, "EMERGENCY", (x1, y1 - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                    cv2.rectangle(processed_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(processed_frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # Mode Indicator
        if only_emergency:
            cv2.putText(processed_frame, "MODE: FORCE SERVICE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        else:
            cv2.putText(processed_frame, "MODE: SMART SPLIT", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(processed_frame, f'Load: {total_pcu:.1f}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return processed_frame, counts, total_pcu, emergency_detected