import unittest

from mission_runtime.reporting import build_mission_report


class MissionReportingTests(unittest.TestCase):
    def test_builds_summary_report_from_supervisor_state(self):
        class StubSupervisor:
            mission_name = "Mission 1"
            state = "completed"
            telemetry_snapshot = {"battery": 85}
            event_log = [{"event": "landing", "level": "info"}]
            checklist_items = []
            approvals = []

        report = build_mission_report(StubSupervisor())

        self.assertIn("mission_name", report)
        self.assertIn("state", report)
        self.assertIn("recommendations", report)


if __name__ == "__main__":
    unittest.main()
