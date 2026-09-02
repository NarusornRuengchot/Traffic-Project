from typing import Dict, List, Tuple, Set, Optional, Any
import numpy as np

class LaneCounter:
    def __init__(self):
        self.inbound_count = 0
        self.outbound_count = 0
        self.counted_ids: Set[int] = set()
        self.class_counts: Dict[str, int] = {"Car": 0, "Motorcycle": 0, "Bus": 0, "Truck": 0}
        self.events_log: List[Dict[str, Any]] = []

    def reset(self):
        self.inbound_count = 0
        self.outbound_count = 0
        self.counted_ids.clear()
        self.class_counts = {"Car": 0, "Motorcycle": 0, "Bus": 0, "Truck": 0}
        self.events_log.clear()

    def check_crossovers(
        self,
        boxes_xyxy: np.ndarray,
        track_ids: List[int],
        class_ids: List[int],
        id_to_name: Dict[int, str],
        track_history: Dict[int, Tuple[int, int]],
        line_y: int,
        mid_x: int,
        swap_directions: bool,
        timestamp_sec: float,
        real_time_full_str: str,
        traffic_level_str: str
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[Tuple[int, int], Tuple[int, int]]]]:
        """
        Calculates line crossover and updates counts.
        Returns: (new_events, active_trigger_lines)
        """
        new_events = []
        triggered_lines = []

        for box, track_id, class_idx in zip(boxes_xyxy, track_ids, class_ids):
            center_x = int((box[0] + box[2]) / 2)
            center_y = int((box[1] + box[3]) / 2)

            if track_id in track_history:
                prev_x, prev_y = track_history[track_id]

                # Check if crossed the horizontal line
                if (prev_y <= line_y <= center_y) or (center_y <= line_y <= prev_y):
                    if track_id not in self.counted_ids:
                        self.counted_ids.add(track_id)

                        # Interpolate exact X coordinate where vehicle crossed LINE_Y
                        if center_y != prev_y:
                            cross_x = prev_x + (center_x - prev_x) * (line_y - prev_y) / (center_y - prev_y)
                        else:
                            cross_x = center_x

                        class_name = id_to_name.get(class_idx, "Vehicle")
                        left_is_inbound = not swap_directions

                        if cross_x < mid_x:
                            if left_is_inbound:
                                self.inbound_count += 1
                                direction = "Inbound"
                            else:
                                self.outbound_count += 1
                                direction = "Outbound"
                            triggered_lines.append(((0, line_y), (mid_x, line_y)))
                        else:
                            if left_is_inbound:
                                self.outbound_count += 1
                                direction = "Outbound"
                            else:
                                self.inbound_count += 1
                                direction = "Inbound"
                            triggered_lines.append(((mid_x, line_y), (int(box[2] * 2), line_y)))

                        if class_name in self.class_counts:
                            self.class_counts[class_name] += 1
                        else:
                            self.class_counts[class_name] = 1

                        event = {
                            "Timestamp (s)": round(timestamp_sec, 2),
                            "Real-world Time": real_time_full_str,
                            "Vehicle ID": track_id,
                            "Type": class_name,
                            "Direction": direction,
                            "Traffic Level": traffic_level_str
                        }
                        self.events_log.append(event)
                        new_events.append(event)

            track_history[track_id] = (center_x, center_y)

        return new_events, triggered_lines
