from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TelemetryEvent:
    ts: str
    level: str
    event: str
    battery: int | None = None
    gps: int | None = None
    wind: float | None = None
    mode: str | None = None
    raw: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChecklistItem:
    item_id: str
    section: str
    label: str
    item_type: str
    completed: bool = False
    status: str = "pending"
    source: str = "system"
    answer: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MissionQuestion:
    question_id: str
    label: str
    answer: bool | None = None
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MissionApproval:
    action: str
    label: str
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
