from __future__ import annotations

import json
import os
from dataclasses import dataclass

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")

DEFAULT_MODEL = os.getenv("RUNTIME_CREWAI_MODEL", os.getenv("OPENAI_MODEL_NAME", "openrouter/owl-alpha"))


@dataclass
class RuntimeCrewDecision:
    agent_role: str
    task_name: str
    message: str
    mode: str
    fallback_reason: str | None = None


class RuntimeMissionCrew:
    def __init__(self) -> None:
        self._agent_specs = {
            "mission_supervisor": {
                "role": "Mission Supervisor",
                "goal": "Coordinate mission phases, approvals, and cross-agent decisions.",
                "backstory": "You orchestrate UAV mission flow and turn multi-agent signals into operator-ready action.",
            },
            "telemetry_analyst": {
                "role": "Telemetry Analyst",
                "goal": "Interpret telemetry and detect route, GPS, and link anomalies early.",
                "backstory": "You monitor UAV telemetry for meaningful operational signals, not raw numbers.",
            },
            "safety_officer": {
                "role": "Safety Officer",
                "goal": "Enforce GO/NO-GO limits and choose the safest operational response.",
                "backstory": "You are strict about margins, battery reserves, landing readiness, and flight termination.",
            },
            "meteorology_agent": {
                "role": "Meteorology Agent",
                "goal": "Assess wind and weather trends and warn before conditions become unsafe.",
                "backstory": "You focus on weather-driven operational risk and early intervention.",
            },
            "report_writer": {
                "role": "Report Writer",
                "goal": "Summarize mission outcome, risk notes, and actions into a concise operational report.",
                "backstory": "You translate mission events into a clean post-flight narrative for operators and auditors.",
            },
        }

    def _has_llm_access(self) -> tuple[bool, str | None]:
        if os.getenv("RUNTIME_CREWAI_ENABLED", "1") in {"0", "false", "False"}:
            return False, "Runtime CrewAI disabled by environment"
        if not (os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")):
            return False, "LLM credentials unavailable"
        return True, None

    def _build_fallback(self, task_name: str, context: dict) -> RuntimeCrewDecision:
        agent_role = {
            "mission_opening": "Mission Supervisor",
            "takeoff_brief": "Safety Officer",
            "wind_early_warning": "Meteorology Agent",
            "battery_buffer": "Safety Officer",
            "gps_watch": "Telemetry Analyst",
            "emergency_decision": context.get("agent_role", "Mission Supervisor"),
            "landing_review": "Safety Officer",
            "mission_completed": "Report Writer",
        }[task_name]

        if task_name == "mission_opening":
            message = "Preflight telemetrisi, checklist ve hava penceresi birlikte izlenecek."
        elif task_name == "takeoff_brief":
            message = "Kalkis oncesi son GPS ve ruzgar degeriyle GO/NO-GO karari netlestirilmeli."
        elif task_name == "wind_early_warning":
            message = "Ruzgar artisi rota kisaltma veya erken inis penceresi hazirlanmasini gerektiriyor."
        elif task_name == "battery_buffer":
            message = "Batarya rezervi erken donus tamponunu etkiliyor; gorev suresi kisaltilabilir."
        elif task_name == "gps_watch":
            message = "GPS kalite dususu toleranslari daraltiyor; hold veya RTH hazir tutulmali."
        elif task_name == "emergency_decision":
            message = f"{context.get('emergency_type', 'acil durum')} icin {context.get('action', 'operasyon aksiyonu')} uygulanmali."
        elif task_name == "landing_review":
            message = "Inis sonrasi son emniyet kontrolu tamamlanmadan gorev kapatilmaz."
        else:
            message = "Gorev tamamlandi; risk notlari ve checklist sonucu rapora islenecek."

        return RuntimeCrewDecision(
            agent_role=agent_role,
            task_name=task_name,
            message=message,
            mode="fallback",
            fallback_reason="LLM unavailable -> fallback engaged",
        )

    def _run_with_crewai(self, agent_key: str, task_name: str, prompt: str, context: dict) -> RuntimeCrewDecision:
        from crewai import Agent, Crew, Process, Task

        spec = self._agent_specs[agent_key]
        agent = Agent(
            role=spec["role"],
            goal=spec["goal"],
            backstory=spec["backstory"],
            verbose=False,
            allow_delegation=False,
            llm=DEFAULT_MODEL,
        )
        task = Task(
            description=prompt + "\n\nMission context JSON:\n{context_json}",
            expected_output="One short operational paragraph with a recommendation.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
        result = crew.kickoff(inputs={"context_json": json.dumps(context, ensure_ascii=False)})
        return RuntimeCrewDecision(
            agent_role=spec["role"],
            task_name=task_name,
            message=str(result).strip(),
            mode="crewai",
        )

    def decide(self, task_name: str, context: dict) -> RuntimeCrewDecision:
        prompts = {
            "mission_opening": (
                "Summarize the mission opening in Turkish. Mention what the runtime agents will monitor first."
            ),
            "takeoff_brief": (
                "Evaluate takeoff readiness in Turkish using GPS, wind, checklist, and approvals. End with a clear recommendation."
            ),
            "wind_early_warning": (
                "Produce a short Turkish weather warning for a UAV mission and suggest two operational options."
            ),
            "battery_buffer": (
                "Produce a short Turkish battery reserve warning for a UAV mission and suggest a safe mission adjustment."
            ),
            "gps_watch": (
                "Produce a short Turkish GPS quality warning and describe the operational implication."
            ),
            "emergency_decision": (
                "Explain the emergency decision in Turkish, name the action, and state the immediate operational rationale."
            ),
            "landing_review": (
                "Write a short Turkish post-landing safety note for the operator."
            ),
            "mission_completed": (
                "Write a short Turkish mission completion summary including risk notes and checklist completion tone."
            ),
        }
        agent_keys = {
            "mission_opening": "mission_supervisor",
            "takeoff_brief": "safety_officer",
            "wind_early_warning": "meteorology_agent",
            "battery_buffer": "safety_officer",
            "gps_watch": "telemetry_analyst",
            "emergency_decision": "mission_supervisor",
            "landing_review": "safety_officer",
            "mission_completed": "report_writer",
        }

        enabled, reason = self._has_llm_access()
        if not enabled:
            decision = self._build_fallback(task_name, context)
            if reason:
                decision.fallback_reason = reason
            return decision

        try:
            return self._run_with_crewai(agent_keys[task_name], task_name, prompts[task_name], context)
        except Exception as exc:
            decision = self._build_fallback(task_name, context)
            decision.fallback_reason = f"LLM unavailable -> fallback engaged ({exc.__class__.__name__})"
            return decision
