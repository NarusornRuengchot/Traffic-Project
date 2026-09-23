import math
from typing import Dict, Tuple, Optional, List
from collections import deque

class SpeedEstimator:
    """
    Computes smoothed vehicle speed (km/h) based on centroid motion vectors,
    frame rate (FPS), and configurable pixels-per-meter calibration scale.
    """
    def __init__(
        self,
        pixels_per_meter: float = 22.0,
        smoothing_window: int = 8,
        min_motion_threshold: float = 1.5,
        max_speed_kmh: float = 140.0
    ):
        self.pixels_per_meter = max(pixels_per_meter, 1.0)
        self.smoothing_window = smoothing_window
        self.min_motion_threshold = min_motion_threshold
        self.max_speed_kmh = max_speed_kmh

        # History per vehicle: track_id -> deque of (frame_idx, (cx, cy))
        self.track_positions: Dict[int, deque] = {}
        # Smoothed speed cache: track_id -> float (km/h)
        self.speed_cache: Dict[int, float] = {}

    def set_calibration_scale(self, pixels_per_meter: float):
        """Allows dynamic adjustment of road pixel-to-meter calibration scale."""
        self.pixels_per_meter = max(float(pixels_per_meter), 1.0)

    def reset(self):
        """Clears all historical tracks and speed caches."""
        self.track_positions.clear()
        self.speed_cache.clear()

    def update(
        self,
        track_id: int,
        centroid: Tuple[int, int],
        frame_idx: int,
        fps: float
    ) -> float:
        """
        Updates tracking history for a vehicle and calculates smoothed speed in km/h.
        """
        if fps <= 0:
            fps = 30.0

        if track_id not in self.track_positions:
            self.track_positions[track_id] = deque(maxlen=self.smoothing_window)

        hist = self.track_positions[track_id]
        hist.append((frame_idx, centroid))

        # Need at least 3 frames of history for stable derivative estimation
        if len(hist) < 3:
            return self.speed_cache.get(track_id, 0.0)

        first_frame, (x1, y1) = hist[0]
        last_frame, (x2, y2) = hist[-1]
        delta_frames = last_frame - first_frame

        if delta_frames <= 0:
            return self.speed_cache.get(track_id, 0.0)

        delta_time = delta_frames / fps
        pixel_distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # If vehicle moved less than noise threshold, consider stationary
        if pixel_distance < self.min_motion_threshold:
            instant_speed = 0.0
        else:
            meters = pixel_distance / self.pixels_per_meter
            instant_speed = (meters / delta_time) * 3.6  # m/s -> km/h

            # Filter outlier physics (e.g., track id hopping or detection glitch)
            if instant_speed > self.max_speed_kmh:
                instant_speed = self.speed_cache.get(track_id, 0.0)

        # Exponential moving average filter (alpha = 0.35)
        prev_speed = self.speed_cache.get(track_id, instant_speed)
        smoothed_speed = round(0.35 * instant_speed + 0.65 * prev_speed, 1)

        self.speed_cache[track_id] = smoothed_speed
        return smoothed_speed

    def get_speed(self, track_id: int) -> float:
        """Retrieves cached speed for a vehicle."""
        return self.speed_cache.get(track_id, 0.0)

    def prune_lost_tracks(self, active_track_ids: List[int]):
        """Evicts stale tracks not in current active frame to prevent memory leaks."""
        active_set = set(active_track_ids)
        stale_ids = [tid for tid in list(self.track_positions.keys()) if tid not in active_set]
        for tid in stale_ids:
            self.track_positions.pop(tid, None)
            self.speed_cache.pop(tid, None)
