from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request

from mission_runtime.reporting import build_mission_report
from mission_runtime.store import MissionStore

load_dotenv(override=True)


STATE_ORDER = [
    "draft",
    "preflight",
    "ready_for_takeoff",
    "in_flight",
    "rth",
    "landed",
    "postflight",
    "completed",
]


def runtime_base_dir() -> Path:
    if os.getenv("MISSION_DATA_DIR"):
        return Path(os.environ["MISSION_DATA_DIR"])
    if os.getenv("VERCEL"):
        return Path("/tmp/drone-mission-data")
    return Path("runtime_data")


def build_timeline(state: str) -> list[dict]:
    if state not in STATE_ORDER:
        state = "preflight"
    current_index = STATE_ORDER.index(state)
    timeline = []
    for index, name in enumerate(STATE_ORDER[1:]):
        order_index = index + 1
        if order_index < current_index:
            status = "done"
        elif order_index == current_index:
            status = "current"
        else:
            status = "upcoming"
        timeline.append({"state": name, "status": status})
    return timeline


def serialize_mission(supervisor) -> dict:
    payload = supervisor.to_api_payload()
    payload["timeline"] = build_timeline(supervisor.state)
    return payload


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["MISSION_STORE"] = MissionStore(runtime_base_dir())
    if test_config:
        app.config.update(test_config)
        if "MISSION_STORE" not in test_config:
            app.config["MISSION_STORE"] = MissionStore(runtime_base_dir())

    def mission_store() -> MissionStore:
        return app.config["MISSION_STORE"]

    @app.route("/")
    def index():
        return render_template_string(HTML_TEMPLATE)

    @app.route("/api/missions", methods=["POST"])
    def create_mission():
        payload = request.get_json(silent=True) or {}
        mission_name = payload.get("mission_name", "Demo Mission")
        mission = mission_store().create(mission_name)
        return jsonify(serialize_mission(mission))

    @app.route("/api/missions/active", methods=["GET"])
    def get_active_mission():
        mission = mission_store().get_active()
        if mission is None:
            return jsonify(None)
        return jsonify(serialize_mission(mission))

    @app.route("/api/missions/<mission_id>/step", methods=["POST"])
    def step_mission(mission_id: str):
        mission = mission_store().get(mission_id)
        if mission is None:
            return jsonify({"error": "Mission not found"}), 404
        event = mission.process_next_event()
        response = serialize_mission(mission)
        response["processed_event"] = event.to_dict() if event else None
        return jsonify(response)

    @app.route("/api/missions/<mission_id>/approve", methods=["POST"])
    def approve_mission_action(mission_id: str):
        mission = mission_store().get(mission_id)
        if mission is None:
            return jsonify({"error": "Mission not found"}), 404
        payload = request.get_json(force=True) or {}
        mission.approve_action(payload.get("action", ""), bool(payload.get("approved", False)))
        return jsonify(serialize_mission(mission))

    @app.route("/api/missions/<mission_id>/answer", methods=["POST"])
    def answer_mission_question(mission_id: str):
        mission = mission_store().get(mission_id)
        if mission is None:
            return jsonify({"error": "Mission not found"}), 404
        payload = request.get_json(force=True) or {}
        mission.answer_question(payload.get("question_id", ""), bool(payload.get("answer", False)))
        return jsonify(serialize_mission(mission))

    @app.route("/api/missions/<mission_id>/events", methods=["GET"])
    def mission_events(mission_id: str):
        mission = mission_store().get(mission_id)
        if mission is None:
            return jsonify({"error": "Mission not found"}), 404
        return jsonify({"mission_id": mission_id, "events": mission.event_log})

    @app.route("/api/missions/<mission_id>/report", methods=["GET"])
    def mission_report(mission_id: str):
        mission = mission_store().get(mission_id)
        if mission is None:
            return jsonify({"error": "Mission not found"}), 404
        return jsonify(build_mission_report(mission))

    return app


app = create_app()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drone Mission Supervisor</title>
    <style>
        :root {
            --bg: #0f1a20;
            --bg-soft: #15252d;
            --panel: rgba(20, 35, 43, 0.86);
            --border: rgba(162, 194, 207, 0.16);
            --text: #edf6f8;
            --muted: #90aab2;
            --accent: #f4b942;
            --success: #5ad09b;
            --warning: #ffb454;
            --danger: #ff7474;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "Avenir Next", "Segoe UI", sans-serif;
            background:
                radial-gradient(circle at top left, rgba(244, 185, 66, 0.15), transparent 30%),
                linear-gradient(180deg, #081217 0%, var(--bg) 100%);
            color: var(--text);
            min-height: 100vh;
        }
        .shell {
            max-width: 1380px;
            margin: 0 auto;
            padding: 28px 20px 40px;
        }
        .hero {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            align-items: end;
            margin-bottom: 24px;
        }
        .hero h1 {
            margin: 0;
            font-size: clamp(2rem, 4vw, 3.4rem);
            letter-spacing: -0.04em;
        }
        .hero p {
            margin: 10px 0 0;
            color: var(--muted);
            max-width: 760px;
        }
        .hero .badge {
            background: rgba(244, 185, 66, 0.12);
            color: var(--accent);
            border: 1px solid rgba(244, 185, 66, 0.24);
            border-radius: 999px;
            padding: 10px 14px;
            font-size: 0.9rem;
            white-space: nowrap;
        }
        .panel {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 22px;
            backdrop-filter: blur(16px);
            box-shadow: 0 22px 40px rgba(0, 0, 0, 0.24);
        }
        .start-panel {
            padding: 24px;
            display: flex;
            gap: 12px;
            align-items: center;
            margin-bottom: 20px;
        }
        .start-panel input {
            flex: 1;
            min-width: 220px;
            background: rgba(255, 255, 255, 0.03);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px 16px;
        }
        .btn {
            border: none;
            border-radius: 16px;
            padding: 12px 18px;
            font-weight: 700;
            cursor: pointer;
        }
        .btn-primary { background: var(--accent); color: #22180a; }
        .btn-secondary { background: rgba(255,255,255,0.08); color: var(--text); border: 1px solid var(--border); }
        .btn-danger { background: rgba(255,116,116,0.16); color: #ffd2d2; border: 1px solid rgba(255,116,116,0.3); }
        .grid {
            display: grid;
            grid-template-columns: 0.95fr 1.4fr 1fr;
            gap: 18px;
            align-items: start;
        }
        .card {
            padding: 20px;
        }
        .card h2, .card h3 {
            margin: 0 0 14px;
            font-size: 1.05rem;
            letter-spacing: -0.02em;
        }
        .timeline-item, .inbox-item, .question-item, .event-item, .check-item {
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 12px 14px;
            background: rgba(255,255,255,0.03);
            margin-bottom: 10px;
        }
        .timeline-item.done { border-color: rgba(90, 208, 155, 0.35); }
        .timeline-item.current { border-color: rgba(244, 185, 66, 0.4); background: rgba(244,185,66,0.08); }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .status-success { background: rgba(90, 208, 155, 0.14); color: var(--success); }
        .status-warning { background: rgba(255, 180, 84, 0.16); color: var(--warning); }
        .status-danger { background: rgba(255, 116, 116, 0.14); color: var(--danger); }
        .status-muted { background: rgba(255,255,255,0.06); color: var(--muted); }
        .telemetry-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 18px;
        }
        .metric {
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px;
            background: rgba(255,255,255,0.03);
        }
        .metric-label {
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .metric-value {
            margin-top: 8px;
            font-size: 1.35rem;
            font-weight: 800;
        }
        .section-label {
            margin: 18px 0 10px;
            color: var(--accent);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.78rem;
        }
        .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 16px;
        }
        .two-col {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
            margin-top: 18px;
        }
        .report {
            white-space: pre-wrap;
            color: var(--muted);
            font-size: 0.94rem;
        }
        .empty {
            color: var(--muted);
            border: 1px dashed var(--border);
            border-radius: 16px;
            padding: 16px;
        }
        @media (max-width: 1080px) {
            .grid, .two-col { grid-template-columns: 1fr; }
            .hero { flex-direction: column; align-items: start; }
        }
    </style>
</head>
<body>
    <div class="shell">
        <div class="hero">
            <div>
                <h1>Mission Supervisor Console</h1>
                <p>Checklist artik agent destekli ilerliyor. Telemetri log'u sirayla okunuyor, fiziksel kontroller operatore soruluyor ve kritik eylemler onay gerektiriyor.</p>
            </div>
            <div class="badge">Balanced Approval Mode</div>
        </div>

        <div class="panel start-panel">
            <input id="mission-name" value="Demo Mission" placeholder="Mission name">
            <button class="btn btn-primary" onclick="startMission()">Ornek Gorev Baslat</button>
            <button class="btn btn-secondary" onclick="loadActiveMission()">Aktif Gorevi Yenile</button>
        </div>

        <div class="grid">
            <div class="panel card">
                <h2>Mission Timeline</h2>
                <div id="timeline" class="empty">Aktif gorev yok.</div>
            </div>

            <div>
                <div class="panel card">
                    <h2>Telemetry + Auto Checklist</h2>
                    <div class="actions">
                        <button class="btn btn-primary" onclick="stepMission()">Siradaki Log Satirini Isle</button>
                        <button class="btn btn-secondary" onclick="loadMissionReport()">Raporu Yenile</button>
                    </div>
                    <div class="telemetry-grid" id="telemetry-grid"></div>
                    <div id="checklist-container" class="empty">Checklist bekleniyor.</div>
                </div>

                <div class="two-col">
                    <div class="panel card">
                        <h3>Agent Inbox</h3>
                        <div id="inbox" class="empty">Bekleyen aksiyon yok.</div>
                    </div>
                    <div class="panel card">
                        <h3>Mission Report</h3>
                        <div id="report" class="report">Rapor henuz uretilmedi.</div>
                    </div>
                </div>
            </div>

            <div class="panel card">
                <h2>Event Log</h2>
                <div id="event-log" class="empty">Event log bos.</div>
            </div>
        </div>
    </div>

    <script>
        let currentMission = null;

        async function api(url, options = {}) {
            const response = await fetch(url, options);
            return await response.json();
        }

        function statusClass(status) {
            if (["completed", "done", "approved"].includes(status)) return "status-success";
            if (["current", "pending"].includes(status)) return "status-warning";
            if (["failed", "rejected"].includes(status)) return "status-danger";
            return "status-muted";
        }

        function humanizeState(state) {
            const map = {
                preflight: "Preflight",
                ready_for_takeoff: "Takeoff Bekliyor",
                in_flight: "Ucus Sirasinda",
                rth: "RTH",
                landed: "Inis Tamamlandi",
                postflight: "Postflight",
                completed: "Tamamlandi"
            };
            return map[state] || state;
        }

        async function startMission() {
            const missionName = document.getElementById("mission-name").value || "Demo Mission";
            currentMission = await api("/api/missions", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({mission_name: missionName})
            });
            renderMission(currentMission);
            loadMissionReport();
        }

        async function loadActiveMission() {
            const mission = await api("/api/missions/active");
            if (!mission) {
                currentMission = null;
                renderMission(null);
                return;
            }
            currentMission = mission;
            renderMission(currentMission);
            loadMissionReport();
        }

        async function stepMission() {
            if (!currentMission) return;
            currentMission = await api(`/api/missions/${currentMission.mission_id}/step`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: "{}"
            });
            renderMission(currentMission);
            loadMissionReport();
        }

        async function approveAction(action, approved) {
            if (!currentMission) return;
            currentMission = await api(`/api/missions/${currentMission.mission_id}/approve`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({action, approved})
            });
            renderMission(currentMission);
            loadMissionReport();
        }

        async function answerQuestion(questionId, answer) {
            if (!currentMission) return;
            currentMission = await api(`/api/missions/${currentMission.mission_id}/answer`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({question_id: questionId, answer})
            });
            renderMission(currentMission);
            loadMissionReport();
        }

        async function loadMissionReport() {
            if (!currentMission) {
                document.getElementById("report").textContent = "Rapor henuz uretilmedi.";
                return;
            }
            const report = await api(`/api/missions/${currentMission.mission_id}/report`);
            const recommendations = (report.recommendations || []).length
                ? report.recommendations.map(item => `- ${item}`).join("\\n")
                : "- Ek onerisi yok.";
            document.getElementById("report").textContent =
                `Mission: ${report.mission_name}\\n` +
                `State: ${humanizeState(report.state)}\\n` +
                `Battery: ${report.telemetry_snapshot?.battery ?? "--"}\\n` +
                `GPS: ${report.telemetry_snapshot?.gps ?? "--"}\\n` +
                `Wind: ${report.telemetry_snapshot?.wind ?? "--"}\\n\\n` +
                `Oneriler\\n${recommendations}`;
        }

        function renderTimeline(mission) {
            const container = document.getElementById("timeline");
            if (!mission) {
                container.className = "empty";
                container.textContent = "Aktif gorev yok.";
                return;
            }
            container.className = "";
            container.innerHTML = mission.timeline.map(item => `
                <div class="timeline-item ${item.status}">
                    <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;">
                        <strong>${humanizeState(item.state)}</strong>
                        <span class="status-pill ${statusClass(item.status)}">${item.status}</span>
                    </div>
                </div>
            `).join("");
        }

        function renderTelemetry(mission) {
            const snapshot = mission?.telemetry_snapshot || {};
            const grid = document.getElementById("telemetry-grid");
            grid.innerHTML = [
                ["Mission State", humanizeState(mission?.state || "preflight")],
                ["Battery", snapshot.battery ?? "--"],
                ["GPS", snapshot.gps ?? "--"],
                ["Wind", snapshot.wind ?? "--"],
                ["Mode", snapshot.mode ?? "--"],
                ["Event", snapshot.event ?? "--"]
            ].map(([label, value]) => `
                <div class="metric">
                    <div class="metric-label">${label}</div>
                    <div class="metric-value">${value}</div>
                </div>
            `).join("");
        }

        function renderChecklist(mission) {
            const container = document.getElementById("checklist-container");
            if (!mission) {
                container.className = "empty";
                container.textContent = "Checklist bekleniyor.";
                return;
            }
            container.className = "";
            const sections = {};
            mission.checklist.forEach(item => {
                if (!sections[item.section]) sections[item.section] = [];
                sections[item.section].push(item);
            });
            container.innerHTML = Object.entries(sections).map(([section, items]) => `
                <div class="section-label">${section}</div>
                ${items.map(item => `
                    <div class="check-item">
                        <div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start;">
                            <div>
                                <strong>${item.label}</strong>
                                <div style="color:var(--muted);margin-top:6px;">${item.item_type} · ${item.source}</div>
                            </div>
                            <span class="status-pill ${statusClass(item.status)}">${item.status}</span>
                        </div>
                    </div>
                `).join("")}
            `).join("");
        }

        function renderInbox(mission) {
            const container = document.getElementById("inbox");
            if (!mission) {
                container.className = "empty";
                container.textContent = "Bekleyen aksiyon yok.";
                return;
            }

            const chunks = [];
            if (mission.pending_approval) {
                chunks.push(`
                    <div class="inbox-item">
                        <strong>Onay Bekleniyor</strong>
                        <div style="margin:8px 0 12px;">${mission.pending_approval.label || mission.pending_approval.action}</div>
                        <div class="actions">
                            <button class="btn btn-primary" onclick="approveAction('${mission.pending_approval.action}', true)">Onayla</button>
                            <button class="btn btn-danger" onclick="approveAction('${mission.pending_approval.action}', false)">Reddet</button>
                        </div>
                    </div>
                `);
            }
            (mission.pending_questions || []).forEach(question => {
                chunks.push(`
                    <div class="question-item">
                        <strong>Operator Sorusu</strong>
                        <div style="margin:8px 0 12px;">${question.label}</div>
                        <div class="actions">
                            <button class="btn btn-primary" onclick="answerQuestion('${question.question_id}', true)">Evet</button>
                            <button class="btn btn-danger" onclick="answerQuestion('${question.question_id}', false)">Hayir</button>
                        </div>
                    </div>
                `);
            });

            if (!chunks.length) {
                container.className = "empty";
                container.textContent = "Bekleyen soru veya onay yok.";
                return;
            }

            container.className = "";
            container.innerHTML = chunks.join("");
        }

        function renderEventLog(mission) {
            const container = document.getElementById("event-log");
            if (!mission || !mission.event_log.length) {
                container.className = "empty";
                container.textContent = "Event log bos.";
                return;
            }
            container.className = "";
            container.innerHTML = [...mission.event_log].reverse().map(entry => `
                <div class="event-item">
                    <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;">
                        <strong>${entry.event}</strong>
                        <span class="status-pill ${statusClass(entry.level === 'critical' ? 'failed' : (entry.level === 'warn' ? 'pending' : 'completed'))}">${entry.level}</span>
                    </div>
                    <div style="margin-top:8px;color:var(--muted);">${entry.message || ""}</div>
                </div>
            `).join("");
        }

        function renderMission(mission) {
            renderTimeline(mission);
            renderTelemetry(mission);
            renderChecklist(mission);
            renderInbox(mission);
            renderEventLog(mission);
        }

        window.onload = loadActiveMission;
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=True, host="0.0.0.0", port=port)
