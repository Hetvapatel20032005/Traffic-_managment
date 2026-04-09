import sqlite3
import datetime

DB_NAME = "smartcity_noc.db"

def get_connection():
    # Database connection establish karne ke liye helper function
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Isse data dictionary format me milta hai
    return conn

def init_db():
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # ==========================================
        # TABLE 1: ADMIN USERS (Login/Security)
        # ==========================================
        c.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'System Admin'
            )
        ''')
        # Default Admin ID bana do agar nahi hai toh
        c.execute("INSERT OR IGNORE INTO admin_users (username, password) VALUES ('admin', 'admin123')")

        # ==========================================
        # TABLE 2: HELPDESK TICKETS (Incident Logs)
        # ==========================================
        c.execute('''
            CREATE TABLE IF NOT EXISTS helpdesk_tickets (
                ticket_id TEXT PRIMARY KEY,
                issue_type TEXT,
                priority TEXT,
                location TEXT,
                timestamp TEXT,
                status TEXT DEFAULT 'ACTIVE'
            )
        ''')

        # ==========================================
        # TABLE 3: ADVANCED TRAFFIC LOGS (Analytics)
        # ==========================================
        c.execute('''
            CREATE TABLE IF NOT EXISTS traffic_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER, 
                timestamp TEXT,
                cars INTEGER, 
                bikes INTEGER, 
                buses INTEGER, 
                trucks INTEGER,
                total_pcu REAL, 
                signal_state TEXT
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ Smart City Database & Tables Initialized Successfully!")
    except Exception as e:
        print(f"❌ Database Init Error: {e}")

# --- 1. TRAFFIC DATA LOGGING FUNCTION ---
def log_traffic_data(node_id, counts, pcu, signal):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Safe dictionary getters (agar koi gaadi na ho to error na aaye)
        cars = counts.get('car', 0)
        bikes = counts.get('motorbike', 0) + counts.get('bicycle', 0)
        buses = counts.get('bus', 0)
        trucks = counts.get('truck', 0)

        c.execute('''
            INSERT INTO traffic_logs 
            (node_id, timestamp, cars, bikes, buses, trucks, total_pcu, signal_state) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (node_id, now, cars, bikes, buses, trucks, pcu, signal))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Traffic DB Error: {e}")

# --- 2. HELPDESK TICKET FUNCTIONS ---
def add_ticket(ticket_id, issue_type, priority, location):
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        c.execute('''
            INSERT INTO helpdesk_tickets (ticket_id, issue_type, priority, location, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (ticket_id, issue_type, priority, location, now))
        
        conn.commit()
        conn.close()
        return now
    except Exception as e:
        print(f"❌ Ticket DB Error: {e}")

def get_active_tickets():
    try:
        conn = get_connection()
        c = conn.cursor()
        # Sirf latest 10 active tickets API me bhejenge
        c.execute("SELECT * FROM helpdesk_tickets WHERE status='ACTIVE' ORDER BY timestamp DESC LIMIT 10")
        tickets = c.fetchall()
        conn.close()
        
        # JSON API friendly format
        result = []
        for t in tickets:
            result.append({
                "id": t["ticket_id"],
                "type": t["issue_type"],
                "priority": t["priority"],
                "location": t["location"],
                "time": t["timestamp"].split(" ")[1] # Sirf time (HH:MM:SS) return karenge UI ke liye
            })
        return result
    except Exception as e:
        print(f"❌ Fetch Tickets Error: {e}")
        return []

# --- 3. ADMIN LOGIN FUNCTION ---
def verify_login(username, password):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM admin_users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        return user is not None
    except Exception as e:
        print(f"❌ Login DB Error: {e}")
        return False