import unittest

from mission_runtime.runtime_crewai import RuntimeMissionCrew


class RuntimeMissionCrewTests(unittest.TestCase):
    def test_falls_back_without_credentials(self):
        crew = RuntimeMissionCrew()

        decision = crew.decide("takeoff_brief", {"state": "ready_for_takeoff"})

        self.assertEqual(decision.mode, "fallback")
        self.assertEqual(decision.agent_role, "Safety Officer")
        self.assertIn("fallback", decision.fallback_reason.lower())


if __name__ == "__main__":
    unittest.main()
