import cv2
import numpy as np
from typing import Tuple, Dict, Any, List

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
    def draw_hud(
        frame: np.ndarray,
        inbound_count: int,
        outbound_count: int,
        real_time_str: str,
        traffic_level_en: str,
        traffic_level_color: Tuple[int, int, int] = (0, 255, 0),
        swap_directions: bool = False
    ) -> np.ndarray:
        """Draws HUD stats on the top-left of the frame."""
        left_label = "Outbound" if swap_directions else "Inbound"
        right_label = "Inbound" if swap_directions else "Outbound"
        left_count = outbound_count if swap_directions else inbound_count
        right_count = inbound_count if swap_directions else outbound_count

        cv2.putText(frame, f"{left_label}: {left_count}", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)
        cv2.putText(frame, f"{right_label}: {right_count}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 165, 255), 2)
        cv2.putText(frame, f"Time: {real_time_str}", (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f"Traffic: {traffic_level_en}", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, traffic_level_color, 2)

        return frame
