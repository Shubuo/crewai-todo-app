# Mission Supervisor Runtime Design

**Date:** 2026-06-04

## Goal

Transform the current session-based drone checklist demo into a runtime mission system where a supervisor coordinates checklist progression, reads a sequential `telemetry.log`, auto-fills telemetry-backed checklist items, asks the operator only for physical confirmations, and requires operator approval for critical actions.

## Current Problems

- Build-time CrewAI and runtime behavior are mixed conceptually.
- The runtime "agent" mostly applies hard-coded rules inside a large Flask file.
- Telemetry is not replayable from an external source.
- The UI shows risk/demo concepts but not a proper mission workflow.
- FIPA logs are simulated rather than generated from real runtime events.

## Product Direction

The runtime should behave as a **mission supervisor** rather than a code generator or a free-form autonomous pilot.

Key behavior:
- The system owns mission progression.
- The system reads telemetry from `telemetry.log` sequentially.
- Telemetry-backed checklist items are auto-completed.
- Physical checks are asked to the operator.
- Critical actions require explicit approval.
- Every decision is written to an event log.
- A post-flight report summarizes mission behavior.

## Safety Model

Chosen approval level: **balanced approval**

- Auto-advance allowed:
  - mission setup
  - telemetry-backed checklist completion
  - normal checklist progression
- Explicit operator approval required:
  - takeoff
  - return to home (RTH)
  - emergency actions
  - landing

## Checklist Ownership Model

### Auto-filled by system

- weather within threshold
- battery threshold satisfied
- GPS lock available
- route loaded
- flight mode ready
- telemetry channel healthy

### Asked to operator

- propeller physical inspection
- area safety confirmation
- camera/lens visual confirmation
- payload mounting confirmation
- other visual/manual checks

### Reference only

- emergency procedures shown as guidance and triggered contextually

## Runtime State Machine

Mission states:

`draft -> preflight -> ready_for_takeoff -> in_flight -> emergency | rth -> landed -> postflight -> completed`

### State meanings

- `draft`: mission record exists but not initialized
- `preflight`: checklist and mission context are being prepared
- `ready_for_takeoff`: preflight is complete and takeoff approval is pending
- `in_flight`: telemetry replay is active and mission is progressing
- `emergency`: critical issue requires emergency procedure handling
- `rth`: controlled return-to-home flow is active
- `landed`: mission is on the ground and awaiting post-flight handling
- `postflight`: logs, evidence, and remaining checks are being processed
- `completed`: final report is available

## Telemetry Contract

The first implementation will use a replayable, line-oriented `telemetry.log` file.

Example format:

```text
ts=2026-06-04T20:00:00Z level=info event=mission_start battery=96 gps=15 wind=4.2 mode=ground
ts=2026-06-04T20:00:10Z level=info event=home_fix battery=96 gps=16 wind=4.3 mode=ground
ts=2026-06-04T20:00:20Z level=info event=route_loaded battery=95 gps=16 wind=4.5 mode=guided
ts=2026-06-04T20:01:00Z level=info event=takeoff battery=94 gps=17 wind=4.9 mode=guided
ts=2026-06-04T20:03:10Z level=warn event=wind_rise battery=89 gps=15 wind=10.6 mode=guided
ts=2026-06-04T20:03:20Z level=critical event=rth_recommended battery=88 gps=14 wind=11.2 mode=guided
ts=2026-06-04T20:04:00Z level=info event=landing battery=85 gps=14 wind=8.1 mode=land
```

Each line should be:
- parsed into a normalized telemetry event
- appended to the runtime event log
- evaluated against checklist rules
- used to generate approvals/questions if needed

## File Structure

### Runtime package

- `mission_runtime/models.py`
  - mission state structures
  - event records
  - checklist records
  - approval/question payloads
- `mission_runtime/log_reader.py`
  - sequential telemetry reader with cursor state
- `mission_runtime/sample_log_generator.py`
  - generates demo `telemetry.log`
- `mission_runtime/checklist_rules.py`
  - default mission checklist definitions
  - auto/manual/approval classification
  - event-to-checklist mapping
- `mission_runtime/supervisor.py`
  - mission orchestration
  - state transitions
  - question and approval generation
  - event log production
- `mission_runtime/reporting.py`
  - post-flight summary generation

### App surface

- `drone_checklist_app.py`
  - Flask app
  - API routes
  - new mission UI
  - integration with `mission_runtime`

### Tests

- `tests/test_log_reader.py`
- `tests/test_supervisor.py`
- `tests/test_reporting.py`

## API Direction

Primary runtime endpoints:

- `POST /api/missions`
- `GET /api/missions/active`
- `POST /api/missions/<id>/step`
- `POST /api/missions/<id>/approve`
- `POST /api/missions/<id>/answer`
- `GET /api/missions/<id>/events`
- `GET /api/missions/<id>/report`

The current session-based endpoints may remain temporarily for compatibility, but the UI should move to the mission endpoints.

## UI Direction

The main screen should be restructured into:

- `Mission Timeline`
  - current phase
  - completed phases
  - pending phase gates
- `Telemetry + Auto Checklist`
  - current telemetry snapshot
  - auto-completed items
  - pending manual items
  - mission status badges
- `Agent Inbox`
  - pending approvals
  - operator questions
  - supervisor summaries
- `Event Log`
  - chronological runtime decisions
  - telemetry observations
  - checklist updates
  - approval outcomes

## Report Output

The post-flight report should contain:

- mission status
- key timings
- final telemetry summary
- completed checklist items
- unanswered or failed checks
- triggered warnings or emergency events
- approvals requested and outcomes
- next-flight recommendations

## Non-Goals For This Phase

- real drone control integration
- live streaming telemetry ingestion
- multi-user collaboration
- complex storage migration
- fully autonomous action execution without approval

## Implementation Strategy

1. Add the runtime package behind tests.
2. Generate and replay a sample `telemetry.log`.
3. Move mission logic into the supervisor.
4. Replace the UI flow with mission-driven panels.
5. Add post-flight reporting.
6. Keep build-time CrewAI separate and intact.
