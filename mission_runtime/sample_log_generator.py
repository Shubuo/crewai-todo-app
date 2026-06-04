from __future__ import annotations

from pathlib import Path


SAMPLE_LINES = [
    "ts=2026-06-04T20:00:00Z level=info event=mission_start battery=96 gps=15 wind=4.2 mode=ground lat=38.4200 lon=27.1400 heading=0 altitude=0",
    "ts=2026-06-04T20:00:10Z level=info event=home_fix battery=96 gps=16 wind=4.3 mode=ground lat=38.4200 lon=27.1400 heading=0 altitude=0",
    "ts=2026-06-04T20:00:20Z level=info event=route_loaded battery=95 gps=16 wind=4.5 mode=guided lat=38.4200 lon=27.1400 heading=15 altitude=0",
    "ts=2026-06-04T20:00:30Z level=info event=telemetry_ok battery=95 gps=16 wind=4.4 mode=guided lat=38.4200 lon=27.1400 heading=20 altitude=0",
    "ts=2026-06-04T20:01:00Z level=info event=takeoff battery=94 gps=17 wind=4.9 mode=guided lat=38.4205 lon=27.1404 heading=35 altitude=18",
    "ts=2026-06-04T20:01:30Z level=info event=waypoint_alpha battery=93 gps=17 wind=5.1 mode=guided lat=38.4218 lon=27.1420 heading=42 altitude=27",
    "ts=2026-06-04T20:02:00Z level=warn event=wind_watch battery=92 gps=16 wind=8.8 mode=guided lat=38.4230 lon=27.1436 heading=54 altitude=27",
    "ts=2026-06-04T20:02:30Z level=info event=waypoint_bravo battery=90 gps=16 wind=8.4 mode=guided lat=38.4245 lon=27.1455 heading=64 altitude=24",
    "ts=2026-06-04T20:03:00Z level=info event=landing battery=88 gps=15 wind=7.6 mode=land lat=38.4252 lon=27.1472 heading=90 altitude=0",
]


def write_sample_telemetry_log(path: Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(SAMPLE_LINES) + "\n", encoding="utf-8")
    return output_path
