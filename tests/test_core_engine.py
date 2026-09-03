import unittest
import numpy as np
import datetime

from src.core.vehicle_detector import VehicleDetector
from src.core.vehicle_tracker import VehicleTracker
from src.core.lane_counter import LaneCounter
from src.core.analytics import TrafficAnalytics, evaluate_traffic_level
from ai_engine import AITrafficEngine, get_traffic_level

class TestVehicleTracker(unittest.TestCase):
    def test_stale_track_eviction(self):
        tracker = VehicleTracker(max_lost_frames=10)
        boxes = np.array([[100, 100, 200, 200]])
        track_ids = [1]

        # Vehicle 1 is active at frame 1
        tracker.update_positions(boxes, track_ids, mid_x=400, frame_idx=1)
        tracker.track_history[1] = (150, 150)
        self.assertIn(1, tracker.prev_positions)
        self.assertIn(1, tracker.track_history)

        # 15 frames pass without Vehicle 1
        empty_boxes = np.empty((0, 4))
        tracker.update_positions(empty_boxes, [], mid_x=400, frame_idx=16)

        # Vehicle 1 should be pruned to prevent memory leak
        self.assertNotIn(1, tracker.track_history)
        self.assertNotIn(1, tracker.prev_positions)
        self.assertNotIn(1, tracker.last_seen)

    def test_stall_ratio_calculation(self):
        tracker = VehicleTracker(stall_distance_threshold=5.0)
        boxes = np.array([[100, 100, 200, 200], [300, 300, 400, 400]])
        track_ids = [1, 2]

        # Initial frame
        tracker.update_positions(boxes, track_ids, mid_x=500, frame_idx=1)

        # Next frame: vehicle 1 does not move (stalled), vehicle 2 moves 50px
        boxes_next = np.array([[101, 101, 201, 201], [350, 350, 450, 450]])
        count, stall_ratio, inbound, outbound, _ = tracker.update_positions(
            boxes_next, track_ids, mid_x=500, frame_idx=2
        )

        self.assertEqual(count, 2)
        self.assertAlmostEqual(stall_ratio, 0.5)

class TestLaneCounter(unittest.TestCase):
    def test_inbound_outbound_crossover(self):
        counter = LaneCounter(max_counted_cache=10)
        track_history = {1: (200, 240), 2: (600, 240)} # Y=240, just above LINE_Y=250

        # Next positions: both cross LINE_Y=250 to Y=260
        # Vehicle 1 is at X=200 (< MID_X=400) -> Inbound
        # Vehicle 2 is at X=600 (> MID_X=400) -> Outbound
        boxes = np.array([[150, 250, 250, 270], [550, 250, 650, 270]])
        track_ids = [1, 2]
        class_ids = [0, 0]
        id_to_name = {0: "Car"}

        events, triggers = counter.check_crossovers(
            boxes_xyxy=boxes,
            track_ids=track_ids,
            class_ids=class_ids,
            id_to_name=id_to_name,
            track_history=track_history,
            line_y=250,
            mid_x=400,
            swap_directions=False,
            timestamp_sec=1.0,
            real_time_full_str="2026-09-03 10:00:00",
            traffic_level_str="🟢 Smooth",
            frame_width=800
        )

        self.assertEqual(counter.inbound_count, 1)
        self.assertEqual(counter.outbound_count, 1)
        self.assertEqual(len(events), 2)
        # Check triggered line coordinates
        self.assertIn(((0, 250), (400, 250)), triggers)
        self.assertIn(((400, 250), (800, 250)), triggers)

    def test_bounded_counted_ids(self):
        counter = LaneCounter(max_counted_cache=5)
        # Add 10 IDs
        for i in range(10):
            counter._mark_counted(i)

        self.assertLessEqual(len(counter.counted_ids), 5)
        # The oldest IDs (0, 1, 2, 3, 4) should have been evicted
        self.assertNotIn(0, counter.counted_ids)
        self.assertIn(9, counter.counted_ids)

class TestTrafficAnalytics(unittest.TestCase):
    def test_traffic_level_evaluation(self):
        smooth = evaluate_traffic_level(3.0, 0.0)
        self.assertEqual(smooth.english_name, "Smooth")

        moderate = evaluate_traffic_level(10.0, 0.0)
        self.assertEqual(moderate.english_name, "Moderate")

        congested = evaluate_traffic_level(18.0, 0.0)
        self.assertEqual(congested.english_name, "Congested")

        gridlock = evaluate_traffic_level(25.0, 0.5)
        self.assertEqual(gridlock.english_name, "Gridlock")

    def test_rolling_density_window(self):
        analytics = TrafficAnalytics(window_size=3)
        analytics.update_rolling_stats(10, 5, 5)
        analytics.update_rolling_stats(20, 10, 10)
        analytics.update_rolling_stats(30, 15, 15)
        # Avg of 10, 20, 30 is 20
        rolling, in_roll, out_roll = analytics.update_rolling_stats(40, 20, 20)
        # After window pop of oldest (10), current is 20, 30, 40 -> avg is 30
        self.assertAlmostEqual(rolling, 30.0)
        self.assertAlmostEqual(in_roll, 15.0)

class TestAITrafficEngineAdapter(unittest.TestCase):
    def test_adapter_surface(self):
        # Verify backward compatibility methods and properties exist
        engine = AITrafficEngine(model_name="yolov11n.pt")
        self.assertTrue(hasattr(engine, "process_frame"))
        self.assertTrue(hasattr(engine, "reset_state"))
        self.assertTrue(hasattr(engine, "get_available_models"))
        self.assertTrue(hasattr(engine, "inbound_count"))
        self.assertTrue(hasattr(engine, "outbound_count"))
        self.assertEqual(engine.inbound_count, 0)

if __name__ == "__main__":
    unittest.main()
