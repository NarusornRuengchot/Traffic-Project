import math
from typing import Dict, List, Tuple, Set, Optional, Any
import numpy as np

class VehicleTracker:
    def __init__(self, stall_distance_threshold: float = 5.0):
        self.stall_distance_threshold = stall_distance_threshold
        self.track_history: Dict[int, Tuple[int, int]] = {}
        self.prev_positions: Dict[int, Tuple[int, int]] = {}

    def reset(self):
        self.track_history.clear()
        self.prev_positions.clear()

    def update_positions(
        self,
        boxes_xyxy: np.ndarray,
        track_ids: List[int],
        mid_x: int
    ) -> Tuple[int, float, int, int, Dict[int, Tuple[int, int]]]:
        """
        Updates tracked vehicle positions, calculates stall ratio,
        and counts active vehicles separated by lane side.
        
        Returns:
            (active_count, stall_ratio, inbound_active, outbound_active, current_positions)
        """
        active_count = len(track_ids)
        stall_count = 0
        current_positions: Dict[int, Tuple[int, int]] = {}
        inbound_active = 0
        outbound_active = 0

        for box, tid in zip(boxes_xyxy, track_ids):
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)
            current_positions[tid] = (cx, cy)

            # Stall detection
            if tid in self.prev_positions:
                px, py = self.prev_positions[tid]
                dist = math.hypot(cx - px, cy - py)
                if dist < self.stall_distance_threshold:
                    stall_count += 1

            # Side check
            if cx < mid_x:
                inbound_active += 1
            else:
                outbound_active += 1

        self.prev_positions = current_positions
        stall_ratio = (stall_count / active_count) if active_count > 0 else 0.0

        return active_count, stall_ratio, inbound_active, outbound_active, current_positions
