import time

class TrafficController:
    def __init__(self):
        self.current_green_lane = 0
        self.start_time = time.time()
        self.duration = 10  # Minimum green time lock
        self.is_emergency_active = False 
        print("🚦 Logic Engine Started.")

    def decide_signal(self, lane_data):
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        # 1. Emergency Override
        emergency_lane = -1
        for i, lane in enumerate(lane_data):
            if lane['emergency']:
                emergency_lane = i
                break
        
        # If Emergency is detected
        if emergency_lane != -1:
            # If we are already green on that lane and mode is active, just return high time
            if self.current_green_lane == emergency_lane and self.is_emergency_active:
                return self._generate_output(emergency_lane, 99)
            
            # Switch to Emergency immediately
            self.current_green_lane = emergency_lane
            self.start_time = current_time 
            self.duration = 10 
            self.is_emergency_active = True
            return self._generate_output(emergency_lane, 99)
        
        # Reset Emergency Flag if clear
        if self.is_emergency_active and emergency_lane == -1:
            self.is_emergency_active = False
            self.start_time = current_time - self.duration # Allow immediate switch

        # 2. Timer Lock (Crucial for Stability)
        if elapsed_time < self.duration:
            return self._generate_output(self.current_green_lane, int(self.duration - elapsed_time))

        # 3. Smart Switching
        pcus = [lane['pcu'] for lane in lane_data]
        new_best_lane = pcus.index(max(pcus))
        max_pcu = max(pcus)
        
        # Logic: If high traffic continues on current lane, extend green light
        if new_best_lane == self.current_green_lane and max_pcu > 10:
            self.duration = 10 
            self.start_time = current_time
            return self._generate_output(self.current_green_lane, self.duration)
        elif new_best_lane == self.current_green_lane:
            # If traffic is low on current lane, cycle to next
            new_best_lane = (self.current_green_lane + 1) % 4 

        # Assign Time based on Load
        if max_pcu > 40: new_time = 45
        elif max_pcu > 20: new_time = 25
        else: new_time = 15
            
        self.current_green_lane = new_best_lane
        self.duration = new_time
        self.start_time = current_time

        return self._generate_output(new_best_lane, new_time)

    def _generate_output(self, active_lane, timer):
        signals = ["RED"] * 4
        timers = [0] * 4
        signals[active_lane] = "GREEN"
        timers[active_lane] = timer
        return signals, timers, active_lane