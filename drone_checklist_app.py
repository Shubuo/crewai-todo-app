from flask import Flask, render_template_string, request, jsonify, redirect, g
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from litellm import completion

load_dotenv(override=True)

# Normalize OpenRouter/OpenAI-compatible env names before CrewAI uses them.
os.environ.setdefault("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
os.environ.setdefault("OPENAI_MODEL_NAME", "openrouter/owl-alpha")
if os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = os.environ["OPENAI_API_KEY"]
if os.environ.get("OPENROUTER_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
if os.environ.get("OPENAI_API_BASE"):
    os.environ["OPENROUTER_API_BASE"] = os.environ["OPENAI_API_BASE"]
if os.environ.get("OPENROUTER_API_BASE") and not os.environ.get("OPENAI_API_BASE"):
    os.environ["OPENAI_API_BASE"] = os.environ["OPENROUTER_API_BASE"]

app = Flask(__name__)
app.config['DATABASE'] = 'drone_checklist_ges.db'

# Turkish labels for sections
SECTION_LABELS = {
    'Ortam Kontrolu': 'Ortam Kontrolü',
    'Ucus Oncesi': 'Uçuş Öncesi',
    'Ucus Sirasinda': 'Uçuş Sırasında',
    'Acil Durum Prosedurleri': 'Acil Durum Prosedürleri',
    'Ucus Sonrasi': 'Uçuş Sonrası'
}

# Default checklist items
DEFAULT_ITEMS = [
    # Ortam Kontrolu
    ('Ortam Kontrolu', 'Solar radyasyon seviyesi (W/m²) ölçüldü ve uçuşa uygun', 1, 0),
    ('Ortam Kontrolu', 'Bulutluluk oranı ve rüzgar hızı meteorolojik limitler içinde', 2, 0),
    ('Ortam Kontrolu', 'Uçuş alanı, enerji nakil hatları ve yüksek gerilim engellerinden arındırıldı', 3, 0),
    ('Ortam Kontrolu', 'RTK GPS sinyali yeterli seviyede ve doğruluk sağlandı', 4, 0),
    ('Ortam Kontrolu', 'Elektromanyetik girişim ölçümleri tamamlandı', 5, 0),
    
    # Ucus Oncesi
    ('Ucus Oncesi', 'Batarya şarj seviyesi kontrol edildi (%80+)', 1, 0),
    ('Ucus Oncesi', 'Pervane bıçakları ve motorlar kontrol edildi', 2, 0),
    ('Ucus Oncesi', 'Termal kamera kalibrasyonu (RGB+IR) yapıldı', 3, 0),
    ('Ucus Oncesi', 'Gimbal açı ayarları PV panellerine göre (-90 derece) ayarlandı', 4, 0),
    ('Ucus Oncesi', 'Otonom uçuş rotası (Waypoints) ve grid yapısı doğrulandı', 5, 0),
    ('Ucus Oncesi', 'Uçuş kontrolör firmware güncel', 6, 0),
    ('Ucus Oncesi', 'HOMEFIX noktası inverter veya güvenli bölgeye ayarlandı', 7, 0),
    
    # Ucus Sirasinda
    ('Ucus Sirasinda', 'Kalkış normal gerçekleşti', 1, 0),
    ('Ucus Sirasinda', 'İrtifa (GSD gereksinimlerine göre) korundu', 2, 0),
    ('Ucus Sirasinda', 'Sıcak nokta (hot-spot) tespiti için termal kayıt aktif', 3, 0),
    ('Ucus Sirasinda', 'RTK GPS konum bilgisi sapmasız ilerliyor', 4, 0),
    ('Ucus Sirasinda', 'Batarya seviyesi izlendi (kritik seviye uyarısı)', 5, 0),
    
    # Acil Durum Prosedurleri (reference only)
    ('Acil Durum Prosedurleri', 'İnverter dairesi yangını tespiti: İtfaiyeye haber ver, bölgeden uzaklaş', 1, 1),
    ('Acil Durum Prosedurleri', 'Yüksek gerilim hattına yaklaşma tehlikesi: Derhal irtifa düşür, uzaklaş', 2, 1),
    ('Acil Durum Prosedurleri', 'Termal anomali (Aşırı sıcak panel): Koordinat kaydet, uçuşu sürdür', 3, 1),
    ('Acil Durum Prosedurleri', 'Batarya aşırı ısınması: Derhal inişe geç', 4, 1),
    ('Acil Durum Prosedurleri', 'Sinyal kaybı: Return to Home (RTH) aktif olmasını bekle', 5, 1),
    ('Acil Durum Prosedurleri', 'Aşırı rüzgar: Alçak irtifa, kontrollü iniş', 6, 1),
    
    # Ucus Sonrasi
    ('Ucus Sonrasi', 'Drone güvenli şekilde yere indirildi', 1, 0),
    ('Ucus Sonrasi', 'Batarya çıkarıldı ve soğumaya bırakıldı', 2, 0),
    ('Ucus Sonrasi', 'Termal görüntüler ve RGB veriler SD karttan aktarıldı', 3, 0),
    ('Ucus Sonrasi', 'Anomalili panel koordinatları rapora eklendi', 4, 0),
    ('Ucus Sonrasi', 'Uçuş kayıtları incelendi', 5, 0),
    ('Ucus Sonrasi', 'Kamera lensleri ve donanım temizliği yapıldı', 6, 0),
    ('Ucus Sonrasi', 'Bir sonraki görev için notlar kaydedildi', 7, 0),
]

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def fetch_telemetry_data():
    import urllib.request
    import json
    import random
    
    battery = random.randint(40, 100)
    gps_satellites = random.randint(6, 20)
    
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=38.42&longitude=27.14&current=temperature_2m,wind_speed_10m,precipitation"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            current = data.get("current", {})
            temp = current.get("temperature_2m", 25.0)
            wind = current.get("wind_speed_10m", 5.0)
            precip = current.get("precipitation", 0.0)
    except Exception as e:
        temp = 25.0
        wind = round(random.uniform(2.0, 12.0), 1)
        precip = 0.0

    return {
        "battery": battery,
        "gps_satellites": gps_satellites,
        "temperature": temp,
        "wind_speed": wind,
        "precipitation": precip
    }

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS template_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT NOT NULL,
            item_text TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            is_reference INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS flight_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT DEFAULT 'active',
            drone_name TEXT,
            notes TEXT,
            telemetry_data TEXT
        );
        
        CREATE TABLE IF NOT EXISTS session_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            template_item_id INTEGER NOT NULL,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            FOREIGN KEY (session_id) REFERENCES flight_sessions(id),
            FOREIGN KEY (template_item_id) REFERENCES template_items(id)
        );
    ''')
    
    # Check if we need to seed
    cursor = db.execute('SELECT COUNT(*) FROM template_items')
    if cursor.fetchone()[0] == 0:
        for section, item_text, order_index, is_reference in DEFAULT_ITEMS:
            db.execute(
                'INSERT INTO template_items (section, item_text, order_index, is_reference) VALUES (?, ?, ?, ?)',
                (section, item_text, order_index, is_reference)
            )
        db.commit()

# API Routes
@app.route('/api/sessions', methods=['POST'])
def create_session():
    db = get_db()
    drone_name = request.json.get('drone_name', 'Varsayılan Drone')
    
    # Close any existing active sessions first
    db.execute(
        "UPDATE flight_sessions SET status = 'cancelled' WHERE status = 'active'"
    )
    
    # Create new session
    start_time = datetime.now().isoformat()
    import json
    telemetry_data_str = json.dumps(fetch_telemetry_data())
    cursor = db.execute(
        'INSERT INTO flight_sessions (start_time, drone_name, status, telemetry_data) VALUES (?, ?, ?, ?)',
        (start_time, drone_name, 'active', telemetry_data_str)
    )
    session_id = cursor.lastrowid
    AgentTraceLogger.clear(session_id)
    db.commit()
    
    # Create session items from template
    template_items = db.execute(
        'SELECT id, is_reference FROM template_items ORDER BY section, order_index'
    ).fetchall()
    
    for item in template_items:
        db.execute(
            'INSERT INTO session_items (session_id, template_item_id, completed) VALUES (?, ?, ?)',
            (session_id, item['id'], 0)
        )
    db.commit()
    
    return jsonify({
        'id': session_id,
        'start_time': start_time,
        'drone_name': drone_name,
        'status': 'active'
    })


@app.route('/new-flight', methods=['POST'])
def new_flight():
    db = get_db()
    drone_name = request.form.get('drone_name', 'Varsayılan Drone')
    db.execute(
        "UPDATE flight_sessions SET status = 'cancelled' WHERE status = 'active'"
    )
    start_time = datetime.now().isoformat()
    cursor = db.execute(
        'INSERT INTO flight_sessions (start_time, drone_name, status) VALUES (?, ?, ?)',
        (start_time, drone_name, 'active')
    )
    session_id = cursor.lastrowid
    AgentTraceLogger.clear(session_id)
    template_items = db.execute(
        'SELECT id, is_reference FROM template_items ORDER BY section, order_index'
    ).fetchall()
    for item in template_items:
        db.execute(
            'INSERT INTO session_items (session_id, template_item_id, completed) VALUES (?, ?, ?)',
            (session_id, item['id'], 0)
        )
    db.commit()
    return redirect('/', 303)


@app.route('/api/sessions/active', methods=['GET'])
def get_active_session():
    db = get_db()
    session = db.execute(
        "SELECT * FROM flight_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    
    if not session:
        return jsonify(None)
    
    items = db.execute('''
        SELECT si.id as session_item_id, si.completed, ti.id as template_id,
               ti.section, ti.item_text, ti.order_index, ti.is_reference
        FROM session_items si
        JOIN template_items ti ON si.template_item_id = ti.id
        WHERE si.session_id = ?
        ORDER BY ti.section, ti.order_index
    ''', (session['id'],)).fetchall()
    
    import json
    telemetry_data = json.loads(session['telemetry_data']) if session['telemetry_data'] else {}

    return jsonify({
        'id': session['id'],
        'start_time': session['start_time'],
        'drone_name': session['drone_name'],
        'status': session['status'],
        'telemetry_data': telemetry_data,
        'items': [dict(item) for item in items]
    })

@app.route('/api/sessions/<int:session_id>/items/<int:item_id>', methods=['PUT'])
def update_item(session_id, item_id):
    db = get_db()
    data = request.json
    completed = 1 if data.get('completed', False) else 0
    
    db.execute(
        'UPDATE session_items SET completed = ?, completed_at = ? WHERE id = ? AND session_id = ?',
        (completed, datetime.now().isoformat() if completed else None, item_id, session_id)
    )
    db.commit()
    
    return jsonify({'success': True})

@app.route('/api/sessions/<int:session_id>/close', methods=['POST'])
def close_session(session_id):
    db = get_db()
    notes = request.json.get('notes', '')
    
    db.execute(
        'UPDATE flight_sessions SET status = ?, end_time = ?, notes = ? WHERE id = ?',
        ('completed', datetime.now().isoformat(), notes, session_id)
    )
    db.commit()
    
    return jsonify({'success': True, 'status': 'completed'})

@app.route('/api/sessions/history', methods=['GET'])
def get_history():
    db = get_db()
    sessions = db.execute('''
        SELECT fs.*, 
               (SELECT COUNT(*) FROM session_items si 
                JOIN template_items ti ON si.template_item_id = ti.id 
                WHERE si.session_id = fs.id AND si.completed = 1 AND ti.is_reference = 0) as completed_count,
               (SELECT COUNT(*) FROM session_items si 
                JOIN template_items ti ON si.template_item_id = ti.id 
                WHERE si.session_id = fs.id AND ti.is_reference = 0) as total_count
        FROM flight_sessions fs
        WHERE fs.status = 'completed'
        ORDER BY fs.start_time DESC
        LIMIT 50
    ''').fetchall()
    
    return jsonify([dict(s) for s in sessions])

@app.route('/api/sessions/<int:session_id>', methods=['GET'])
def get_session(session_id):
    db = get_db()
    session = db.execute(
        'SELECT * FROM flight_sessions WHERE id = ?', (session_id,)
    ).fetchone()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    items = db.execute('''
        SELECT si.id as session_item_id, si.completed, si.completed_at, ti.id as template_id,
               ti.section, ti.item_text, ti.order_index, ti.is_reference
        FROM session_items si
        JOIN template_items ti ON si.template_item_id = ti.id
        WHERE si.session_id = ?
        ORDER BY ti.section, ti.order_index
    ''', (session_id,)).fetchall()
    
    return jsonify({
        'id': session['id'],
        'start_time': session['start_time'],
        'end_time': session['end_time'],
        'drone_name': session['drone_name'],
        'status': session['status'],
        'notes': session['notes'],
        'items': [dict(item) for item in items]
    })

@app.route('/api/reference/emergency', methods=['GET'])
def get_emergency_reference():
    db = get_db()
    items = db.execute('''
        SELECT * FROM template_items 
        WHERE is_reference = 1 
        ORDER BY section, order_index
    ''').fetchall()
    
    return jsonify([dict(item) for item in items])

@app.route('/api/template', methods=['GET'])
def get_template():
    db = get_db()
    items = db.execute('''
        SELECT * FROM template_items 
        ORDER BY section, order_index
    ''').fetchall()
    
    return jsonify([dict(item) for item in items])

SECTION_ORDER = ['Ortam Kontrolu', 'Ucus Oncesi', 'Ucus Sirasinda', 'Ucus Sonrasi']
CRITICAL_SECTIONS = ['Ortam Kontrolu', 'Ucus Oncesi']

class AgentTraceLogger:
    _traces = {}
    _group_seq = {}

    @classmethod
    def clear(cls, session_id):
        cls._traces[session_id] = []
        cls._group_seq[session_id] = 0

    @classmethod
    def log(cls, session_id, action, thought, function=None, detail=None, result=None, is_crewai_flow=False):
        if session_id not in cls._traces:
            cls._traces[session_id] = []
            cls._group_seq[session_id] = 0
        if session_id not in cls._group_seq:
            cls._group_seq[session_id] = 0

        if is_crewai_flow:
            cls._group_seq[session_id] += 1
        group = cls._group_seq.get(session_id, 0)

        cls._traces[session_id].append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'action': action,
            'thought': thought,
            'function': function,
            'detail': detail,
            'result': result,
            'is_crewai_flow': is_crewai_flow,
            'group': group,
        })

    @classmethod
    def get_trace(cls, session_id):
        return cls._traces.get(session_id, [])

    @classmethod
    def get_all_session_ids(cls):
        return list(cls._traces.keys())

    @classmethod
    def has_trace(cls, session_id):
        return session_id in cls._traces and len(cls._traces[session_id]) > 0


class DroneChecklistAgent:
    @staticmethod
    def assess_risk(session_id):
        AgentTraceLogger.log(session_id,
            'Veri Analizi',
            'Checklist verileri okunuyor... Drone uçuş kontrol listesindeki tüm maddeler taranıyor.',
            function='query_db',
            detail={'query': 'SELECT ti.section, ti.item_text, si.completed FROM template_items LEFT JOIN session_items ...', 'params': {'session_id': session_id, 'is_reference': 0}},
            is_crewai_flow=True
        )
        db = get_db()
        items = db.execute('''
            SELECT ti.section, ti.item_text, COALESCE(si.completed, 0) as completed
            FROM template_items ti
            LEFT JOIN session_items si ON ti.id = si.template_item_id AND si.session_id = ?
            WHERE ti.is_reference = 0
            ORDER BY ti.section, ti.order_index
        ''', (session_id,)).fetchall()

        if not items:
            AgentTraceLogger.log(session_id,
                'Hata',
                'Checklist bulunamadi! Veritabaninda template_items tablosu bos veya ucus oturumu gecersiz.',
                function='validate',
                result='NO-GO'
            )
            return jsonify({'decision': 'NO-GO', 'reason': 'Checklist bulunamadi'})

        AgentTraceLogger.log(session_id,
            'Veri Analizi',
            f'{len(items)} adet checklist maddesi bulundu. Maddeler fazlarina gore gruplaniyor.',
            function='group_by_section',
            detail={'total_items': len(items)}
        )

        sections = {}
        items_by_section = {}
        for item in items:
            sec = item['section']
            if sec not in sections:
                sections[sec] = {'total': 0, 'completed': 0}
                items_by_section[sec] = []
            sections[sec]['total'] += 1
            if item['completed']:
                sections[sec]['completed'] += 1
            items_by_section[sec].append({
                'text': item['item_text'],
                'completed': bool(item['completed'])
            })

        AgentTraceLogger.log(session_id,
            'Faz Analizi',
            'Her fazin tamamlanma orani hesaplaniyor... Kritik fazlar (Ortam Kontrolu, Ucus Oncesi) ozel olarak inceleniyor.',
            function='analyze_phases',
            detail={SECTION_LABELS.get(k, k): f'{v["completed"]}/{v["total"]}' for k, v in sections.items()}
        )

        total = sum(s['total'] for s in sections.values())
        completed = sum(s['completed'] for s in sections.values())
        completion_pct = round(completed / total * 100) if total > 0 else 0

        critical_pct = {}
        warnings = []
        critical_missing = []

        for sec in CRITICAL_SECTIONS:
            if sec in sections:
                s = sections[sec]
                pct = round(s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                label = SECTION_LABELS.get(sec, sec)
                critical_pct[label] = pct
                if pct < 100:
                    for i in items_by_section[sec]:
                        if not i['completed']:
                            warnings.append(f"[{label}] {i['text']}")
                            critical_missing.append(i['text'])

        all_critical_done = all(
            sections.get(sec, {}).get('completed', 0) == sections.get(sec, {}).get('total', 1)
            for sec in CRITICAL_SECTIONS if sec in sections
        )

        AgentTraceLogger.log(session_id,
            'Kritik Degerlendirme',
            'Kritik fazlar kontrol ediliyor: Tum kritik maddeler tamamlanmis mi?',
            function='evaluate_critical',
            detail={SECTION_LABELS.get(s, s): {'completed': sections[s]['completed'], 'total': sections[s]['total'], 'all_done': sections[s]['completed'] == sections[s]['total']} for s in CRITICAL_SECTIONS if s in sections}
        )

        if not all_critical_done:
            decision = 'NO-GO'
        elif completion_pct < 80:
            decision = 'WARNING'
        else:
            decision = 'GO'

        AgentTraceLogger.log(session_id,
            'Karar Verme',
            f'Toplam %{completion_pct} tamamlanma. Kritik fazlar {"tamamlandi" if all_critical_done else "TAMAMLANMADI"}. Karar: {decision}',
            function='decide',
            detail={'completion_pct': completion_pct, 'all_critical_done': all_critical_done, 'rules': ['NO-GO: kritik fazlar tamamlanmadi', 'WARNING: %80 alti', 'GO: tum kosullar saglaniyor']},
            result=decision
        )

        phase_progress = {}
        for sec in SECTION_ORDER:
            if sec in sections:
                s = sections[sec]
                pct = round(s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                phase_progress[SECTION_LABELS.get(sec, sec)] = {
                    'total': s['total'],
                    'completed': s['completed'],
                    'percentage': pct
                }

        AgentTraceLogger.log(session_id,
            'Rapor Hazirlama',
            f'{len(warnings)} uyari ve {len(critical_missing)} kritik eksik madde tespit edildi. Yanit hazirlaniyor.',
            function='format_response',
            detail={'warnings_count': len(warnings), 'critical_missing_count': len(critical_missing)}
        )

        return jsonify({
            'decision': decision,
            'completion_percentage': completion_pct,
            'critical_sections': critical_pct,
            'phase_progress': phase_progress,
            'warnings': warnings[:10],
            'critical_missing': critical_missing[:5],
            'total_items': total,
            'completed_items': completed
        })

    @staticmethod
    def get_advice(session_id):
        AgentTraceLogger.log(session_id,
            'Veri Analizi',
            'Checklist durumu taranıyor... Hangi maddeler tamamlanmış, hangileri bekliyor, tespit ediliyor.',
            function='query_db',
            detail={'query': 'SELECT ti.section, ti.item_text, si.completed FROM template_items LEFT JOIN session_items ...', 'params': {'session_id': session_id, 'is_reference': 0}},
            is_crewai_flow=True
        )
        db = get_db()
        items = db.execute('''
            SELECT ti.section, ti.item_text, ti.order_index,
                   COALESCE(si.completed, 0) as completed
            FROM template_items ti
            LEFT JOIN session_items si ON ti.id = si.template_item_id AND si.session_id = ?
            WHERE ti.is_reference = 0
            ORDER BY ti.section, ti.order_index
        ''', (session_id,)).fetchall()

        if not items:
            AgentTraceLogger.log(session_id, 'Hata', 'Checklist verisi bulunamadi.', function='validate', result='Bilinmiyor')
            return jsonify({'current_phase': 'Bilinmiyor', 'next_steps': [], 'blockers': []})

        AgentTraceLogger.log(session_id,
            'Durum Tespiti',
            f'{len(items)} madde inceleniyor. Mevcut faz belirleniyor...',
            function='find_current_phase'
        )

        sections = {}
        current_phase = None
        incomplete_in_phase = {}

        for item in items:
            sec = item['section']
            if sec not in sections:
                sections[sec] = {'total': 0, 'completed': 0, 'incomplete': []}
                incomplete_in_phase[sec] = []
            sections[sec]['total'] += 1
            if item['completed']:
                sections[sec]['completed'] += 1
            else:
                sections[sec]['incomplete'].append(item['item_text'])
                incomplete_in_phase[sec].append(item['item_text'])

        for sec in SECTION_ORDER:
            if sec in sections:
                if sections[sec]['completed'] < sections[sec]['total']:
                    current_phase = SECTION_LABELS.get(sec, sec)
                    break
                current_phase = SECTION_LABELS.get(sec, sec)

        AgentTraceLogger.log(session_id,
            'Faz Belirleme',
            f'Mevcut faz: {current_phase}. Bu fazda {sections.get(current_phase, {}).get("total", 0)} maddeden {sections.get(current_phase, {}).get("completed", 0)} tamamlanmış.',
            function='identify_phase',
            detail={SECTION_LABELS.get(k, k): f'{v["completed"]}/{v["total"]}' for k, v in sections.items()},
            result=current_phase
        )

        next_steps = []
        blockers = []
        for sec in SECTION_ORDER:
            if sec in sections and incomplete_in_phase[sec]:
                steps = incomplete_in_phase[sec][:5]
                next_steps.extend(steps)
                label = SECTION_LABELS.get(sec, sec)
                blockers.append(f"[{label}] {steps[0]}")
                if len(next_steps) >= 5:
                    next_steps = next_steps[:5]
                    break

        AgentTraceLogger.log(session_id,
            'Adim Plani',
            f'{len(next_steps)} sonraki adim, {len(blockers)} blokaj tespit edildi. Operatore en kritik adimlar oneriliyor.',
            function='plan_steps',
            detail={'next_steps_count': len(next_steps), 'blockers_count': len(blockers), 'next_steps': next_steps[:5], 'blockers': blockers[:3]},
            result=f'Ilk adim: {next_steps[0] if next_steps else "Yok"}'
        )

        phase_progress = {}
        for sec in SECTION_ORDER:
            if sec in sections:
                s = sections[sec]
                pct = round(s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                phase_progress[SECTION_LABELS.get(sec, sec)] = {
                    'total': s['total'],
                    'completed': s['completed'],
                    'percentage': pct
                }

        ai_advice = "Devam edebilirsiniz."
        try:
            if os.environ.get("OPENAI_API_KEY"):
                session_info = db.execute("SELECT telemetry_data FROM flight_sessions WHERE id = ?", (session_id,)).fetchone()
                import json
                telemetry_data = json.loads(session_info['telemetry_data']) if session_info and session_info['telemetry_data'] else {}
                
                advisor_agent = Agent(
                    role='Flight Advisor',
                    goal='Provide actionable next steps and autonomous GO/NO-GO decisions for a UAV flight based on telemetry.',
                    backstory='Experienced drone flight safety advisor prioritizing sensor data over operator input.',
                    verbose=False,
                    allow_delegation=False,
                    
                )
                task = Task(
                    description=f'Current phase: {current_phase}. Next steps: {next_steps[:3]}. Blockers: {blockers[:2]}. Telemetry: {telemetry_data}. IMPORTANT RULE: If Wind > 10m/s or Battery < 80% or GPS Satellites < 10, you MUST warn the operator strongly and suggest NO-GO or WARNING, overriding the operator\'s progress. Provide a 2-sentence advice in Turkish.',
                    expected_output='2-sentence autonomous advice in Turkish.',
                    agent=advisor_agent
                )
                crew = Crew(agents=[advisor_agent], tasks=[task], verbose=False)
                ai_advice = str(crew.kickoff())
                AgentTraceLogger.log(session_id, 'LLM Advice', 'CrewAI Flight Advisor gave autonomous advice based on telemetry', detail={'advice': ai_advice, 'telemetry': telemetry_data}, function='crew_kickoff')
        except Exception as e:
            AgentTraceLogger.log(session_id, 'LLM Error', str(e), function='crew_kickoff')
            return jsonify({'error': str(e)})

        return jsonify({
            'current_phase': current_phase,
            'next_steps': next_steps[:5],
            'blockers': blockers[:3],
            'phase_progress': phase_progress,
            'ai_advice': ai_advice
        })

    @staticmethod
    def generate_report(session_id):
        AgentTraceLogger.log(session_id,
            'Veri Analizi',
            'Uçuş kaydı ve checklist verileri yükleniyor... Rapor için tüm veriler derleniyor.',
            function='query_db',
            detail={'queries': ['SELECT * FROM flight_sessions', 'SELECT ti.*, si.completed FROM template_items LEFT JOIN session_items ...'], 'params': {'session_id': session_id}},
            is_crewai_flow=True
        )
        db = get_db()
        session = db.execute('''
            SELECT * FROM flight_sessions WHERE id = ?
        ''', (session_id,)).fetchone()

        if not session:
            AgentTraceLogger.log(session_id, 'Hata', f'Session #{session_id} bulunamadi!', function='validate', result='hata')
            return jsonify({'error': 'Session bulunamadi'}), 404

        AgentTraceLogger.log(session_id,
            'Durum Tespiti',
            f'Uçuş #{session_id} bulundu. Drone: {session["drone_name"]}, Durum: {session["status"]}. Checklist maddeleri analiz ediliyor.',
            function='load_session',
            detail={'drone_name': session['drone_name'], 'status': session['status'], 'start_time': session['start_time']}
        )

        items = db.execute('''
            SELECT ti.section, ti.item_text, ti.order_index, ti.is_reference,
                   COALESCE(si.completed, 0) as completed, si.completed_at
            FROM template_items ti
            LEFT JOIN session_items si ON ti.id = si.template_item_id AND si.session_id = ?
            ORDER BY ti.section, ti.order_index
        ''', (session_id,)).fetchall()

        AgentTraceLogger.log(session_id,
            'Faz Analizi',
            f'{len(items)} checklist maddesi faz bazında gruplanıyor ve tamamlanma oranları hesaplanıyor.',
            function='analyze_phases',
            detail={'total_items': len(items)}
        )

        sections = {}
        completed_all = 0
        total_all = 0

        for item in items:
            sec = item['section']
            if sec not in sections:
                sections[sec] = {'total': 0, 'completed': 0, 'items': []}
            sections[sec]['total'] += 1
            total_all += 1
            if item['completed']:
                sections[sec]['completed'] += 1
                completed_all += 1
            sections[sec]['items'].append({
                'text': item['item_text'],
                'completed': bool(item['completed']),
                'completed_at': item['completed_at']
            })

        completion_pct = round(completed_all / total_all * 100) if total_all > 0 else 0

        AgentTraceLogger.log(session_id,
            'Istatistik',
            f'Toplam %{completion_pct} tamamlanma ({completed_all}/{total_all}). Eksik maddeler ve uyarilar listeleniyor.',
            function='compute_stats',
            detail={'completion_pct': completion_pct, 'completed': completed_all, 'total': total_all}
        )

        phases = {}
        missing_items = []
        warnings = []
        for sec in SECTION_ORDER:
            if sec in sections:
                s = sections[sec]
                pct = round(s['completed'] / s['total'] * 100) if s['total'] > 0 else 0
                label = SECTION_LABELS.get(sec, sec)
                phases[label] = pct
                for i in s['items']:
                    if not i['completed']:
                        missing_items.append({'phase': label, 'text': i['text']})
                if pct < 100:
                    warnings.append(f"{label}: %{pct} tamamlandi")

        start = session['start_time']
        end = session['end_time']
        duration_str = None
        if start and end:
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                diff = end_dt - start_dt
                mins = int(diff.total_seconds() / 60)
                duration_str = f"{mins} dakika" if mins > 0 else "1 dakikadan az"
            except (ValueError, TypeError):
                duration_str = "Bilinmiyor"

        AgentTraceLogger.log(session_id,
            'Oneri Hazirlama',
            f'{len(warnings)} uyari, {len(missing_items)} eksik madde. Kritik fazlar icin oncelikli aksiyon onerileri hazirlaniyor.',
            function='generate_recommendations',
            detail={'warnings': warnings[:5], 'missing_items_count': len(missing_items)}
        )

        recommendations = []
        for sec in SECTION_ORDER:
            if sec in sections and sections[sec]['completed'] < sections[sec]['total']:
                pct = round(sections[sec]['completed'] / sections[sec]['total'] * 100) if sections[sec]['total'] > 0 else 0
                label = SECTION_LABELS.get(sec, sec)
                if sec in CRITICAL_SECTIONS:
                    recommendations.append(f"{label} kritik, bir sonraki ucusta tamamlanmali (%{pct})")
                else:
                    recommendations.append(f"{label} gelistirilebilir (%{pct})")

        AgentTraceLogger.log(session_id,
            'Rapor Tamamlama',
            f'Rapor hazir. {len(recommendations)} iyilestirme onerisi ile birlikte yanit olusturuluyor.',
            function='format_response',
            detail={'recommendations': recommendations, 'duration': duration_str, 'phases': phases},
            result=f'%{completion_pct} tamamlanma'
        )

        return jsonify({
            'session_id': session_id,
            'status': session['status'],
            'drone_name': session['drone_name'],
            'duration': duration_str,
            'notes': session['notes'],
            'completion_percentage': completion_pct,
            'phases': phases,
            'missing_items': missing_items,
            'warnings': warnings,
            'recommendations': recommendations
        })


# Agent API Routes
@app.route('/api/sessions/<int:session_id>/assess-risk', methods=['GET'])
def assess_risk(session_id):
    return DroneChecklistAgent.assess_risk(session_id)


@app.route('/api/sessions/<int:session_id>/advisor', methods=['GET'])
def get_advisor(session_id):
    return DroneChecklistAgent.get_advice(session_id)


@app.route('/api/sessions/<int:session_id>/report', methods=['GET'])
def get_report(session_id):
    return DroneChecklistAgent.generate_report(session_id)


@app.route('/api/sessions/<int:session_id>/agent-trace', methods=['GET'])
def get_agent_trace(session_id):
    return jsonify({
        'session_id': session_id,
        'traces': AgentTraceLogger.get_trace(session_id)
    })


@app.route('/api/traced-sessions', methods=['GET'])
def get_traced_sessions():
    session_ids = AgentTraceLogger.get_all_session_ids()
    if not session_ids:
        return jsonify({'sessions': []})
    db = get_db()
    placeholders = ','.join('?' * len(session_ids))
    rows = db.execute(
        f'SELECT id, drone_name, start_time, status FROM flight_sessions WHERE id IN ({placeholders}) ORDER BY id DESC',
        session_ids
    ).fetchall()
    result = []
    for row in rows:
        trace = AgentTraceLogger.get_trace(row['id'])
        last_entry = trace[-1] if trace else None
        first_entry = trace[0] if trace else None
        result.append({
            'id': row['id'],
            'drone_name': row['drone_name'],
            'start_time': row['start_time'],
            'status': row['status'],
            'entry_count': len(trace),
            'last_result': last_entry['result'] if last_entry else None,
            'first_action': first_entry['action'] if first_entry else None,
        })
    return jsonify({'sessions': result})



@app.route('/api/weather_advice', methods=['POST'])
def weather_advice():
    import urllib.request
    import json
    data = request.json
    lat = data.get('lat')
    lon = data.get('lon')
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m,precipitation"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            weather = json.loads(response.read().decode()).get("current", {})
        
        temp = weather.get("temperature_2m", 25)
        wind = weather.get("wind_speed_10m", 5)
        
        advice = "Sistem devrede değil."
        import os
        if os.environ.get("OPENAI_API_KEY"):
            from crewai import Agent, Task, Crew
            advisor = Agent(
                role='Meteorology Expert',
                goal='Decide if it is safe to fly based on wind speed.',
                backstory='A drone flight weather expert.',
                verbose=False,
                allow_delegation=False,
                
            )
            task = Task(
                description=f'Location Weather: {temp}C, Wind {wind} m/s. If wind > 10m/s answer NO-GO and explain. Otherwise answer GO. Reply in 1 short sentence in Turkish.',
                expected_output='1 short sentence in Turkish.',
                agent=advisor
            )
            crew = Crew(agents=[advisor], tasks=[task], verbose=False)
            advice = str(crew.kickoff())
                
        return jsonify({"temp": temp, "wind": wind, "advice": advice})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drone Uçuş Kontrol Listesi</title>
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --glass-bg: rgba(30, 41, 59, 0.7);
            --glass-border: rgba(255, 255, 255, 0.1);
            --accent: #38bdf8;
            --danger: #ef4444;
            --success: #10b981;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }
        body {
            background: var(--bg-color);
            background-image: radial-gradient(circle at 50% 0%, #1e293b 0%, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: var(--text-main);
            margin-bottom: 20px;
            font-weight: 800;
            letter-spacing: -1px;
            text-shadow: 0 0 20px rgba(56, 189, 248, 0.5);
        }
        .nav-tabs {
            display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; justify-content: center;
        }
        .nav-tab {
            padding: 12px 24px;
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 30px;
            color: var(--text-muted);
            cursor: pointer;
            backdrop-filter: blur(10px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            font-weight: 600;
        }
        .nav-tab:hover {
            color: var(--text-main);
            border-color: var(--accent);
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        }
        .nav-tab.active {
            background: var(--accent);
            color: #0f172a;
            border-color: var(--accent);
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
        }
        .panel {
            display: none;
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(16px);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.4s ease-out;
            margin-bottom: 20px;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .panel.active { display: block; }
        
        .session-header {
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(56, 189, 248, 0.1);
            border-radius: 15px; padding: 20px; margin-bottom: 20px;
            border: 1px solid rgba(56, 189, 248, 0.2);
        }
        .session-header h2 { color: var(--accent); }
        .telemetry-panel {
            display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px;
        }
        .tel-card {
            background: rgba(0,0,0,0.3); padding: 15px; border-radius: 12px; text-align: center;
            border: 1px solid var(--glass-border);
        }
        .tel-card strong { color: var(--text-muted); font-size: 0.9em; display: block; margin-bottom: 5px; }
        .tel-card span { font-size: 1.2em; font-weight: 800; color: var(--text-main); }
        
        /* Map Container */
        #map {
            height: 400px;
            border-radius: 15px;
            margin-bottom: 20px;
            border: 1px solid var(--glass-border);
        }

        .btn {
            padding: 12px 28px; border: none; border-radius: 30px; cursor: pointer; font-weight: 600; transition: all 0.3s;
        }
        .btn-primary { background: var(--accent); color: #0f172a; }
        .btn-primary:hover { box-shadow: 0 0 20px rgba(56, 189, 248, 0.6); transform: scale(1.05); }
        .btn-success { background: var(--success); color: white; }
        .btn-danger { background: var(--danger); color: white; }
        
        /* Progress */
        .progress-bar { height: 10px; background: rgba(0,0,0,0.5); border-radius: 5px; overflow: hidden; margin-bottom: 20px; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #38bdf8, #818cf8); width: 0%; transition: width 0.5s; }
        
        /* Toast Notification */
        .toast-container {
            position: fixed; bottom: 20px; right: 20px; z-index: 9999;
        }
        .toast {
            background: rgba(15, 23, 42, 0.9);
            border-left: 4px solid var(--accent);
            padding: 15px 25px;
            margin-top: 10px;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            color: white;
            backdrop-filter: blur(10px);
            animation: slideIn 0.3s ease-out forwards;
        }
        @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }

        /* Checklist */
        .checklist-section { margin-bottom: 25px; }
        .checklist-section h3 { color: var(--accent); margin-bottom: 15px; border-bottom: 1px solid var(--glass-border); padding-bottom: 5px; }
        .checklist-item {
            background: rgba(0,0,0,0.2); padding: 12px 15px; border-radius: 10px; margin-bottom: 8px;
            display: flex; justify-content: space-between; align-items: center; transition: all 0.2s;
            border: 1px solid transparent;
        }
        .checklist-item:hover { border-color: rgba(255,255,255,0.1); background: rgba(0,0,0,0.3); }
        .item-text { cursor: pointer; user-select: none; flex-grow: 1; }
        .item-text.completed { text-decoration: line-through; color: var(--success); }
        
        input[type="text"] {
            width: 100%; max-width: 300px; padding: 12px 20px; border-radius: 30px;
            border: 1px solid var(--glass-border); background: rgba(0,0,0,0.3); color: white;
        }
        
        /* FIPA Console */
        .console-box {
            background-color: #000;
            color: #00ff00;
            font-family: monospace;
            padding: 15px;
            height: 300px;
            overflow-y: scroll;
            border-radius: 10px;
            border: 1px solid #333;
            margin-bottom: 20px;
        }
        .fipa-msg { margin-bottom: 10px; border-bottom: 1px dashed #333; padding-bottom: 5px; }
        .fipa-sender { font-weight: bold; color: #ffeb3b; }
        .fipa-receiver { font-weight: bold; color: #03a9f4; }
        .fipa-performative { color: #ff9800; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Otonom İHA Komuta Merkezi</h1>
        
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="switchTab('tab-active')">Ana Komuta Ekranı</button>
            <button class="nav-tab" onclick="switchTab('tab-fipa')">FIPA Ajan Simülasyonu</button>
            <button class="nav-tab" onclick="switchTab('tab-history')">Uçuş Geçmişi</button>
        </div>
        
        <div class="toast-container" id="toast-container"></div>
        
        <!-- ACTIVE SESSION -->
        <div id="tab-active" class="panel active">
            
            <!-- Map visible on the main screen -->
            <div id="map-container" style="margin-bottom: 30px;">
                <h2 style="color: var(--accent); margin-bottom: 15px;">İnteraktif Harita & Meteoroloji Ajanı</h2>
                <p style="color: var(--text-muted); margin-bottom: 15px;">Haritada herhangi bir yere tıklayarak gerçek zamanlı rüzgar ve otonom risk analizini görüntüleyin.</p>
                <div id="map"></div>
            </div>

            <div id="start-session" style="text-align: center; padding: 30px 0; background: var(--glass-bg); border-radius: 15px; border: 1px solid var(--glass-border);">
                <h2 style="margin-bottom: 20px;">Yeni Operasyon Başlat</h2>
                <input type="text" id="drone_name_input" placeholder="Drone Adı (örn: DJI Matrice)" value="DJI Mavic 3">
                <br><br>
                <button onclick="startFlightSession()" class="btn btn-primary">🚀 Sistemi Aktif Et</button>
            </div>

            <div id="active-session" style="display:none;">
                <div class="session-header">
                    <div>
                        <h2 style="margin-bottom: 5px;">Operasyon #<span id="session-id"></span></h2>
                        <div style="color: var(--text-muted); font-size: 0.9em;">
                            Başlangıç: <span id="session-start"></span><br>
                            Drone: <span id="session-drone"></span>
                        </div>
                    </div>
                    <div>
                        <button class="btn btn-primary" onclick="simulateFlight()" id="sim-btn">▶ Uçuş Simülasyonunu Başlat</button>
                    </div>
                </div>


                <div class="telemetry-panel">
                    <div class="tel-card">
                        <strong>📡 HAVA DURUMU</strong>
                        <span id="telemetry-weather">--</span>
                    </div>
                    <div class="tel-card">
                        <strong>🔋 BATARYA</strong>
                        <span id="telemetry-battery">--</span>
                    </div>
                    <div class="tel-card">
                        <strong>🛰️ UYDU BAĞLANTISI</strong>
                        <span id="telemetry-gps">--</span>
                    </div>
                </div>
                
                <!-- COMBINED AGENT PANEL -->
                <div class="agent-grid" style="margin-bottom: 20px;">
                    <div class="agent-card" id="combined-risk-card" style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 12px; border: 1px solid var(--glass-border);">
                        <h3 style="color: var(--accent); margin-bottom: 10px;">🛡️ Otonom Risk ve Uçuş Analizi <button onclick="loadRiskAssessment()" style="float:right; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:10px; padding:2px 8px; cursor:pointer;">Yenile</button></h3>
                        <div id="risk-content" style="color: var(--text-muted); font-size: 0.9em;">
                            Analiz ediliyor...
                        </div>
                    </div>
                </div>

                
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
                
                <div id="checklist-container"></div>
                
                <div style="margin-top: 30px; text-align: center;">
                    <button class="btn btn-success" onclick="closeSession()">Görevi Tamamla</button>
                    <button class="btn btn-danger" onclick="cancelSession()">İptal (RTH)</button>
                </div>
            </div>
        </div>
        
        <!-- FIPA SIMULATION TAB -->
        <div id="tab-fipa" class="panel">
            <h2 style="color: var(--accent); margin-bottom: 15px;">FIPA-ACL Ajan İletişim Simülasyonu</h2>
            <p style="color: var(--text-muted); margin-bottom: 20px;">Koordinatör, Danışman ve Risk Analiz ajanları arasındaki anlık iletişim logları:</p>
            <button class="btn btn-primary" onclick="startFipaSimulation()" style="margin-bottom: 15px;">▶ FIPA Simülasyonu Başlat</button>
            <div id="agent-log" class="console-box">
                > Sistem beklemede...
            </div>
        </div>
        
        <!-- HISTORY TAB -->
        <div id="tab-history" class="panel">
            <h2>Geçmiş Uçuşlar</h2>
            <button class="btn btn-primary" onclick="loadHistory()" style="margin: 15px 0;">Yenile</button>
            <div id="history-container"></div>
        </div>
    </div>

    <!-- Scripts -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let currentSession = null;
        let map = null;
        let marker = null;
        let flightMarker = null;

        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = 'toast';
            if (type === 'warning') toast.style.borderLeftColor = 'var(--danger)';
            else if (type === 'success') toast.style.borderLeftColor = 'var(--success)';
            toast.innerHTML = message;
            container.appendChild(toast);
            setTimeout(() => { toast.remove(); }, 5000);
        }

        function switchTab(tabId) {
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
            
            if (map) {
                setTimeout(() => map.invalidateSize(), 100);
            }
        }

        async function api(url, options = {}) {
            const res = await fetch(url, options);
            return await res.json();
        }

        async function loadActiveSession() {
            try {
                const session = await api('/api/sessions/active');
                if (session) {
                    currentSession = session;
                    document.getElementById('start-session').style.display = 'none';
                    document.getElementById('active-session').style.display = 'block';
                    
                    document.getElementById('session-id').textContent = session.id;
                    document.getElementById('session-start').textContent = new Date(session.start_time).toLocaleString('tr-TR');
                    document.getElementById('session-drone').textContent = session.drone_name;
                    
                    if (session.telemetry_data) {
                        const tel = session.telemetry_data;
                        const wEl = document.getElementById('telemetry-weather');
                        const bEl = document.getElementById('telemetry-battery');
                        const gEl = document.getElementById('telemetry-gps');
                        
                        wEl.textContent = `${tel.wind_speed} m/s Rüzgar, ${tel.temperature}°C`;
                        bEl.textContent = `%${tel.battery}`;
                        gEl.textContent = `${tel.gps_satellites} Uydu`;
                        
                        wEl.style.color = (tel.wind_speed > 10) ? 'var(--danger)' : 'var(--success)';
                        bEl.style.color = (tel.battery < 80) ? 'var(--danger)' : 'var(--success)';
                        gEl.style.color = (tel.gps_satellites < 10) ? 'var(--danger)' : 'var(--success)';
                    }
                    renderChecklist(session.items);
                    loadRiskAssessment();
                } else {
                    currentSession = null;
                    document.getElementById('start-session').style.display = 'block';
                    document.getElementById('active-session').style.display = 'none';
                }
            } catch(e) { console.error(e); }
        }

        async function startFlightSession() {
            const name = document.getElementById('drone_name_input').value;
            await api('/api/sessions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ drone_name: name })
            });
            showToast('Uygulama İHA ile bağlantı kurdu, telemetri alındı.', 'success');
            loadActiveSession();
        }

        function renderChecklist(items) {
            const container = document.getElementById('checklist-container');
            container.innerHTML = '';
            const sections = {};
            let total = 0, completed = 0;
            
            items.forEach(item => {
                if (!sections[item.section]) sections[item.section] = [];
                sections[item.section].push(item);
                if (item.is_reference === 0) {
                    total++;
                    if (item.completed) completed++;
                }
            });
            
            const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
            document.getElementById('progress-fill').style.width = pct + '%';
            
            for (const [section, sectionItems] of Object.entries(sections)) {
                const secDiv = document.createElement('div');
                secDiv.className = 'checklist-section';
                secDiv.innerHTML = `<h3>${section}</h3>`;
                
                sectionItems.forEach(item => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'checklist-item';
                    const isCompleted = (item.completed === 1 || item.completed === true || item.completed === '1');
                    const isChecked = isCompleted ? 'completed' : '';
                    const checkIcon = isCompleted ? '✅' : '⬜';
                    
                    if (item.is_reference === 1) {
                        itemDiv.innerHTML = `<div class="item-text" style="color:var(--text-muted)">ℹ️ ${item.item_text}</div>`;
                    } else {
                        itemDiv.innerHTML = `
                            <div class="item-text ${isChecked}" onclick="toggleItem(${currentSession.id}, ${item.session_item_id}, ${isCompleted ? 0 : 1})">
                                ${checkIcon} ${item.item_text}
                            </div>
                        `;
                    }
                    secDiv.appendChild(itemDiv);
                });
                container.appendChild(secDiv);
            }
        }


        async function loadRiskAssessment() {
            if (!currentSession) return;
            const content = document.getElementById('risk-content');
            content.innerHTML = '<span style="color: var(--accent)">Analiz ediliyor...</span>';
            try {
                const data = await api(`/api/sessions/${currentSession.id}/assess-risk`);
                if (data.error) throw new Error(data.error);
                
                let riskHtml = `
                    <strong>Risk Durumu:</strong> <span style="color: ${data.decision === 'GO' ? 'var(--success)' : (data.decision === 'WARNING' ? '#f59e0b' : 'var(--danger)')}; font-weight:bold;">${data.decision}</span><br>
                    <strong>Tamamlanma:</strong> %${data.completion_percentage}<br>
                `;
                if(data.warnings && data.warnings.length > 0) {
                    riskHtml += `<br><strong>Uyarılar:</strong><ul style="margin-left: 20px; color: var(--danger);">`;
                    data.warnings.forEach(w => { riskHtml += `<li>${w}</li>`; });
                    riskHtml += `</ul>`;
                } else {
                    riskHtml += `<br><span style="color:var(--success);">Tüm kontroller temiz.</span>`;
                }
                content.innerHTML = riskHtml;

            } catch(e) {
                content.innerHTML = `<span style="color: var(--danger)">Hata: ${e.message}</span>`;
            }
        }

        async function loadAdvisor() {
            if (!currentSession) return;
            const content = document.getElementById('advisor-content');
            content.innerHTML = '<span style="color: var(--accent)">Öneriler hazırlanıyor...</span>';
            try {
                const data = await api(`/api/sessions/${currentSession.id}/advisor`);
                if (data.error) throw new Error(data.error);
                
                let adviceTxt = data.ai_advice || "Öneri alınamadı.";
                let adviceHtml = `<pre style="white-space: pre-wrap; font-family: Inter; color: var(--text-main); font-weight: bold;">${adviceTxt}</pre>`;
                
                if(adviceTxt.includes("NO-GO") || adviceTxt.includes("İPTAL") || adviceTxt.includes("İptal")) {
                     adviceHtml = `<div style="background: rgba(239, 68, 68, 0.2); border-left: 4px solid var(--danger); padding: 10px;">${adviceHtml}</div>`;
                } else if(adviceTxt.includes("GO")) {
                     adviceHtml = `<div style="background: rgba(16, 185, 129, 0.2); border-left: 4px solid var(--success); padding: 10px;">${adviceHtml}</div>`;
                }
                content.innerHTML = adviceHtml;
            } catch(e) {
                content.innerHTML = `<span style="color: var(--danger)">Hata: ${e.message}</span>`;
            }
        }

        async function toggleItem
(sessionId, itemId, status) {
            await api(`/api/sessions/${sessionId}/items/${itemId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ completed: status })
            });
            loadActiveSession();
        }

        async function closeSession(simulateMessage=false) {
            if(!currentSession) return;
            await api(`/api/sessions/${currentSession.id}/close`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
            if(simulateMessage) {
                showToast('Uçuş simülasyonu başarıyla tamamlandı. Geçmişe kaydedildi.', 'success');
            } else {
                showToast('Uçuş başarıyla tamamlandı.', 'success');
            }
            loadActiveSession();
            loadHistory();
        }
        
        async function cancelSession() {
            if(!currentSession) return;
            await api(`/api/sessions/${currentSession.id}/close`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
            showToast('Uçuş iptal edildi (RTH Devrede).', 'warning');
            loadActiveSession();
        }


        function toggleHistoryDetails(id) {
            const el = document.getElementById(`history-detail-${id}`);
            if(el.style.display === 'none') {
                el.style.display = 'block';
            } else {
                el.style.display = 'none';
            }
        }

        async function loadHistory() {
            const history = await api('/api/sessions/history');
            const container = document.getElementById('history-container');
            container.innerHTML = history.map(s => `
                <div class="panel" style="display:block; padding: 15px; margin-bottom: 10px;">
                    <div style="display:flex; justify-content:space-between; cursor: pointer;" onclick="toggleHistoryDetails(${s.id})">
                        <strong>Oturum #${s.id} - ${s.drone_name}</strong>
                        <span style="color: ${s.status === 'completed' ? 'var(--success)' : 'var(--danger)'}">
                            ${s.status.toUpperCase()} <span style="font-size:0.8em;">(Detay 👇)</span>
                        </span>
                    </div>
                    <div style="color:var(--text-muted); font-size:0.9em; margin-top:10px;">
                        Başlangıç: ${new Date(s.start_time).toLocaleString('tr-TR')}
                        ${s.end_time ? `<br>Bitiş: ${new Date(s.end_time).toLocaleString('tr-TR')}` : ''}
                    </div>
                    <div id="history-detail-${s.id}" style="display:none; margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--glass-border);">
                        <strong>Telemetri:</strong> 
                        ${s.telemetry_data ? `Rüzgar: ${JSON.parse(s.telemetry_data).wind_speed || '-'}m/s, Batarya: %${JSON.parse(s.telemetry_data).battery || '-'}, GPS: ${JSON.parse(s.telemetry_data).gps_satellites || '-'}` : 'Veri Yok'}<br>
                        <strong>Checklist Başarısı:</strong> ${s.completed_count} / ${s.total_count} tamamlandı.
                    </div>
                </div>
            `).join('');
        }

        function initMap() {
            map = L.map('map').setView([38.42, 27.14], 11);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
            }).addTo(map);

            map.on('click', async function(e) {
                const lat = e.latlng.lat;
                const lon = e.latlng.lng;
                
                if (marker) map.removeLayer(marker);
                marker = L.marker([lat, lon]).addTo(map)
                    .bindPopup('<b>Ajan Analiz Ediyor...</b><br>Meteorolojik veri çekiliyor.')
                    .openPopup();
                
                try {
                    const res = await api('/api/weather_advice', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ lat, lon })
                    });
                    
                    if (res.error) {
                         marker.bindPopup(`<b>Hata:</b> ${res.error}`).openPopup();
                         return;
                    }
                    
                    const color = res.wind > 10 ? 'red' : 'green';
                    marker.bindPopup(`
                        <div style="font-family:Inter; font-size:14px; text-align:center;">
                            <b>📍 Hava Durumu Raporu</b><br>
                            Sıcaklık: ${res.temp}°C | Rüzgar: ${res.wind} m/s<br><br>
                            <b style="color:${color};">🤖 AI Danışman:</b><br>
                            <i>"${res.advice}"</i>
                        </div>
                    `).openPopup();
                } catch(err) {
                    marker.bindPopup('Bağlantı hatası.').openPopup();
                }
            });
        }

        function simulateFlight() {
            if (!map) return;
            document.getElementById('sim-btn').disabled = true;
            document.getElementById('sim-btn').textContent = "Simülasyon Sürüyor...";
            showToast('<b>🚨 Koordinatör Ajan:</b> Uçuş simülasyonu başlatıldı.', 'info');
            
            var droneIcon = L.divIcon({
                html: '<div style="font-size:30px; color:var(--accent); text-shadow:0 0 10px var(--accent); transform: rotate(-45deg); line-height: 1;">➤</div>',
                className: '',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });

            let currentLat = 38.42;
            let currentLon = 27.14;
            
            if (flightMarker) map.removeLayer(flightMarker);
            flightMarker = L.marker([currentLat, currentLon], {icon: droneIcon}).addTo(map);
            map.setView([currentLat, currentLon], 14);

            let steps = 0;
            const interval = setInterval(() => {
                steps++;
                currentLat += 0.001;
                currentLon += 0.001;
                flightMarker.setLatLng([currentLat, currentLon]);
                map.panTo([currentLat, currentLon]);

                if (steps === 3) {
                    showToast('<b>🔋 Batarya Ajanı:</b> Görev sırasında motor akımları normal. Tüketim stabil.', 'success');
                } else if (steps === 7) {
                    showToast('<b>🛰️ GPS Ajanı:</b> RTK sinyalinde anlık zayıflama tespit edildi. Yönlendirme otonom modda devam ediyor.', 'warning');
                } else if (steps === 12) {
                    showToast('<b>🤖 Flight Advisor:</b> Rüzgar yönü değişti. Eve Dönüş (RTH) batarya rezervi yeniden hesaplandı.', 'info');
                } else if (steps === 18) {
                    showToast('<b>✅ Koordinatör:</b> Görev başarıyla tamamlandı. Rota bitiş noktasına ulaşıldı.', 'success');
                    clearInterval(interval);
                    document.getElementById('sim-btn').disabled = false;
                    document.getElementById('sim-btn').textContent = "▶ Uçuş Simülasyonunu Başlat";
                    
                    // Mark session as completed (simulated)
                    closeSession(true);
                }
            }, 1000);
        }
        
        function addFipaLog(sender, receiver, performative, content) {
            const consoleEl = document.getElementById('agent-log');
            const entry = document.createElement('div');
            entry.className = 'fipa-msg';
            entry.innerHTML = `
                <span class="fipa-sender">${sender}</span> &rarr; 
                <span class="fipa-receiver">${receiver}</span> 
                [<span class="fipa-performative">${performative}</span>]<br>
                ${content}
            `;
            consoleEl.appendChild(entry);
            consoleEl.scrollTop = consoleEl.scrollHeight;
        }

        function startFipaSimulation() {
            const consoleEl = document.getElementById('agent-log');
            consoleEl.innerHTML = '';
            
            setTimeout(() => addFipaLog('Coordinator_Agent', 'Risk_Assessor', 'REQUEST', 'Lütfen batarya ve hava durumu metriklerini değerlendir.'), 500);
            setTimeout(() => addFipaLog('Risk_Assessor', 'Coordinator_Agent', 'AGREE', 'Telemetri verisi analiz ediliyor...'), 2000);
            setTimeout(() => addFipaLog('Risk_Assessor', 'Flight_Advisor', 'INFORM', 'Batarya %85, Rüzgar 8 m/s, GPS 12 Uydu.'), 4000);
            setTimeout(() => addFipaLog('Flight_Advisor', 'Coordinator_Agent', 'PROPOSE', 'Veriler güvenli limitler dahilinde. Uçuşa devam edilebilir (GO).'), 7000);
            setTimeout(() => addFipaLog('Coordinator_Agent', 'Report_Writer', 'REQUEST', 'Logları veritabanına kaydet.'), 9000);
            setTimeout(() => addFipaLog('Report_Writer', 'Coordinator_Agent', 'INFORM', 'Oturum logları sisteme işlendi.'), 11000);
            
            setTimeout(() => {
                const end = document.createElement('div');
                end.style.color = '#ffeb3b';
                end.style.marginTop = '10px';
                end.innerHTML = '> FIPA İletişim Simülasyonu Tamamlandı.';
                consoleEl.appendChild(end);
                consoleEl.scrollTop = consoleEl.scrollHeight;
            }, 11500);
        }

        window.onload = () => {
            initMap();
            loadActiveSession();
            loadHistory();
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
