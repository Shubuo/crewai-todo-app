import tempfile
import unittest
from pathlib import Path

from mission_runtime.sample_log_generator import write_sample_telemetry_log
from mission_runtime.supervisor import MissionSupervisor


class MissionSupervisorTests(unittest.TestCase):
    def _build_supervisor(self, scenario_id: str = "survey_grid"):
        tmp = tempfile.TemporaryDirectory()
        log_path = Path(tmp.name) / "telemetry.log"
        write_sample_telemetry_log(log_path, scenario_id=scenario_id)
        supervisor = MissionSupervisor.create("Mission 1", log_path, scenario_id=scenario_id)
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

    def test_payload_contains_scenario_route_and_trail(self):
        supervisor = self._build_supervisor("perimeter_sweep")
        self._complete_preflight(supervisor)
        supervisor.approve_action("takeoff", True)
        supervisor.process_next_event()
        supervisor.process_next_event()

        payload = supervisor.to_api_payload()

        self.assertEqual(payload["scenario_id"], "perimeter_sweep")
        self.assertTrue(payload["planned_route"])
        self.assertGreaterEqual(len(payload["trail"]), 2)

    def test_manual_emergency_triggers_immediate_agent_action(self):
        supervisor = self._build_supervisor("survey_grid")
        self._complete_preflight(supervisor)
        supervisor.approve_action("takeoff", True)
        supervisor.process_next_event()

        supervisor.trigger_emergency("motor_fault")

        self.assertEqual(supervisor.last_emergency["emergency_type"], "motor_fault")
        self.assertEqual(supervisor.last_emergency["action"], "abort_and_land")
        self.assertEqual(supervisor.state, "landed")
        self.assertEqual(supervisor.replay_status, "awaiting_landing_approval")
        self.assertTrue(any(entry["agent_role"] == "Safety Officer" for entry in supervisor.event_log))

    def test_proactive_messages_and_fipa_log_follow_runtime_flow(self):
        supervisor = self._build_supervisor("windy_inspection")
        self._complete_preflight(supervisor)
        supervisor.approve_action("takeoff", True)
        for _ in range(4):
            supervisor.process_next_event()

        payload = supervisor.to_api_payload()

        self.assertTrue(payload["proactive_messages"])
        self.assertTrue(any(msg["agent_role"] == "Meteorology Agent" for msg in payload["proactive_messages"]))
        self.assertTrue(payload["fipa_log"])
        self.assertTrue(any(msg["sender"] == "Mission Supervisor" for msg in payload["fipa_log"]))

    def test_runtime_crewai_fallback_is_visible_in_logs(self):
        supervisor = self._build_supervisor("survey_grid")

        event_types = [entry["event_type"] for entry in supervisor.event_log]
        self.assertTrue(any(event_type.endswith("_fallback") for event_type in event_types))
        self.assertTrue(
            any("fallback engaged" in entry["content"] for entry in supervisor.fipa_log)
        )


if __name__ == "__main__":
    unittest.main()
