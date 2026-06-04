from __future__ import annotations

import json
import os
import urllib.request
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


def weather_decision(wind: float, temperature: float) -> tuple[str, str]:
    if wind >= 12:
        return "NO-GO", f"Ruzgar {wind:.1f} m/s. Kalkis ertelenmeli."
    if wind >= 9:
        return "WARNING", f"Ruzgar {wind:.1f} m/s. Kalkis sinirda, operator teyidi gerekli."
    if temperature >= 38:
        return "WARNING", f"Sicaklik {temperature:.1f}°C. Batarya termal takibi onerilir."
    return "GO", f"Ruzgar {wind:.1f} m/s. Ucus kosullari uygun gorunuyor."


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

    @app.route("/api/missions/history", methods=["GET"])
    def mission_history():
        return jsonify(mission_store().history())

    @app.route("/api/missions/<mission_id>", methods=["GET"])
    def mission_detail(mission_id: str):
        detail = mission_store().detail(mission_id)
        if detail is None:
            return jsonify({"error": "Mission not found"}), 404
        if "timeline" not in detail:
            detail["timeline"] = build_timeline(detail.get("state", "preflight"))
        return jsonify(detail)

    @app.route("/api/missions/<mission_id>/step", methods=["POST"])
    def step_mission(mission_id: str):
        mission = mission_store().get(mission_id)
        if mission is None:
            return jsonify({"error": "Mission not found"}), 404
        event = mission.process_next_event()
        mission_store().save(mission)
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
        mission_store().save(mission)
        return jsonify(serialize_mission(mission))

    @app.route("/api/missions/<mission_id>/answer", methods=["POST"])
    def answer_mission_question(mission_id: str):
        mission = mission_store().get(mission_id)
        if mission is None:
            return jsonify({"error": "Mission not found"}), 404
        payload = request.get_json(force=True) or {}
        mission.answer_question(payload.get("question_id", ""), bool(payload.get("answer", False)))
        mission_store().save(mission)
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
            detail = mission_store().detail(mission_id)
            if detail is None:
                return jsonify({"error": "Mission not found"}), 404
            return jsonify(detail.get("report", {}))
        mission_store().save(mission)
        return jsonify(build_mission_report(mission))

    @app.route("/api/weather_advice", methods=["POST"])
    def weather_advice():
        data = request.get_json(force=True) or {}
        lat = data.get("lat")
        lon = data.get("lon")
        if lat is None or lon is None:
            return jsonify({"error": "lat ve lon gerekli"}), 400

        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                current = json.loads(response.read().decode()).get("current", {})
            temperature = float(current.get("temperature_2m", 26))
            wind = float(current.get("wind_speed_10m", 5))
        except Exception:
            temperature = 26.0
            wind = 5.0

        decision, advice = weather_decision(wind, temperature)
        return jsonify(
            {
                "temp": temperature,
                "wind": wind,
                "decision": decision,
                "advice": advice,
                "agent_role": "Meteorology Agent",
            }
        )

    return app


app = create_app()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Otonom IHA Komuta Merkezi</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <style>
        :root {
            --bg: #08131a;
            --panel: rgba(15, 30, 38, 0.86);
            --panel-soft: rgba(255, 255, 255, 0.03);
            --border: rgba(153, 197, 217, 0.16);
            --text: #eef7f8;
            --muted: #90acb6;
            --accent: #7ad7ff;
            --accent-strong: #2db8f6;
            --success: #58d59b;
            --warning: #ffbf63;
            --danger: #ff7a7a;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            background:
                radial-gradient(circle at top left, rgba(45, 184, 246, 0.15), transparent 28%),
                radial-gradient(circle at top right, rgba(122, 215, 255, 0.08), transparent 24%),
                linear-gradient(180deg, #041017 0%, #0a161d 100%);
            color: var(--text);
            font-family: "Avenir Next", "Segoe UI", sans-serif;
        }
        .shell {
            max-width: 1440px;
            margin: 0 auto;
            padding: 28px 20px 42px;
        }
        .hero {
            display: flex;
            justify-content: space-between;
            align-items: end;
            gap: 20px;
            margin-bottom: 22px;
        }
        .hero h1 {
            margin: 0;
            font-size: clamp(2rem, 4vw, 3.3rem);
            letter-spacing: -0.04em;
        }
        .hero .badge {
            padding: 10px 14px;
            border-radius: 999px;
            color: var(--accent);
            background: rgba(122, 215, 255, 0.1);
            border: 1px solid rgba(122, 215, 255, 0.2);
            white-space: nowrap;
        }
        .tabs {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 18px;
        }
        .tab {
            border: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.03);
            color: var(--muted);
            padding: 12px 18px;
            border-radius: 999px;
            font-weight: 700;
            cursor: pointer;
        }
        .tab.active {
            background: linear-gradient(135deg, rgba(45, 184, 246, 0.24), rgba(122, 215, 255, 0.14));
            color: var(--text);
            border-color: rgba(122, 215, 255, 0.35);
        }
        .panel {
            display: none;
        }
        .panel.active {
            display: block;
        }
        .card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 22px;
            backdrop-filter: blur(14px);
            box-shadow: 0 22px 46px rgba(0, 0, 0, 0.28);
            padding: 20px;
        }
        .card + .card {
            margin-top: 16px;
        }
        .start-panel {
            display: flex;
            gap: 12px;
            align-items: center;
            margin-bottom: 18px;
        }
        .start-panel input {
            flex: 1;
            min-width: 220px;
            border-radius: 16px;
            border: 1px solid var(--border);
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.04);
            color: var(--text);
        }
        .btn {
            border: none;
            border-radius: 14px;
            padding: 12px 16px;
            font-weight: 700;
            cursor: pointer;
        }
        .btn-primary {
            background: var(--accent-strong);
            color: #06202c;
        }
        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text);
            border: 1px solid var(--border);
        }
        .btn-danger {
            background: rgba(255, 122, 122, 0.15);
            color: #ffd4d4;
            border: 1px solid rgba(255, 122, 122, 0.26);
        }
        .section-title {
            margin: 0 0 12px;
            font-size: 1.05rem;
            letter-spacing: -0.02em;
        }
        .helper {
            color: var(--muted);
            margin: 0 0 14px;
            line-height: 1.45;
        }
        #map {
            height: 340px;
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid var(--border);
        }
        .layout {
            display: grid;
            grid-template-columns: 0.95fr 1.2fr 1fr;
            gap: 18px;
            align-items: start;
            margin-top: 18px;
        }
        .timeline-item, .compact-card, .check-item, .history-card, .fipa-entry {
            border-radius: 16px;
            border: 1px solid var(--border);
            background: var(--panel-soft);
        }
        .timeline-item, .compact-card, .check-item {
            padding: 12px 14px;
            margin-bottom: 10px;
        }
        .timeline-item.done { border-color: rgba(88, 213, 155, 0.25); }
        .timeline-item.current { border-color: rgba(122, 215, 255, 0.35); background: rgba(122, 215, 255, 0.08); }
        .pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 0.76rem;
            font-weight: 800;
        }
        .pill-success { background: rgba(88, 213, 155, 0.14); color: var(--success); }
        .pill-warning { background: rgba(255, 191, 99, 0.14); color: var(--warning); }
        .pill-danger { background: rgba(255, 122, 122, 0.14); color: var(--danger); }
        .pill-muted { background: rgba(255, 255, 255, 0.05); color: var(--muted); }
        .metrics {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }
        .metric {
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px;
            background: var(--panel-soft);
        }
        .metric-label {
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
        }
        .metric-value {
            margin-top: 8px;
            font-size: 1.35rem;
            font-weight: 800;
        }
        .section-label {
            margin: 18px 0 10px;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--accent);
            font-weight: 800;
        }
        .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .empty {
            border: 1px dashed var(--border);
            border-radius: 16px;
            color: var(--muted);
            padding: 16px;
        }
        .event-line {
            display: grid;
            grid-template-columns: 62px 1fr;
            gap: 10px;
            align-items: start;
            font-size: 0.92rem;
        }
        .event-line strong {
            color: var(--text);
        }
        .event-meta {
            color: var(--muted);
            margin-top: 4px;
            font-size: 0.84rem;
        }
        .history-card {
            padding: 16px;
            margin-bottom: 12px;
        }
        .history-head {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
            cursor: pointer;
        }
        .history-detail {
            display: none;
            margin-top: 14px;
            padding-top: 14px;
            border-top: 1px solid var(--border);
        }
        .history-detail.open {
            display: block;
        }
        .console-box {
            border-radius: 18px;
            padding: 16px;
            background: rgba(0, 0, 0, 0.28);
            border: 1px solid var(--border);
            min-height: 320px;
            max-height: 420px;
            overflow: auto;
            font-family: "SFMono-Regular", Consolas, monospace;
        }
        .fipa-entry {
            padding: 12px;
            margin-bottom: 10px;
        }
        .fipa-entry .sender { color: var(--accent); font-weight: 800; }
        .fipa-entry .receiver { color: var(--success); font-weight: 800; }
        .fipa-entry .performative { color: var(--warning); }
        .toast-wrap {
            position: fixed;
            top: 20px;
            right: 20px;
            width: min(360px, calc(100vw - 40px));
            z-index: 9999;
        }
        .toast {
            background: rgba(5, 17, 24, 0.96);
            border-left: 4px solid var(--accent);
            color: var(--text);
            padding: 14px 16px;
            border-radius: 14px;
            margin-bottom: 10px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.28);
        }
        @media (max-width: 1100px) {
            .layout, .metrics { grid-template-columns: 1fr; }
            .hero { flex-direction: column; align-items: start; }
            .start-panel { flex-direction: column; align-items: stretch; }
        }
    </style>
</head>
<body>
    <div class="toast-wrap" id="toast-wrap"></div>
    <div class="shell">
        <div class="hero">
            <div>
                <h1>Otonom IHA Komuta Merkezi</h1>
            </div>
            <div class="badge">Balanced Approval Mode</div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="switchTab(event, 'tab-active')">Ana Komuta Ekrani</button>
            <button class="tab" onclick="switchTab(event, 'tab-fipa')">FIPA Ajan Simulasyonu</button>
            <button class="tab" onclick="switchTab(event, 'tab-history')">Ucus Gecmisi</button>
        </div>

        <div id="tab-active" class="panel active">
            <div class="card">
                <h2 class="section-title">Interaktif Harita & Meteoroloji Ajani</h2>
                <p class="helper">Haritada herhangi bir noktaya tiklayarak gercek zamanli ruzgar ve otonom risk analizini goruntuleyin. Gorev replay sirasinda drone marker ayni harita ustunde hareket eder.</p>
                <div id="map"></div>
            </div>

            <div class="card start-panel">
                <input id="mission-name" value="Demo Mission" placeholder="Mission name">
                <button class="btn btn-primary" onclick="startMission()">Gorevi Baslat</button>
                <button class="btn btn-secondary" onclick="loadActiveMission()">Aktif Gorevi Yenile</button>
                <button class="btn btn-secondary" onclick="primePreflight()">Preflight Telemetrisi Yukle</button>
            </div>

            <div class="layout">
                <div>
                    <div class="card">
                        <h2 class="section-title">Mission Timeline</h2>
                        <div id="timeline" class="empty">Aktif gorev yok.</div>
                    </div>
                    <div class="card">
                        <h2 class="section-title">Agent Inbox</h2>
                        <div id="inbox" class="empty">Bekleyen aksiyon yok.</div>
                    </div>
                </div>

                <div>
                    <div class="card">
                        <h2 class="section-title">Telemetry + Checklist</h2>
                        <div class="actions" style="margin-bottom: 14px;">
                            <button class="btn btn-primary" onclick="stepMission(true)">Siradaki Log Satirini Isle</button>
                        </div>
                        <div id="telemetry-grid" class="metrics"></div>
                        <div class="card" style="padding: 16px; margin: 0 0 14px; background: rgba(255,255,255,0.02);">
                            <h3 class="section-title" style="margin-bottom: 8px;">Otonom Risk ve Ucus Analizi</h3>
                            <div id="risk-panel" class="helper">Risk analizi bekleniyor.</div>
                        </div>
                        <div id="checklist-container" class="empty">Checklist bekleniyor.</div>
                    </div>
                </div>

                <div>
                    <div class="card">
                        <h2 class="section-title">Mission Report</h2>
                        <div id="report" class="helper">Rapor henuz uretilmedi.</div>
                    </div>
                    <div class="card">
                        <h2 class="section-title">Event Log</h2>
                        <div id="event-log" class="empty">Event log bos.</div>
                    </div>
                </div>
            </div>
        </div>

        <div id="tab-fipa" class="panel">
            <div class="card">
                <h2 class="section-title">FIPA-ACL Ajan Iletisim Simulasyonu</h2>
                <p class="helper">Koordinator, risk analiz ve raporlama ajanlari arasindaki ornek mesajlasma akisi.</p>
                <button class="btn btn-primary" onclick="startFipaSimulation()" style="margin-bottom: 14px;">Simulasyonu Baslat</button>
                <div id="agent-log" class="console-box">> Sistem beklemede...</div>
            </div>
        </div>

        <div id="tab-history" class="panel">
            <div class="card">
                <h2 class="section-title">Ucus Gecmisi</h2>
                <p class="helper">Tamamlanan gorevler SQLite snapshot'larindan okunur.</p>
                <button class="btn btn-primary" onclick="loadHistory()" style="margin-bottom: 14px;">Yenile</button>
                <div id="history-container" class="empty">Kayitli gorev yok.</div>
            </div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let currentMission = null;
        let map = null;
        let weatherMarker = null;
        let droneMarker = null;
        let replayTimer = null;

        function showToast(message, type = "info") {
            const wrap = document.getElementById("toast-wrap");
            const toast = document.createElement("div");
            toast.className = "toast";
            if (type === "warning") toast.style.borderLeftColor = "var(--warning)";
            if (type === "danger") toast.style.borderLeftColor = "var(--danger)";
            if (type === "success") toast.style.borderLeftColor = "var(--success)";
            toast.innerHTML = message;
            wrap.appendChild(toast);
            setTimeout(() => toast.remove(), 4200);
        }

        function switchTab(event, tabId) {
            document.querySelectorAll(".panel").forEach(panel => panel.classList.remove("active"));
            document.querySelectorAll(".tab").forEach(tab => tab.classList.remove("active"));
            document.getElementById(tabId).classList.add("active");
            event.target.classList.add("active");
            if (map) {
                setTimeout(() => map.invalidateSize(), 100);
            }
        }

        async function api(url, options = {}) {
            const response = await fetch(url, options);
            return await response.json();
        }

        function statusClass(status) {
            if (["completed", "done", "approved", "GO"].includes(status)) return "pill-success";
            if (["current", "pending", "WARNING"].includes(status)) return "pill-warning";
            if (["failed", "rejected", "NO-GO"].includes(status)) return "pill-danger";
            return "pill-muted";
        }

        function humanizeState(state) {
            const map = {
                preflight: "Preflight",
                ready_for_takeoff: "Takeoff Bekliyor",
                in_flight: "Ucus Sirasinda",
                rth: "RTH",
                landed: "Inis Noktasinda",
                postflight: "Postflight",
                completed: "Tamamlandi"
            };
            return map[state] || state;
        }

        function formatTime(value) {
            if (!value) return "--";
            return new Date(value).toLocaleString("tr-TR");
        }

        function stopReplayLoop() {
            if (replayTimer) {
                clearTimeout(replayTimer);
                replayTimer = null;
            }
        }

        function buildDroneIcon(heading = 0) {
            return L.divIcon({
                html: `<div style="font-size:30px;color:var(--accent);text-shadow:0 0 10px rgba(122,215,255,0.7);transform: rotate(${heading - 45}deg);line-height:1;">➤</div>`,
                className: "",
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });
        }

        function initMap() {
            map = L.map("map").setView([38.42, 27.14], 12);
            L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
                attribution: "&copy; OpenStreetMap contributors &copy; CARTO"
            }).addTo(map);

            map.on("click", async function(e) {
                const lat = e.latlng.lat;
                const lon = e.latlng.lng;
                if (weatherMarker) {
                    map.removeLayer(weatherMarker);
                }
                weatherMarker = L.marker([lat, lon]).addTo(map)
                    .bindPopup("<b>Meteorology Agent</b><br>Analiz ediliyor...")
                    .openPopup();

                const res = await api("/api/weather_advice", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({lat, lon})
                });
                if (res.error) {
                    weatherMarker.bindPopup(`<b>Hata</b><br>${res.error}`).openPopup();
                    return;
                }
                const color = res.decision === "GO" ? "#58d59b" : (res.decision === "WARNING" ? "#ffbf63" : "#ff7a7a");
                weatherMarker.bindPopup(`
                    <div style="font-size:14px;line-height:1.45;">
                        <strong>Meteorology Agent</strong><br>
                        Sicaklik: ${res.temp}°C<br>
                        Ruzgar: ${res.wind} m/s<br>
                        <strong style="color:${color};">${res.decision}</strong><br>
                        ${res.advice}
                    </div>
                `).openPopup();
            });
        }

        function updateDroneMarker(mission) {
            if (!map || !mission || !mission.map_position) return;
            const pos = mission.map_position;
            const latLng = [pos.lat || 38.42, pos.lon || 27.14];
            const icon = buildDroneIcon(pos.heading || 0);
            if (!droneMarker) {
                droneMarker = L.marker(latLng, {icon}).addTo(map);
            } else {
                droneMarker.setLatLng(latLng);
                droneMarker.setIcon(icon);
            }
            droneMarker.bindPopup(`
                <strong>Drone Replay</strong><br>
                State: ${humanizeState(mission.state)}<br>
                Replay: ${mission.replay_status}<br>
                Altitude: ${pos.altitude ?? 0}m
            `);
            if (mission.replay_status === "flying" || mission.state === "landed") {
                map.panTo(latLng, {animate: true});
            }
        }

        async function startMission() {
            const missionName = document.getElementById("mission-name").value || "Demo Mission";
            currentMission = await api("/api/missions", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({mission_name: missionName})
            });
            renderMission(currentMission);
            await primePreflight();
            await loadMissionReport();
            loadHistory();
            showToast("<b>Mission Supervisor:</b> Gorev hazirlandi. Preflight telemetrisi okunuyor.", "success");
        }

        async function loadActiveMission() {
            const mission = await api("/api/missions/active");
            currentMission = mission || null;
            renderMission(currentMission);
            if (currentMission) {
                await loadMissionReport();
                maybeContinueReplay();
            }
        }

        async function primePreflight() {
            if (!currentMission) return;
            const autoEvents = ["mission_start", "home_fix", "route_loaded", "telemetry_ok"];
            for (let index = 0; index < autoEvents.length; index += 1) {
                if (currentMission.pending_approval) break;
                currentMission = await api(`/api/missions/${currentMission.mission_id}/step`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: "{}"
                });
            }
            renderMission(currentMission);
            await loadMissionReport();
        }

        async function stepMission(manual = false) {
            if (!currentMission) return;
            currentMission = await api(`/api/missions/${currentMission.mission_id}/step`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: "{}"
            });
            renderMission(currentMission);
            await loadMissionReport();
            if (manual && currentMission.processed_event) {
                showToast(`<b>Telemetry Analyst:</b> ${currentMission.processed_event.event} islendi.`);
            }
            maybeContinueReplay();
            if (currentMission.state === "completed") {
                loadHistory();
                showToast("<b>Report Writer:</b> Gorev tamamlandi ve gecmise kaydedildi.", "success");
            }
        }

        async function approveAction(action, approved) {
            if (!currentMission) return;
            currentMission = await api(`/api/missions/${currentMission.mission_id}/approve`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({action, approved})
            });
            renderMission(currentMission);
            await loadMissionReport();
            if (action === "takeoff" && approved) {
                showToast("<b>Mission Supervisor:</b> Kalkis onayi alindi, replay basliyor.", "success");
                maybeContinueReplay();
            } else if (action === "landing" && approved) {
                showToast("<b>Report Writer:</b> Inis onaylandi, gorev raporlaniyor.", "success");
                stopReplayLoop();
                loadHistory();
            }
        }

        async function answerQuestion(questionId, answer) {
            if (!currentMission) return;
            currentMission = await api(`/api/missions/${currentMission.mission_id}/answer`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({question_id: questionId, answer})
            });
            renderMission(currentMission);
            await loadMissionReport();
        }

        async function loadMissionReport() {
            if (!currentMission) {
                document.getElementById("report").textContent = "Rapor henuz uretilmedi.";
                return;
            }
            const report = await api(`/api/missions/${currentMission.mission_id}/report`);
            const recommendations = (report.recommendations || []).length
                ? report.recommendations.map(item => `- ${item}`).join("<br>")
                : "- Ek onerisi yok.";
            const riskNotes = (report.risk_summary?.notes || []).map(item => `- ${item}`).join("<br>");
            document.getElementById("report").innerHTML =
                `<strong>${report.mission_name}</strong><br>` +
                `State: ${humanizeState(report.state)}<br>` +
                `Baslangic: ${formatTime(report.started_at)}<br>` +
                `Bitis: ${formatTime(report.ended_at)}<br>` +
                `Replay: ${report.replay_status || "--"}<br><br>` +
                `<strong>Risk Ozeti</strong><br>${riskNotes || "- Veri yok."}<br><br>` +
                `<strong>Oneriler</strong><br>${recommendations}`;
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
                        <span class="pill ${statusClass(item.status)}">${item.status}</span>
                    </div>
                </div>
            `).join("");
        }

        function renderTelemetry(mission) {
            const grid = document.getElementById("telemetry-grid");
            const snapshot = mission?.telemetry_snapshot || {};
            const replay = mission?.replay_status || "--";
            grid.innerHTML = [
                ["Mission State", humanizeState(mission?.state || "preflight")],
                ["Replay", replay],
                ["Battery", snapshot.battery ?? "--"],
                ["GPS", snapshot.gps ?? "--"],
                ["Wind", snapshot.wind ?? "--"],
                ["Mode", snapshot.mode ?? "--"],
                ["Event", snapshot.event ?? "--"],
                ["Altitude", snapshot.altitude ?? "--"]
            ].map(([label, value]) => `
                <div class="metric">
                    <div class="metric-label">${label}</div>
                    <div class="metric-value">${value}</div>
                </div>
            `).join("");
        }

        function renderRisk(mission) {
            const container = document.getElementById("risk-panel");
            if (!mission) {
                container.textContent = "Risk analizi bekleniyor.";
                return;
            }
            const status = mission.risk_summary?.status || "--";
            const notes = mission.risk_summary?.notes || [];
            container.innerHTML =
                `<span class="pill ${statusClass(status)}">${status}</span>` +
                `<div style="margin-top:10px;">${notes.map(item => `- ${item}`).join("<br>")}</div>`;
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
                                <div class="event-meta">${item.item_type} · ${item.source}</div>
                            </div>
                            <span class="pill ${statusClass(item.status)}">${item.status}</span>
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
                    <div class="compact-card">
                        <strong>Onay Bekleniyor</strong>
                        <div class="event-meta">${mission.pending_approval.label || mission.pending_approval.action}</div>
                        <div class="actions" style="margin-top:10px;">
                            <button class="btn btn-primary" onclick="approveAction('${mission.pending_approval.action}', true)">Onayla</button>
                            <button class="btn btn-danger" onclick="approveAction('${mission.pending_approval.action}', false)">Reddet</button>
                        </div>
                    </div>
                `);
            }
            (mission.pending_questions || []).forEach(question => {
                chunks.push(`
                    <div class="compact-card">
                        <strong>Operator Sorusu</strong>
                        <div class="event-meta">${question.label}</div>
                        <div class="actions" style="margin-top:10px;">
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
            if (!mission || !mission.event_log?.length) {
                container.className = "empty";
                container.textContent = "Event log bos.";
                return;
            }
            container.className = "";
            container.innerHTML = [...mission.event_log].reverse().map(entry => {
                const time = entry.timestamp ? entry.timestamp.slice(11, 16) : "--:--";
                const result = entry.result ? `<div class="event-meta">${entry.result}</div>` : "";
                return `
                    <div class="compact-card">
                        <div class="event-line">
                            <div><span class="pill ${statusClass(entry.level === "warn" ? "WARNING" : "GO")}">${time}</span></div>
                            <div>
                                <strong>${entry.agent_role}</strong> · ${entry.event_type}
                                <div>${entry.summary}</div>
                                ${result}
                            </div>
                        </div>
                    </div>
                `;
            }).join("");
        }

        function renderMission(mission) {
            renderTimeline(mission);
            renderTelemetry(mission);
            renderRisk(mission);
            renderChecklist(mission);
            renderInbox(mission);
            renderEventLog(mission);
            updateDroneMarker(mission);
        }

        function maybeContinueReplay() {
            if (!currentMission) {
                stopReplayLoop();
                return;
            }
            if (currentMission.replay_status !== "flying" || currentMission.pending_approval) {
                stopReplayLoop();
                return;
            }
            if (replayTimer) return;
            replayTimer = setTimeout(async () => {
                replayTimer = null;
                await stepMission(false);
            }, 1200);
        }

        function addFipaLog(sender, receiver, performative, content) {
            const consoleEl = document.getElementById("agent-log");
            const entry = document.createElement("div");
            entry.className = "fipa-entry";
            entry.innerHTML = `
                <div><span class="sender">${sender}</span> → <span class="receiver">${receiver}</span> [<span class="performative">${performative}</span>]</div>
                <div style="margin-top:8px;">${content}</div>
            `;
            consoleEl.appendChild(entry);
            consoleEl.scrollTop = consoleEl.scrollHeight;
        }

        function startFipaSimulation() {
            const consoleEl = document.getElementById("agent-log");
            consoleEl.innerHTML = "";
            const messages = [
                ["Coordinator_Agent", "Risk_Assessor", "REQUEST", "Batarya ve hava durumunu mission replay oncesi degerlendir."],
                ["Risk_Assessor", "Coordinator_Agent", "AGREE", "Telemetri ve checklist sinyalleri okunuyor."],
                ["Risk_Assessor", "Flight_Advisor", "INFORM", "Ruzgar stabil, GPS lock hazir, takeoff approval bekleniyor."],
                ["Flight_Advisor", "Coordinator_Agent", "PROPOSE", "Takeoff verilebilir, rota replay modunda izlenebilir."],
                ["Coordinator_Agent", "Report_Writer", "REQUEST", "Olaylari compact log formatinda sakla."],
                ["Report_Writer", "Coordinator_Agent", "INFORM", "Gorev iletişim izi kaydedildi."]
            ];
            messages.forEach((item, index) => {
                setTimeout(() => addFipaLog(item[0], item[1], item[2], item[3]), 900 * (index + 1));
            });
        }

        async function loadHistory() {
            const history = await api("/api/missions/history");
            const container = document.getElementById("history-container");
            if (!history.length) {
                container.className = "empty";
                container.textContent = "Kayitli gorev yok.";
                return;
            }
            container.className = "";
            container.innerHTML = history.map(item => `
                <div class="history-card">
                    <div class="history-head" onclick="toggleHistoryDetails('${item.mission_id}')">
                        <div>
                            <strong>${item.mission_name}</strong>
                            <div class="event-meta">${formatTime(item.started_at)}${item.ended_at ? ` → ${formatTime(item.ended_at)}` : ""}</div>
                        </div>
                        <span class="pill ${statusClass(item.state === "completed" ? "GO" : "WARNING")}">${humanizeState(item.state)}</span>
                    </div>
                    <div class="history-detail" id="history-detail-${item.mission_id}">
                        <div class="event-meta">Checklist: ${item.history_summary?.completed_count || 0} / ${item.history_summary?.total_count || 0} · %${item.history_summary?.completion_percentage || 0}</div>
                        <div class="event-meta">Son telemetri: Batarya ${item.telemetry_snapshot?.battery ?? "--"} · GPS ${item.telemetry_snapshot?.gps ?? "--"} · Ruzgar ${item.telemetry_snapshot?.wind ?? "--"}</div>
                        <div class="event-meta">Event sayisi: ${item.event_count}</div>
                        <div id="history-payload-${item.mission_id}" style="margin-top:10px;"></div>
                    </div>
                </div>
            `).join("");
        }

        async function toggleHistoryDetails(missionId) {
            const detailEl = document.getElementById(`history-detail-${missionId}`);
            detailEl.classList.toggle("open");
            if (!detailEl.classList.contains("open")) return;
            const payloadEl = document.getElementById(`history-payload-${missionId}`);
            if (payloadEl.dataset.loaded === "1") return;
            const detail = await api(`/api/missions/${missionId}`);
            const checklist = detail.checklist || [];
            payloadEl.innerHTML = `
                <div class="section-label">Final Checklist</div>
                ${checklist.map(item => `
                    <div class="check-item" style="margin-bottom:8px;">
                        <div style="display:flex;justify-content:space-between;gap:10px;">
                            <span>${item.label}</span>
                            <span class="pill ${statusClass(item.status)}">${item.status}</span>
                        </div>
                    </div>
                `).join("")}
            `;
            payloadEl.dataset.loaded = "1";
        }

        window.onload = () => {
            initMap();
            loadActiveMission();
            loadHistory();
        };
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=True, host="0.0.0.0", port=port)
