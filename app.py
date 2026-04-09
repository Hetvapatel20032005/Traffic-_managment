from flask import Flask, render_template, Response, jsonify, request, session, redirect, url_for, make_response
from flask_cors import CORS
from ai_engine.detector import TrafficDetector
from ai_engine.traffic_logic import TrafficController
from ai_engine.radar import RadarDetector
import database
from functools import wraps 
import os
import random
import time
import csv
from io import StringIO
import requests # 🔥 NAYA IMPORT: FastAPI se baat karne ke liye

# --- 🛠️ SYSTEM OPTIMIZATION (Fix for Lag) ---
cv2.setNumThreads(0) 
# --------------------------------------------

app = Flask(__name__)
app.secret_key = "SUPER_SECRET_KEY_FOR_VIVA" # Session Security Key
CORS(app) # Cloud deployment ke liye allow cross-origin

# --- ⚙️ PERFORMANCE CONFIG (Speed Control) ---
FRAME_SKIP = 7        # Har 7th frame process hoga
JPEG_QUALITY = 70     # Video quality 70%
RESIZE_DIM = (640, 360) # Standard Resolution

# --- 📹 LOAD VIDEOS ---
VIDEOS = [
    "static/traffic1.mp4", 
    "static/traffic2.mp4",
    "static/traffic3.mp4", 
    "static/traffic4.mp4"
]

# Live camera ke liye normal cv2, MP4 ke liye FFMPEG
cameras = []
for v in VIDEOS:
    if isinstance(v, str) and (v.startswith("http") or v.startswith("rtsp")):
        cameras.append(cv2.VideoCapture(v))
    else:
        cameras.append(cv2.VideoCapture(v, cv2.CAP_FFMPEG))

# --- 🧠 AI ENGINES INITIALIZATION ---
print("⏳ Initializing AI Engines...")
detector = TrafficDetector()
controller = TrafficController()
radar = RadarDetector()
print("✅ AI Engines Ready!")

# --- 📊 GLOBAL STATE ---
current_state = {
    "lanes": [
        {"id": 1, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False},
        {"id": 2, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False},
        {"id": 3, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False},
        {"id": 4, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False}
    ],
    "priority_lane": 0,
    "accident_mode": False,
    "helpdesk_tickets": [] # Tickets store karne ke liye
}

# DB Timer Tracker
last_db_log_time = time.time()

# --- 🔐 SECURITY DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- 📹 VIDEO GENERATOR FUNCTION ---
def generate_frames(lane_id):
    cam = cameras[lane_id]
    frame_counter = 0
    last_processed_frame = None

    while True:
        success, frame = cam.read()
        if not success: 
            video_source = VIDEOS[lane_id]
            if isinstance(video_source, str) and video_source.endswith('.mp4'):
                cam.set(cv2.CAP_PROP_POS_FRAMES, 0) 
            continue
        
        frame = cv2.resize(frame, RESIZE_DIM) 
        frame_counter += 1
        
        lane_data = current_state["lanes"][lane_id]
        signal = lane_data["signal"]
        is_service_mode = lane_data["is_service"]
        
        if current_state["accident_mode"]: 
            signal = "RED"

        if frame_counter % FRAME_SKIP == 0:
            processed_frame, counts, pcu, is_emergency = detector.process_frame(frame, only_emergency=is_service_mode)
            
            if signal == "RED":
                overlay = processed_frame.copy()
                cv2.rectangle(overlay, (0, 0), RESIZE_DIM, (0, 0, 100), -1) 
                cv2.addWeighted(overlay, 0.3, processed_frame, 0.7, 0, processed_frame)
                cv2.putText(processed_frame, "HALT", (250, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
            else:
                cv2.putText(processed_frame, "GO", (270, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 4)

            current_state["lanes"][lane_id]["pcu"] = pcu
            current_state["lanes"][lane_id]["counts"] = counts
            current_state["lanes"][lane_id]["emergency"] = is_emergency
            
            last_processed_frame = processed_frame
        else:
            processed_frame = last_processed_frame if last_processed_frame is not None else frame

        if current_state["accident_mode"]:
            cv2.putText(processed_frame, "ACCIDENT MODE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        ret, buffer = cv2.imencode('.jpg', processed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# --- 🧠 LOGIC UPDATER & LIVE DB LOGGING ---
def update_logic():
    global last_db_log_time

    if current_state["accident_mode"]:
        for i in range(4): current_state["lanes"][i]["signal"] = "RED"
        return

    lane_data = [{"pcu": l["pcu"], "emergency": l.get("emergency", False)} for l in current_state["lanes"]]
    signals, timers, active_idx = controller.decide_signal(lane_data)

    for i in range(4):
        current_state["lanes"][i]["signal"] = signals[i]
        current_state["lanes"][i]["timer"] = timers[i]
    current_state["priority_lane"] = active_idx

    # 🔥 LIVE DATA LOGGING TO DATABASE (Every 5 seconds) 🔥
    current_time = time.time()
    if current_time - last_db_log_time > 5.0:
        for i in range(4):
            l = current_state["lanes"][i]
            database.log_traffic_data(i+1, l["counts"], l["pcu"], l["signal"])
        last_db_log_time = current_time

# --- 🌐 WEB ROUTES ---



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username') 
        if not user and request.is_json:
            data = request.get_json()
            user = data.get('username')
            pw = data.get('password')
        else:
            pw = request.form.get('password')

        if database.verify_login(user, pw):
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="🚫 Invalid Credentials!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required 
def index(): 
    return render_template('dashboard.html')


@app.route('/')
def home():
    return "✅ Backend Working on Render!"

@app.route('/video_feed_<int:lane_id>')
@login_required
def video_feed(lane_id): 
    return Response(generate_frames(lane_id-1), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_stats')
@login_required
def get_stats():
    update_logic() 
    
    # 🔥 FASTAPI BRIDGE: Fetch live tickets from FastAPI
    try:
        response = requests.get("http://127.0.0.1:8000/api/v1/tickets/", timeout=1)
        if response.status_code == 200:
            all_tickets = response.json()
            # Format tickets for Vercel Dashboard
            formatted_tickets = []
            for t in all_tickets:
                if t['status'] != 'resolved': # Only show open tickets
                    formatted_tickets.append({
                        "type": t['issue_type'],
                        "location": t['location'],
                        "priority": t['severity'].upper()
                    })
            # Ulta kar do taaki latest ticket upar dikhe
            current_state["helpdesk_tickets"] = formatted_tickets[::-1]
        else:
            current_state["helpdesk_tickets"] = database.get_active_tickets()
    except Exception:
        # Fallback to local DB if FastAPI is off
        current_state["helpdesk_tickets"] = database.get_active_tickets()

    return jsonify(current_state)

@app.route('/toggle_service_mode/<int:lane_id>', methods=['POST'])
@login_required
def toggle_service_mode(lane_id):
    current_state["lanes"][lane_id-1]["is_service"] = not current_state["lanes"][lane_id-1]["is_service"]
    return jsonify({"status": "success", "new_mode": current_state["lanes"][lane_id-1]["is_service"]})

# 🗄️ FASTAPI BRIDGE: SAVE TICKETS
@app.route('/create_ticket', methods=['POST'])
@login_required
def create_ticket():
    data = request.get_json()
    
    # Priority Format Theek karna
    raw_priority = data.get("priority", "low").lower()
    if raw_priority == "med risk": raw_priority = "medium"
    elif raw_priority == "high risk": raw_priority = "high"
    elif raw_priority not in ["low", "medium", "high", "critical"]: raw_priority = "low"

    fastapi_payload = {
        "issue_type": data.get("type", "Manual Dashboard Alert"),
        "location": data.get("location", "Unknown Zone"),
        "device_id": "DASHBOARD-001",
        "severity": raw_priority
    }

    try:
        # Send to FastAPI Server
        response = requests.post("http://127.0.0.1:8000/api/v1/tickets/", json=fastapi_payload, timeout=2)
        if response.status_code == 200:
            ticket_id = response.json()['ticket_id']
            return jsonify({"status": "success", "ticket": f"TKT-{ticket_id}"})
    except Exception as e:
        print(f"⚠️ FastAPI is down, saving to Local DB: {e}")

    # Fallback if FastAPI is not running
    ticket_id = f"TKT-{random.randint(1000, 9999)}"
    database.add_ticket(ticket_id, data.get("type", "General Issue"), data.get("priority", "Medium"), data.get("location", "Unknown Zone"))
    return jsonify({"status": "success", "ticket": ticket_id})

# 🚨 SOS MODE (Creates Ticket Automatically)
@app.route('/toggle_accident', methods=['POST'])
@login_required
def toggle_accident():
    current_state["accident_mode"] = not current_state["accident_mode"]
    if current_state["accident_mode"]:
        fastapi_payload = {
            "issue_type": "CRITICAL: Collision Detected",
            "location": "Global Lockdown Triggered",
            "device_id": "SYS-SOS",
            "severity": "critical"
        }
        try:
            requests.post("http://127.0.0.1:8000/api/v1/tickets/", json=fastapi_payload, timeout=2)
        except:
            ticket_id = f"SOS-{random.randint(1000, 9999)}"
            database.add_ticket(ticket_id, "CRITICAL: Collision Detected", "CRITICAL", "Global Lockdown")
            
    return jsonify({"status": current_state["accident_mode"]})

# 📊 EXCEL EXPORT ROUTE
@app.route('/export_excel')
@login_required
def export_excel():
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traffic_logs ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Database ID', 'Node / Camera', 'Date & Time', 'Cars', 'Bikes', 'Buses', 'Trucks', 'Total PCU Density', 'Signal State'])
    
    for row in logs:
        cw.writerow([row['id'], f"NODE-0{row['node_id']}", row['timestamp'], row['cars'], row['bikes'], row['buses'], row['trucks'], round(row['total_pcu'], 1), row['signal_state']])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=SmartCity_Traffic_Analytics.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# 📡 RADAR LIVE DATA ROUTE
@app.route('/get_radar_data')
@login_required
def get_radar_data():
    data = radar.get_data()
    return jsonify(data)

# 🤖 SUPPORT CHATBOT
@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    user_msg = data.get("message", "").lower()
    
    if "camera" in user_msg and ("offline" in user_msg or "black" in user_msg):
        reply = "🛠️ CAMERA ISSUE: Check if the IP address matches your phone's current IP."
    elif "lag" in user_msg or "slow" in user_msg:
        reply = "⚡ PERFORMANCE: Reduce 'JPEG_QUALITY' or increase 'FRAME_SKIP' in app.py."
    elif "ticket" in user_msg or "report" in user_msg:
        reply = f"🎫 TICKETING: There are currently {len(current_state['helpdesk_tickets'])} active incidents in the database."
    elif "status" in user_msg or "traffic" in user_msg:
        reply = f"📊 STATUS: Lane 0{current_state['priority_lane'] + 1} has the Green signal."
    elif "excel" in user_msg or "download" in user_msg or "report" in user_msg:
        reply = "📊 EXCEL REPORT: You can download the full database log by clicking the Green 'DOWNLOAD EXCEL' button on the left sidebar."
    else:
        reply = "🤖 I am your NOC AI. Ask about 'camera offline', 'lag', 'tickets', or 'excel download'."

    return jsonify({"response": reply})

# --- 🚀 MAIN ENTRY POINT ---
if __name__ == "__main__":
    database.init_db()
    
    port = int(os.environ.get('PORT', 5005))
    print("\n" + "="*50)
    print("🔒 SECURE TRAFFIC AI SERVER STARTING...")
    print(f"🚀 PERFORMANCE CONFIG: Skip={FRAME_SKIP}, Quality={JPEG_QUALITY}%")
    print(f"🌍 SERVER URL: http://127.0.0.1:{port}") 
    print("="*50 + "\n")
    
    # 🔥 FIXED: ssl_context removed to prevent Vercel/Ngrok connection errors
    app.run(debug=False, threaded=True, host='0.0.0.0', port=port)