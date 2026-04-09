import random
import time

class RadarDetector:
    def __init__(self):
        self.speed_limit = 60  # km/h
        self.detection_range = 100  # meters

    def get_live_speed(self):
        # Simulate live radar speed detection
        # In real implementation, connect to radar hardware/API
        speed = random.randint(20, 120)  # Random speed for demo
        return speed

    def check_speed_violation(self, speed):
        return speed > self.speed_limit

    def get_data(self):
        speed = self.get_live_speed()
        violation = self.check_speed_violation(speed)
        return {
            "speed": speed,
            "violation": violation,
            "timestamp": time.time()
        }