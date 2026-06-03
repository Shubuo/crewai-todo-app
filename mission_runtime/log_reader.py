from __future__ import annotations

from pathlib import Path

from mission_runtime.models import TelemetryEvent


def _parse_value(value: str):
    if value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


class TelemetryLogReader:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lines = self.path.read_text(encoding="utf-8").splitlines()
        self._index = 0

    def read_next(self) -> TelemetryEvent | None:
        if self._index >= len(self._lines):
            return None

        raw_line = self._lines[self._index]
        self._index += 1
        raw_fields = dict(part.split("=", 1) for part in raw_line.split())
        fields = {key: _parse_value(value) for key, value in raw_fields.items()}

        return TelemetryEvent(
            ts=str(fields.get("ts", "")),
            level=str(fields.get("level", "info")),
            event=str(fields.get("event", "")),
            battery=fields.get("battery"),
            gps=fields.get("gps"),
            wind=fields.get("wind"),
            mode=fields.get("mode"),
            raw=raw_fields,
        )
