from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from mission_runtime.reporting import build_mission_report
from mission_runtime.sample_log_generator import write_sample_telemetry_log
from mission_runtime.supervisor import MissionSupervisor


class MissionStore:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_dir / "missions.db"
        self._missions: dict[str, MissionSupervisor] = {}
        self._active_id: str | None = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    mission_name TEXT NOT NULL,
                    state TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    snapshot_json TEXT NOT NULL,
                    report_json TEXT,
                    completion_percentage INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    def _snapshot_for(self, supervisor: MissionSupervisor) -> dict:
        payload = supervisor.to_api_payload()
        payload["report"] = build_mission_report(supervisor)
        return payload

    def save(self, supervisor: MissionSupervisor) -> None:
        snapshot = self._snapshot_for(supervisor)
        summary = snapshot["history_summary"]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO missions (
                    mission_id,
                    mission_name,
                    state,
                    started_at,
                    ended_at,
                    snapshot_json,
                    report_json,
                    completion_percentage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_id) DO UPDATE SET
                    mission_name = excluded.mission_name,
                    state = excluded.state,
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    snapshot_json = excluded.snapshot_json,
                    report_json = excluded.report_json,
                    completion_percentage = excluded.completion_percentage
                """,
                (
                    supervisor.mission_id,
                    supervisor.mission_name,
                    supervisor.state,
                    supervisor.started_at,
                    supervisor.ended_at,
                    json.dumps(snapshot),
                    json.dumps(snapshot["report"]),
                    summary["completion_percentage"],
                ),
            )
        if supervisor.state == "completed" and self._active_id == supervisor.mission_id:
            self._active_id = None

    def create(self, mission_name: str, scenario_id: str = "survey_grid") -> MissionSupervisor:
        supervisor = MissionSupervisor.create(
            mission_name,
            self._build_log_path(mission_name, scenario_id),
            scenario_id=scenario_id,
        )
        self._missions[supervisor.mission_id] = supervisor
        self._active_id = supervisor.mission_id
        self.save(supervisor)
        return supervisor

    def _build_log_path(self, mission_name: str, scenario_id: str) -> Path:
        mission_key = mission_name.lower().replace(" ", "-")
        mission_dir = self.base_dir / mission_key
        mission_dir.mkdir(parents=True, exist_ok=True)
        log_path = mission_dir / "telemetry.log"
        write_sample_telemetry_log(log_path, scenario_id=scenario_id)
        return log_path

    def get(self, mission_id: str) -> MissionSupervisor | None:
        return self._missions.get(mission_id)

    def get_active(self) -> MissionSupervisor | None:
        if self._active_id is None:
            return None
        return self._missions.get(self._active_id)

    def history(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT mission_id, mission_name, state, started_at, ended_at, snapshot_json, completion_percentage
                FROM missions
                WHERE ended_at IS NOT NULL OR state = 'completed'
                ORDER BY COALESCE(ended_at, started_at) DESC
                """
            ).fetchall()

        history = []
        for row in rows:
            snapshot = json.loads(row["snapshot_json"])
            last_emergency = snapshot.get("last_emergency") or {}
            history.append(
                {
                    "mission_id": row["mission_id"],
                    "mission_name": row["mission_name"],
                    "scenario_id": snapshot.get("scenario_id"),
                    "scenario_label": snapshot.get("scenario_label"),
                    "state": row["state"],
                    "started_at": row["started_at"],
                    "ended_at": row["ended_at"],
                    "telemetry_snapshot": snapshot.get("telemetry_snapshot", {}),
                    "history_summary": snapshot.get("history_summary", {}),
                    "event_count": len(snapshot.get("event_log", [])),
                    "emergency_count": 1 if last_emergency else 0,
                    "latest_decision": last_emergency.get("action"),
                }
            )
        return history

    def detail(self, mission_id: str) -> dict | None:
        if mission_id in self._missions:
            return self._snapshot_for(self._missions[mission_id])

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot_json
                FROM missions
                WHERE mission_id = ?
                """,
                (mission_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["snapshot_json"])

    def delete(self, mission_id: str) -> bool:
        active = self._missions.get(mission_id)
        if active is not None and active.state != "completed":
            return False
        self._missions.pop(mission_id, None)
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM missions WHERE mission_id = ?", (mission_id,))
        return cursor.rowcount > 0
