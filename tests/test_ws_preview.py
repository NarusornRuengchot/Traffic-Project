import unittest
import asyncio
import json
import os
from server import websocket_stream_endpoint

class DummyWebSocket:
    def __init__(self, messages):
        self.incoming = messages.copy()
        self.sent = []
        self.is_closed = False

    async def accept(self):
        pass

    async def receive_text(self):
        if not self.incoming:
            # Simulate disconnect
            from fastapi import WebSocketDisconnect
            raise WebSocketDisconnect()
        return self.incoming.pop(0)

    async def send_json(self, data):
        self.sent.append(data)

    async def send_bytes(self, data):
        self.sent.append(data)

class TestWebSocketFeatures(unittest.TestCase):
    def test_ws_preview_and_status(self):
        video_path = os.path.join("uploads", "IMG_1357.MOV")
        if not os.path.exists(video_path):
            self.skipTest("Sample video not found")

        # Prepare messages: request preview via WS
        messages = [
            json.dumps({
                "command": "get_preview",
                "video_path": video_path,
                "line_y_ratio": 0.5,
                "mid_x_ratio": 0.45,
                "swap_directions": False
            })
        ]

        dummy_ws = DummyWebSocket(messages)
        asyncio.run(websocket_stream_endpoint(dummy_ws))

        # Check sent messages:
        # 1. First message should be initial model_status
        # 2. Second message should be preview packet
        msg_types = [m.get("type") for m in dummy_ws.sent if isinstance(m, dict)]
        self.assertIn("model_status", msg_types)
        self.assertIn("preview", msg_types)

        preview_msg = next(m for m in dummy_ws.sent if isinstance(m, dict) and m.get("type") == "preview")
        self.assertIn("preview", preview_msg)
        self.assertGreater(len(preview_msg["preview"]), 100)

if __name__ == "__main__":
    unittest.main()
