from __future__ import annotations

from pathlib import Path


def _line(
    ts: str,
    event: str,
    battery: int,
    gps: int,
    wind: float,
    mode: str,
    lat: float,
    lon: float,
    heading: float,
    altitude: float,
    *,
    level: str = "info",
) -> str:
    return (
        f"ts={ts} level={level} event={event} battery={battery} gps={gps} wind={wind} "
        f"mode={mode} lat={lat:.4f} lon={lon:.4f} heading={heading} altitude={altitude}"
    )


SCENARIOS = {
    "survey_grid": {
        "label": "Survey Grid",
        "lines": [
            _line("2026-06-04T20:00:00Z", "mission_start", 96, 15, 4.2, "ground", 38.4200, 27.1400, 0, 0),
            _line("2026-06-04T20:00:08Z", "home_fix", 96, 16, 4.3, "ground", 38.4200, 27.1400, 0, 0),
            _line("2026-06-04T20:00:16Z", "route_loaded", 95, 16, 4.4, "guided", 38.4200, 27.1400, 15, 0),
            _line("2026-06-04T20:00:24Z", "telemetry_ok", 95, 16, 4.3, "guided", 38.4200, 27.1400, 18, 0),
            _line("2026-06-04T20:00:40Z", "takeoff", 94, 17, 4.7, "guided", 38.4203, 27.1406, 32, 18),
            _line("2026-06-04T20:01:00Z", "waypoint_a1", 93, 17, 4.9, "guided", 38.4210, 27.1418, 45, 24),
            _line("2026-06-04T20:01:20Z", "waypoint_a2", 92, 17, 5.0, "guided", 38.4221, 27.1435, 58, 26),
            _line("2026-06-04T20:01:40Z", "waypoint_b1", 91, 16, 5.2, "guided", 38.4230, 27.1417, 140, 25),
            _line("2026-06-04T20:02:00Z", "waypoint_b2", 90, 16, 5.1, "guided", 38.4240, 27.1431, 44, 24),
            _line("2026-06-04T20:02:20Z", "waypoint_c1", 89, 16, 5.3, "guided", 38.4250, 27.1445, 52, 23),
            _line("2026-06-04T20:02:40Z", "landing", 88, 15, 4.9, "land", 38.4258, 27.1452, 88, 0),
        ],
    },
    "perimeter_sweep": {
        "label": "Perimeter Sweep",
        "lines": [
            _line("2026-06-04T20:10:00Z", "mission_start", 97, 15, 3.8, "ground", 38.4180, 27.1360, 0, 0),
            _line("2026-06-04T20:10:08Z", "home_fix", 97, 16, 3.9, "ground", 38.4180, 27.1360, 0, 0),
            _line("2026-06-04T20:10:16Z", "route_loaded", 96, 16, 4.1, "guided", 38.4180, 27.1360, 20, 0),
            _line("2026-06-04T20:10:24Z", "telemetry_ok", 96, 16, 4.0, "guided", 38.4180, 27.1360, 24, 0),
            _line("2026-06-04T20:10:40Z", "takeoff", 95, 17, 4.3, "guided", 38.4185, 27.1370, 38, 20),
            _line("2026-06-04T20:11:00Z", "waypoint_north", 94, 17, 4.6, "guided", 38.4210, 27.1378, 15, 27),
            _line("2026-06-04T20:11:20Z", "waypoint_east", 93, 17, 4.4, "guided", 38.4216, 27.1420, 92, 29),
            _line("2026-06-04T20:11:40Z", "waypoint_south", 92, 16, 4.7, "guided", 38.4187, 27.1440, 174, 26),
            _line("2026-06-04T20:12:00Z", "waypoint_west", 91, 16, 4.5, "guided", 38.4175, 27.1394, 248, 24),
            _line("2026-06-04T20:12:20Z", "waypoint_home_arc", 90, 16, 4.2, "guided", 38.4188, 27.1371, 316, 19),
            _line("2026-06-04T20:12:40Z", "landing", 89, 15, 4.1, "land", 38.4180, 27.1360, 0, 0),
        ],
    },
    "windy_inspection": {
        "label": "Windy Inspection",
        "lines": [
            _line("2026-06-04T20:20:00Z", "mission_start", 96, 15, 5.6, "ground", 38.4192, 27.1384, 0, 0),
            _line("2026-06-04T20:20:08Z", "home_fix", 96, 16, 5.8, "ground", 38.4192, 27.1384, 0, 0),
            _line("2026-06-04T20:20:16Z", "route_loaded", 95, 16, 6.2, "guided", 38.4192, 27.1384, 18, 0),
            _line("2026-06-04T20:20:24Z", "telemetry_ok", 95, 16, 6.1, "guided", 38.4192, 27.1384, 20, 0),
            _line("2026-06-04T20:20:40Z", "takeoff", 94, 17, 6.8, "guided", 38.4198, 27.1390, 34, 18),
            _line("2026-06-04T20:21:00Z", "waypoint_stack_1", 93, 17, 7.4, "guided", 38.4207, 27.1406, 48, 23),
            _line("2026-06-04T20:21:20Z", "wind_watch", 92, 16, 9.8, "guided", 38.4216, 27.1422, 55, 25, level="warn"),
            _line("2026-06-04T20:21:40Z", "waypoint_stack_2", 91, 16, 9.1, "guided", 38.4224, 27.1439, 60, 25),
            _line("2026-06-04T20:22:00Z", "high_wind", 90, 16, 10.6, "guided", 38.4230, 27.1450, 66, 23, level="warn"),
            _line("2026-06-04T20:22:20Z", "landing", 88, 15, 8.4, "land", 38.4235, 27.1459, 84, 0),
        ],
    },
}


def scenario_label(scenario_id: str) -> str:
    return SCENARIOS.get(scenario_id, SCENARIOS["survey_grid"])["label"]


def scenario_route(scenario_id: str) -> list[dict[str, float]]:
    lines = SCENARIOS.get(scenario_id, SCENARIOS["survey_grid"])["lines"]
    route = []
    for line in lines:
        parts = dict(part.split("=", 1) for part in line.split())
        route.append(
            {
                "lat": float(parts["lat"]),
                "lon": float(parts["lon"]),
                "heading": float(parts["heading"]),
                "altitude": float(parts["altitude"]),
            }
        )
    return route


def write_sample_telemetry_log(path: Path, scenario_id: str = "survey_grid") -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scenario = SCENARIOS.get(scenario_id, SCENARIOS["survey_grid"])
    output_path.write_text("\n".join(scenario["lines"]) + "\n", encoding="utf-8")
    return output_path
