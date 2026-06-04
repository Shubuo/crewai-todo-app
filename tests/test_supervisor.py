import tempfile
import unittest
from pathlib import Path

from mission_runtime.sample_log_generator import write_sample_telemetry_log
from mission_runtime.supervisor import MissionSupervisor


class MissionSupervisorTests(unittest.TestCase):
    def _build_supervisor(self):
        tmp = tempfile.TemporaryDirectory()
        log_path = Path(tmp.name) / "telemetry.log"
        write_sample_telemetry_log(log_path)
        supervisor = MissionSupervisor.create("Mission 1", log_path)
        self.addCleanup(tmp.cleanup)
        return supervisor

    def _complete_preflight(self, supervisor: MissionSupervisor) -> None:
        supervisor.answer_question("propeller_check", True)
        supervisor.answer_question("area_check", True)
        supervisor.answer_question("camera_check", True)
        for _ in range(4):
            supervisor.process_next_event()

    def test_preflight_requires_takeoff_approval_after_checks(self):
        supervisor = self._build_supervisor()

        self._complete_preflight(supervisor)

        self.assertEqual(supervisor.state, "ready_for_takeoff")
        self.assertEqual(supervisor.pending_approval["action"], "takeoff")
        self.assertTrue(
            any(entry["agent_role"] == "Mission Supervisor" for entry in supervisor.event_log)
        )

    def test_takeoff_approval_starts_replay(self):
        supervisor = self._build_supervisor()

        self._complete_preflight(supervisor)
        supervisor.approve_action("takeoff", True)
        supervisor.process_next_event()

        self.assertEqual(supervisor.state, "in_flight")
        self.assertEqual(supervisor.replay_status, "flying")
        self.assertEqual(supervisor.telemetry_snapshot["event"], "takeoff")

    def test_landing_event_pauses_replay_and_landing_approval_completes(self):
        supervisor = self._build_supervisor()

        self._complete_preflight(supervisor)
        supervisor.approve_action("takeoff", True)
        while supervisor.pending_approval is None:
            supervisor.process_next_event()

        self.assertEqual(supervisor.pending_approval["action"], "landing")
        self.assertEqual(supervisor.replay_status, "awaiting_landing_approval")
        supervisor.approve_action("landing", True)

        self.assertEqual(supervisor.state, "completed")
        self.assertEqual(supervisor.replay_status, "stopped")
        self.assertIsNotNone(supervisor.ended_at)


if __name__ == "__main__":
    unittest.main()
