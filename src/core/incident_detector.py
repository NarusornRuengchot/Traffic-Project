import time
import datetime
from typing import Dict, List, Tuple, Optional, Any

class IncidentDetector:
    """
    Real-time Traffic Incident & Anomaly Detection:
    - Wrong-Way Driving (ขับรถย้อนศร)
    - Stalled / Obstructing Vehicle (รถจอดแช่ / กีดขวางการจราจร)
    - Speeding (ขับรถเร็วเกินกำหนด)
    """
    def __init__(
        self,
        speed_limit_kmh: float = 50.0,
        stalled_duration_sec: float = 6.0,
        min_wrong_way_displacement_px: float = 25.0
    ):
        self.speed_limit_kmh = speed_limit_kmh
        self.stalled_duration_sec = stalled_duration_sec
        self.min_wrong_way_displacement_px = min_wrong_way_displacement_px

        # Tracking state: track_id -> dict
        # {"first_seen_time": float, "first_pos": (x, y), "last_pos": (x, y), "stationary_start": float, "reported_incidents": set()}
        self.vehicle_records: Dict[int, Dict[str, Any]] = {}
        self.active_incidents: List[Dict[str, Any]] = []

    def set_speed_limit(self, limit_kmh: float):
        self.speed_limit_kmh = max(10.0, float(limit_kmh))

    def reset(self):
        self.vehicle_records.clear()
        self.active_incidents.clear()

    def check_incidents(
        self,
        track_ids: List[int],
        centroids: List[Tuple[int, int]],
        speeds: List[float],
        class_names: List[str],
        mid_x: int,
        swap_directions: bool,
        current_time_sec: float,
        real_time_str: str,
        fps: float = 30.0
    ) -> List[Dict[str, Any]]:
        """
        Evaluates active vehicles for any abnormal behavior.
        Returns: list of newly detected incidents in this frame.
        """
        new_incidents = []
        active_set = set(track_ids)

        for tid, centroid, speed, c_name in zip(track_ids, centroids, speeds, class_names):
            cx, cy = centroid

            if tid not in self.vehicle_records:
                self.vehicle_records[tid] = {
                    "first_seen_time": current_time_sec,
                    "first_pos": (cx, cy),
                    "last_pos": (cx, cy),
                    "prev_positions": [(current_time_sec, (cx, cy))],
                    "stationary_since": current_time_sec if speed < 3.0 else None,
                    "reported": set()
                }
            else:
                rec = self.vehicle_records[tid]
                rec["last_pos"] = (cx, cy)
                rec["prev_positions"].append((current_time_sec, (cx, cy)))
                if len(rec["prev_positions"]) > 30:
                    rec["prev_positions"].pop(0)

            rec = self.vehicle_records[tid]

            # -------------------------------------------------------------
            # 1. Stalled Vehicle Detection (รถจอดแช่ / กีดขวาง)
            # -------------------------------------------------------------
            if speed < 3.0:
                if rec["stationary_since"] is None:
                    rec["stationary_since"] = current_time_sec
                else:
                    duration_stalled = current_time_sec - rec["stationary_since"]
                    if duration_stalled >= self.stalled_duration_sec and "stalled" not in rec["reported"]:
                        incident = {
                            "incident_type": "stalled",
                            "severity": "high",
                            "vehicle_id": tid,
                            "vehicle_type": c_name,
                            "speed_kmh": round(speed, 1),
                            "timestamp_sec": round(current_time_sec, 2),
                            "real_time": real_time_str,
                            "message": f"⚠️ ตรวจพบรถ {c_name} ID #{tid} จอดนิ่งกีดขวาง ({round(duration_stalled, 0)} วินาที)",
                            "centroid": (cx, cy)
                        }
                        rec["reported"].add("stalled")
                        new_incidents.append(incident)
                        self.active_incidents.append(incident)
            else:
                rec["stationary_since"] = None

            # -------------------------------------------------------------
            # 2. Speeding Detection (ขับเร็วเกินกำหนด)
            # -------------------------------------------------------------
            if speed > self.speed_limit_kmh and "speeding" not in rec["reported"]:
                incident = {
                    "incident_type": "speeding",
                    "severity": "medium",
                    "vehicle_id": tid,
                    "vehicle_type": c_name,
                    "speed_kmh": round(speed, 1),
                    "timestamp_sec": round(current_time_sec, 2),
                    "real_time": real_time_str,
                    "message": f"🚨 รถ {c_name} ID #{tid} ขับเร็ว {speed} km/h (จำกัด {int(self.speed_limit_kmh)} km/h)",
                    "centroid": (cx, cy)
                }
                rec["reported"].add("speeding")
                new_incidents.append(incident)
                self.active_incidents.append(incident)

            # -------------------------------------------------------------
            # 3. Wrong-Way Driving Detection (ขับรถย้อนศร)
            # -------------------------------------------------------------
            # Compare first recorded position with current position
            if len(rec["prev_positions"]) >= 10 and "wrong_way" not in rec["reported"]:
                old_time, (old_x, old_y) = rec["prev_positions"][0]
                dy = cy - old_y
                dt = current_time_sec - old_time

                # Left side (X < mid_x): default Inbound = moving DOWNWARDS (dy > 0)
                # Right side (X >= mid_x): default Outbound = moving UPWARDS (dy < 0)
                is_left = cx < mid_x
                left_expected_dy = 1 if not swap_directions else -1
                right_expected_dy = -1 if not swap_directions else 1

                expected_direction_dy = left_expected_dy if is_left else right_expected_dy

                # If vehicle has moved significant vertical distance in opposite direction
                if abs(dy) >= self.min_wrong_way_displacement_px and dt >= 0.5:
                    actual_dir = 1 if dy > 0 else -1
                    if actual_dir != expected_direction_dy:
                        incident = {
                            "incident_type": "wrong_way",
                            "severity": "critical",
                            "vehicle_id": tid,
                            "vehicle_type": c_name,
                            "speed_kmh": round(speed, 1),
                            "timestamp_sec": round(current_time_sec, 2),
                            "real_time": real_time_str,
                            "message": f"⛔ ตรวจพบรถ {c_name} ID #{tid} ขับขี่ย้อนศรในเลน {'เข้าเมือง' if is_left else 'ออกเมือง'}",
                            "centroid": (cx, cy)
                        }
                        rec["reported"].add("wrong_way")
                        new_incidents.append(incident)
                        self.active_incidents.append(incident)

        # Evict lost tracks
        stale_ids = [tid for tid in list(self.vehicle_records.keys()) if tid not in active_set]
        for tid in stale_ids:
            self.vehicle_records.pop(tid, None)

        # Keep active incidents list bounded to recent 20
        if len(self.active_incidents) > 20:
            self.active_incidents = self.active_incidents[-20:]

        return new_incidents
