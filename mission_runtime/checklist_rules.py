from __future__ import annotations

from mission_runtime.models import ChecklistItem, MissionQuestion


AUTO_EVENT_ITEM_MAP = {
    "mission_start": "weather_check",
    "home_fix": "gps_check",
    "route_loaded": "route_check",
    "telemetry_ok": "telemetry_check",
    "takeoff": "takeoff_check",
    "landing": "landing_check",
}


def default_checklist_items() -> list[ChecklistItem]:
    return [
        ChecklistItem("weather_check", "Ortam Kontrolu", "Hava kosullari uygun", "auto", source="telemetry"),
        ChecklistItem("gps_check", "Ortam Kontrolu", "GPS lock alindi", "auto", source="telemetry"),
        ChecklistItem("route_check", "Ucus Oncesi", "Rota yuklendi", "auto", source="telemetry"),
        ChecklistItem("telemetry_check", "Ucus Oncesi", "Telemetri baglantisi saglikli", "auto", source="telemetry"),
        ChecklistItem("propeller_check", "Ucus Oncesi", "Pervane fiziksel kontrolu", "question", source="operator"),
        ChecklistItem("area_check", "Ucus Oncesi", "Alan guvenligi teyidi", "question", source="operator"),
        ChecklistItem("camera_check", "Ucus Oncesi", "Kamera ve lens gorsel kontrolu", "question", source="operator"),
        ChecklistItem("takeoff_check", "Ucus Sirasinda", "Kalkis gerceklesti", "approval", source="supervisor"),
        ChecklistItem("landing_check", "Ucus Sonrasi", "Inis tamamlandi", "approval", source="supervisor"),
    ]


def default_questions() -> list[MissionQuestion]:
    return [
        MissionQuestion("propeller_check", "Pervane fiziksel kontrolu tamam mi?"),
        MissionQuestion("area_check", "Ucus alani guvenli mi?"),
        MissionQuestion("camera_check", "Kamera ve lens gorsel kontrolden gecti mi?"),
    ]


def apply_event_to_checklist(items: list[ChecklistItem], event_name: str) -> None:
    mapped_item_id = AUTO_EVENT_ITEM_MAP.get(event_name)
    if not mapped_item_id:
        return

    for item in items:
        if item.item_id == mapped_item_id:
            item.completed = True
            item.status = "completed"
            item.answer = True
            return
