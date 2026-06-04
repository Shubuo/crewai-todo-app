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


if __name__ == "__main__":
    unittest.main()
