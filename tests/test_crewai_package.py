from pathlib import Path
import unittest


class CrewAIPackageTests(unittest.TestCase):
    def test_crewai_package_imports_from_repository_root(self):
        import crewai_todo_app
        from crewai_todo_app import main

        self.assertTrue(str(Path(crewai_todo_app.__file__)).endswith("crewai_todo_app/__init__.py"))
        self.assertTrue(str(Path(main.__file__)).endswith("src/crewai_todo_app/main.py"))

    def test_runtime_agent_catalog_lists_runtime_roles(self):
        catalog = Path("mission_runtime/runtime_agents.yaml").read_text(encoding="utf-8")

        for role in [
            "Mission Supervisor",
            "Telemetry Analyst",
            "Safety Officer",
            "Meteorology Agent",
            "Report Writer",
        ]:
            self.assertIn(role, catalog)


if __name__ == "__main__":
    unittest.main()
