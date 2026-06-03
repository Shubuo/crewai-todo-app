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
                events.append(event.event)

            self.assertIn("mission_start", events)
            self.assertIn("landing", events)
            self.assertGreaterEqual(len(events), 7)


if __name__ == "__main__":
    unittest.main()
