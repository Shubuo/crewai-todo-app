from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from mission_runtime.checklist_rules import (
    apply_event_to_checklist,
    default_checklist_items,
    default_questions,
)
from mission_runtime.log_reader import TelemetryLogReader
from mission_runtime.models import ChecklistItem, MissionApproval, MissionQuestion


INITIAL_COORDINATES = {"lat": 38.42, "lon": 27.14, "heading": 0.0, "altitude": 0.0}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MissionSupervisor:
    @classmethod
    def create(cls, mission_name: str, log_path: Path) -> "MissionSupervisor":
        return cls(mission_name, log_path)

    def __init__(self, mission_name: str, log_path: Path):
        self.mission_id = uuid4().hex[:8]
        self.mission_name = mission_name
        self.log_path = Path(log_path)
        self.reader = TelemetryLogReader(self.log_path)
        self.state = "preflight"
        self.started_at = utc_now()
        self.ended_at: str | None = None
        self.replay_status = "ready"
        self.map_position = dict(INITIAL_COORDINATES)
        self.checklist_items: list[ChecklistItem] = default_checklist_items()
        self.questions: list[MissionQuestion] = default_questions()
        self.approvals: list[dict] = []
        self.pending_approval: dict | None = None
        self.event_log: list[dict] = []
        self.telemetry_snapshot: dict = {}
        self._log(
            "Mission Supervisor",
            "mission_created",
            f"{mission_name} gorevi hazirlandi.",
            result="Preflight baslatildi",
        )

    def _find_item(self, item_id: str) -> ChecklistItem | None:
        for item in self.checklist_items:
            if item.item_id == item_id:
                return item
        return None

    def _find_question(self, question_id: str) -> MissionQuestion | None:
        for question in self.questions:
            if question.question_id == question_id:
                return question
        return None

    def _log(
        self,
        agent_role: str,
        event_type: str,
        summary: str,
        *,
        result: str | None = None,
        level: str = "info",
        ts: str | None = None,
    ) -> None:
        self.event_log.append(
            {
                "timestamp": ts or utc_now(),
                "agent_role": agent_role,
                "event_type": event_type,
                "summary": summary,
                "result": result,
                "level": level,
            }
        )

    def _all_questions_answered(self) -> bool:
        return all(question.status == "answered" and question.answer for question in self.questions)

    def _preflight_auto_items_completed(self) -> bool:
        required = {"weather_check", "gps_check", "route_check", "telemetry_check"}
        return all(item.completed for item in self.checklist_items if item.item_id in required)

    def _update_map_position(self, event) -> None:
        if event.lat is not None:
            self.map_position["lat"] = float(event.lat)
        if event.lon is not None:
            self.map_position["lon"] = float(event.lon)
        if event.heading is not None:
            self.map_position["heading"] = float(event.heading)
        if event.altitude is not None:
            self.map_position["altitude"] = float(event.altitude)

    def _risk_summary(self) -> dict:
        wind = self.telemetry_snapshot.get("wind")
        battery = self.telemetry_snapshot.get("battery")
        status = "GO"
        notes: list[str] = []

        if wind is not None and wind >= 9:
            status = "WARNING"
            notes.append("Ruzgar sinira yaklasiyor.")
        if battery is not None and battery < 90:
            status = "WARNING" if status == "GO" else status
            notes.append("Batarya gorev sonuna yaklasiyor.")
        if self.pending_approval:
            notes.append(f"Bekleyen onay: {self.pending_approval['action']}")
        if not notes:
            notes.append("Gorev parametreleri dengeli gorunuyor.")

        return {"status": status, "notes": notes}

    def _history_summary(self) -> dict:
        items = [item for item in self.checklist_items if item.item_type != "reference"]
        completed = sum(1 for item in items if item.completed)
        total = len(items)
        completion_percentage = round((completed / total) * 100) if total else 0
        return {
            "completed_count": completed,
            "total_count": total,
            "completion_percentage": completion_percentage,
        }

    def _finalize_completed_mission(self) -> None:
        if self.state == "completed":
            return
        self.state = "completed"
        self.replay_status = "stopped"
        self.ended_at = self.ended_at or utc_now()
        self._log(
            "Report Writer",
            "mission_completed",
            "Ucus sonu kontrol ve rapor tamamladi.",
            result=f"%{self._history_summary()['completion_percentage']} checklist tamamlama",
        )

    def _ensure_takeoff_approval(self) -> None:
        if (
            self.pending_approval is None
            and self.state == "preflight"
            and self._all_questions_answered()
            and self._preflight_auto_items_completed()
        ):
            self.state = "ready_for_takeoff"
            approval = MissionApproval("takeoff", "Kalkis onayi gerekli")
            self.pending_approval = approval.to_dict()
            self.approvals.append(self.pending_approval)
            self._log(
                "Mission Supervisor",
                "phase_ready",
                "Preflight tamamlandi, kalkis onayi istendi.",
                result="Takeoff approval requested",
            )

    def answer_question(self, question_id: str, answer: bool) -> None:
        question = self._find_question(question_id)
        item = self._find_item(question_id)
        if question is None or item is None:
            return

        question.answer = bool(answer)
        question.status = "answered"
        item.answer = bool(answer)
        item.completed = bool(answer)
        item.status = "completed" if answer else "failed"
        self._log(
            "Mission Supervisor",
            "operator_check",
            f"{question.label}",
            result="Evet" if answer else "Hayir",
            level="info" if answer else "warn",
        )
        self._ensure_takeoff_approval()

    def approve_action(self, action: str, approved: bool) -> None:
        status = "approved" if approved else "rejected"
        self._log(
            "Safety Officer",
            f"{action}_{status}",
            f"{action} aksiyonu operator tarafindan degerlendirildi.",
            result=status.upper(),
            level="info" if approved else "warn",
        )
        if self.pending_approval and self.pending_approval.get("action") == action:
            self.pending_approval["status"] = status

        if not approved:
            self.pending_approval = None
            self.replay_status = "paused"
            return

        if action == "takeoff":
            self.pending_approval = None
            self.state = "in_flight"
            self.replay_status = "flying"
        elif action == "landing":
            self.pending_approval = None
            self.state = "postflight"
            self.replay_status = "stopped"
            self.ended_at = utc_now()
            self._finalize_completed_mission()

    def process_next_event(self):
        if self.state in {"ready_for_takeoff", "landed"} and self.pending_approval is not None:
            return None

        event = self.reader.read_next()
        if event is None:
            if self.state == "postflight":
                self._finalize_completed_mission()
            return None

        self.telemetry_snapshot = {
            "ts": event.ts,
            "level": event.level,
            "event": event.event,
            "battery": event.battery,
            "gps": event.gps,
            "wind": event.wind,
            "mode": event.mode,
            "lat": event.lat,
            "lon": event.lon,
            "heading": event.heading,
            "altitude": event.altitude,
        }
        self._update_map_position(event)
        apply_event_to_checklist(self.checklist_items, event.event)

        if event.event in {"mission_start", "home_fix", "route_loaded", "telemetry_ok"}:
            self._log(
                "Telemetry Analyst",
                event.event,
                f"GPS={event.gps or '--'}, wind={event.wind or '--'}",
                result=f"Mode={event.mode or '--'}",
                ts=event.ts,
            )
        elif event.event == "takeoff":
            self.state = "in_flight"
            self.replay_status = "flying"
            self._log(
                "Mission Supervisor",
                "takeoff",
                "Kalkis gerceklesti, rota replay basladi.",
                result=f"Alt={event.altitude or 0}m",
                ts=event.ts,
            )
        elif event.event.startswith("waypoint_"):
            self._log(
                "Telemetry Analyst",
                event.event,
                f"Drone rota noktasina ulasti ({self.map_position['lat']:.4f}, {self.map_position['lon']:.4f}).",
                result=f"Battery={event.battery or '--'}%",
                ts=event.ts,
            )
        elif event.event == "wind_watch":
            self._log(
                "Safety Officer",
                "warning",
                f"Ruzgar {event.wind or '--'} m/s seviyesine cikti.",
                result="Yol devam ediyor, limit izleniyor",
                level="warn",
                ts=event.ts,
            )
        elif event.event == "landing":
            self.state = "landed"
            self.replay_status = "awaiting_landing_approval"
            approval = MissionApproval("landing", "Inis sonrasi onay gerekli")
            self.pending_approval = approval.to_dict()
            self.approvals.append(self.pending_approval)
            self._log(
                "Mission Supervisor",
                "landing_hold",
                "Drone inis noktasina ulasti ve operator onayi bekliyor.",
                result="Landing approval requested",
                ts=event.ts,
            )
        else:
            self._log(
                "Telemetry Analyst",
                event.event,
                f"{event.event} olayi islendi.",
                ts=event.ts,
            )

        if event.event == "mission_start":
            weather_item = self._find_item("weather_check")
            if weather_item and event.wind is not None and event.wind <= 10:
                weather_item.completed = True
                weather_item.status = "completed"

        self._ensure_takeoff_approval()
        return event

    def pending_questions(self) -> list[dict]:
        return [question.to_dict() for question in self.questions if question.status == "pending"]

    def to_api_payload(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "mission_name": self.mission_name,
            "state": self.state,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "replay_status": self.replay_status,
            "map_position": dict(self.map_position),
            "telemetry_snapshot": self.telemetry_snapshot,
            "pending_approval": self.pending_approval,
            "pending_questions": self.pending_questions(),
            "approvals": list(self.approvals),
            "questions": [question.to_dict() for question in self.questions],
            "checklist": [item.to_dict() for item in self.checklist_items],
            "event_log": list(self.event_log),
            "history_summary": self._history_summary(),
            "risk_summary": self._risk_summary(),
            "log_path": str(self.log_path),
        }

