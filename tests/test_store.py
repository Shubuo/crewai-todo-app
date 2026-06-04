import tempfile
import unittest
from pathlib import Path

from mission_runtime.store import MissionStore


class MissionStoreTests(unittest.TestCase):
    def test_completed_mission_appears_in_history_and_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MissionStore(Path(tmp))
            mission = store.create("History Mission")

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
            self.assertEqual(detail["state"], "completed")
            self.assertIn("report", detail)


if __name__ == "__main__":
    unittest.main()
