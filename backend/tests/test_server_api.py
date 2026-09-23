import unittest
import asyncio
from server import get_models, get_videos, export_data

class TestServerAPI(unittest.TestCase):
    def test_get_models(self):
        result = asyncio.run(get_models())
        self.assertIn("models", result)
        self.assertIn("devices", result)
        self.assertIn("current_model", result)

    def test_get_videos(self):
        result = asyncio.run(get_videos())
        self.assertIn("videos", result)

    def test_export_empty_csv(self):
        response = asyncio.run(export_data(format="csv"))
        self.assertIn("text/csv", response.media_type)
        csv_content = response.body.decode("utf-8")
        self.assertTrue("Timestamp (s),Real-world Time" in csv_content)

    def test_export_summary(self):
        result = asyncio.run(export_data(format="summary"))
        self.assertIn("summary", result)

if __name__ == "__main__":
    unittest.main()

