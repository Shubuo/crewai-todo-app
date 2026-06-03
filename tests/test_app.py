import unittest

from drone_checklist_app import create_app


class FlaskMissionAppTests(unittest.TestCase):
    def test_create_mission_returns_runtime_payload(self):
        app = create_app({"TESTING": True})
        client = app.test_client()

        response = client.post("/api/missions", json={"mission_name": "Demo Mission"})
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("mission_id", payload)
        self.assertEqual(payload["state"], "preflight")


if __name__ == "__main__":
    unittest.main()
