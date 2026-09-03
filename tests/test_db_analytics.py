import os
import unittest
import shutil
import tempfile
from src.database.db_manager import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_traffic.db")
        self.db = DatabaseManager(self.test_db)
        self.db.clear_all()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_log_and_retrieve_event(self):
        row_id = self.db.log_event(
            vehicle_id=101,
            vehicle_type="Car",
            direction="Inbound",
            traffic_level="🟢 คล่องตัว",
            timestamp_sec=12.5,
            real_time_str="2026-09-03 08:15:30"
        )
        self.assertGreater(row_id, 0)

        events, total = self.db.get_events_history(limit=10, offset=0)
        self.assertEqual(total, 1)
        self.assertEqual(events[0]["vehicle_id"], 101)
        self.assertEqual(events[0]["vehicle_type"], "Car")
        self.assertEqual(events[0]["direction"], "Inbound")
        self.assertEqual(events[0]["hour"], 8)
        self.assertEqual(events[0]["date"], "2026-09-03")

    def test_peak_hours_analysis(self):
        # Insert events for morning peak (Hour 8), normal (Hour 12), and evening peak (Hour 18)
        events = []
        # 5 cars at 08:00
        for i in range(5):
            events.append({
                "Timestamp (s)": i,
                "Real-world Time": "2026-09-03 08:20:00",
                "Vehicle ID": i,
                "Type": "Car",
                "Direction": "Inbound",
                "Traffic Level": "🟡 ปานกลาง"
            })
        # 2 motorcycles at 12:00
        for i in range(2):
            events.append({
                "Timestamp (s)": i + 10,
                "Real-world Time": "2026-09-03 12:30:00",
                "Vehicle ID": i + 10,
                "Type": "Motorcycle",
                "Direction": "Outbound",
                "Traffic Level": "🟢 คล่องตัว"
            })
        # 8 cars at 18:00 (Busiest)
        for i in range(8):
            events.append({
                "Timestamp (s)": i + 20,
                "Real-world Time": "2026-09-03 18:45:00",
                "Vehicle ID": i + 20,
                "Type": "Car",
                "Direction": "Outbound",
                "Traffic Level": "🔴 ติดขัด"
            })

        self.db.log_events_batch(events)

        analysis = self.db.get_peak_hours_analysis("2026-09-03")
        self.assertEqual(analysis["total_vehicles"], 15)
        self.assertEqual(analysis["busiest_count"], 8)
        self.assertIn("18:00", analysis["busiest_hour"])
        self.assertIn("08:00", analysis["morning_peak"])
        self.assertEqual(analysis["morning_peak_count"], 5)
        self.assertIn("18:00", analysis["evening_peak"])
        self.assertEqual(analysis["evening_peak_count"], 8)
        self.assertEqual(analysis["dominant_vehicle"], "Car")

        # Test CSV export
        csv_content = self.db.export_csv("2026-09-03")
        self.assertIn("Car", csv_content)
        self.assertIn("Motorcycle", csv_content)

if __name__ == "__main__":
    unittest.main()
