import tempfile
import unittest
from pathlib import Path

from mission_runtime.log_reader import TelemetryLogReader
from mission_runtime.sample_log_generator import write_sample_telemetry_log


class SampleLogGeneratorTests(unittest.TestCase):
    def test_writes_a_replayable_log_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "telemetry.log"
            write_sample_telemetry_log(log_path)

            reader = TelemetryLogReader(log_path)
            events = []
            while True:
                event = reader.read_next()
                if event is None:
                    break
                events.append(event)

            names = [event.event for event in events]
            self.assertIn("mission_start", names)
            self.assertIn("landing", names)
            self.assertGreaterEqual(len(events), 9)
            self.assertIsNotNone(events[0].lat)
            self.assertIsNotNone(events[-1].heading)

    def test_supports_multiple_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            survey_path = Path(tmp) / "survey.log"
            windy_path = Path(tmp) / "windy.log"
            write_sample_telemetry_log(survey_path, scenario_id="survey_grid")
            write_sample_telemetry_log(windy_path, scenario_id="windy_inspection")

            survey_lines = survey_path.read_text(encoding="utf-8").splitlines()
            windy_lines = windy_path.read_text(encoding="utf-8").splitlines()

            self.assertNotEqual(survey_lines, windy_lines)
            self.assertGreater(len(survey_lines), 9)
            self.assertTrue(any("high_wind" in line or "wind_watch" in line for line in windy_lines))


if __name__ == "__main__":
    unittest.main()
