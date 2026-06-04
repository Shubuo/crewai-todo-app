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
from mission_runtime.sample_log_generator import scenario_label, scenario_route


INITIAL_COORDINATES = {"lat": 38.42, "lon": 27.14, "heading": 0.0, "altitude": 0.0}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MissionSupervisor:
    @classmethod
    def create(
        cls,
        mission_name: str,
        log_path: Path,
        scenario_id: str = "survey_grid",
    ) -> "MissionSupervisor":
        return cls(mission_name, log_path, scenario_id=scenario_id)

    def __init__(self, mission_name: str, log_path: Path, scenario_id: str = "survey_grid"):
        self.mission_id = uuid4().hex[:8]
        self.mission_name = mission_name
        self.scenario_id = scenario_id
        self.scenario_label = scenario_label(scenario_id)
        self.log_path = Path(log_path)
        self.reader = TelemetryLogReader(self.log_path)
        self.state = "preflight"
        self.started_at = utc_now()
        self.ended_at: str | None = None
        self.replay_status = "ready"
        self.map_position = dict(INITIAL_COORDINATES)
        self.planned_route = scenario_route(scenario_id)
        self.trail: list[dict] = []
        self.last_emergency: dict | None = None
        self.proactive_messages: list[dict] = []
        self.fipa_log: list[dict] = []
        self._proactive_flags: set[str] = set()
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
        self._fipa(
            "Mission Supervisor",
            "Telemetry Analyst",
            "REQUEST",
            "Preflight telemetrisi, rota ve link sagligi hazirlansin.",
        )
        self._fipa(
            "Mission Supervisor",
            "Safety Officer",
            "REQUEST",
            "Checklist tamamlandiginda kalkis uygunlugunu degerlendir.",
        )
        self._fipa(
            "Mission Supervisor",
            "Meteorology Agent",
            "REQUEST",
            "Ruzgar trendini gorev boyunca izle ve esik oncesi uyar.",
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

    def _fipa(
        self,
        sender: str,
        receiver: str,
        performative: str,
        content: str,
        *,
        ts: str | None = None,
    ) -> None:
        self.fipa_log.append(
            {
                "timestamp": ts or utc_now(),
                "sender": sender,
                "receiver": receiver,
                "performative": performative,
                "content": content,
            }
        )

    def _add_proactive(
        self,
        key: str,
        agent_role: str,
        title: str,
        message: str,
        *,
        severity: str = "info",
        actions: list[str] | None = None,
    ) -> None:
        if key in self._proactive_flags:
            return
        self._proactive_flags.add(key)
        self.proactive_messages.append(
            {
                "timestamp": utc_now(),
                "agent_role": agent_role,
                "title": title,
                "message": message,
                "severity": severity,
                "actions": actions or [],
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
        self.trail.append(dict(self.map_position))

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
        if self.last_emergency:
            status = "WARNING" if status == "GO" else status
            notes.append(
                f"Acil durum: {self.last_emergency['emergency_type']} -> {self.last_emergency['action']}"
            )
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
        self._fipa(
            "Mission Supervisor",
            "Report Writer",
            "REQUEST",
            "Ucus sonu bulgularini rapora donustur.",
        )
        self._fipa(
            "Report Writer",
            "Mission Supervisor",
            "INFORM",
            "Mission raporu, risk notlari ve checklist sonucu hazirlandi.",
        )

    def _run_proactive_checks(self, ts: str | None = None) -> None:
        wind = self.telemetry_snapshot.get("wind")
        battery = self.telemetry_snapshot.get("battery")
        gps = self.telemetry_snapshot.get("gps")

        if self.state == "ready_for_takeoff":
            self._add_proactive(
                "takeoff-brief",
                "Safety Officer",
                "Takeoff degerlendirmesi",
                "Checklist tamamlandi. Kalkis onayi verilirken ruzgar ve GPS trendi birlikte kontrol edilmeli.",
                severity="info",
                actions=["Kalkisi onayla", "1 ek tur telemetry oku"],
            )
            self._fipa(
                "Safety Officer",
                "Mission Supervisor",
                "PROPOSE",
                "Takeoff oncesi son ruzgar/GPS degeri kontrol edilerek GO karari verilebilir.",
                ts=ts,
            )

        if self.state in {"in_flight", "rth"}:
            if wind is not None and wind >= 8:
                self._add_proactive(
                    "wind-early-warning",
                    "Meteorology Agent",
                    "Ruzgar trendi yukseliyor",
                    "Ruzgar limit yakini. Rota kisaltma veya erken inis icin hazirlik oneriliyor.",
                    severity="warning",
                    actions=["Rota kisalt", "RTH hazirla"],
                )
                self._fipa(
                    "Meteorology Agent",
                    "Mission Supervisor",
                    "PROPOSE",
                    "Ruzgar artiyor; rota kisaltma veya erken inis secenekleri operatora sunulmali.",
                    ts=ts,
                )
            if battery is not None and battery <= 92:
                self._add_proactive(
                    "battery-buffer",
                    "Safety Officer",
                    "Batarya rezervi izleniyor",
                    "Batarya dusus hizi mevcut gorev profilinde erken donus penceresini etkileyebilir.",
                    severity="warning",
                    actions=["RTH rezervi hesapla", "Gorevi kisalt"],
                )
                self._fipa(
                    "Safety Officer",
                    "Mission Supervisor",
                    "PROPOSE",
                    "Batarya trendi nedeniyle mission suresi kisaltilabilir veya rezerv korunabilir.",
                    ts=ts,
                )
            if gps is not None and gps <= 15:
                self._add_proactive(
                    "gps-watch",
                    "Telemetry Analyst",
                    "GPS kalite takibi",
                    "Uydu sayisi dusuyor. Rota hassasiyeti azalirsa hold veya RTH secenekleri hazir tutulmali.",
                    severity="warning",
                    actions=["Hold hazirla", "RTH hazirla"],
                )
                self._fipa(
                    "Telemetry Analyst",
                    "Mission Supervisor",
                    "INFORM",
                    "GPS kalitesi azalma egiliminde; konum toleransi dusurulmeli.",
                    ts=ts,
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
            self._fipa(
                "Mission Supervisor",
                "Safety Officer",
                "REQUEST",
                "Preflight tamamlandi, kalkis uygunlugunu degerlendir.",
            )
            self._run_proactive_checks()

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
        self._fipa(
            "Mission Supervisor",
            "Safety Officer",
            "INFORM",
            f"Operator kontrol sonucu: {question.label} -> {'evet' if answer else 'hayir'}",
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
        self._fipa(
            "Safety Officer",
            "Mission Supervisor",
            "INFORM",
            f"Operator {action} icin {status} karari verdi.",
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

    def trigger_emergency(self, emergency_type: str) -> None:
        mapping = {
            "low_battery": ("Safety Officer", "rth_now", "rth", "emergency_rth"),
            "high_wind": ("Meteorology Agent", "land_now", "landed", "awaiting_landing_approval"),
            "gps_loss": ("Telemetry Analyst", "hold_then_rth", "rth", "emergency_hold"),
            "motor_fault": ("Safety Officer", "abort_and_land", "landed", "awaiting_landing_approval"),
        }
        agent_role, action, state, replay_status = mapping.get(
            emergency_type,
            ("Mission Supervisor", "hold_position", self.state, self.replay_status),
        )
        self.last_emergency = {
            "emergency_type": emergency_type,
            "agent_role": agent_role,
            "action": action,
            "timestamp": utc_now(),
        }
        self.state = state
        self.replay_status = replay_status
        if state == "landed":
            approval = MissionApproval("landing", "Acil inis sonrasi operator onayi")
            self.pending_approval = approval.to_dict()
            self.approvals.append(self.pending_approval)
        else:
            self.pending_approval = None
        self._log(
            agent_role,
            "emergency_action",
            f"{emergency_type} tetiklendi.",
            result=action,
            level="warn",
        )
        self._fipa(
            "Mission Supervisor",
            agent_role,
            "REQUEST",
            f"{emergency_type} icin acil karar uret.",
        )
        self._fipa(
            agent_role,
            "Mission Supervisor",
            "INFORM",
            f"Acil durum karari: {action}. Replay durumu {replay_status} olarak guncellendi.",
        )

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
            self._fipa(
                "Telemetry Analyst",
                "Mission Supervisor",
                "INFORM",
                f"{event.event}: gps={event.gps or '--'}, wind={event.wind or '--'}, mode={event.mode or '--'}",
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
            self._fipa(
                "Mission Supervisor",
                "Telemetry Analyst",
                "REQUEST",
                "Ucus sirasinda trend sapmalarini erken bildir.",
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
            self._fipa(
                "Telemetry Analyst",
                "Mission Supervisor",
                "INFORM",
                f"Waypoint gecildi; battery={event.battery or '--'}%, gps={event.gps or '--'}",
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
            self._fipa(
                "Meteorology Agent",
                "Safety Officer",
                "INFORM",
                f"Ruzgar {event.wind or '--'} m/s seviyesine cikti; sinira yaklasiliyor.",
                ts=event.ts,
            )
        elif event.event == "high_wind":
            self._log(
                "Meteorology Agent",
                "warning",
                f"Yuksek ruzgar tespit edildi: {event.wind or '--'} m/s.",
                result="Erken inis degerlendiriliyor",
                level="warn",
                ts=event.ts,
            )
            self._fipa(
                "Meteorology Agent",
                "Mission Supervisor",
                "PROPOSE",
                "Yuksek ruzgar nedeniyle erken inis veya gorev kisaltma uygulanmali.",
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
            self._fipa(
                "Mission Supervisor",
                "Safety Officer",
                "REQUEST",
                "Inis sonrasi son kontrol ve kapatma onayi gereksinimini bildir.",
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
        self._run_proactive_checks(event.ts)
        return event

    def pending_questions(self) -> list[dict]:
        return [question.to_dict() for question in self.questions if question.status == "pending"]

    def to_api_payload(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "mission_name": self.mission_name,
            "scenario_id": self.scenario_id,
            "scenario_label": self.scenario_label,
            "state": self.state,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "replay_status": self.replay_status,
            "map_position": dict(self.map_position),
            "planned_route": list(self.planned_route),
            "trail": list(self.trail),
            "last_emergency": self.last_emergency,
            "telemetry_snapshot": self.telemetry_snapshot,
            "compact_telemetry": {
                "battery": self.telemetry_snapshot.get("battery"),
                "gps": self.telemetry_snapshot.get("gps"),
                "wind": self.telemetry_snapshot.get("wind"),
                "mode": self.telemetry_snapshot.get("mode"),
            },
            "pending_approval": self.pending_approval,
            "pending_questions": self.pending_questions(),
            "approvals": list(self.approvals),
            "questions": [question.to_dict() for question in self.questions],
            "checklist": [item.to_dict() for item in self.checklist_items],
            "event_log": list(self.event_log),
            "proactive_messages": list(self.proactive_messages),
            "fipa_log": list(self.fipa_log),
            "history_summary": self._history_summary(),
            "risk_summary": self._risk_summary(),
            "log_path": str(self.log_path),
        }
