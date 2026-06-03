from __future__ import annotations

from pathlib import Path


SAMPLE_LINES = [
    "ts=2026-06-04T20:00:00Z level=info event=mission_start battery=96 gps=15 wind=4.2 mode=ground",
    "ts=2026-06-04T20:00:10Z level=info event=home_fix battery=96 gps=16 wind=4.3 mode=ground",
    "ts=2026-06-04T20:00:20Z level=info event=route_loaded battery=95 gps=16 wind=4.5 mode=guided",
    "ts=2026-06-04T20:00:30Z level=info event=telemetry_ok battery=95 gps=16 wind=4.4 mode=guided",
    "ts=2026-06-04T20:01:00Z level=info event=takeoff battery=94 gps=17 wind=4.9 mode=guided",
    "ts=2026-06-04T20:03:20Z level=critical event=rth_recommended battery=88 gps=14 wind=11.2 mode=guided",
    "ts=2026-06-04T20:04:00Z level=info event=landing battery=85 gps=14 wind=8.1 mode=land",
]


def write_sample_telemetry_log(path: Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(SAMPLE_LINES) + "\n", encoding="utf-8")
    return output_path
