from __future__ import annotations


def build_mission_report(supervisor) -> dict:
    incomplete = [item.label for item in getattr(supervisor, "checklist_items", []) if not item.completed]
    recommendations = []
    if incomplete:
        recommendations.append("Eksik checklist maddelerini bir sonraki gorev oncesi tamamlayin.")
    if getattr(supervisor, "state", "") != "completed":
        recommendations.append("Gorev tamamlanmadan rapor alinmis; bekleyen adimlari kontrol edin.")

    return {
        "mission_name": supervisor.mission_name,
        "state": supervisor.state,
        "telemetry_snapshot": getattr(supervisor, "telemetry_snapshot", {}),
        "events": list(getattr(supervisor, "event_log", [])),
        "recommendations": recommendations,
    }
