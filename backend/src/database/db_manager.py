import os
import sqlite3
import datetime
import threading
from typing import List, Dict, Any, Optional, Tuple

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

from src.utils.security import hash_password, verify_password

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
DEFAULT_DB_PATH = os.path.join(DB_DIR, "traffic_analytics.db")
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv(os.path.join(PROJECT_DIR, ".env"))


class _MySQLCursor:
    """Small compatibility layer so existing SQLite-style queries keep working."""

    def __init__(self, cursor):
        self._cursor = cursor

    @staticmethod
    def _sql(query: str) -> str:
        return query.replace("?", "%s")

    def execute(self, query, args=None):
        return self._cursor.execute(self._sql(query), args)

    def executemany(self, query, args):
        return self._cursor.executemany(self._sql(query), args)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount


class _MySQLConnection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return _MySQLCursor(self._connection.cursor())

    def execute(self, query, args=None):
        cursor = self.cursor()
        cursor.execute(query, args)
        return cursor

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.rollback()
        else:
            self.commit()

class DatabaseManager:
    """
    Thread-safe database manager. Production uses the MySQL database configured in
    .env; an explicit db_path is retained for the existing SQLite test suite.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        with cls._lock:
            if db_path is not None:
                # Dedicated isolated instance for custom paths (e.g. unit testing)
                inst = super(DatabaseManager, cls).__new__(cls)
                inst.backend = "sqlite"
                inst._init_db(db_path)
                return inst

            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance.backend = "mysql"
                cls._instance._local = threading.local()
                cls._instance._mysql_initialized = False
                cls._instance._mysql_initializing = False
            return cls._instance

    def _init_db(self, db_path: str):
        if self.backend == "mysql":
            self._init_mysql()
            return

        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._local = threading.local()

        # Create schema
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            
            # 1. Individual vehicle crossing event table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_sec REAL,
                    real_time TEXT NOT NULL,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    vehicle_id INTEGER NOT NULL,
                    vehicle_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    speed_kmh REAL DEFAULT 0.0,
                    traffic_level TEXT NOT NULL,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Safe migration for existing DB
            try:
                conn.execute("ALTER TABLE vehicle_events ADD COLUMN speed_kmh REAL DEFAULT 0.0;")
            except Exception:
                pass

            # 2. Periodic traffic density snapshot table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traffic_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    active_vehicles INTEGER NOT NULL,
                    density_score REAL NOT NULL,
                    traffic_level TEXT NOT NULL,
                    stall_ratio REAL DEFAULT 0.0,
                    avg_speed_kmh REAL DEFAULT 0.0,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            try:
                conn.execute("ALTER TABLE traffic_snapshots ADD COLUMN avg_speed_kmh REAL DEFAULT 0.0;")
            except Exception:
                pass

            # 3. Traffic incidents and anomalies table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traffic_incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_sec REAL,
                    real_time TEXT NOT NULL,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    incident_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    vehicle_id INTEGER NOT NULL,
                    vehicle_type TEXT NOT NULL,
                    speed_kmh REAL DEFAULT 0.0,
                    message TEXT,
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. Users and Authentication table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traffic_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'user', -- admin, user
                    business_id INTEGER,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 5. Business entities and organizations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS businesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    business_type TEXT DEFAULT 'retail', -- retail, gas_station, logistics, smart_parking, campus
                    branch_code TEXT,
                    address TEXT,
                    contact_email TEXT,
                    contact_phone TEXT,
                    opening_hour INTEGER DEFAULT 8,
                    closing_hour INTEGER DEFAULT 22,
                    target_hourly_traffic INTEGER DEFAULT 100,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 6. Business CCTV cameras table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS business_cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    stream_url TEXT NOT NULL,
                    camera_type TEXT DEFAULT 'entrance', -- entrance, exit, parking, lane
                    location_note TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 7. Business daily metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS business_daily_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    total_customer_vehicles INTEGER DEFAULT 0,
                    peak_customer_hour INTEGER DEFAULT 0,
                    peak_vehicle_count INTEGER DEFAULT 0,
                    car_count INTEGER DEFAULT 0,
                    motorcycle_count INTEGER DEFAULT 0,
                    commercial_truck_count INTEGER DEFAULT 0,
                    bus_count INTEGER DEFAULT 0,
                    estimated_footfall INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(business_id, date)
                );
            """)

            # Indices for lightning-fast academic reports, peak-hour, and business queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_date_hour ON vehicle_events(date, hour);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON vehicle_events(vehicle_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_direction ON vehicle_events(direction);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_date ON traffic_snapshots(date);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_date ON traffic_incidents(date);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_type ON traffic_incidents(incident_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON traffic_users(username);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON traffic_users(email);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_business_cameras ON business_cameras(business_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_business_metrics ON business_daily_metrics(business_id, date);")

            # Seed default admin user if table is empty
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM traffic_users;")
            if cur.fetchone()[0] == 0:
                admin_hash = hash_password("admin123")
                cur.execute("""
                    INSERT INTO traffic_users (username, email, password_hash, full_name, role)
                    VALUES (?, ?, ?, ?, ?);
                """, ("admin", "admin@kusrc.ac.th", admin_hash, "ผู้ดูแลระบบ (System Admin)", "admin"))

            # Seed default business baseline if table is empty
            cur.execute("SELECT COUNT(*) FROM businesses;")
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO businesses (name, business_type, branch_code, address, contact_email, contact_phone, target_hourly_traffic)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    "มหาวิทยาลัยเกษตรศาสตร์ วิทยาเขตศรีราชา",
                    "campus",
                    "KU-SRC-01",
                    "199 ม.6 ถ.สุขุมวิท ต.ทุ่งสุขลา อ.ศรีราชา จ.ชลบุรี 20230",
                    "traffic@src.ku.ac.th",
                    "038-354580",
                    150
                ))

            conn.commit()

    def _init_mysql(self):
        """Create the application tables in the configured phpMyAdmin database."""
        self._mysql_initializing = True
        try:
            with self.get_connection() as conn:
                schema = (
                    """CREATE TABLE IF NOT EXISTS traffic_users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(100) NOT NULL UNIQUE,
                        email VARCHAR(255) NULL UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        full_name VARCHAR(255) NULL,
                        role VARCHAR(40) NOT NULL DEFAULT 'user',
                        business_id INT NULL,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB""",
                    """CREATE TABLE IF NOT EXISTS vehicle_events (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        timestamp_sec DOUBLE NULL,
                        real_time VARCHAR(32) NOT NULL,
                        date DATE NOT NULL,
                        hour INT NOT NULL,
                        vehicle_id INT NOT NULL,
                        vehicle_type VARCHAR(40) NOT NULL,
                        direction VARCHAR(20) NOT NULL,
                        speed_kmh DOUBLE DEFAULT 0,
                        traffic_level VARCHAR(80) NOT NULL,
                        session_id VARCHAR(255) NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB""",
                    """CREATE TABLE IF NOT EXISTS traffic_snapshots (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        timestamp VARCHAR(32) NOT NULL,
                        date DATE NOT NULL,
                        hour INT NOT NULL,
                        active_vehicles INT NOT NULL,
                        density_score DOUBLE NOT NULL,
                        traffic_level VARCHAR(80) NOT NULL,
                        stall_ratio DOUBLE DEFAULT 0,
                        avg_speed_kmh DOUBLE DEFAULT 0,
                        session_id VARCHAR(255) NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB""",
                    """CREATE TABLE IF NOT EXISTS traffic_incidents (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        timestamp_sec DOUBLE NULL,
                        real_time VARCHAR(32) NOT NULL,
                        date DATE NOT NULL,
                        hour INT NOT NULL,
                        incident_type VARCHAR(80) NOT NULL,
                        severity VARCHAR(40) NOT NULL,
                        vehicle_id INT NOT NULL,
                        vehicle_type VARCHAR(40) NOT NULL,
                        speed_kmh DOUBLE DEFAULT 0,
                        message TEXT NULL,
                        session_id VARCHAR(255) NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB""",
                    """CREATE TABLE IF NOT EXISTS businesses (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        business_type VARCHAR(80) DEFAULT 'retail',
                        branch_code VARCHAR(80) NULL,
                        address TEXT NULL,
                        contact_email VARCHAR(255) NULL,
                        contact_phone VARCHAR(80) NULL,
                        opening_hour INT DEFAULT 8,
                        closing_hour INT DEFAULT 22,
                        target_hourly_traffic INT DEFAULT 100,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB""",
                    """CREATE TABLE IF NOT EXISTS business_cameras (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        business_id INT NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        stream_url TEXT NOT NULL,
                        camera_type VARCHAR(40) DEFAULT 'entrance',
                        location_note TEXT NULL,
                        is_active TINYINT(1) DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB""",
                    """CREATE TABLE IF NOT EXISTS business_daily_metrics (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        business_id INT NOT NULL,
                        date DATE NOT NULL,
                        total_customer_vehicles INT DEFAULT 0,
                        peak_customer_hour INT DEFAULT 0,
                        peak_vehicle_count INT DEFAULT 0,
                        car_count INT DEFAULT 0,
                        motorcycle_count INT DEFAULT 0,
                        commercial_truck_count INT DEFAULT 0,
                        bus_count INT DEFAULT 0,
                        estimated_footfall INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_business_date (business_id, date)
                    ) ENGINE=InnoDB""",
                )
                for statement in schema:
                    conn.execute(statement)

                # Extend the traffic_users table created earlier in phpMyAdmin.
                for statement in (
                    "ALTER TABLE traffic_users ADD COLUMN email VARCHAR(255) NULL UNIQUE",
                    "ALTER TABLE traffic_users ADD COLUMN full_name VARCHAR(255) NULL",
                    "ALTER TABLE traffic_users ADD COLUMN business_id INT NULL",
                    "ALTER TABLE traffic_users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1",
                ):
                    try:
                        conn.execute(statement)
                    except Exception:
                        pass

                for statement in (
                    "CREATE INDEX idx_events_date_hour ON vehicle_events(date, hour)",
                    "CREATE INDEX idx_events_type ON vehicle_events(vehicle_type)",
                    "CREATE INDEX idx_events_direction ON vehicle_events(direction)",
                    "CREATE INDEX idx_snapshots_date ON traffic_snapshots(date)",
                    "CREATE INDEX idx_incidents_date ON traffic_incidents(date)",
                    "CREATE INDEX idx_incidents_type ON traffic_incidents(incident_type)",
                    "CREATE INDEX idx_users_username ON traffic_users(username)",
                    "CREATE INDEX idx_users_email ON traffic_users(email)",
                    "CREATE INDEX idx_business_cameras ON business_cameras(business_id)",
                    "CREATE INDEX idx_business_metrics ON business_daily_metrics(business_id, date)",
                ):
                    try:
                        conn.execute(statement)
                    except Exception:
                        pass

                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) AS total FROM traffic_users")
                if (cur.fetchone() or {}).get("total", 0) == 0:
                    cur.execute(
                        """INSERT INTO traffic_users
                        (username, email, password_hash, full_name, role)
                        VALUES (?, ?, ?, ?, ?)""",
                        ("admin", "admin@kusrc.ac.th", hash_password("admin123"),
                         "ผู้ดูแลระบบ (System Admin)", "admin"),
                    )

                cur.execute("SELECT COUNT(*) AS total FROM businesses")
                if (cur.fetchone() or {}).get("total", 0) == 0:
                    cur.execute(
                        """INSERT INTO businesses
                        (name, business_type, branch_code, address, contact_email,
                         contact_phone, target_hourly_traffic)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        ("มหาวิทยาลัยเกษตรศาสตร์ วิทยาเขตศรีราชา", "campus", "KU-SRC-01",
                         "199 ม.6 ถ.สุขุมวิท ต.ทุ่งสุขลา อ.ศรีราชา จ.ชลบุรี 20230",
                         "traffic@src.ku.ac.th", "038-354580", 150),
                    )
                conn.commit()
            self._mysql_initialized = True
        finally:
            self._mysql_initializing = False

    def get_connection(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection with dictionary-like row factory."""
        if self.backend == "mysql":
            if not self._mysql_initialized and not self._mysql_initializing:
                self._init_mysql()
            if not hasattr(self._local, "conn") or self._local.conn is None:
                raw = pymysql.connect(
                    host=os.getenv("DB_HOST", "127.0.0.1"),
                    port=int(os.getenv("DB_PORT", "3306")),
                    user=os.getenv("DB_USER"),
                    password=os.getenv("DB_PASSWORD", ""),
                    database=os.getenv("DB_NAME"),
                    charset="utf8mb4",
                    cursorclass=DictCursor,
                    autocommit=False,
                    connect_timeout=10,
                )
                self._local.conn = _MySQLConnection(raw)
            return self._local.conn

        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def log_event(
        self,
        vehicle_id: int,
        vehicle_type: str,
        direction: str,
        traffic_level: str,
        speed_kmh: float = 0.0,
        timestamp_sec: float = 0.0,
        real_time_str: Optional[str] = None,
        session_id: str = "default"
    ) -> int:
        """Logs a single vehicle crossing event."""
        now = datetime.datetime.now()
        dt_str = real_time_str or now.strftime("%Y-%m-%d %H:%M:%S")
        date_str = dt_str.split(" ")[0]
        try:
            hour = int(dt_str.split(" ")[1].split(":")[0])
        except Exception:
            hour = now.hour

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vehicle_events (
                timestamp_sec, real_time, date, hour, vehicle_id,
                vehicle_type, direction, speed_kmh, traffic_level, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            timestamp_sec, dt_str, date_str, hour, vehicle_id,
            vehicle_type, direction, speed_kmh, traffic_level, session_id
        ))
        conn.commit()
        return cursor.lastrowid

    def log_events_batch(self, events: List[Dict[str, Any]], session_id: str = "default") -> int:
        """Batch inserts multiple crossing events inside a single transaction."""
        if not events:
            return 0

        now = datetime.datetime.now()
        rows = []
        for ev in events:
            dt_str = ev.get("Real-world Time") or now.strftime("%Y-%m-%d %H:%M:%S")
            date_str = dt_str.split(" ")[0]
            try:
                hour = int(dt_str.split(" ")[1].split(":")[0])
            except Exception:
                hour = now.hour

            speed_val = float(ev.get("Speed (km/h)", ev.get("speed_kmh", 0.0)))

            rows.append((
                float(ev.get("Timestamp (s)", 0.0)),
                dt_str,
                date_str,
                hour,
                int(ev.get("Vehicle ID", 0)),
                str(ev.get("Type", "Car")),
                str(ev.get("Direction", "Inbound")),
                speed_val,
                str(ev.get("Traffic Level", "🟢 คล่องตัว")),
                session_id
            ))

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO vehicle_events (
                timestamp_sec, real_time, date, hour, vehicle_id,
                vehicle_type, direction, speed_kmh, traffic_level, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, rows)
        conn.commit()
        return len(rows)

    def log_incident(
        self,
        incident_type: str,
        severity: str,
        vehicle_id: int,
        vehicle_type: str,
        speed_kmh: float = 0.0,
        message: str = "",
        timestamp_sec: float = 0.0,
        real_time_str: Optional[str] = None,
        session_id: str = "default"
    ) -> int:
        """Logs a single traffic incident (wrong-way, stalled, speeding)."""
        now = datetime.datetime.now()
        dt_str = real_time_str or now.strftime("%Y-%m-%d %H:%M:%S")
        date_str = dt_str.split(" ")[0]
        try:
            hour = int(dt_str.split(" ")[1].split(":")[0])
        except Exception:
            hour = now.hour

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO traffic_incidents (
                timestamp_sec, real_time, date, hour, incident_type,
                severity, vehicle_id, vehicle_type, speed_kmh, message, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            timestamp_sec, dt_str, date_str, hour, incident_type,
            severity, vehicle_id, vehicle_type, speed_kmh, message, session_id
        ))
        conn.commit()
        return cursor.lastrowid

    def log_incidents_batch(self, incidents: List[Dict[str, Any]], session_id: str = "default") -> int:
        """Batch inserts multiple traffic incidents inside a single transaction."""
        if not incidents:
            return 0
        now = datetime.datetime.now()
        rows = []
        for inc in incidents:
            dt_str = inc.get("real_time") or now.strftime("%Y-%m-%d %H:%M:%S")
            date_str = dt_str.split(" ")[0]
            try:
                hour = int(dt_str.split(" ")[1].split(":")[0])
            except Exception:
                hour = now.hour

            rows.append((
                float(inc.get("timestamp_sec", 0.0)),
                dt_str,
                date_str,
                hour,
                str(inc.get("incident_type", "unknown")),
                str(inc.get("severity", "medium")),
                int(inc.get("vehicle_id", 0)),
                str(inc.get("vehicle_type", "Vehicle")),
                float(inc.get("speed_kmh", 0.0)),
                str(inc.get("message", "")),
                session_id
            ))

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO traffic_incidents (
                timestamp_sec, real_time, date, hour, incident_type,
                severity, vehicle_id, vehicle_type, speed_kmh, message, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, rows)
        conn.commit()
        return len(rows)

    def log_snapshot(
        self,
        active_vehicles: int,
        density_score: float,
        traffic_level: str,
        stall_ratio: float = 0.0,
        avg_speed_kmh: float = 0.0,
        session_id: str = "default"
    ) -> int:
        """Logs an aggregated traffic state snapshot."""
        now = datetime.datetime.now()
        dt_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")
        hour = now.hour

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO traffic_snapshots (
                timestamp, date, hour, active_vehicles, density_score,
                traffic_level, stall_ratio, avg_speed_kmh, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            dt_str, date_str, hour, active_vehicles, density_score,
            traffic_level, stall_ratio, avg_speed_kmh, session_id
        ))
        conn.commit()
        return cursor.lastrowid

    def get_hourly_traffic(self, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Computes 24-hour traffic volume (00:00 - 23:00) with inbound/outbound and modal breakdown.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        date_clause = "WHERE date = ?" if target_date else ""
        params = (target_date,) if target_date else ()

        query = f"""
            SELECT
                hour,
                COUNT(*) AS total_count,
                SUM(CASE WHEN direction = 'Inbound' THEN 1 ELSE 0 END) AS inbound_count,
                SUM(CASE WHEN direction = 'Outbound' THEN 1 ELSE 0 END) AS outbound_count,
                SUM(CASE WHEN vehicle_type = 'Car' THEN 1 ELSE 0 END) AS car_count,
                SUM(CASE WHEN vehicle_type = 'Motorcycle' THEN 1 ELSE 0 END) AS motorcycle_count,
                SUM(CASE WHEN vehicle_type = 'Bus' THEN 1 ELSE 0 END) AS bus_count,
                SUM(CASE WHEN vehicle_type = 'Truck' THEN 1 ELSE 0 END) AS truck_count
            FROM vehicle_events
            {date_clause}
            GROUP BY hour
            ORDER BY hour ASC;
        """
        cursor.execute(query, params)
        raw_rows = {row["hour"]: dict(row) for row in cursor.fetchall()}

        # Ensure all 24 hours (0-23) are present for charts
        result = []
        for h in range(24):
            if h in raw_rows:
                r = raw_rows[h]
                result.append({
                    "hour": h,
                    "label": f"{h:02d}:00",
                    "total": r["total_count"],
                    "inbound": r["inbound_count"],
                    "outbound": r["outbound_count"],
                    "car": r["car_count"],
                    "motorcycle": r["motorcycle_count"],
                    "bus": r["bus_count"],
                    "truck": r["truck_count"]
                })
            else:
                result.append({
                    "hour": h,
                    "label": f"{h:02d}:00",
                    "total": 0,
                    "inbound": 0,
                    "outbound": 0,
                    "car": 0,
                    "motorcycle": 0,
                    "bus": 0,
                    "truck": 0
                })
        return result

    def get_peak_hours_analysis(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes and detects morning and evening peak traffic hours, modal split, and congestion KPIs.
        """
        hourly = self.get_hourly_traffic(target_date)
        total_vehicles = sum(h["total"] for h in hourly)

        if total_vehicles == 0:
            return {
                "total_vehicles": 0,
                "busiest_hour": None,
                "busiest_count": 0,
                "morning_peak": None,
                "morning_peak_count": 0,
                "evening_peak": None,
                "evening_peak_count": 0,
                "dominant_vehicle": "None",
                "dominant_percentage": 0.0,
                "inbound_percentage": 50.0,
                "outbound_percentage": 50.0,
                "hourly_distribution": hourly,
                "modal_split": {"Car": 0, "Motorcycle": 0, "Bus": 0, "Truck": 0}
            }

        # Find absolute busiest hour
        busiest = max(hourly, key=lambda x: x["total"])

        # Morning Peak window: 06:00 to 10:59
        morning_hours = [h for h in hourly if 6 <= h["hour"] <= 10]
        morning_peak = max(morning_hours, key=lambda x: x["total"]) if morning_hours else None

        # Evening Peak window: 16:00 to 20:59
        evening_hours = [h for h in hourly if 16 <= h["hour"] <= 20]
        evening_peak = max(evening_hours, key=lambda x: x["total"]) if evening_hours else None

        # Totals by class
        total_car = sum(h["car"] for h in hourly)
        total_moto = sum(h["motorcycle"] for h in hourly)
        total_bus = sum(h["bus"] for h in hourly)
        total_truck = sum(h["truck"] for h in hourly)

        modal_split = {
            "Car": total_car,
            "Motorcycle": total_moto,
            "Bus": total_bus,
            "Truck": total_truck
        }
        dominant_vehicle, dominant_count = max(modal_split.items(), key=lambda x: x[1])
        dominant_pct = round((dominant_count / total_vehicles) * 100, 1) if total_vehicles > 0 else 0.0

        total_inbound = sum(h["inbound"] for h in hourly)
        total_outbound = sum(h["outbound"] for h in hourly)
        inbound_pct = round((total_inbound / total_vehicles) * 100, 1) if total_vehicles > 0 else 50.0
        outbound_pct = round((total_outbound / total_vehicles) * 100, 1) if total_vehicles > 0 else 50.0

        # Mark peak flags in hourly data for frontend charting
        for h in hourly:
            h["is_peak"] = (
                (busiest and h["hour"] == busiest["hour"] and busiest["total"] > 0) or
                (morning_peak and h["hour"] == morning_peak["hour"] and morning_peak["total"] > 0) or
                (evening_peak and h["hour"] == evening_peak["hour"] and evening_peak["total"] > 0)
            )

        return {
            "total_vehicles": total_vehicles,
            "busiest_hour": f"{busiest['hour']:02d}:00 - {busiest['hour']+1:02d}:00" if busiest["total"] > 0 else "N/A",
            "busiest_count": busiest["total"],
            "morning_peak": f"{morning_peak['hour']:02d}:00 - {morning_peak['hour']+1:02d}:00" if (morning_peak and morning_peak["total"] > 0) else "N/A",
            "morning_peak_count": morning_peak["total"] if morning_peak else 0,
            "evening_peak": f"{evening_peak['hour']:02d}:00 - {evening_peak['hour']+1:02d}:00" if (evening_peak and evening_peak["total"] > 0) else "N/A",
            "evening_peak_count": evening_peak["total"] if evening_peak else 0,
            "dominant_vehicle": dominant_vehicle,
            "dominant_percentage": dominant_pct,
            "inbound_percentage": inbound_pct,
            "outbound_percentage": outbound_pct,
            "hourly_distribution": hourly,
            "modal_split": modal_split
        }

    def get_events_history(
        self,
        limit: int = 50,
        offset: int = 0,
        target_date: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        direction: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves paginated history of vehicle crossing events with filtering.
        Returns: (events_list, total_count)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        conditions = []
        params = []

        if target_date:
            conditions.append("date = ?")
            params.append(target_date)
        if vehicle_type and vehicle_type != "All":
            conditions.append("vehicle_type = ?")
            params.append(vehicle_type)
        if direction and direction != "All":
            conditions.append("direction = ?")
            params.append(direction)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # Total count
        count_query = f"SELECT COUNT(*) AS total FROM vehicle_events {where_clause};"
        cursor.execute(count_query, params)
        total_records = cursor.fetchone()["total"]

        # Paginated events
        events_query = f"""
            SELECT
                id, timestamp_sec, real_time, date, hour,
                vehicle_id, vehicle_type, direction, speed_kmh, traffic_level, session_id
            FROM vehicle_events
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?;
        """
        cursor.execute(events_query, params + [limit, offset])
        events = [dict(row) for row in cursor.fetchall()]
        return events, total_records

    def get_incidents_history(
        self,
        limit: int = 50,
        offset: int = 0,
        target_date: Optional[str] = None,
        incident_type: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves paginated history of traffic incidents with filtering.
        Returns: (incidents_list, total_count)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        conditions = []
        params = []
        if target_date:
            conditions.append("date = ?")
            params.append(target_date)
        if incident_type and incident_type != "All":
            conditions.append("incident_type = ?")
            params.append(incident_type)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"SELECT COUNT(*) AS total FROM traffic_incidents {where_clause};", params)
        total_records = cursor.fetchone()["total"]

        cursor.execute(f"""
            SELECT id, timestamp_sec, real_time, date, hour, incident_type,
                   severity, vehicle_id, vehicle_type, speed_kmh, message, session_id
            FROM traffic_incidents
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?;
        """, params + [limit, offset])
        incidents = [dict(row) for row in cursor.fetchall()]
        return incidents, total_records

    def get_speed_analytics(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Computes average speed, max speed, and modal speed distribution.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        date_clause = "WHERE date = ? AND speed_kmh > 0" if target_date else "WHERE speed_kmh > 0"
        params = (target_date,) if target_date else ()

        cursor.execute(f"""
            SELECT
                COUNT(*) AS sample_count,
                AVG(speed_kmh) AS avg_speed,
                MAX(speed_kmh) AS max_speed,
                MIN(speed_kmh) AS min_speed
            FROM vehicle_events
            {date_clause};
        """, params)
        summary = cursor.fetchone()
        avg_speed = round(summary["avg_speed"], 1) if summary and summary["avg_speed"] is not None else 0.0
        max_speed = round(summary["max_speed"], 1) if summary and summary["max_speed"] is not None else 0.0
        min_speed = round(summary["min_speed"], 1) if summary and summary["min_speed"] is not None else 0.0

        cursor.execute(f"""
            SELECT vehicle_type, AVG(speed_kmh) AS avg_speed, MAX(speed_kmh) AS max_speed, COUNT(*) AS count
            FROM vehicle_events
            {date_clause}
            GROUP BY vehicle_type;
        """, params)
        by_class = {
            r["vehicle_type"]: {
                "avg_speed": round(r["avg_speed"], 1),
                "max_speed": round(r["max_speed"], 1),
                "count": r["count"]
            } for r in cursor.fetchall()
        }

        return {
            "avg_speed": avg_speed,
            "max_speed": max_speed,
            "min_speed": min_speed,
            "total_sampled": summary["sample_count"] if summary else 0,
            "by_class": by_class
        }

    def get_available_dates(self) -> List[str]:
        """Returns list of distinct dates present in the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT date FROM vehicle_events ORDER BY date DESC;")
        return [row["date"] for row in cursor.fetchall()]

    def export_csv(self, target_date: Optional[str] = None) -> str:
        """Generates full CSV text of vehicle events for download/academic reporting."""
        events, _ = self.get_events_history(limit=50000, offset=0, target_date=target_date)
        lines = ["ID,Timestamp (s),Real-world Time,Date,Hour,Vehicle ID,Vehicle Type,Direction,Speed (km/h),Traffic Level,Session ID"]
        for ev in events:
            lines.append(
                f"{ev['id']},{ev['timestamp_sec']},{ev['real_time']},{ev['date']},{ev['hour']},"
                f"{ev['vehicle_id']},{ev['vehicle_type']},{ev['direction']},{ev.get('speed_kmh', 0.0)},\"{ev['traffic_level']}\",{ev.get('session_id', '')}"
            )
        return "\n".join(lines)

    # =========================================================================
    # USER & AUTHENTICATION METHODS
    # =========================================================================
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str = "",
        role: str = "user",
        business_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Creates a new user with securely hashed PBKDF2 password."""
        conn = self.get_connection()
        cursor = conn.cursor()
        pwd_hash = hash_password(password)
        cursor.execute("""
            INSERT INTO traffic_users (username, email, password_hash, full_name, role, business_id)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (username.strip(), email.strip().lower(), pwd_hash, full_name.strip(), role, business_id))
        conn.commit()
        uid = cursor.lastrowid
        return {
            "id": uid,
            "username": username.strip(),
            "email": email.strip().lower(),
            "full_name": full_name.strip(),
            "role": role,
            "business_id": business_id
        }

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetches user by ID (excluding password hash)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.full_name, u.role, u.business_id, u.is_active, u.created_at,
                   b.name as business_name, b.business_type
            FROM traffic_users u
            LEFT JOIN businesses b ON u.business_id = b.id
            WHERE u.id = ?;
        """, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetches user by username (includes password_hash for internal verification)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.password_hash, u.full_name, u.role, u.business_id, u.is_active,
                   b.name as business_name, b.business_type
            FROM traffic_users u
            LEFT JOIN businesses b ON u.business_id = b.id
            WHERE u.username = ?;
        """, (username.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetches user by email."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.password_hash, u.full_name, u.role, u.business_id, u.is_active,
                   b.name as business_name, b.business_type
            FROM traffic_users u
            LEFT JOIN businesses b ON u.business_id = b.id
            WHERE u.email = ?;
        """, (email.strip().lower(),))
        row = cursor.fetchone()
        return dict(row) if row else None

    def authenticate_user(self, username_or_email: str, plain_password: str) -> Optional[Dict[str, Any]]:
        """Verifies credentials, returns user profile dictionary if valid, None otherwise."""
        user = self.get_user_by_username(username_or_email) or self.get_user_by_email(username_or_email)
        if not user or not user.get("is_active"):
            return None
        if verify_password(plain_password, user["password_hash"]):
            safe_user = dict(user)
            safe_user.pop("password_hash", None)
            return safe_user
        return None

    def list_users(self) -> List[Dict[str, Any]]:
        """Lists all registered users."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.full_name, u.role, u.business_id, u.is_active, u.created_at,
                   b.name as business_name
            FROM traffic_users u
            LEFT JOIN businesses b ON u.business_id = b.id
            ORDER BY u.id ASC;
        """)
        return [dict(r) for r in cursor.fetchall()]

    # =========================================================================
    # BUSINESS & ORGANIZATION MANAGEMENT
    # =========================================================================
    def create_business(
        self,
        name: str,
        business_type: str = "retail",
        branch_code: str = "",
        address: str = "",
        contact_email: str = "",
        contact_phone: str = "",
        opening_hour: int = 8,
        closing_hour: int = 22,
        target_hourly_traffic: int = 100
    ) -> int:
        """Registers a new business, branch, or commercial facility."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO businesses (name, business_type, branch_code, address, contact_email, contact_phone, opening_hour, closing_hour, target_hourly_traffic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (name.strip(), business_type, branch_code.strip(), address.strip(), contact_email.strip(), contact_phone.strip(), opening_hour, closing_hour, target_hourly_traffic))
        conn.commit()
        return cursor.lastrowid

    def get_businesses(self) -> List[Dict[str, Any]]:
        """Lists all businesses with their registered camera count."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.*, COUNT(c.id) as cameras_count
            FROM businesses b
            LEFT JOIN business_cameras c ON b.id = c.business_id
            GROUP BY b.id
            ORDER BY b.id ASC;
        """)
        return [dict(r) for r in cursor.fetchall()]

    def get_business_by_id(self, business_id: int) -> Optional[Dict[str, Any]]:
        """Fetches single business details by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM businesses WHERE id = ?;", (business_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_business(self, business_id: int, data: Dict[str, Any]) -> bool:
        """Updates business details."""
        allowed_fields = [
            "name", "business_type", "branch_code", "address",
            "contact_email", "contact_phone", "opening_hour",
            "closing_hour", "target_hourly_traffic"
        ]
        updates = []
        vals = []
        for k, v in data.items():
            if k in allowed_fields:
                updates.append(f"{k} = ?")
                vals.append(v)
        if not updates:
            return False
        vals.append(business_id)
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE businesses SET {', '.join(updates)} WHERE id = ?;", vals)
        conn.commit()
        return cursor.rowcount > 0

    def delete_business(self, business_id: int) -> bool:
        """Deletes a business and associated camera entries."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM business_cameras WHERE business_id = ?;", (business_id,))
            conn.execute("DELETE FROM business_daily_metrics WHERE business_id = ?;", (business_id,))
            conn.execute("DELETE FROM businesses WHERE id = ?;", (business_id,))
            conn.commit()
            return True

    # =========================================================================
    # BUSINESS CCTV CAMERAS
    # =========================================================================
    def create_business_camera(
        self,
        business_id: int,
        name: str,
        stream_url: str,
        camera_type: str = "entrance",
        location_note: str = ""
    ) -> int:
        """Links a CCTV or RTSP stream to a specific business branch."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO business_cameras (business_id, name, stream_url, camera_type, location_note)
            VALUES (?, ?, ?, ?, ?);
        """, (business_id, name.strip(), stream_url.strip(), camera_type, location_note.strip()))
        conn.commit()
        return cursor.lastrowid

    def get_business_cameras(self, business_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns CCTV cameras linked to business branches."""
        conn = self.get_connection()
        cursor = conn.cursor()
        if business_id is not None:
            cursor.execute("""
                SELECT c.*, b.name as business_name, b.branch_code
                FROM business_cameras c
                JOIN businesses b ON c.business_id = b.id
                WHERE c.business_id = ?
                ORDER BY c.id ASC;
            """, (business_id,))
        else:
            cursor.execute("""
                SELECT c.*, b.name as business_name, b.branch_code
                FROM business_cameras c
                JOIN businesses b ON c.business_id = b.id
                ORDER BY c.id ASC;
            """)
        return [dict(r) for r in cursor.fetchall()]

    def delete_business_camera(self, camera_id: int) -> bool:
        """Removes a camera from business."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM business_cameras WHERE id = ?;", (camera_id,))
        conn.commit()
        return cursor.rowcount > 0

    # =========================================================================
    # BUSINESS ANALYTICS & INSIGHTS
    # =========================================================================
    def get_business_dashboard_analytics(
        self,
        business_id: Optional[int] = None,
        target_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregates traffic data into actionable business intelligence:
        - Customer volume by operating hours
        - Estimated footfall (passengers / shoppers)
        - Peak business arrival hour & volume
        - Commercial logistics vs Passenger customer breakdown
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Fetch business metadata
        biz = None
        if business_id:
            biz = self.get_business_by_id(business_id)
        if not biz:
            businesses = self.get_businesses()
            biz = businesses[0] if businesses else {
                "id": 1, "name": "General Business", "business_type": "retail",
                "opening_hour": 8, "closing_hour": 22, "target_hourly_traffic": 100
            }

        opening_hour = biz.get("opening_hour", 8)
        closing_hour = biz.get("closing_hour", 22)
        target_traffic = biz.get("target_hourly_traffic", 100)

        # 2. Date filtering
        date_clause = ""
        params = []
        if target_date:
            date_clause = "WHERE date = ?"
            params.append(target_date)

        # Total vehicles and breakdown
        cursor.execute(f"""
            SELECT vehicle_type, COUNT(*) as count
            FROM vehicle_events
            {date_clause}
            GROUP BY vehicle_type;
        """, params)
        class_counts = {r["vehicle_type"]: r["count"] for r in cursor.fetchall()}

        car_cnt = class_counts.get("Car", 0)
        bike_cnt = class_counts.get("Motorcycle", 0)
        bus_cnt = class_counts.get("Bus", 0)
        truck_cnt = class_counts.get("Truck", 0)
        total_vehicles = car_cnt + bike_cnt + bus_cnt + truck_cnt

        # Estimated Footfall Formula (People who arrived):
        # Car = ~1.6 people, Bike = ~1.2 people, Bus = ~25 people, Truck = ~1.1 people
        estimated_footfall = int(car_cnt * 1.6 + bike_cnt * 1.2 + bus_cnt * 25.0 + truck_cnt * 1.1)

        # Commercial vs Passenger Split
        commercial_cnt = truck_cnt + bus_cnt
        passenger_cnt = car_cnt + bike_cnt
        commercial_ratio = round((commercial_cnt / total_vehicles * 100.0), 1) if total_vehicles > 0 else 0.0
        passenger_ratio = round((passenger_cnt / total_vehicles * 100.0), 1) if total_vehicles > 0 else 0.0

        # Hourly Distribution (0..23)
        cursor.execute(f"""
            SELECT hour,
                   COUNT(*) as total,
                   SUM(CASE WHEN direction = 'inbound' THEN 1 ELSE 0 END) as inbound,
                   SUM(CASE WHEN direction = 'outbound' THEN 1 ELSE 0 END) as outbound,
                   ROUND(AVG(speed_kmh), 1) as avg_speed
            FROM vehicle_events
            {date_clause}
            GROUP BY hour
            ORDER BY hour ASC;
        """, params)
        hourly_raw = {r["hour"]: dict(r) for r in cursor.fetchall()}

        hourly_series = []
        peak_hour = opening_hour
        peak_count = 0
        operating_hours_traffic = 0

        for h in range(24):
            item = hourly_raw.get(h, {"total": 0, "inbound": 0, "outbound": 0, "avg_speed": 0.0})
            total_h = item["total"]
            is_open = (opening_hour <= h <= closing_hour)
            if is_open:
                operating_hours_traffic += total_h

            if total_h > peak_count:
                peak_count = total_h
                peak_hour = h

            hourly_series.append({
                "hour": h,
                "hour_label": f"{h:02d}:00",
                "total": total_h,
                "inbound": item["inbound"],
                "outbound": item["outbound"],
                "avg_speed": item["avg_speed"] or 0.0,
                "is_operating_hour": is_open
            })

        operating_hours_count = max(1, closing_hour - opening_hour + 1)
        avg_hourly_traffic = round(operating_hours_traffic / operating_hours_count, 1)
        target_achievement = round((avg_hourly_traffic / target_traffic * 100.0), 1) if target_traffic > 0 else 100.0

        # Cameras count
        cameras = self.get_business_cameras(biz.get("id"))

        return {
            "business": biz,
            "target_date": target_date or "All-Time",
            "kpis": {
                "total_vehicles": total_vehicles,
                "estimated_footfall": estimated_footfall,
                "peak_hour": f"{peak_hour:02d}:00 - {peak_hour+1:02d}:00",
                "peak_vehicle_count": peak_count,
                "avg_hourly_traffic": avg_hourly_traffic,
                "target_hourly_traffic": target_traffic,
                "target_achievement_pct": target_achievement,
                "operating_hours_traffic": operating_hours_traffic,
                "commercial_ratio": commercial_ratio,
                "passenger_ratio": passenger_ratio,
                "cameras_count": len(cameras)
            },
            "vehicle_breakdown": {
                "Car": car_cnt,
                "Motorcycle": bike_cnt,
                "Bus": bus_cnt,
                "Truck": truck_cnt
            },
            "hourly_traffic": hourly_series,
            "cameras": cameras
        }

    def clear_all(self):
        """Clears all events, snapshots, incidents, and test records."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM vehicle_events;")
            conn.execute("DELETE FROM traffic_snapshots;")
            conn.execute("DELETE FROM traffic_incidents;")
            conn.execute("DELETE FROM business_cameras;")
            conn.execute("DELETE FROM business_daily_metrics;")
            conn.execute("DELETE FROM businesses;")
            conn.execute("DELETE FROM traffic_users;")

            # Re-seed default admin
            admin_hash = hash_password("admin123")
            conn.execute("""
                INSERT INTO traffic_users (username, email, password_hash, full_name, role)
                VALUES (?, ?, ?, ?, ?);
            """, ("admin", "admin@kusrc.ac.th", admin_hash, "ผู้ดูแลระบบ (System Admin)", "admin"))

            # Re-seed default business baseline
            conn.execute("""
                INSERT INTO businesses (name, business_type, branch_code, address, contact_email, contact_phone, target_hourly_traffic)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                "มหาวิทยาลัยเกษตรศาสตร์ วิทยาเขตศรีราชา",
                "campus",
                "KU-SRC-01",
                "199 ม.6 ถ.สุขุมวิท ต.ทุ่งสุขลา อ.ศรีราชา จ.ชลบุรี 20230",
                "traffic@src.ku.ac.th",
                "038-354580",
                150
            ))
            conn.commit()

# Global Singleton Database Manager instance
db_manager = DatabaseManager()
