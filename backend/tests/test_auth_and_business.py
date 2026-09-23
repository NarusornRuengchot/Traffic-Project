import os
import unittest
import shutil
import tempfile
import asyncio
from src.utils.security import hash_password, verify_password, create_access_token, verify_access_token, decode_access_token
from src.database.db_manager import DatabaseManager
import src.api.routers.auth as auth_router_mod
import src.api.routers.business as biz_router_mod

class TestAuthAndBusiness(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_traffic.db")
        self.db = DatabaseManager(self.test_db)
        self.db.clear_all()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_security_utils(self):
        # 1. Password hashing & verification
        pwd = "SecretPassword123!"
        hashed = hash_password(pwd)
        self.assertIn("$", hashed)
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

        # 2. JWT Token creation and decoding
        token = create_access_token({"sub": 42, "username": "somchai", "role": "admin"})
        payload = verify_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], 42)
        self.assertEqual(payload["username"], "somchai")
        self.assertEqual(payload["role"], "admin")

        # 3. decode_access_token alias
        payload2 = decode_access_token(token)
        self.assertEqual(payload2["username"], "somchai")

        # 4. Invalid token
        tampered_token = token + "xyz"
        self.assertIsNone(verify_access_token(tampered_token))

    def test_user_database_crud(self):
        # Create user
        user = self.db.create_user(
            username="retail_owner",
            password="secure_password",
            email="owner@retail.co.th",
            full_name="คุณสมชาย ค้าปลีก",
            role="business_owner"
        )
        self.assertIsNotNone(user)
        user_id = user["id"]
        self.assertGreater(user_id, 0)

        # Duplicate username should fail
        with self.assertRaises(Exception):
            self.db.create_user(
                username="retail_owner",
                password="another_password",
                email="another@retail.co.th"
            )

        # Authenticate
        auth_success = self.db.authenticate_user("retail_owner", "secure_password")
        self.assertIsNotNone(auth_success)
        self.assertEqual(auth_success["username"], "retail_owner")
        self.assertEqual(auth_success["role"], "business_owner")

        auth_fail = self.db.authenticate_user("retail_owner", "wrong_password")
        self.assertIsNone(auth_fail)

        # Get by ID
        user_fetched = self.db.get_user_by_id(user_id)
        self.assertIsNotNone(user_fetched)
        self.assertEqual(user_fetched["email"], "owner@retail.co.th")
        self.assertNotIn("password_hash", user_fetched)

    def test_business_and_cameras_crud(self):
        # Create business
        biz_id = self.db.create_business(
            name="ศูนย์การค้าศรีราชาเซ็นทรัล",
            business_type="retail",
            branch_code="SRC-001",
            address="อ.ศรีราชา จ.ชลบุรี",
            contact_email="manager@src-central.com",
            opening_hour=10,
            closing_hour=22,
            target_hourly_traffic=150
        )
        self.assertIsNotNone(biz_id)

        # Get business list
        businesses = self.db.get_businesses()
        self.assertGreaterEqual(len(businesses), 1)
        found_biz = [b for b in businesses if b["id"] == biz_id]
        self.assertEqual(len(found_biz), 1)
        self.assertEqual(found_biz[0]["name"], "ศูนย์การค้าศรีราชาเซ็นทรัล")

        # Update business
        updated = self.db.update_business(biz_id, {"target_hourly_traffic": 200, "name": "ศรีราชา เซ็นทรัล มอลล์"})
        self.assertTrue(updated)
        biz_detail = self.db.get_business_by_id(biz_id)
        self.assertEqual(biz_detail["target_hourly_traffic"], 200)
        self.assertEqual(biz_detail["name"], "ศรีราชา เซ็นทรัล มอลล์")

        # Create camera
        cam_id = self.db.create_business_camera(
            business_id=biz_id,
            name="Main Entrance Gate 1",
            stream_url="https://live.src-traffic.com/cam1.m3u8",
            camera_type="entrance",
            location_note="ทางเข้าหลัก ลานจอด A"
        )
        self.assertIsNotNone(cam_id)

        # List cameras
        cams = self.db.get_business_cameras(biz_id)
        self.assertEqual(len(cams), 1)
        self.assertEqual(cams[0]["name"], "Main Entrance Gate 1")

        # Delete camera
        del_cam = self.db.delete_business_camera(cam_id)
        self.assertTrue(del_cam)
        self.assertEqual(len(self.db.get_business_cameras(biz_id)), 0)

        # Delete business
        del_biz = self.db.delete_business(biz_id)
        self.assertTrue(del_biz)
        self.assertIsNone(self.db.get_business_by_id(biz_id))

    def test_business_dashboard_analytics(self):
        biz_id = self.db.create_business(
            name="PTT Station & EV Hub Sriracha",
            business_type="gas_station",
            opening_hour=6,
            closing_hour=23,
            target_hourly_traffic=50
        )
        # Log traffic events
        test_events = [
            {"Timestamp (s)": 1.0, "Real-world Time": "2026-09-23 08:30:00", "Vehicle ID": 1, "Type": "Car", "Direction": "Inbound", "Traffic Level": "🟢 คล่องตัว"},
            {"Timestamp (s)": 2.0, "Real-world Time": "2026-09-23 08:35:00", "Vehicle ID": 2, "Type": "Car", "Direction": "Inbound", "Traffic Level": "🟢 คล่องตัว"},
            {"Timestamp (s)": 3.0, "Real-world Time": "2026-09-23 12:15:00", "Vehicle ID": 3, "Type": "Truck", "Direction": "Inbound", "Traffic Level": "🟢 คล่องตัว"},
            {"Timestamp (s)": 4.0, "Real-world Time": "2026-09-23 12:20:00", "Vehicle ID": 4, "Type": "Motorcycle", "Direction": "Outbound", "Traffic Level": "🟢 คล่องตัว"},
            {"Timestamp (s)": 5.0, "Real-world Time": "2026-09-23 02:00:00", "Vehicle ID": 5, "Type": "Car", "Direction": "Inbound", "Traffic Level": "🟢 คล่องตัว"}, # off-hours
        ]
        self.db.log_events_batch(test_events)

        analytics = self.db.get_business_dashboard_analytics(biz_id, target_date="2026-09-23")
        self.assertIsNotNone(analytics)
        self.assertEqual(analytics["business"]["name"], "PTT Station & EV Hub Sriracha")
        self.assertEqual(analytics["kpis"]["total_vehicles"], 5)
        self.assertGreater(analytics["kpis"]["estimated_footfall"], 0)
        self.assertIn("08:00", analytics["kpis"]["peak_hour"])

    def test_api_auth_and_business_handlers(self):
        # Override global db_manager in router modules
        orig_auth_db = auth_router_mod.db_manager
        orig_biz_db = biz_router_mod.db_manager
        auth_router_mod.db_manager = self.db
        biz_router_mod.db_manager = self.db

        try:
            # 1. Register API
            reg_payload = {
                "username": "api_user",
                "password": "password999",
                "email": "api_user@ku.th",
                "full_name": "KU Developer",
                "role": "business_owner"
            }
            reg_res = asyncio.run(auth_router_mod.register_user(reg_payload))
            self.assertEqual(reg_res["status"], "success")
            self.assertIn("access_token", reg_res)

            # 2. Login API
            login_payload = {"username_or_email": "api_user", "password": "password999"}
            login_res = asyncio.run(auth_router_mod.login_user(login_payload))
            self.assertEqual(login_res["status"], "success")
            token = login_res["access_token"]

            # 3. Get Current User Profile API
            profile_res = asyncio.run(auth_router_mod.get_current_profile(f"Bearer {token}"))
            self.assertEqual(profile_res["status"], "success")
            self.assertEqual(profile_res["user"]["username"], "api_user")

            # 4. Demo Accounts
            demo_res = asyncio.run(auth_router_mod.get_demo_accounts())
            self.assertIn("accounts", demo_res)

            # 5. Create Business via API
            biz_req = {
                "name": "Kasetsart Logistics Hub",
                "business_type": "logistics",
                "branch_code": "SRC-LOG-01",
                "target_hourly_traffic": 80
            }
            create_biz_res = asyncio.run(biz_router_mod.create_business_endpoint(biz_req))
            self.assertEqual(create_biz_res["status"], "success")
            biz_id = create_biz_res["business_id"]

            # 6. List Businesses via API
            list_res = asyncio.run(biz_router_mod.list_businesses())
            self.assertEqual(list_res["status"], "success")
            self.assertGreaterEqual(len(list_res["businesses"]), 1)

            # 7. Add Camera via API
            cam_req = {
                "business_id": biz_id,
                "name": "Main Gate Cam",
                "stream_url": "rtsp://demo-camera.org/live",
                "camera_type": "entrance"
            }
            add_cam_res = asyncio.run(biz_router_mod.create_business_camera_endpoint(cam_req))
            self.assertEqual(add_cam_res["status"], "success")

            # 8. Get Business Analytics via API
            dash_res = asyncio.run(biz_router_mod.get_business_dashboard(business_id=biz_id))
            self.assertEqual(dash_res["business"]["name"], "Kasetsart Logistics Hub")

        finally:
            auth_router_mod.db_manager = orig_auth_db
            biz_router_mod.db_manager = orig_biz_db

if __name__ == "__main__":
    unittest.main()
