import os
import datetime
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, DateTime, Text, ForeignKey, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import pymysql

# Load environment variables
load_dotenv()

logger = logging.getLogger("TrafficDB")
logging.basicConfig(level=logging.INFO)

# Database credentials (Defaults tailored for phpMyAdmin / XAMPP)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "ku_src_traffic")

Base = declarative_base()

class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_name = Column(String(255), nullable=False)
    video_recorded_time = Column(DateTime, nullable=True) # เวลาที่ถ่ายคลิป
    analysis_timestamp = Column(DateTime, default=datetime.datetime.now) # เวลาที่รันระบบ
    model_used = Column(String(100), default="best.pt")
    
    total_vehicles = Column(Integer, default=0)
    inbound_count = Column(Integer, default=0)
    outbound_count = Column(Integer, default=0)
    dominant_direction = Column(String(50), default="Balanced")
    max_congestion_level = Column(String(50), default="คล่องตัว (Smooth)")
    avg_density = Column(Float, default=0.0)
    stall_ratio = Column(Float, default=0.0)
    
    # Class breakdown
    car_count = Column(Integer, default=0)
    motorcycle_count = Column(Integer, default=0)
    bus_count = Column(Integer, default=0)
    truck_count = Column(Integer, default=0)
    
    notes = Column(Text, nullable=True)

    # Relationships
    intervals = relationship("TrafficInterval", back_populates="session", cascade="all, delete-orphan")
    events = relationship("TrafficEvent", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "video_name": self.video_name,
            "video_recorded_time": self.video_recorded_time.strftime("%Y-%m-%d %H:%M:%S") if self.video_recorded_time else None,
            "analysis_timestamp": self.analysis_timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.analysis_timestamp else None,
            "model_used": self.model_used,
            "total_vehicles": self.total_vehicles,
            "inbound_count": self.inbound_count,
            "outbound_count": self.outbound_count,
            "dominant_direction": self.dominant_direction,
            "max_congestion_level": self.max_congestion_level,
            "avg_density": round(self.avg_density, 2) if self.avg_density else 0.0,
            "stall_ratio": round(self.stall_ratio, 2) if self.stall_ratio else 0.0,
            "class_counts": {
                "Car": self.car_count,
                "Motorcycle": self.motorcycle_count,
                "Bus": self.bus_count,
                "Truck": self.truck_count
            },
            "notes": self.notes
        }

class TrafficInterval(Base):
    __tablename__ = "traffic_intervals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False)
    interval_index = Column(Integer, default=0)
    time_window = Column(String(50), nullable=False)
    inbound = Column(Integer, default=0)
    outbound = Column(Integer, default=0)
    total = Column(Integer, default=0)
    stall_ratio = Column(Float, default=0.0)
    congestion_level = Column(String(50), default="คล่องตัว")

    session = relationship("AnalysisSession", back_populates="intervals")

    def to_dict(self):
        return {
            "id": self.id,
            "interval_index": self.interval_index,
            "time_window": self.time_window,
            "inbound": self.inbound,
            "outbound": self.outbound,
            "total": self.total,
            "stall_ratio": self.stall_ratio,
            "congestion_level": self.congestion_level
        }

class TrafficEvent(Base):
    __tablename__ = "traffic_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False)
    event_time = Column(String(50), nullable=False)
    vehicle_class = Column(String(50), nullable=False)
    direction = Column(String(50), nullable=False)
    track_id = Column(Integer, nullable=True)

    session = relationship("AnalysisSession", back_populates="events")

    def to_dict(self):
        return {
            "id": self.id,
            "event_time": self.event_time,
            "vehicle_class": self.vehicle_class,
            "direction": self.direction,
            "track_id": self.track_id
        }


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.db_type = "none"
        self.is_connected = False
        self.error_message = None
        self.init_database()

    def init_database(self):
        """Attempts to connect to MySQL (phpMyAdmin), auto-creates db, falls back to SQLite if offline."""
        try:
            # 1. Attempt raw PyMySQL connection to create MySQL DB if not exists
            conn = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                charset="utf8mb4",
                connect_timeout=3
            )
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.commit()
            conn.close()

            # 2. Setup SQLAlchemy Engine with MySQL
            mysql_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
            self.engine = create_engine(mysql_url, pool_pre_ping=True, pool_recycle=3600)
            Base.metadata.create_all(bind=self.engine)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.db_type = "MySQL (phpMyAdmin)"
            self.is_connected = True
            self.error_message = None
            logger.info(f"✅ Connected successfully to MySQL [{DB_NAME}] for phpMyAdmin at {DB_HOST}:{DB_PORT}")
        except Exception as e:
            self.error_message = str(e)
            logger.warning(f"⚠️ Could not connect to MySQL: {e}. Falling back to SQLite local database.")
            # Fallback to local SQLite so the system never crashes
            sqlite_url = "sqlite:///./traffic_database.db"
            self.engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
            Base.metadata.create_all(bind=self.engine)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.db_type = "SQLite (Local Fallback)"
            self.is_connected = True

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.is_connected,
            "db_type": self.db_type,
            "host": DB_HOST,
            "port": DB_PORT,
            "user": DB_USER,
            "database": DB_NAME,
            "error": self.error_message
        }

    def save_analysis_session(self, session_data: Dict[str, Any]) -> Optional[int]:
        """Saves a complete session with its intervals and events."""
        if not self.SessionLocal:
            return None

        db = self.SessionLocal()
        try:
            rec_time = None
            if session_data.get("video_recorded_time"):
                try:
                    rec_time = datetime.datetime.strptime(
                        str(session_data["video_recorded_time"]), "%Y-%m-%d %H:%M:%S"
                    )
                except Exception:
                    rec_time = datetime.datetime.now()

            class_counts = session_data.get("class_counts", {})
            
            # Determine dominant direction
            inbound = int(session_data.get("inbound_count", 0))
            outbound = int(session_data.get("outbound_count", 0))
            if inbound > outbound:
                dom_dir = "Inbound (ขาเข้า)"
            elif outbound > inbound:
                dom_dir = "Outbound (ขาออก)"
            else:
                dom_dir = "Balanced (เท่ากัน)"

            new_session = AnalysisSession(
                video_name=session_data.get("video_name", "Unknown Video"),
                video_recorded_time=rec_time or datetime.datetime.now(),
                model_used=session_data.get("model_used", "best.pt"),
                total_vehicles=session_data.get("total_vehicles", inbound + outbound),
                inbound_count=inbound,
                outbound_count=outbound,
                dominant_direction=dom_dir,
                max_congestion_level=session_data.get("max_congestion_level", "คล่องตัว (Smooth)"),
                avg_density=float(session_data.get("avg_density", 0.0)),
                stall_ratio=float(session_data.get("stall_ratio", 0.0)),
                car_count=class_counts.get("Car", 0),
                motorcycle_count=class_counts.get("Motorcycle", 0),
                bus_count=class_counts.get("Bus", 0),
                truck_count=class_counts.get("Truck", 0),
                notes=session_data.get("notes", "")
            )
            db.add(new_session)
            db.flush() # Populate new_session.id

            # Save summary intervals
            summary_table = session_data.get("summary_table", [])
            for idx, row in enumerate(summary_table):
                interval = TrafficInterval(
                    session_id=new_session.id,
                    interval_index=idx,
                    time_window=str(row.get("Time Window", "")),
                    inbound=int(row.get("Inbound", 0)),
                    outbound=int(row.get("Outbound", 0)),
                    total=int(row.get("Total", 0)),
                    stall_ratio=float(row.get("Stall Ratio", 0.0)),
                    congestion_level=str(row.get("Congestion Level", "คล่องตัว"))
                )
                db.add(interval)

            # Save events log
            events_log = session_data.get("events_log", [])
            for ev in events_log:
                event = TrafficEvent(
                    session_id=new_session.id,
                    event_time=str(ev.get("time", "")),
                    vehicle_class=str(ev.get("class", "Car")),
                    direction=str(ev.get("direction", "Inbound")),
                    track_id=int(ev.get("track_id", 0)) if ev.get("track_id") is not None else None
                )
                db.add(event)

            db.commit()
            session_id = new_session.id
            logger.info(f"💾 Saved Session #{session_id} to database ({self.db_type})")
            return session_id
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error saving session to database: {e}")
            return None
        finally:
            db.close()

    def get_all_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch list of all past analysis sessions."""
        if not self.SessionLocal:
            return []
        db = self.SessionLocal()
        try:
            sessions = db.query(AnalysisSession).order_by(AnalysisSession.id.desc()).limit(limit).all()
            return [s.to_dict() for s in sessions]
        finally:
            db.close()

    def get_session_details(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Fetch full session details including intervals and events."""
        if not self.SessionLocal:
            return None
        db = self.SessionLocal()
        try:
            s = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
            if not s:
                return None
            res = s.to_dict()
            res["intervals"] = [i.to_dict() for i in s.intervals]
            res["events"] = [e.to_dict() for e in s.events]
            return res
        finally:
            db.close()

    def delete_session(self, session_id: int) -> bool:
        """Delete a session by ID."""
        if not self.SessionLocal:
            return False
        db = self.SessionLocal()
        try:
            s = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
            if s:
                db.delete(s)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting session #{session_id}: {e}")
            return False
        finally:
            db.close()


# Singleton database instance
db_manager = DatabaseManager()
