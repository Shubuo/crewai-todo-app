from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from mission_runtime.checklist_rules import (
    apply_event_to_checklist,
    default_checklist_items,
    default_questions,
)
from mission_runtime.log_reader import TelemetryLogReader
from mission_runtime.models import ChecklistItem, MissionApproval, MissionQuestion


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
        self.checklist_items: list[ChecklistItem] = default_checklist_items()
        self.questions: list[MissionQuestion] = default_questions()
        self.approvals: list[dict] = []
        self.pending_approval: dict | None = None
        self.event_log: list[dict] = []
        self.telemetry_snapshot: dict = {}

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

    def _all_questions_answered(self) -> bool:
        return all(question.status == "answered" and question.answer for question in self.questions)

    def _preflight_auto_items_completed(self) -> bool:
        required = {"weather_check", "gps_check", "route_check", "telemetry_check"}
        return all(
            item.completed for item in self.checklist_items if item.item_id in required
        )

    def _ensure_takeoff_approval(self) -> None:
        if self.pending_approval is None and self.state == "preflight" and self._all_questions_answered() and self._preflight_auto_items_completed():
            self.state = "ready_for_takeoff"
            approval = MissionApproval("takeoff", "Kalkis onayi gerekli")
            self.pending_approval = approval.to_dict()
            self.approvals.append(self.pending_approval)
            self.event_log.append(
                {"event": "takeoff_approval_requested", "level": "info", "message": approval.label}
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
        self.event_log.append(
            {
                "event": "operator_answer",
                "level": "info" if answer else "warn",
                "message": f"{question_id}={answer}",
            }
        )
        self._ensure_takeoff_approval()

    def approve_action(self, action: str, approved: bool) -> None:
        status = "approved" if approved else "rejected"
        self.event_log.append(
            {"event": f"{action}_{status}", "level": "info" if approved else "warn", "message": action}
        )
        if self.pending_approval and self.pending_approval.get("action") == action:
            self.pending_approval["status"] = status

        if not approved:
            self.pending_approval = None
            return

        if action == "takeoff":
            self.pending_approval = None
            self.state = "in_flight"
        elif action == "rth":
            self.pending_approval = None
            self.state = "rth"
        elif action == "landing":
            self.pending_approval = None
            self.state = "postflight"

    def process_next_event(self):
        if self.state in {"ready_for_takeoff", "rth", "landed"} and self.pending_approval is not None:
            return None

        event = self.reader.read_next()
        if event is None:
            if self.state == "postflight":
                self.state = "completed"
            return None

        self.telemetry_snapshot = {
            "ts": event.ts,
            "level": event.level,
            "event": event.event,
            "battery": event.battery,
            "gps": event.gps,
            "wind": event.wind,
            "mode": event.mode,
        }
        self.event_log.append(
            {
                "event": event.event,
                "level": event.level,
                "message": f"{event.event} işlendi",
            }
        )
        apply_event_to_checklist(self.checklist_items, event.event)

        if event.event == "mission_start":
            battery_item = self._find_item("weather_check")
            if battery_item and event.wind is not None and event.wind <= 10:
                battery_item.completed = True
                battery_item.status = "completed"

        if event.event == "takeoff":
            self.state = "in_flight"
        elif event.event == "rth_recommended":
            self.state = "rth"
            approval = MissionApproval("rth", "RTH onayi gerekli")
            self.pending_approval = approval.to_dict()
            self.approvals.append(self.pending_approval)
        elif event.event == "landing":
            self.state = "landed"
            approval = MissionApproval("landing", "Inis sonrasi onay gerekli")
            self.pending_approval = approval.to_dict()
            self.approvals.append(self.pending_approval)

        self._ensure_takeoff_approval()
        return event

    def pending_questions(self) -> list[dict]:
        return [question.to_dict() for question in self.questions if question.status == "pending"]

    def to_api_payload(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "mission_name": self.mission_name,
            "state": self.state,
            "telemetry_snapshot": self.telemetry_snapshot,
            "pending_approval": self.pending_approval,
            "pending_questions": self.pending_questions(),
            "approvals": list(self.approvals),
            "questions": [question.to_dict() for question in self.questions],
            "checklist": [item.to_dict() for item in self.checklist_items],
            "event_log": list(self.event_log),
        }
