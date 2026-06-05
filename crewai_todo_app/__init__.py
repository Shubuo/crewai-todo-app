"""Compatibility shim for local imports and console scripts.

This keeps `crewai_todo_app` importable from the repository root while the
source of truth remains under `src/crewai_todo_app`.
"""

from pathlib import Path

_SOURCE_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "crewai_todo_app"
if _SOURCE_PACKAGE.exists():
    __path__.append(str(_SOURCE_PACKAGE))
