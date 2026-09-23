"""Persist AI crossing events in Firebase Firestore.

The service account key is read only by the backend and is never sent to the
browser. If Firebase is not configured, the AI pipeline continues using its
local database and logs a warning instead of crashing the stream.
"""

import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional


class FirebaseVehicleLogger:
    def __init__(self) -> None:
        self._client = None
        self._server_timestamp = None
        self._disabled = False
        self._lock = threading.Lock()

    def _get_client(self):
        if self._client is not None or self._disabled:
            return self._client

        with self._lock:
            if self._client is not None or self._disabled:
                return self._client

            try:
                import firebase_admin
                from firebase_admin import credentials, firestore

                key_path = os.getenv(
                    "FIREBASE_SERVICE_ACCOUNT_PATH",
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "firebase-service-account.json")),
                )
                if not os.path.exists(key_path):
                    raise FileNotFoundError(f"Firebase key not found: {key_path}")

                if not firebase_admin._apps:
                    firebase_admin.initialize_app(credentials.Certificate(key_path))
                self._client = firestore.client()
                self._server_timestamp = firestore.SERVER_TIMESTAMP
            except Exception as error:
                self._disabled = True
                print(f"⚠️ Firebase vehicle logging disabled: {error}")

        return self._client

    def log_crossing(self, event: Dict[str, Any], session_id: str = "default") -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None

        track_id = event.get("Vehicle ID", "unknown")
        vehicle_type = str(event.get("Type", "Vehicle"))
        direction = str(event.get("Direction", "Inbound"))
        action_type = "CHECK_IN" if direction.lower() == "inbound" else "CHECK_OUT"
        logged_at = datetime.now().astimezone()

        payload = {
            "user_id": os.getenv("FIREBASE_LOG_USER_ID", "AI-SYSTEM"),
            "vehicle_id": f"AI-TRACK-{track_id}",
            "vehicle_type": vehicle_type,
            "action_type": action_type,
            "timestamp_sec": float(event.get("Timestamp (s)", 0.0) or 0.0),
            "real_time": event.get("Real-world Time", logged_at.isoformat()),
            "direction": direction,
            "speed_kmh": float(event.get("Speed (km/h)", 0.0) or 0.0),
            "traffic_level": event.get("Traffic Level", ""),
            "session_id": session_id,
            "date": logged_at.strftime("%Y-%m-%d"),
            "hour": logged_at.hour,
            "source": "ai_camera",
            "logged_at": self._server_timestamp,
            "created_at": self._server_timestamp,
        }
        readable_id = (
            f"AI-TRACK-{track_id}-"
            f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
        )
        reference = client.collection("vehicle_events").document(readable_id)
        reference.set(payload)
        return reference.id

    def log_incident(self, incident: Dict[str, Any], session_id: str = "default") -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None

        logged_at = datetime.now().astimezone()
        track_id = incident.get("vehicle_id", "unknown")
        incident_id = (
            f"{incident.get('incident_type', 'incident')}-"
            f"AI-TRACK-{track_id}-"
            f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
        )
        payload = {
            "incident_type": incident.get("incident_type", "unknown"),
            "severity": incident.get("severity", "unknown"),
            "vehicle_id": f"AI-TRACK-{track_id}",
            "vehicle_type": incident.get("vehicle_type", "Vehicle"),
            "speed_kmh": float(incident.get("speed_kmh", 0.0) or 0.0),
            "timestamp_sec": float(incident.get("timestamp_sec", 0.0) or 0.0),
            "real_time": incident.get("real_time", logged_at.isoformat()),
            "date": logged_at.strftime("%Y-%m-%d"),
            "hour": logged_at.hour,
            "message": incident.get("message", ""),
            "centroid": list(incident.get("centroid", [])),
            "session_id": session_id,
            "source": "ai_camera",
            "logged_at": self._server_timestamp,
            "created_at": self._server_timestamp,
        }
        reference = client.collection("traffic_incidents").document(incident_id)
        reference.set(payload)
        return reference.id

    def log_snapshot(self, snapshot: Dict[str, Any], session_id: str = "default") -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None

        logged_at = datetime.now().astimezone()
        snapshot_id = (
            f"{session_id}-snapshot-"
            f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
        )
        payload = {
            "timestamp": logged_at.isoformat(),
            "date": logged_at.strftime("%Y-%m-%d"),
            "hour": logged_at.hour,
            "active_vehicles": int(snapshot.get("active_vehicles", 0) or 0),
            "density_score": float(snapshot.get("density_score", 0.0) or 0.0),
            "traffic_level": snapshot.get("traffic_level", ""),
            "stall_ratio": float(snapshot.get("stall_ratio", 0.0) or 0.0),
            "avg_speed_kmh": float(snapshot.get("avg_speed_kmh", 0.0) or 0.0),
            "session_id": session_id,
            "source": "ai_camera",
            "logged_at": self._server_timestamp,
            "created_at": self._server_timestamp,
        }
        reference = client.collection("traffic_snapshots").document(snapshot_id)
        reference.set(payload)
        return reference.id


firebase_vehicle_logger = FirebaseVehicleLogger()
