import unittest
import numpy as np
import tempfile
import shutil
import os

from src.core.speed_estimator import SpeedEstimator
from src.core.incident_detector import IncidentDetector
from src.database.db_manager import DatabaseManager

class TestSpeedEstimator(unittest.TestCase):
    def test_stationary_vehicle(self):
        estimator = SpeedEstimator(pixels_per_meter=20.0)
        # 5 frames of identical position
        for f in range(1, 6):
            speed = estimator.update(track_id=1, centroid=(100, 100), frame_idx=f, fps=30.0)
        self.assertEqual(speed, 0.0)

    def test_moving_vehicle_speed(self):
        estimator = SpeedEstimator(pixels_per_meter=20.0, smoothing_window=5)
        # Vehicle moves 20 pixels per frame at 30 fps
        # 20 px = 1 meter. 1 meter / (1/30 s) = 30 m/s = 108 km/h
        for f in range(1, 10):
            speed = estimator.update(track_id=2, centroid=(100, 100 + f * 20), frame_idx=f, fps=30.0)
        
        # After smoothing, speed should be within reasonable range of ~108 km/h
        self.assertGreater(speed, 70.0)
        self.assertLessEqual(speed, 140.0)

    def test_prune_lost_tracks(self):
        estimator = SpeedEstimator()
        estimator.update(track_id=10, centroid=(50, 50), frame_idx=1, fps=30.0)
        estimator.update(track_id=20, centroid=(60, 60), frame_idx=1, fps=30.0)
        self.assertIn(10, estimator.track_positions)
        self.assertIn(20, estimator.track_positions)

        # Vehicle 10 is still active, vehicle 20 has disappeared
        estimator.prune_lost_tracks([10])
        self.assertIn(10, estimator.track_positions)
        self.assertNotIn(20, estimator.track_positions)

class TestIncidentDetector(unittest.TestCase):
    def test_stalled_vehicle_detection(self):
        detector = IncidentDetector(stalled_duration_sec=3.0)
        
        # Stationary vehicle at t=0 to t=4.0s
        for t in range(5):
            incidents = detector.check_incidents(
                track_ids=[1],
                centroids=[(100, 100)],
                speeds=[0.0],
                class_names=["Car"],
                mid_x=400,
                swap_directions=False,
                current_time_sec=float(t),
                real_time_str="10:00:00"
            )
        
        types = [inc["incident_type"] for inc in detector.active_incidents]
        self.assertIn("stalled", types)

    def test_speeding_detection(self):
        detector = IncidentDetector(speed_limit_kmh=50.0)
        
        incidents = detector.check_incidents(
            track_ids=[5],
            centroids=[(200, 300)],
            speeds=[75.0],
            class_names=["Car"],
            mid_x=400,
            swap_directions=False,
            current_time_sec=1.0,
            real_time_str="10:00:01"
        )
        types = [inc["incident_type"] for inc in detector.active_incidents]
        self.assertIn("speeding", types)

    def test_wrong_way_detection(self):
        detector = IncidentDetector(min_wrong_way_displacement_px=20.0)
        
        # Inbound lane is left side (X < mid_x=400).
        # Expected motion is downwards (dy > 0).
        # We simulate vehicle moving UPWARDS (Y decreases: 300 -> 240)
        for i in range(15):
            detector.check_incidents(
                track_ids=[7],
                centroids=[(200, 300 - i * 5)],
                speeds=[35.0],
                class_names=["Car"],
                mid_x=400,
                swap_directions=False,
                current_time_sec=0.1 * i,
                real_time_str="10:00:02"
            )
        types = [inc["incident_type"] for inc in detector.active_incidents]
        self.assertIn("wrong_way", types)

class TestDatabaseSpeedAndIncidents(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_incidents.db")
        self.db = DatabaseManager(self.test_db)
        self.db.clear_all()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_log_and_retrieve_incidents(self):
        inc_id = self.db.log_incident(
            incident_type="wrong_way",
            severity="critical",
            vehicle_id=99,
            vehicle_type="Motorcycle",
            speed_kmh=42.5,
            message="Test wrong way",
            timestamp_sec=10.0,
            real_time_str="2026-09-10 10:15:00"
        )
        self.assertGreater(inc_id, 0)

        incidents, total = self.db.get_incidents_history(limit=10, offset=0)
        self.assertEqual(total, 1)
        self.assertEqual(incidents[0]["incident_type"], "wrong_way")
        self.assertEqual(incidents[0]["vehicle_id"], 99)
        self.assertEqual(incidents[0]["speed_kmh"], 42.5)

    def test_speed_analytics(self):
        events = [
            {
                "Timestamp (s)": 1.0,
                "Real-world Time": "2026-09-10 10:00:00",
                "Vehicle ID": 1,
                "Type": "Car",
                "Direction": "Inbound",
                "Speed (km/h)": 40.0,
                "Traffic Level": "🟢 คล่องตัว"
            },
            {
                "Timestamp (s)": 2.0,
                "Real-world Time": "2026-09-10 10:00:05",
                "Vehicle ID": 2,
                "Type": "Car",
                "Direction": "Inbound",
                "Speed (km/h)": 60.0,
                "Traffic Level": "🟢 คล่องตัว"
            }
        ]
        self.db.log_events_batch(events)

        analytics = self.db.get_speed_analytics("2026-09-10")
        self.assertEqual(analytics["total_sampled"], 2)
        self.assertEqual(analytics["avg_speed"], 50.0)
        self.assertEqual(analytics["max_speed"], 60.0)
        self.assertIn("Car", analytics["by_class"])

if __name__ == "__main__":
    unittest.main()
