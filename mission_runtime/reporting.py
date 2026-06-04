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
        "started_at": getattr(supervisor, "started_at", None),
        "ended_at": getattr(supervisor, "ended_at", None),
        "replay_status": getattr(supervisor, "replay_status", None),
        "telemetry_snapshot": getattr(supervisor, "telemetry_snapshot", {}),
        "events": list(getattr(supervisor, "event_log", [])),
        "history_summary": getattr(supervisor, "_history_summary", lambda: {})(),
        "risk_summary": getattr(supervisor, "_risk_summary", lambda: {})(),
        "recommendations": recommendations,
    }
