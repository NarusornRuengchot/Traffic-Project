import math
from typing import Dict, List, Tuple, Set, Optional, Any
import numpy as np

class VehicleTracker:
    def __init__(self, stall_distance_threshold: float = 5.0, max_lost_frames: int = 60):
        self.stall_distance_threshold = stall_distance_threshold
        self.max_lost_frames = max_lost_frames
        self.track_history: Dict[int, Tuple[int, int]] = {}
        self.prev_positions: Dict[int, Tuple[int, int]] = {}
        self.last_seen: Dict[int, int] = {}
        self.current_frame = 0

    def reset(self):
        self.track_history.clear()
        self.prev_positions.clear()
        self.last_seen.clear()
        self.current_frame = 0

    def prune_stale_tracks(self):
        """Removes track IDs that haven't been detected for max_lost_frames to prevent memory leaks."""
        if self.current_frame <= self.max_lost_frames:
            return

        stale_ids = [
            tid for tid, seen_frame in self.last_seen.items()
            if self.current_frame - seen_frame > self.max_lost_frames
        ]
        for tid in stale_ids:
            self.track_history.pop(tid, None)
            self.prev_positions.pop(tid, None)
            self.last_seen.pop(tid, None)

    def update_positions(
        self,
        boxes_xyxy: np.ndarray,
        track_ids: List[int],
        mid_x: int,
        frame_idx: Optional[int] = None
    ) -> Tuple[int, float, int, int, Dict[int, Tuple[int, int]]]:
        """
        Updates tracked vehicle positions, calculates stall ratio,
        counts active vehicles separated by lane side, and prunes stale tracks.
        
        Returns:
            (active_count, stall_ratio, inbound_active, outbound_active, current_positions)
        """
        if frame_idx is not None:
            self.current_frame = frame_idx
        else:
            self.current_frame += 1

        active_count = len(track_ids)
        stall_count = 0
        current_positions: Dict[int, Tuple[int, int]] = {}
        inbound_active = 0
        outbound_active = 0

        for box, tid in zip(boxes_xyxy, track_ids):
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)
            current_positions[tid] = (cx, cy)
            self.last_seen[tid] = self.current_frame

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

        # Run periodic memory pruning
        self.prune_stale_tracks()

        return active_count, stall_ratio, inbound_active, outbound_active, current_positions

