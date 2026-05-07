import os
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, render_template_string, request

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "drone_checklist.db"
app = Flask(__name__)

CATEGORY_LABELS = {
    "ortam_kontrolu": "Ortam Kontrolu",
    "ucus_oncesi": "Ucus Oncesi",
    "ucus_sirasinda": "Ucus Sirasinda",
    "acil_durum_prosedurleri": "Acil Durum Prosedurleri",
    "ucus_sonrasi": "Ucus Sonrasi",
}

CHECKLIST_CATEGORIES = [
    "ortam_kontrolu",
    "ucus_oncesi",
    "ucus_sirasinda",
    "ucus_sonrasi",
]

SEED_TEMPLATES = [
    ("ortam_kontrolu", "Hava durumu uygun", 1, 1, 0),
    ("ortam_kontrolu", "Ruzgar sinirlar icinde", 2, 1, 0),
    ("ortam_kontrolu", "Yagis yok", 3, 1, 0),
    ("ortam_kontrolu", "Gorus yeterli", 4, 1, 0),
    ("ortam_kontrolu", "GPS kosullari uygun", 5, 1, 0),
    ("ortam_kontrolu", "Ucus alani yasal olarak uygun", 6, 1, 0),
    ("ortam_kontrolu", "Cevresel engeller kontrol edildi", 7, 1, 0),
    ("ortam_kontrolu", "Insan ve arac yogunlugu degerlendirildi", 8, 1, 0),
    ("ucus_oncesi", "Batarya seviyesi yeterli", 1, 1, 0),
    ("ucus_oncesi", "Kumanda baglantisi tamam", 2, 1, 0),
    ("ucus_oncesi", "Pervaneler saglam", 3, 1, 0),
    ("ucus_oncesi", "Govde ve motorlar kontrol edildi", 4, 1, 0),
    ("ucus_oncesi", "SD kart takili", 5, 0, 0),
    ("ucus_oncesi", "Kamera kontrol edildi", 6, 0, 0),
    ("ucus_oncesi", "IMU ve pusula durumu uygun", 7, 1, 0),
    ("ucus_oncesi", "Kalkis alani guvenli", 8, 1, 0),
    ("ucus_oncesi", "Acil durum prosedurleri gozden gecirildi", 9, 1, 0),
    ("ucus_sirasinda", "Batarya seviyesi izleniyor", 1, 1, 0),
    ("ucus_sirasinda", "Sinyal gucu izleniyor", 2, 1, 0),
    ("ucus_sirasinda", "Gorus hatti korunuyor", 3, 1, 0),
    ("ucus_sirasinda", "Irtifa ve mesafe sinirlari izleniyor", 4, 1, 0),
    ("ucus_sirasinda", "Cevresel riskler takip ediliyor", 5, 1, 0),
    ("ucus_sonrasi", "Motorlar kapatildi", 1, 1, 0),
    ("ucus_sonrasi", "Batarya cikarildi", 2, 1, 0),
    ("ucus_sonrasi", "Govde hasar kontrolu yapildi", 3, 1, 0),
    ("ucus_sonrasi", "Ucus notu alindi", 4, 0, 0),
    ("ucus_sonrasi", "Medya yedeklendi", 5, 0, 0),
    ("ucus_sonrasi", "Ekipman toplandi", 6, 1, 0),
    ("acil_durum_prosedurleri", "Sinyal kaybinda eve donus prosedurunu uygula", 1, 0, 1),
    ("acil_durum_prosedurleri", "Dusuk bataryada guvenli donus veya inis karari ver", 2, 0, 1),
    ("acil_durum_prosedurleri", "Kontrol kaybinda guvenli inis alani sec", 3, 0, 1),
    ("acil_durum_prosedurleri", "Ani hava degisiminde gorevi iptal et ve geri don", 4, 0, 1),
    ("acil_durum_prosedurleri", "Motor veya pervane anomalisinde ucusu sonlandir", 5, 0, 1),
]

ORDER_BY_CATEGORY_SQL = """
CASE category
    WHEN 'ortam_kontrolu' THEN 1
    WHEN 'ucus_oncesi' THEN 2
    WHEN 'ucus_sirasinda' THEN 3
    WHEN 'acil_durum_prosedurleri' THEN 4
    WHEN 'ucus_sonrasi' THEN 5
    ELSE 99
END
"""


def get_db():
    """Return the SQLite connection for the current request context."""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    """Close the database connection at the end of the request."""
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def get_json_payload():
    """Return a JSON object payload or None when the request body is invalid."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def init_db():
    """Create tables and seed the default checklist templates."""
    with app.app_context():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS checklist_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                required INTEGER NOT NULL DEFAULT 0 CHECK (required IN (0, 1)),
                is_reference_only INTEGER NOT NULL DEFAULT 0 CHECK (is_reference_only IN (0, 1))
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS flight_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS session_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                template_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                required INTEGER NOT NULL DEFAULT 0 CHECK (required IN (0, 1)),
                completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
                completed_at TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES flight_sessions (id),
                FOREIGN KEY (template_id) REFERENCES checklist_templates (id)
            )
            """
        )

        template_count = db.execute("SELECT COUNT(*) AS count FROM checklist_templates").fetchone()["count"]
        if template_count == 0:
            db.executemany(
                """
                INSERT INTO checklist_templates (category, title, sort_order, required, is_reference_only)
                VALUES (?, ?, ?, ?, ?)
                """,
                SEED_TEMPLATES,
            )

        db.commit()


def row_to_session(row):
    return {
        "id": row["id"],
        "flight_name": row["flight_name"],
        "status": row["status"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
    }


def row_to_session_item(row):
    return {
        "id": row["id"],
        "category": row["category"],
        "category_label": CATEGORY_LABELS.get(row["category"], row["category"]),
        "title": row["title"],
        "sort_order": row["sort_order"],
        "required": bool(row["required"]),
        "completed": bool(row["completed"]),
        "completed_at": row["completed_at"],
    }


def row_to_reference_item(row):
    return {
        "id": row["id"],
        "category": row["category"],
        "category_label": CATEGORY_LABELS.get(row["category"], row["category"]),
        "title": row["title"],
        "sort_order": row["sort_order"],
    }


def fetch_active_session_row():
    db = get_db()
    return db.execute(
        "SELECT * FROM flight_sessions WHERE status = 'active' ORDER BY started_at DESC LIMIT 1"
    ).fetchone()


def fetch_session_row(session_id):
    db = get_db()
    return db.execute("SELECT * FROM flight_sessions WHERE id = ?", (session_id,)).fetchone()


def fetch_session_item_row(item_id):
    db = get_db()
    return db.execute("SELECT * FROM session_items WHERE id = ?", (item_id,)).fetchone()


def fetch_reference_items():
    db = get_db()
    rows = db.execute(
        f"""
        SELECT * FROM checklist_templates
        WHERE is_reference_only = 1
        ORDER BY {ORDER_BY_CATEGORY_SQL}, sort_order, id
        """
    ).fetchall()
    return [row_to_reference_item(row) for row in rows]


def fetch_session_items(session_id):
    db = get_db()
    rows = db.execute(
        f"""
        SELECT * FROM session_items
        WHERE session_id = ?
        ORDER BY {ORDER_BY_CATEGORY_SQL}, sort_order, id
        """,
        (session_id,),
    ).fetchall()
    return [row_to_session_item(row) for row in rows]


def group_items_by_category(items):
    grouped = []
    items_by_category = {category: [] for category in CHECKLIST_CATEGORIES}

    for item in items:
        items_by_category.setdefault(item["category"], []).append(item)

    for category in CHECKLIST_CATEGORIES:
        category_items = items_by_category.get(category, [])
        required_total = sum(1 for item in category_items if item["required"])
        required_completed = sum(1 for item in category_items if item["required"] and item["completed"])
        grouped.append(
            {
                "key": category,
                "label": CATEGORY_LABELS[category],
                "items": category_items,
                "total_count": len(category_items),
                "completed_count": sum(1 for item in category_items if item["completed"]),
                "required_total": required_total,
                "required_completed": required_completed,
            }
        )

    return grouped


def build_session_payload(session_row):
    if session_row is None:
        return {
            "session": None,
            "sections": [],
            "reference_items": fetch_reference_items(),
            "can_close": False,
            "summary": None,
        }

    items = fetch_session_items(session_row["id"])
    sections = group_items_by_category(items)
    total_count = sum(section["total_count"] for section in sections)
    completed_count = sum(section["completed_count"] for section in sections)
    required_total = sum(section["required_total"] for section in sections)
    required_completed = sum(section["required_completed"] for section in sections)

    return {
        "session": row_to_session(session_row),
        "sections": sections,
        "reference_items": fetch_reference_items(),
        "can_close": required_total == required_completed,
        "summary": {
            "total_count": total_count,
            "completed_count": completed_count,
            "pending_count": total_count - completed_count,
            "required_total": required_total,
            "required_completed": required_completed,
        },
    }


def build_history_payload():
    db = get_db()
    sessions = db.execute(
        "SELECT * FROM flight_sessions ORDER BY started_at DESC, id DESC"
    ).fetchall()
    payload = []

    for session in sessions:
        counts = db.execute(
            """
            SELECT
                COUNT(*) AS total_count,
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS completed_count,
                SUM(CASE WHEN required = 1 THEN 1 ELSE 0 END) AS required_total,
                SUM(CASE WHEN required = 1 AND completed = 1 THEN 1 ELSE 0 END) AS required_completed
            FROM session_items
            WHERE session_id = ?
            """,
            (session["id"],),
        ).fetchone()
        payload.append(
            {
                **row_to_session(session),
                "total_count": counts["total_count"] or 0,
                "completed_count": counts["completed_count"] or 0,
                "required_total": counts["required_total"] or 0,
                "required_completed": counts["required_completed"] or 0,
            }
        )

    return payload


def create_session_items(session_id):
    db = get_db()
    templates = db.execute(
        f"""
        SELECT * FROM checklist_templates
        WHERE is_reference_only = 0
        ORDER BY {ORDER_BY_CATEGORY_SQL}, sort_order, id
        """
    ).fetchall()
    db.executemany(
        """
        INSERT INTO session_items (session_id, template_id, category, title, sort_order, required)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                session_id,
                template["id"],
                template["category"],
                template["title"],
                template["sort_order"],
                template["required"],
            )
            for template in templates
        ],
    )


@app.route("/")
def index():
    """Render the main single-page drone checklist UI."""
    return render_template_string(TEMPLATE)


@app.route("/api/active-session", methods=["GET"])
def get_active_session():
    """Return the current active flight session and its checklist state."""
    active_session = fetch_active_session_row()
    return jsonify(build_session_payload(active_session))


@app.route("/api/sessions", methods=["POST"])
def create_session():
    """Create a new flight session from the shared checklist template."""
    data = get_json_payload()
    if data is None:
        return jsonify({"error": "Gecerli bir JSON nesnesi gonderilmelidir."}), 400

    active_session = fetch_active_session_row()
    if active_session is not None:
        return jsonify({"error": "Halihazirda aktif bir ucus bulunuyor."}), 400

    flight_name = str(data.get("flight_name", "")).strip()
    if not flight_name:
        return jsonify({"error": "Ucus adi zorunludur."}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO flight_sessions (flight_name, status) VALUES (?, 'active')",
        (flight_name,),
    )
    session_id = cursor.lastrowid
    create_session_items(session_id)
    db.commit()

    return jsonify(build_session_payload(fetch_session_row(session_id))), 201


@app.route("/api/sessions/<int:session_id>/items", methods=["GET"])
def get_session_items(session_id):
    """Return grouped checklist items for a flight session."""
    session_row = fetch_session_row(session_id)
    if session_row is None:
        return jsonify({"error": "Ucus oturumu bulunamadi."}), 404

    return jsonify(build_session_payload(session_row))


@app.route("/api/session-items/<int:item_id>", methods=["PUT"])
def update_session_item(item_id):
    """Update the completion status of a checklist item."""
    data = get_json_payload()
    if data is None:
        return jsonify({"error": "Gecerli bir JSON nesnesi gonderilmelidir."}), 400

    completed = data.get("completed")
    if not isinstance(completed, bool):
        return jsonify({"error": "completed alani true veya false olmalidir."}), 400

    item_row = fetch_session_item_row(item_id)
    if item_row is None:
        return jsonify({"error": "Checklist maddesi bulunamadi."}), 404

    session_row = fetch_session_row(item_row["session_id"])
    if session_row is None:
        return jsonify({"error": "Bagli ucus oturumu bulunamadi."}), 404
    if session_row["status"] != "active":
        return jsonify({"error": "Tamamlanmis bir ucus oturumu degistirilemez."}), 400

    db = get_db()
    db.execute(
        """
        UPDATE session_items
        SET completed = ?, completed_at = CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END
        WHERE id = ?
        """,
        (1 if completed else 0, 1 if completed else 0, item_id),
    )
    db.commit()

    return jsonify(build_session_payload(fetch_session_row(session_row["id"])))


@app.route("/api/sessions/<int:session_id>/close", methods=["POST"])
def close_session(session_id):
    """Close a flight session once all required items are completed."""
    session_row = fetch_session_row(session_id)
    if session_row is None:
        return jsonify({"error": "Ucus oturumu bulunamadi."}), 404
    if session_row["status"] != "active":
        return jsonify({"error": "Bu ucus oturumu zaten kapatildi."}), 400

    payload = build_session_payload(session_row)
    if not payload["can_close"]:
        summary = payload["summary"]
        return jsonify(
            {
                "error": "Zorunlu maddeler tamamlanmadan ucus kapatilamaz.",
                "required_total": summary["required_total"],
                "required_completed": summary["required_completed"],
            }
        ), 400

    db = get_db()
    db.execute(
        "UPDATE flight_sessions SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (session_id,),
    )
    db.commit()

    return jsonify({"message": "Ucus oturumu kapatildi."})


@app.route("/api/history", methods=["GET"])
def get_history():
    """Return previously created flight sessions."""
    return jsonify(build_history_payload())


@app.route("/api/reference-items", methods=["GET"])
def get_reference_items():
    """Return emergency reference items."""
    return jsonify(fetch_reference_items())


TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drone Flight Checklist App</title>
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #f3f4f6;
            color: #111827;
        }
        .page {
            max-width: 960px;
            margin: 0 auto;
            padding: 24px 16px 48px;
        }
        .hero {
            background: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
        }
        h1, h2, h3 {
            margin: 0;
        }
        h1 {
            font-size: 30px;
            margin-bottom: 8px;
        }
        p {
            margin: 0;
            color: #4b5563;
        }
        .grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 16px;
        }
        .card {
            background: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 16px;
            padding: 20px;
        }
        .card + .card {
            margin-top: 16px;
        }
        .muted {
            color: #6b7280;
            font-size: 14px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-top: 16px;
        }
        .summary-box {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 12px;
        }
        .summary-box strong {
            display: block;
            font-size: 22px;
            margin-top: 4px;
        }
        form {
            display: flex;
            gap: 12px;
            margin-top: 16px;
            flex-wrap: wrap;
        }
        input[type="text"] {
            flex: 1;
            min-width: 220px;
            padding: 12px 14px;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            font-size: 15px;
        }
        button {
            border: none;
            border-radius: 10px;
            background: #1d4ed8;
            color: #ffffff;
            padding: 12px 16px;
            font-size: 15px;
            cursor: pointer;
        }
        button.secondary {
            background: #111827;
        }
        button:disabled {
            background: #94a3b8;
            cursor: not-allowed;
        }
        .status {
            display: inline-block;
            margin-top: 12px;
            padding: 8px 10px;
            border-radius: 999px;
            background: #dbeafe;
            color: #1d4ed8;
            font-size: 14px;
            font-weight: 700;
        }
        .section-list {
            display: grid;
            gap: 16px;
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 12px;
            margin-bottom: 12px;
        }
        .section-header span {
            color: #6b7280;
            font-size: 14px;
        }
        .items {
            display: grid;
            gap: 10px;
        }
        .item {
            display: flex;
            gap: 10px;
            align-items: flex-start;
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 12px;
        }
        .item.completed {
            opacity: 0.72;
        }
        .item input {
            margin-top: 4px;
            width: 18px;
            height: 18px;
        }
        .item-title {
            font-size: 15px;
            color: #111827;
        }
        .item.completed .item-title {
            text-decoration: line-through;
        }
        .required-tag {
            display: inline-block;
            margin-top: 6px;
            font-size: 12px;
            color: #92400e;
            background: #fef3c7;
            border-radius: 999px;
            padding: 4px 8px;
        }
        .reference-box {
            background: #fff7ed;
            border: 1px solid #fdba74;
            border-radius: 12px;
            padding: 12px;
        }
        .reference-box + .reference-box {
            margin-top: 12px;
        }
        .reference-box ul,
        .history-list {
            margin: 10px 0 0;
            padding-left: 18px;
        }
        .history-list li {
            margin: 8px 0;
            color: #374151;
        }
        .empty {
            padding: 18px;
            border-radius: 12px;
            background: #f9fafb;
            border: 1px dashed #cbd5e1;
            color: #6b7280;
        }
        .error,
        .success {
            display: none;
            margin-bottom: 16px;
            padding: 12px 14px;
            border-radius: 12px;
            font-size: 14px;
        }
        .error.show {
            display: block;
            background: #fee2e2;
            color: #b91c1c;
            border: 1px solid #fecaca;
        }
        .success.show {
            display: block;
            background: #dcfce7;
            color: #166534;
            border: 1px solid #bbf7d0;
        }
        @media (max-width: 820px) {
            .grid {
                grid-template-columns: 1fr;
            }
            .summary {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="page">
        <div class="hero">
            <h1>Drone Flight Checklist App</h1>
            <p>Faz 1 tek agent urunu: basit, Turkce ve her ucus icin yeniden baslayan checklist akisi.</p>
        </div>

        <div id="error-message" class="error"></div>
        <div id="success-message" class="success"></div>

        <div class="grid">
            <main>
                <section class="card">
                    <h2>Aktif Ucus</h2>
                    <p class="muted">Yeni bir ucus baslatildiginda checklist maddeleri bu oturuma kopyalanir.</p>
                    <div id="active-session"></div>
                </section>

                <section class="card">
                    <h2>Checklist</h2>
                    <p class="muted">Ortam Kontrolu, Ucus Oncesi, Ucus Sirasinda ve Ucus Sonrasi maddelerini burada yonetin.</p>
                    <div id="checklist-sections" class="section-list"></div>
                </section>
            </main>

            <aside>
                <section class="card">
                    <h2>Acil Durum Prosedurleri</h2>
                    <p class="muted">Bu bolum referans amaclidir ve normal checklist maddesi gibi tamamlanmaz.</p>
                    <div id="reference-items"></div>
                </section>

                <section class="card">
                    <h2>Gecmis Ucuslar</h2>
                    <p class="muted">Tamamlanan ve aktif oturumlarin basit ozeti.</p>
                    <div id="history"></div>
                </section>
            </aside>
        </div>
    </div>

    <script>
        async function fetchDashboard() {
            try {
                const [activeResponse, historyResponse] = await Promise.all([
                    fetch('/api/active-session'),
                    fetch('/api/history')
                ]);

                if (!activeResponse.ok || !historyResponse.ok) {
                    throw new Error('Veriler yuklenemedi.');
                }

                const activePayload = await activeResponse.json();
                const historyPayload = await historyResponse.json();
                renderActiveSession(activePayload);
                renderSections(activePayload.sections);
                renderReferenceItems(activePayload.reference_items || []);
                renderHistory(historyPayload);
            } catch (error) {
                showError(error.message || 'Beklenmeyen bir hata olustu.');
            }
        }

        function renderActiveSession(payload) {
            const container = document.getElementById('active-session');

            if (!payload.session) {
                container.innerHTML = `
                    <div class="empty">Su anda aktif ucus yok.</div>
                    <form onsubmit="createSession(event)">
                        <input id="flight-name" type="text" placeholder="Ornek: Test Ucusu 001" autocomplete="off">
                        <button type="submit">Yeni Ucus Baslat</button>
                    </form>
                `;
                return;
            }

            const session = payload.session;
            const summary = payload.summary;
            container.innerHTML = `
                <h3>${escapeHtml(session.flight_name)}</h3>
                <div class="status">${session.status === 'active' ? 'Aktif Ucus' : 'Tamamlandi'}</div>
                <p class="muted" style="margin-top: 12px;">Baslangic: ${formatDate(session.started_at)}</p>
                <div class="summary">
                    <div class="summary-box">
                        Tamamlanan
                        <strong>${summary.completed_count}/${summary.total_count}</strong>
                    </div>
                    <div class="summary-box">
                        Zorunlu
                        <strong>${summary.required_completed}/${summary.required_total}</strong>
                    </div>
                    <div class="summary-box">
                        Bekleyen
                        <strong>${summary.pending_count}</strong>
                    </div>
                </div>
                <form onsubmit="closeSession(event, ${session.id})">
                    <button class="secondary" type="submit" ${payload.can_close ? '' : 'disabled'}>Ucusu Tamamla</button>
                </form>
            `;
        }

        function renderSections(sections) {
            const container = document.getElementById('checklist-sections');

            if (!sections || sections.length === 0) {
                container.innerHTML = '<div class="empty">Checklist maddeleri aktif bir ucus baslatildiginda gorunecek.</div>';
                return;
            }

            container.innerHTML = sections.map((section) => `
                <section class="card">
                    <div class="section-header">
                        <h3>${escapeHtml(section.label)}</h3>
                        <span>${section.completed_count}/${section.total_count} tamamlandi</span>
                    </div>
                    <div class="items">
                        ${section.items.map((item) => `
                            <label class="item ${item.completed ? 'completed' : ''}">
                                <input type="checkbox" ${item.completed ? 'checked' : ''} onchange="toggleItem(${item.id}, this.checked)">
                                <div>
                                    <div class="item-title">${escapeHtml(item.title)}</div>
                                    ${item.required ? '<div class="required-tag">Zorunlu</div>' : ''}
                                </div>
                            </label>
                        `).join('')}
                    </div>
                </section>
            `).join('');
        }

        function renderReferenceItems(items) {
            const container = document.getElementById('reference-items');

            if (!items.length) {
                container.innerHTML = '<div class="empty">Referans proseduru bulunamadi.</div>';
                return;
            }

            container.innerHTML = `
                <div class="reference-box">
                    <h3>Acil durumda once sakin kal</h3>
                    <ul>
                        ${items.map((item) => `<li>${escapeHtml(item.title)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        function renderHistory(history) {
            const container = document.getElementById('history');

            if (!history.length) {
                container.innerHTML = '<div class="empty">Kayitli ucus yok.</div>';
                return;
            }

            container.innerHTML = `
                <ul class="history-list">
                    ${history.map((session) => `
                        <li>
                            <strong>${escapeHtml(session.flight_name)}</strong><br>
                            ${session.status === 'active' ? 'Aktif' : 'Tamamlandi'} | ${session.completed_count}/${session.total_count} madde | ${formatDate(session.started_at)}
                        </li>
                    `).join('')}
                </ul>
            `;
        }

        async function createSession(event) {
            event.preventDefault();
            const input = document.getElementById('flight-name');
            const flightName = input.value.trim();

            if (!flightName) {
                showError('Lutfen bir ucus adi girin.');
                input.focus();
                return;
            }

            try {
                const response = await fetch('/api/sessions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ flight_name: flightName })
                });
                const payload = await response.json();

                if (!response.ok) {
                    throw new Error(payload.error || 'Ucus baslatilamadi.');
                }

                await fetchDashboard();
                showSuccess('Yeni ucus oturumu baslatildi.');
            } catch (error) {
                showError(error.message || 'Ucus baslatilamadi.');
            }
        }

        async function toggleItem(itemId, completed) {
            try {
                const response = await fetch(`/api/session-items/${itemId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ completed })
                });
                const payload = await response.json();

                if (!response.ok) {
                    throw new Error(payload.error || 'Checklist maddesi guncellenemedi.');
                }

                renderActiveSession(payload);
                renderSections(payload.sections);
                renderReferenceItems(payload.reference_items || []);
            } catch (error) {
                showError(error.message || 'Checklist maddesi guncellenemedi.');
                await fetchDashboard();
            }
        }

        async function closeSession(event, sessionId) {
            event.preventDefault();

            try {
                const response = await fetch(`/api/sessions/${sessionId}/close`, {
                    method: 'POST'
                });
                const payload = await response.json();

                if (!response.ok) {
                    throw new Error(payload.error || 'Ucus tamamlanamadi.');
                }

                await fetchDashboard();
                showSuccess('Ucus oturumu kapatildi.');
            } catch (error) {
                showError(error.message || 'Ucus tamamlanamadi.');
            }
        }

        function formatDate(value) {
            if (!value) {
                return '-';
            }

            const parsed = new Date(value.replace(' ', 'T'));
            if (Number.isNaN(parsed.getTime())) {
                return value;
            }

            return parsed.toLocaleString('tr-TR');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function showError(message) {
            const box = document.getElementById('error-message');
            box.textContent = message;
            box.classList.add('show');
            document.getElementById('success-message').classList.remove('show');
        }

        function showSuccess(message) {
            const box = document.getElementById('success-message');
            box.textContent = message;
            box.classList.add('show');
            document.getElementById('error-message').classList.remove('show');
        }

        fetchDashboard();
    </script>
</body>
</html>
"""


init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
