import tempfile
import unittest
from pathlib import Path

from mission_runtime.log_reader import TelemetryLogReader


class TelemetryLogReaderTests(unittest.TestCase):
    def test_reads_events_sequentially(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "telemetry.log"
            log_path.write_text(
                "ts=2026-06-04T20:00:00Z level=info event=mission_start battery=96 gps=15 wind=4.2 mode=ground\n"
                "ts=2026-06-04T20:00:10Z level=info event=route_loaded battery=95 gps=16 wind=4.5 mode=guided\n",
                encoding="utf-8",
            )
            reader = TelemetryLogReader(log_path)

            first = reader.read_next()
            second = reader.read_next()
            third = reader.read_next()

            self.assertEqual(first.event, "mission_start")
            self.assertEqual(first.level, "info")
            self.assertEqual(first.battery, 96)
            self.assertEqual(second.event, "route_loaded")
            self.assertIsNone(third)


if __name__ == "__main__":
    unittest.main()
