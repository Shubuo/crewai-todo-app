import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from drone_checklist_app import create_app
from mission_runtime.store import MissionStore


class FlaskMissionAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = MissionStore(Path(self.tmp.name))
        self.app = create_app({"TESTING": True, "MISSION_STORE": self.store})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_mission_returns_runtime_payload(self):
        response = self.client.post(
            "/api/missions",
            json={"mission_name": "Demo Mission", "scenario_id": "perimeter_sweep"},
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("mission_id", payload)
        self.assertEqual(payload["state"], "preflight")
        self.assertIn("replay_status", payload)
        self.assertIn("map_position", payload)
        self.assertIn("fipa_log", payload)
        self.assertIn("proactive_messages", payload)
        self.assertEqual(payload["scenario_id"], "perimeter_sweep")
        self.assertTrue(payload["planned_route"])

    def test_history_endpoint_returns_completed_mission(self):
        mission = self.store.create("History Mission", scenario_id="windy_inspection")
        for question_id in ("propeller_check", "area_check", "camera_check"):
            mission.answer_question(question_id, True)
        for _ in range(4):
            mission.process_next_event()
        mission.approve_action("takeoff", True)
        while mission.pending_approval is None:
            mission.process_next_event()
        mission.approve_action("landing", True)
        self.store.save(mission)

        response = self.client.get("/api/missions/history")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["state"], "completed")
        self.assertEqual(payload[0]["scenario_id"], "windy_inspection")

    def test_emergency_endpoint_triggers_runtime_action(self):
        mission = self.store.create("Emergency Mission")
        for question_id in ("propeller_check", "area_check", "camera_check"):
            mission.answer_question(question_id, True)
        for _ in range(4):
            mission.process_next_event()
        mission.approve_action("takeoff", True)
        mission.process_next_event()
        self.store.save(mission)

        response = self.client.post(
            f"/api/missions/{mission.mission_id}/emergency",
            json={"emergency_type": "high_wind"},
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["last_emergency"]["emergency_type"], "high_wind")
        self.assertIn(payload["last_emergency"]["action"], {"land_now", "hold_then_rth", "rth_now"})

    def test_delete_completed_history_mission(self):
        mission = self.store.create("Delete Mission")
        for question_id in ("propeller_check", "area_check", "camera_check"):
            mission.answer_question(question_id, True)
        for _ in range(4):
            mission.process_next_event()
        mission.approve_action("takeoff", True)
        while mission.pending_approval is None:
            mission.process_next_event()
        mission.approve_action("landing", True)
        self.store.save(mission)

        response = self.client.delete(f"/api/missions/{mission.mission_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/missions/history").get_json(), [])

    @patch("drone_checklist_app.urllib.request.urlopen")
    def test_weather_advice_endpoint_returns_decision(self, mock_urlopen):
        class StubResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

            def read(self):
                return json.dumps({"current": {"temperature_2m": 24, "wind_speed_10m": 6}}).encode()

        mock_urlopen.return_value = StubResponse()

        response = self.client.post("/api/weather_advice", json={"lat": 38.42, "lon": 27.14})
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["decision"], "GO")
        self.assertIn("advice", payload)

    def test_index_restores_tabs_and_removes_old_subtitle(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Ana Komuta Ekrani", html)
        self.assertIn("FIPA Ajan Simulasyonu", html)
        self.assertIn("Survey Grid", html)
        self.assertIn("Acil Durum", html)
        self.assertIn("Mission Supervisor", html)
        self.assertIn("Telemetry Analyst", html)
        self.assertNotIn("Checklist artik agent destekli ilerliyor", html)


if __name__ == "__main__":
    unittest.main()
