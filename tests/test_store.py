import tempfile
import unittest
from pathlib import Path

from mission_runtime.store import MissionStore


class MissionStoreTests(unittest.TestCase):
    def test_completed_mission_appears_in_history_and_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MissionStore(Path(tmp))
            mission = store.create("History Mission", scenario_id="windy_inspection")

            for question_id in ("propeller_check", "area_check", "camera_check"):
                mission.answer_question(question_id, True)
            for _ in range(4):
                mission.process_next_event()
            mission.approve_action("takeoff", True)
            while mission.pending_approval is None:
                mission.process_next_event()
            mission.approve_action("landing", True)
            store.save(mission)

            history = store.history()
            detail = store.detail(mission.mission_id)

            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["mission_id"], mission.mission_id)
            self.assertEqual(history[0]["scenario_id"], "windy_inspection")
            self.assertEqual(detail["state"], "completed")
            self.assertIn("report", detail)

    def test_can_delete_completed_mission_but_not_active_mission(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MissionStore(Path(tmp))
            active_mission = store.create("Active Mission")
            self.assertFalse(store.delete(active_mission.mission_id))

            completed = store.create("Delete Me")
            for question_id in ("propeller_check", "area_check", "camera_check"):
                completed.answer_question(question_id, True)
            for _ in range(4):
                completed.process_next_event()
            completed.approve_action("takeoff", True)
            while completed.pending_approval is None:
                completed.process_next_event()
            completed.approve_action("landing", True)
            store.save(completed)

            self.assertTrue(store.delete(completed.mission_id))
            self.assertEqual(store.history(), [])


if __name__ == "__main__":
    unittest.main()
