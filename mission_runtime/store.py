from __future__ import annotations

from pathlib import Path

from mission_runtime.sample_log_generator import write_sample_telemetry_log
from mission_runtime.supervisor import MissionSupervisor


class MissionStore:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._missions: dict[str, MissionSupervisor] = {}
        self._active_id: str | None = None

    def create(self, mission_name: str) -> MissionSupervisor:
        mission_dir = self.base_dir / mission_name.lower().replace(" ", "-")
        mission_dir.mkdir(parents=True, exist_ok=True)
        log_path = mission_dir / "telemetry.log"
        write_sample_telemetry_log(log_path)
        supervisor = MissionSupervisor.create(mission_name, log_path)
        self._missions[supervisor.mission_id] = supervisor
        self._active_id = supervisor.mission_id
        return supervisor

    def get(self, mission_id: str) -> MissionSupervisor | None:
        return self._missions.get(mission_id)

    def get_active(self) -> MissionSupervisor | None:
        if self._active_id is None:
            return None
        return self._missions.get(self._active_id)
