import cv2
import numpy as np
from typing import Tuple, Dict, Any, List, Optional

class FrameAnnotator:
    @staticmethod
    def draw_calibration_lines(
        image: np.ndarray,
        line_y_ratio: float = 0.50,
        mid_x_ratio: float = 0.45,
        swap_directions: bool = False,
        inbound_color: Tuple[int, int, int] = (255, 255, 0),    # Cyan
        outbound_color: Tuple[int, int, int] = (0, 165, 255),  # Orange
        line_thickness: int = 3
    ) -> np.ndarray:
        """Draws tripwire lines, central divider, and lane labels."""
        preview = image.copy()
        height, width = preview.shape[:2]
        line_y = int(height * line_y_ratio)
        mid_x = int(width * mid_x_ratio)

        inbound_start, inbound_end = (0, line_y), (mid_x, line_y)
        outbound_start, outbound_end = (mid_x, line_y), (width, line_y)

        # Draw left and right tripwires
        cv2.line(preview, inbound_start, inbound_end, inbound_color, line_thickness)
        cv2.line(preview, outbound_start, outbound_end, outbound_color, line_thickness)
        cv2.circle(preview, (mid_x, line_y), 8, (0, 0, 255), -1)

        left_label = "Outbound Lane" if swap_directions else "Inbound Lane"
        right_label = "Inbound Lane" if swap_directions else "Outbound Lane"

        cv2.putText(preview, left_label, (20, max(25, line_y - 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, inbound_color, 2)
        cv2.putText(preview, right_label, (mid_x + 20, max(25, line_y - 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, outbound_color, 2)

        return preview

    @staticmethod
    def draw_vehicle_badges(
        frame: np.ndarray,
        boxes_xyxy: np.ndarray,
        track_ids: List[int],
        speeds: Dict[int, float],
        speed_limit_kmh: float = 50.0,
        incident_vehicle_ids: Optional[set] = None
    ) -> np.ndarray:
        """Draws speed badges and alert outlines on detected vehicles."""
        if incident_vehicle_ids is None:
            incident_vehicle_ids = set()

        for box, tid in zip(boxes_xyxy, track_ids):
            x1, y1, x2, y2 = [int(v) for v in box]
            speed = speeds.get(tid, 0.0)

            # Choose badge color
            is_incident = tid in incident_vehicle_ids
            is_speeding = speed > speed_limit_kmh

            if is_incident:
                badge_color = (0, 0, 255)       # Red for incident
                text_color = (255, 255, 255)
                label = f"ID #{tid} | {speed} km/h [ALERT]"
            elif is_speeding:
                badge_color = (0, 140, 255)     # Amber/Orange for speeding
                text_color = (255, 255, 255)
                label = f"ID #{tid} | {speed} km/h !"
            else:
                badge_color = (40, 40, 40)      # Dark grey neutral
                text_color = (0, 255, 180)      # Mint green
                label = f"#{tid} {speed} km/h"

            # Draw background tag above bounding box
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.45
            thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

            tag_y1 = max(0, y1 - text_h - 8)
            tag_y2 = max(text_h + 8, y1)
            tag_x2 = min(frame.shape[1], x1 + text_w + 10)

            # Draw badge rectangle
            cv2.rectangle(frame, (x1, tag_y1), (tag_x2, tag_y2), badge_color, -1)
            cv2.putText(frame, label, (x1 + 4, tag_y2 - 4), font, font_scale, text_color, thickness)

            # If vehicle has an incident, draw attention outline
            if is_incident:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        return frame

    @staticmethod
    def draw_hud(
        frame: np.ndarray,
        inbound_count: int,
        outbound_count: int,
        real_time_str: str,
        traffic_level_en: str,
        traffic_level_color: Tuple[int, int, int] = (0, 255, 0),
        swap_directions: bool = False,
        avg_speed: float = 0.0,
        incident_count: int = 0
    ) -> np.ndarray:
        """Draws HUD stats on the top-left of the frame."""
        left_label = "Outbound" if swap_directions else "Inbound"
        right_label = "Inbound" if swap_directions else "Outbound"
        left_count = outbound_count if swap_directions else inbound_count
        right_count = inbound_count if swap_directions else outbound_count

        # Background panel for HUD readability
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (320, 175), (20, 20, 25), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # HUD lines
        cv2.putText(frame, f"{left_label}: {left_count}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 0), 2)
        cv2.putText(frame, f"{right_label}: {right_count}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 165, 255), 2)
        cv2.putText(frame, f"Speed: {round(avg_speed, 1)} km/h", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)
        cv2.putText(frame, f"Status: {traffic_level_en}", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, traffic_level_color, 2)

        time_str = f"Time: {real_time_str}"
        if incident_count > 0:
            time_str += f" | Alerts: {incident_count}"
        cv2.putText(frame, time_str, (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        return frame
