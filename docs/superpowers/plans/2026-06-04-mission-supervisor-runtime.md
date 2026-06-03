# Mission Supervisor Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runtime mission supervisor that replays a sample `telemetry.log`, auto-fills telemetry-backed checklist items, requests operator input for physical checks, gates critical actions with approvals, and exposes the new flow through the Flask UI.

**Architecture:** Add a focused `mission_runtime` package for state, log replay, checklist rules, supervision, and reporting. Keep build-time CrewAI files intact, and make `drone_checklist_app.py` a thinner integration layer that renders the new mission UI and calls runtime services.

**Tech Stack:** Python 3.12, Flask, SQLite, standard-library dataclasses, standard-library `unittest`, inline HTML/CSS/JS.

---

### Task 1: Guard the repo and document the design

**Files:**
- Modify: `.gitignore`
- Create: `docs/superpowers/specs/2026-06-04-mission-supervisor-design.md`
- Create: `docs/superpowers/plans/2026-06-04-mission-supervisor-runtime.md`

- [ ] **Step 1: Update ignore rules for local brainstorming artifacts**

```gitignore
.superpowers/
```

- [ ] **Step 2: Write the approved design spec**

Key sections to include:

```markdown
## Goal
## Safety Model
## Runtime State Machine
## Telemetry Contract
## File Structure
## API Direction
## UI Direction
```

- [ ] **Step 3: Save the implementation plan**

Run: `test -f docs/superpowers/plans/2026-06-04-mission-supervisor-runtime.md`
Expected: exit code `0`

- [ ] **Step 4: Commit**

```bash
git add .gitignore docs/superpowers/specs/2026-06-04-mission-supervisor-design.md docs/superpowers/plans/2026-06-04-mission-supervisor-runtime.md
git commit -m "docs: add mission supervisor design and plan"
```

### Task 2: Add failing tests for sequential log replay

**Files:**
- Create: `tests/test_log_reader.py`
- Test: `tests/test_log_reader.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from mission_runtime.log_reader import TelemetryLogReader


class TelemetryLogReaderTests(unittest.TestCase):
    def test_reads_events_sequentially(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "telemetry.log"
            log_path.write_text(
                "ts=2026-06-04T20:00:00Z level=info event=mission_start battery=96 gps=15 wind=4.2 mode=ground\n"
                "ts=2026-06-04T20:00:10Z level=info event=route_loaded battery=95 gps=16 wind=4.5 mode=guided\n",
                encoding="utf-8",
            )
            reader = TelemetryLogReader(log_path)

            first = reader.read_next()
            second = reader.read_next()
            third = reader.read_next()

            self.assertEqual(first.event, "mission_start")
            self.assertEqual(second.event, "route_loaded")
            self.assertIsNone(third)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_log_reader -v`
Expected: FAIL with `ModuleNotFoundError` or missing `TelemetryLogReader`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TelemetryEvent:
    event: str


class TelemetryLogReader:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lines = self.path.read_text(encoding="utf-8").splitlines()
        self._index = 0

    def read_next(self):
        if self._index >= len(self._lines):
            return None
        raw = self._lines[self._index]
        self._index += 1
        fields = dict(part.split("=", 1) for part in raw.split())
        return TelemetryEvent(event=fields["event"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_log_reader -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_log_reader.py mission_runtime/log_reader.py
git commit -m "test: add sequential telemetry log reader coverage"
```

### Task 3: Add failing tests for sample log generation

**Files:**
- Create: `tests/test_sample_log_generator.py`
- Create: `mission_runtime/sample_log_generator.py`
- Modify: `mission_runtime/log_reader.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from mission_runtime.sample_log_generator import write_sample_telemetry_log
from mission_runtime.log_reader import TelemetryLogReader


class SampleLogGeneratorTests(unittest.TestCase):
    def test_writes_a_replayable_log_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "telemetry.log"
            write_sample_telemetry_log(log_path)

            reader = TelemetryLogReader(log_path)
            events = []
            while True:
                event = reader.read_next()
                if event is None:
                    break
                events.append(event.event)

            self.assertIn("mission_start", events)
            self.assertIn("landing", events)
            self.assertGreaterEqual(len(events), 6)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_sample_log_generator -v`
Expected: FAIL with missing generator function

- [ ] **Step 3: Write minimal implementation**

```python
from pathlib import Path


def write_sample_telemetry_log(path: Path) -> Path:
    lines = [
        "ts=2026-06-04T20:00:00Z level=info event=mission_start battery=96 gps=15 wind=4.2 mode=ground",
        "ts=2026-06-04T20:00:10Z level=info event=home_fix battery=96 gps=16 wind=4.3 mode=ground",
        "ts=2026-06-04T20:00:20Z level=info event=route_loaded battery=95 gps=16 wind=4.5 mode=guided",
        "ts=2026-06-04T20:01:00Z level=info event=takeoff battery=94 gps=17 wind=4.9 mode=guided",
        "ts=2026-06-04T20:03:20Z level=critical event=rth_recommended battery=88 gps=14 wind=11.2 mode=guided",
        "ts=2026-06-04T20:04:00Z level=info event=landing battery=85 gps=14 wind=8.1 mode=land",
    ]
    output_path = Path(path)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_sample_log_generator -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_sample_log_generator.py mission_runtime/sample_log_generator.py
git commit -m "feat: add sample telemetry log generator"
```

### Task 4: Add failing tests for supervisor state and approvals

**Files:**
- Create: `tests/test_supervisor.py`
- Create: `mission_runtime/models.py`
- Create: `mission_runtime/checklist_rules.py`
- Create: `mission_runtime/supervisor.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from mission_runtime.sample_log_generator import write_sample_telemetry_log
from mission_runtime.supervisor import MissionSupervisor


class MissionSupervisorTests(unittest.TestCase):
    def test_preflight_requires_takeoff_approval_after_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "telemetry.log"
            write_sample_telemetry_log(log_path)
            supervisor = MissionSupervisor.create("Mission 1", log_path)

            supervisor.answer_question("propeller_check", True)
            supervisor.answer_question("area_check", True)
            supervisor.answer_question("camera_check", True)
            supervisor.process_next_event()
            supervisor.process_next_event()
            supervisor.process_next_event()

            self.assertEqual(supervisor.state, "ready_for_takeoff")
            self.assertEqual(supervisor.pending_approval["action"], "takeoff")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_supervisor -v`
Expected: FAIL with missing `MissionSupervisor`

- [ ] **Step 3: Write minimal implementation**

```python
class MissionSupervisor:
    @classmethod
    def create(cls, mission_name, log_path):
        return cls(mission_name, log_path)

    def __init__(self, mission_name, log_path):
        self.state = "preflight"
        self.pending_approval = None

    def answer_question(self, question_id, answer):
        return None

    def process_next_event(self):
        self.state = "ready_for_takeoff"
        self.pending_approval = {"action": "takeoff"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_supervisor -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_supervisor.py mission_runtime/models.py mission_runtime/checklist_rules.py mission_runtime/supervisor.py
git commit -m "test: add mission supervisor approval flow coverage"
```

### Task 5: Expand supervisor behavior for in-flight replay, RTH, and event log

**Files:**
- Modify: `tests/test_supervisor.py`
- Modify: `mission_runtime/log_reader.py`
- Modify: `mission_runtime/supervisor.py`
- Modify: `mission_runtime/checklist_rules.py`
- Modify: `mission_runtime/models.py`

- [ ] **Step 1: Write the failing test**

```python
def test_rth_event_creates_approval_request_and_event_log(self):
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "telemetry.log"
        write_sample_telemetry_log(log_path)
        supervisor = MissionSupervisor.create("Mission 1", log_path)

        supervisor.answer_question("propeller_check", True)
        supervisor.answer_question("area_check", True)
        supervisor.answer_question("camera_check", True)
        supervisor.process_next_event()
        supervisor.process_next_event()
        supervisor.process_next_event()
        supervisor.approve_action("takeoff", True)
        supervisor.process_next_event()
        supervisor.process_next_event()

        self.assertEqual(supervisor.state, "rth")
        self.assertEqual(supervisor.pending_approval["action"], "rth")
        self.assertTrue(any(entry["event"] == "rth_recommended" for entry in supervisor.event_log))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_supervisor -v`
Expected: FAIL because RTH logic is missing

- [ ] **Step 3: Write minimal implementation**

```python
def approve_action(self, action, approved):
    if approved and action == "takeoff":
        self.state = "in_flight"
        self.pending_approval = None

def process_next_event(self):
    event = self.reader.read_next()
    if event is None:
        return None
    self.event_log.append({"event": event.event, "level": event.level})
    if event.event == "rth_recommended":
        self.state = "rth"
        self.pending_approval = {"action": "rth"}
    return event
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_supervisor -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_supervisor.py mission_runtime/log_reader.py mission_runtime/supervisor.py mission_runtime/checklist_rules.py mission_runtime/models.py
git commit -m "feat: replay telemetry through mission supervisor"
```

### Task 6: Add failing tests for reporting

**Files:**
- Create: `tests/test_reporting.py`
- Create: `mission_runtime/reporting.py`
- Modify: `mission_runtime/supervisor.py`

- [ ] **Step 1: Write the failing test**

```python
import tempfile
import unittest
from pathlib import Path

from mission_runtime.reporting import build_mission_report
from mission_runtime.sample_log_generator import write_sample_telemetry_log
from mission_runtime.supervisor import MissionSupervisor


class MissionReportingTests(unittest.TestCase):
    def test_builds_summary_report_from_supervisor_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "telemetry.log"
            write_sample_telemetry_log(log_path)
            supervisor = MissionSupervisor.create("Mission 1", log_path)

            report = build_mission_report(supervisor)

            self.assertIn("mission_name", report)
            self.assertIn("state", report)
            self.assertIn("recommendations", report)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_reporting -v`
Expected: FAIL with missing report builder

- [ ] **Step 3: Write minimal implementation**

```python
def build_mission_report(supervisor):
    return {
        "mission_name": supervisor.mission_name,
        "state": supervisor.state,
        "recommendations": [],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_reporting -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_reporting.py mission_runtime/reporting.py mission_runtime/supervisor.py
git commit -m "feat: add mission reporting"
```

### Task 7: Replace Flask session flow with mission runtime APIs

**Files:**
- Modify: `drone_checklist_app.py`
- Test: `tests/test_supervisor.py`
- Test: `tests/test_reporting.py`

- [ ] **Step 1: Write the failing integration test**

```python
def test_mission_start_creates_runtime_payload(self):
    app = create_app({"TESTING": True})
    client = app.test_client()
    response = client.post("/api/missions", json={"mission_name": "Demo Mission"})
    self.assertEqual(response.status_code, 200)
    self.assertIn("mission_id", response.get_json())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest -v`
Expected: FAIL because mission API routes do not exist

- [ ] **Step 3: Write minimal implementation**

```python
@app.route("/api/missions", methods=["POST"])
def create_mission():
    payload = request.get_json(force=True) or {}
    mission_name = payload.get("mission_name", "Demo Mission")
    mission = mission_store.create(mission_name)
    return jsonify(mission.to_api_payload())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest -v`
Expected: PASS for the new route and existing runtime tests

- [ ] **Step 5: Commit**

```bash
git add drone_checklist_app.py
git commit -m "feat: wire flask app to mission runtime"
```

### Task 8: Redesign the UI around mission timeline, inbox, and event log

**Files:**
- Modify: `drone_checklist_app.py`

- [ ] **Step 1: Write the failing browser-level expectation as a smoke test note**

Expected UI blocks:

```text
Mission Timeline
Telemetry Snapshot
Auto Checklist
Agent Inbox
Event Log
Mission Report
```

- [ ] **Step 2: Implement the new template and client-side mission actions**

Key client functions:

```javascript
loadActiveMission()
stepMission()
approveAction(action, approved)
answerQuestion(questionId, answer)
loadMissionReport()
renderTimeline(data)
renderInbox(data)
renderEventLog(data)
```

- [ ] **Step 3: Run syntax verification**

Run: `python -m py_compile drone_checklist_app.py mission_runtime/*.py`
Expected: no output

- [ ] **Step 4: Manual verification**

Run: `PORT=5001 UV_CACHE_DIR=.uv-cache uv run python drone_checklist_app.py`
Expected: app starts and shows the new mission layout

- [ ] **Step 5: Commit**

```bash
git add drone_checklist_app.py
git commit -m "feat: redesign mission control ui"
```

### Task 9: Final verification, merge, and free hosting

**Files:**
- Modify: deployment files as needed (`requirements.txt`, `vercel.json`, or equivalent)

- [ ] **Step 1: Run full verification**

Run: `python -m unittest -v`
Expected: PASS

Run: `python -m py_compile drone_checklist_app.py mission_runtime/*.py`
Expected: no output

- [ ] **Step 2: Commit deployment configuration**

```bash
git add .
git commit -m "chore: prepare public deployment"
```

- [ ] **Step 3: Merge the working branch into main**

```bash
git checkout main
git merge --no-ff codex-repo-cleanup-openrouter-fix
```

- [ ] **Step 4: Deploy to a free host**

Preferred path:

```bash
vercel --prod
```

Fallback if Vercel is unavailable:

```bash
render blueprint or Cloudflare Pages/Workers setup
```

- [ ] **Step 5: Push main**

```bash
git push origin main
```
