import os
import datetime

# ✅ Render pe DATABASE_URL environment variable set hoy che automatically
# Local testing mate SQLite fallback rakhi che
DATABASE_URL = os.environ.get("DATABASE_URL")

# ✅ Render PostgreSQL URL "postgres://" thi sharu thay, psycopg2 ne "postgresql://" joiye
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# --- CONNECTION HELPER ---
def get_connection():
    if DATABASE_URL:
        # 🌐 RENDER: PostgreSQL
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    else:
        # 💻 LOCAL: SQLite fallback
        import sqlite3
        conn = sqlite3.connect("smartcity_noc.db")
        conn.row_factory = sqlite3.Row
        return conn

def _is_pg():
    return DATABASE_URL is not None

# --- INIT DATABASE ---
def init_db():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        if _is_pg():
            # PostgreSQL syntax
            c.execute('''
                CREATE TABLE IF NOT EXISTS admin_users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT DEFAULT 'System Admin'
                )
            ''')
            c.execute('''
                INSERT INTO admin_users (username, password)
                VALUES ('admin', 'admin123')
                ON CONFLICT (username) DO NOTHING
            ''')
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
            c.execute('''
                CREATE TABLE IF NOT EXISTS traffic_logs (
                    id SERIAL PRIMARY KEY,
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
        else:
            # SQLite syntax (local)
            c.execute('''
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT DEFAULT 'System Admin'
                )
            ''')
            c.execute("INSERT OR IGNORE INTO admin_users (username, password) VALUES ('admin', 'admin123')")
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
        db_type = "PostgreSQL (Render)" if _is_pg() else "SQLite (Local)"
        print(f"✅ Smart City Database Initialized! Using: {db_type}")

    except Exception as e:
        print(f"❌ Database Init Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- 1. TRAFFIC DATA LOGGING ---
def log_traffic_data(node_id, counts, pcu, signal):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cars   = counts.get('car', 0)
        bikes  = counts.get('motorbike', 0) + counts.get('bicycle', 0)
        buses  = counts.get('bus', 0)
        trucks = counts.get('truck', 0)

        if _is_pg():
            c.execute('''
                INSERT INTO traffic_logs
                (node_id, timestamp, cars, bikes, buses, trucks, total_pcu, signal_state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (node_id, now, cars, bikes, buses, trucks, pcu, signal))
        else:
            c.execute('''
                INSERT INTO traffic_logs
                (node_id, timestamp, cars, bikes, buses, trucks, total_pcu, signal_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (node_id, now, cars, bikes, buses, trucks, pcu, signal))

        conn.commit()
        print(f"✅ Traffic data logged for Node {node_id}")

    except Exception as e:
        print(f"❌ Traffic DB Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- 2. HELPDESK TICKET FUNCTIONS ---
def add_ticket(ticket_id, issue_type, priority, location):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if _is_pg():
            c.execute('''
                INSERT INTO helpdesk_tickets (ticket_id, issue_type, priority, location, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (ticket_id) DO NOTHING
            ''', (ticket_id, issue_type, priority, location, now))
        else:
            c.execute('''
                INSERT OR IGNORE INTO helpdesk_tickets (ticket_id, issue_type, priority, location, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (ticket_id, issue_type, priority, location, now))

        conn.commit()
        print(f"✅ Ticket {ticket_id} added successfully.")
        return now

    except Exception as e:
        print(f"❌ Ticket DB Error: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_active_tickets():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM helpdesk_tickets WHERE status='ACTIVE' ORDER BY timestamp DESC LIMIT 10")
        tickets = c.fetchall()

        result = []
        for t in tickets:
            if _is_pg():
                result.append({
                    "id":       t[0],
                    "type":     t[1],
                    "priority": t[2],
                    "location": t[3],
                    "time":     str(t[4]).split(" ")[1] if t[4] else ""
                })
            else:
                result.append({
                    "id":       t["ticket_id"],
                    "type":     t["issue_type"],
                    "priority": t["priority"],
                    "location": t["location"],
                    "time":     t["timestamp"].split(" ")[1] if t["timestamp"] else ""
                })
        return result

    except Exception as e:
        print(f"❌ Fetch Tickets Error: {e}")
        return []
    finally:
        if conn:
            conn.close()

def resolve_ticket(ticket_id):
    """Ticket ne RESOLVED mark karo"""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        if _is_pg():
            c.execute("UPDATE helpdesk_tickets SET status='RESOLVED' WHERE ticket_id=%s", (ticket_id,))
        else:
            c.execute("UPDATE helpdesk_tickets SET status='RESOLVED' WHERE ticket_id=?", (ticket_id,))

        conn.commit()
        print(f"✅ Ticket {ticket_id} resolved.")
        return True

    except Exception as e:
        print(f"❌ Resolve Ticket Error: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# --- 3. ADMIN LOGIN ---
def verify_login(username, password):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        if _is_pg():
            c.execute("SELECT * FROM admin_users WHERE username=%s AND password=%s", (username, password))
        else:
            c.execute("SELECT * FROM admin_users WHERE username=? AND password=?", (username, password))

        user = c.fetchone()
        return user is not None

    except Exception as e:
        print(f"❌ Login DB Error: {e}")
        return False
    finally:
        if conn:
            conn.close()

# --- 4. TRAFFIC STATS (BONUS) ---
def get_traffic_summary(limit=20):
    """Last N traffic logs fetch karo"""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM traffic_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ) if not _is_pg() else c.execute(
            "SELECT * FROM traffic_logs ORDER BY timestamp DESC LIMIT %s",
            (limit,)
        )
        rows = c.fetchall()

        result = []
        for r in rows:
            if _is_pg():
                result.append({
                    "node_id":      r[1],
                    "timestamp":    r[2],
                    "cars":         r[3],
                    "bikes":        r[4],
                    "buses":        r[5],
                    "trucks":       r[6],
                    "total_pcu":    r[7],
                    "signal_state": r[8],
                })
            else:
                result.append({
                    "node_id":      r["node_id"],
                    "timestamp":    r["timestamp"],
                    "cars":         r["cars"],
                    "bikes":        r["bikes"],
                    "buses":        r["buses"],
                    "trucks":       r["trucks"],
                    "total_pcu":    r["total_pcu"],
                    "signal_state": r["signal_state"],
                })
        return result

    except Exception as e:
        print(f"❌ Traffic Summary Error: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- MAIN (Test) ---
if __name__ == "__main__":
    print("🚀 Database initialize thaay che...")
    init_db()

    # Test ticket
    add_ticket("TKT-001", "Signal Fault", "HIGH", "Vastrapur Cross Road")

    # Test tickets fetch
    tickets = get_active_tickets()
    print(f"📋 Active Tickets: {tickets}")

    # Test login
    result = verify_login("admin", "admin123")
    print(f"🔐 Login Test: {'✅ Success' if result else '❌ Failed'}")