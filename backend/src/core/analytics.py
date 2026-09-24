import datetime
import pandas as pd
from typing import Dict, List, Tuple, Any
from src.schema.telemetry import TrafficLevel

TRAFFIC_LEVELS = {
    "Smooth": TrafficLevel(
        thai_desc="คล่องตัว",
        emoji="🟢",
        english_name="Smooth",
        color_rgb=(0, 220, 100),
        color_hex="#10B981"
    ),
    "Moderate": TrafficLevel(
        thai_desc="ปานกลาง",
        emoji="🟡",
        english_name="Moderate",
        color_rgb=(0, 215, 255),
        color_hex="#F59E0B"
    ),
    "Congested": TrafficLevel(
        thai_desc="หนาแน่น",
        emoji="🟠",
        english_name="Congested",
        color_rgb=(0, 140, 255),
        color_hex="#F97316"
    ),
    "Gridlock": TrafficLevel(
        thai_desc="หนาแน่นมาก",
        emoji="🔴",
        english_name="Gridlock",
        color_rgb=(0, 0, 255),
        color_hex="#EF4444"
    )
}

def evaluate_traffic_level(density: float, stall_ratio: float = 0.0) -> TrafficLevel:
    """
    Evaluates traffic congestion level based on vehicle density and stall ratio.
    """
    score = density * (1.0 + 0.2 * stall_ratio)

    if score <= 5.0:
        return TRAFFIC_LEVELS["Smooth"]
    elif score <= 12.0:
        return TRAFFIC_LEVELS["Moderate"]
    elif score <= 20.0:
        return TRAFFIC_LEVELS["Congested"]
    else:
        return TRAFFIC_LEVELS["Gridlock"]

class TrafficAnalytics:
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.active_history: List[int] = []
        self.inbound_active_history: List[int] = []
        self.outbound_active_history: List[int] = []
        self.flow_history: List[Dict[str, Any]] = []

    def reset(self):
        self.active_history.clear()
        self.inbound_active_history.clear()
        self.outbound_active_history.clear()
        self.flow_history.clear()

    def update_rolling_stats(self, active_count: int, inbound_active: int, outbound_active: int) -> Tuple[float, float, float]:
        self.active_history.append(active_count)
        self.inbound_active_history.append(inbound_active)
        self.outbound_active_history.append(outbound_active)

        if len(self.active_history) > self.window_size:
            self.active_history.pop(0)
            self.inbound_active_history.pop(0)
            self.outbound_active_history.pop(0)

        rolling_density = sum(self.active_history) / len(self.active_history) if self.active_history else 0.0
        rolling_inbound = sum(self.inbound_active_history) / len(self.inbound_active_history) if self.inbound_active_history else 0.0
        rolling_outbound = sum(self.outbound_active_history) / len(self.outbound_active_history) if self.outbound_active_history else 0.0

        return rolling_density, rolling_inbound, rolling_outbound

    def record_telemetry(self, telemetry: Dict[str, Any]):
        self.flow_history.append(telemetry)

    def generate_summary_table(self, start_dt: datetime.datetime, interval_seconds: int = 10) -> List[Dict[str, Any]]:
        """Generates interval grouped summary statistics."""
        if not self.flow_history:
            return []

        df = pd.DataFrame(self.flow_history)
        if "time_sec" not in df.columns or "active_vehicles" not in df.columns:
            return []

        df["interval_sec"] = df["time_sec"].apply(lambda t: int(t // interval_seconds) * interval_seconds)
        df["interval_time"] = df["interval_sec"].apply(lambda t: (start_dt + datetime.timedelta(seconds=t)).strftime("%H:%M:%S"))

        summary = df.groupby("interval_time").agg(
            avg_active=("active_vehicles", "mean"),
            inbound_max=("inbound_count", "max"),
            inbound_min=("inbound_count", "min"),
            outbound_max=("outbound_count", "max"),
            outbound_min=("outbound_count", "min")
        ).reset_index()

        summary["inbound_passed"] = summary["inbound_max"] - summary["inbound_min"]
        summary["outbound_passed"] = summary["outbound_max"] - summary["outbound_min"]
        summary["avg_active"] = summary["avg_active"].round(1)

        result = []
        for _, row in summary.iterrows():
            lvl = evaluate_traffic_level(row["avg_active"])
            result.append({
                "time": row["interval_time"],
                "avg_vehicles": row["avg_active"],
                "traffic_level": f"{lvl.emoji} {lvl.thai_desc}",
                "traffic_level_en": lvl.english_name,
                "inbound_flow": int(row["inbound_passed"]),
                "outbound_flow": int(row["outbound_passed"]),
                "total_flow": int(row["inbound_passed"] + row["outbound_passed"])
            })
        return result
