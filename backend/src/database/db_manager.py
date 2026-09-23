import os
import sqlite3
import datetime
import threading
from typing import List, Dict, Any, Optional, Tuple

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
DEFAULT_DB_PATH = os.path.join(DB_DIR, "traffic_analytics.db")

class DatabaseManager:
    """
    High-performance, thread-safe SQLite database manager for traffic analytics.
    Uses Write-Ahead Logging (WAL) for non-blocking concurrent writes and reads.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = DEFAULT_DB_PATH):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._init_db(db_path)
            return cls._instance

    def _init_db(self, db_path: str):
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

            # Indices for lightning-fast academic reports and peak-hour queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_date_hour ON vehicle_events(date, hour);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON vehicle_events(vehicle_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_direction ON vehicle_events(direction);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_date ON traffic_snapshots(date);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_date ON traffic_incidents(date);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_type ON traffic_incidents(incident_type);")
            conn.commit()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection with dictionary-like row factory."""
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

    def clear_all(self):
        """Clears all events, snapshots, and incidents (useful for test resets)."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM vehicle_events;")
            conn.execute("DELETE FROM traffic_snapshots;")
            conn.execute("DELETE FROM traffic_incidents;")
            conn.commit()

# Global Singleton Database Manager instance
db_manager = DatabaseManager()
