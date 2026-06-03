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
            notes TEXT
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
    cursor = db.execute(
        'INSERT INTO flight_sessions (start_time, drone_name, status) VALUES (?, ?, ?)',
        (start_time, drone_name, 'active')
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
    
    return jsonify({
        'id': session['id'],
        'start_time': session['start_time'],
        'drone_name': session['drone_name'],
        'status': session['status'],
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
                advisor_agent = Agent(
                    role='Flight Advisor',
                    goal='Provide actionable next steps for a solar drone flight.',
                    backstory='Experienced GES drone flight safety advisor.',
                    verbose=False,
                    allow_delegation=False,
                    llm="google/gemini-2.5-flash:free"
                )
                task = Task(
                    description=f'Current phase: {current_phase}. Next steps: {next_steps[:3]}. Blockers: {blockers[:2]}. Provide a 2-sentence advice for the operator.',
                    expected_output='2-sentence advice in Turkish.',
                    agent=advisor_agent
                )
                crew = Crew(agents=[advisor_agent], tasks=[task], verbose=False)
                ai_advice = str(crew.kickoff())
                AgentTraceLogger.log(session_id, 'LLM Advice', 'CrewAI Flight Advisor gave advice', detail={'advice': ai_advice}, function='crew_kickoff')
        except Exception as e:
            AgentTraceLogger.log(session_id, 'LLM Error', str(e), function='crew_kickoff')

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


# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drone Uçuş Kontrol Listesi</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            color: #00d4ff;
            margin-bottom: 30px;
            font-size: 2em;
        }
        
        .nav-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .nav-tab {
            padding: 12px 20px;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 8px;
            color: #fff;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        
        .nav-tab:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .nav-tab.active {
            background: #00d4ff;
            color: #1a1a2e;
            font-weight: bold;
        }
        
        .panel {
            display: none;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .panel.active {
            display: block;
        }
        
        .session-header {
            background: rgba(0,212,255,0.2);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .session-header h2 {
            color: #00d4ff;
            margin-bottom: 10px;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s;
            margin: 5px;
        }
        
        .btn-primary {
            background: #00d4ff;
            color: #1a1a2e;
            font-weight: bold;
        }
        
        .btn-primary:hover {
            background: #00b8d4;
            transform: translateY(-2px);
        }
        
        .btn-success {
            background: #4caf50;
            color: #fff;
        }
        
        .btn-danger {
            background: #f44336;
            color: #fff;
        }
        
        .btn-secondary {
            background: rgba(255,255,255,0.2);
            color: #fff;
        }
        
        .section-title {
            color: #ff9800;
            margin: 20px 0 10px 0;
            padding-bottom: 5px;
            border-bottom: 2px solid #ff9800;
            font-size: 1.2em;
        }
        
        .checklist-item {
            display: flex;
            align-items: center;
            padding: 12px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            margin: 8px 0;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .checklist-item:hover {
            background: rgba(255,255,255,0.1);
        }
        
        .checklist-item.completed {
            background: rgba(76,175,80,0.2);
        }
        
        .checklist-item input[type="checkbox"] {
            width: 22px;
            height: 22px;
            margin-right: 15px;
            cursor: pointer;
            accent-color: #4caf50;
        }
        
        .checklist-item label {
            flex: 1;
            cursor: pointer;
            font-size: 15px;
        }
        
        .checklist-item.completed label {
            text-decoration: line-through;
            opacity: 0.7;
        }
        
        .progress-bar {
            height: 25px;
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            overflow: hidden;
            margin: 15px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4ff, #4caf50);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: #1a1a2e;
            font-size: 14px;
        }
        
        .reference-panel {
            background: rgba(255,152,0,0.15);
            border: 2px solid #ff9800;
        }
        
        .reference-panel .section-title {
            color: #ff5722;
            border-bottom-color: #ff5722;
        }
        
        .reference-item {
            background: rgba(255,152,0,0.2);
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 4px solid #ff9800;
        }
        
        .reference-item strong {
            color: #ff9800;
        }
        
        .history-card {
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .history-card:hover {
            background: rgba(255,255,255,0.15);
            transform: translateX(5px);
        }
        
        .history-card h3 {
            color: #00d4ff;
            margin-bottom: 5px;
        }
        
        .history-card .date {
            color: #888;
            font-size: 14px;
        }
        
        .history-card .stats {
            margin-top: 10px;
            display: flex;
            gap: 20px;
        }
        
        .history-card .stat {
            background: rgba(255,255,255,0.1);
            padding: 8px 15px;
            border-radius: 5px;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal.active {
            display: flex;
        }
        
        .modal-content {
            background: #1a1a2e;
            border-radius: 12px;
            padding: 30px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .modal-close {
            background: none;
            border: none;
            color: #fff;
            font-size: 24px;
            cursor: pointer;
        }
        
        input[type="text"], textarea {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 2px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.1);
            color: #fff;
            font-size: 16px;
            margin: 10px 0;
        }
        
        input[type="text"]:focus, textarea:focus {
            outline: none;
            border-color: #00d4ff;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        
        .empty-state h3 {
            margin-bottom: 10px;
        }
        
        .agent-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        @media (max-width: 768px) {
            .agent-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .agent-card {
            background: rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .agent-card h3 {
            font-size: 14px;
            color: #00d4ff;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .decision-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 24px;
            margin: 8px 0;
        }
        
        .decision-go {
            background: rgba(76,175,80,0.3);
            color: #4caf50;
            border: 2px solid #4caf50;
        }
        
        .decision-warning {
            background: rgba(255,152,0,0.3);
            color: #ff9800;
            border: 2px solid #ff9800;
        }
        
        .decision-nogo {
            background: rgba(244,67,54,0.3);
            color: #f44336;
            border: 2px solid #f44336;
        }
        
        .agent-stat {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .agent-stat:last-child {
            border-bottom: none;
        }
        
        .agent-stat .label {
            color: #94a3b8;
        }
        
        .agent-stat .value {
            color: #fff;
            font-weight: 600;
        }
        
        .agent-warning {
            color: #ff9800;
            font-size: 12px;
            padding: 4px 0;
        }
        
        .agent-warning::before {
            content: "⚠️ ";
        }
        
        .agent-next-step {
            padding: 6px 0;
            font-size: 13px;
            color: #e2e8f0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .agent-next-step::before {
            content: "→ ";
            color: #00d4ff;
        }
        
        .agent-blocker {
            padding: 6px 0;
            font-size: 13px;
            color: #f44336;
        }
        
        .agent-blocker::before {
            content: "🚫 ";
        }
        
        .agent-loader {
            text-align: center;
            padding: 20px;
            color: #94a3b8;
            font-size: 13px;
        }
        
        .agent-refresh-btn {
            background: none;
            border: 1px solid rgba(255,255,255,0.2);
            color: #94a3b8;
            padding: 4px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            float: right;
        }
        
        .agent-refresh-btn:hover {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        
        .agent-progress-bar {
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            overflow: hidden;
            margin: 8px 0;
        }
        
        .agent-progress-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.5s ease;
        }
        
        .agent-progress-fill.green { background: #4caf50; }
        .agent-progress-fill.yellow { background: #ff9800; }
        .agent-progress-fill.red { background: #f44336; }
        
        .report-card {
            background: rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .report-card h3 {
            color: #4caf50;
            margin-bottom: 15px;
        }
        
        .report-stat {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .report-stat .label { color: #94a3b8; }
        .report-stat .value { color: #fff; font-weight: 600; }
        
        /* === COMPACT TRACE LOG === */
        
        .trace-controls {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        .trace-controls select {
            background: rgba(255,255,255,0.08);
            color: #e2e8f0;
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            min-width: 200px;
        }
        .trace-controls select:focus { outline: none; border-color: #00d4ff; }
        .trace-controls select option { background: #1a1a2e; color: #e2e8f0; }
        .trace-status { font-size: 12px; color: #94a3b8; }
        
        /* sub-tabs within agent log */
        .trace-tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding-bottom: 8px;
        }
        .trace-tab {
            background: none;
            border: none;
            color: #64748b;
            padding: 6px 16px;
            border-radius: 6px 6px 0 0;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all .2s;
        }
        .trace-tab:hover { color: #e2e8f0; background: rgba(255,255,255,0.04); }
        .trace-tab.active { color: #00d4ff; background: rgba(0,212,255,0.1); }
        
        /* GROUP container */
        .trace-group {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 8px;
            margin-bottom: 10px;
            overflow: hidden;
        }
        .trace-group-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 14px;
            cursor: pointer;
            user-select: none;
            transition: background .15s;
        }
        .trace-group-header:hover { background: rgba(255,255,255,0.04); }
        .trace-group-arrow {
            font-size: 11px;
            color: #64748b;
            transition: transform .2s;
            width: 14px;
            text-align: center;
        }
        .trace-group-arrow.open { transform: rotate(90deg); }
        .trace-group-badge {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
            letter-spacing: 0.3px;
        }
        .trace-group-badge.assess { background: rgba(255,152,0,0.2); color: #ff9800; }
        .trace-group-badge.advice { background: rgba(0,212,255,0.2); color: #00d4ff; }
        .trace-group-badge.report { background: rgba(156,39,176,0.2); color: #ce93d8; }
        .trace-group-title {
            font-size: 13px;
            font-weight: 500;
            color: #e2e8f0;
            flex: 1;
        }
        .trace-group-meta {
            font-size: 11px;
            color: #64748b;
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .trace-group-result {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .trace-group-result.go { background: rgba(76,175,80,0.2); color: #4caf50; }
        .trace-group-result.no-go { background: rgba(244,67,54,0.2); color: #f44336; }
        .trace-group-result.warning { background: rgba(255,152,0,0.2); color: #ff9800; }
        .trace-group-result.info { background: rgba(0,212,255,0.2); color: #00d4ff; }
        
        .trace-group-body { display: none; }
        .trace-group-body.open { display: block; }
        
        /* COMPACT ENTRY (inside group) */
        .trace-entry-compact {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 6px 14px 6px 20px;
            border-top: 1px solid rgba(255,255,255,0.04);
            font-size: 12px;
            line-height: 1.4;
        }
        .trace-entry-compact:hover { background: rgba(255,255,255,0.02); }
        .trace-entry-compact .entry-line {
            flex: 1;
            min-width: 0;
        }
        .trace-entry-compact .entry-badge {
            font-size: 10px;
            font-weight: 600;
            padding: 1px 6px;
            border-radius: 3px;
            white-space: nowrap;
            letter-spacing: 0.2px;
        }
        .trace-entry-compact .entry-badge.data { background: rgba(76,175,80,0.15); color: #4caf50; }
        .trace-entry-compact .entry-badge.decision { background: rgba(255,152,0,0.15); color: #ff9800; }
        .trace-entry-compact .entry-badge.report { background: rgba(156,39,176,0.15); color: #ce93d8; }
        .trace-entry-compact .entry-badge.error { background: rgba(244,67,54,0.15); color: #f44336; }
        .trace-entry-compact .entry-fn {
            font-family: monospace;
            font-size: 11px;
            color: #64748b;
            margin-left: 6px;
        }
        .trace-entry-compact .entry-result {
            color: #4caf50;
            font-weight: 500;
            margin-left: 6px;
        }
        .trace-entry-compact .entry-time {
            font-size: 10px;
            color: #475569;
            font-family: monospace;
            white-space: nowrap;
        }
        .trace-entry-compact .entry-toggle {
            background: none;
            border: none;
            color: #64748b;
            cursor: pointer;
            font-size: 10px;
            padding: 0 4px;
        }
        .trace-entry-compact .entry-toggle:hover { color: #94a3b8; }
        .trace-entry-compact .entry-thought {
            display: none;
            font-size: 11px;
            color: #94a3b8;
            padding: 6px 10px;
            margin-top: 4px;
            background: rgba(0,0,0,0.2);
            border-radius: 4px;
            font-style: italic;
            line-height: 1.5;
        }
        .trace-entry-compact .entry-thought.open { display: block; }
        .trace-entry-compact .entry-detail {
            display: none;
            font-size: 10px;
            color: #64748b;
            font-family: monospace;
            padding: 6px 10px;
            margin-top: 4px;
            background: rgba(0,0,0,0.25);
            border-radius: 4px;
            white-space: pre-wrap;
            line-height: 1.5;
            max-height: 150px;
            overflow-y: auto;
        }
        .trace-entry-compact .entry-detail.open { display: block; }
        
        .trace-entry-compact .entry-crewai {
            display: inline-block;
            font-size: 9px;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 3px;
            background: rgba(0,212,255,0.25);
            color: #00d4ff;
            margin-left: 6px;
            letter-spacing: 0.5px;
        }
        
        /* === CREWAI FLOW VISUALIZATION === */
        .crewai-flow {
            padding: 10px 0;
        }
        .crewai-flow-agent {
            background: linear-gradient(135deg, rgba(0,212,255,0.15), rgba(0,212,255,0.05));
            border: 1px solid rgba(0,212,255,0.3);
            border-radius: 10px;
            padding: 16px 20px;
            text-align: center;
            margin-bottom: 0;
            position: relative;
        }
        .crewai-flow-agent .flow-label {
            font-size: 10px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .crewai-flow-agent .flow-name {
            font-size: 16px;
            font-weight: 700;
            color: #00d4ff;
            margin: 4px 0;
        }
        .crewai-flow-agent .flow-role {
            font-size: 12px;
            color: #94a3b8;
        }
        .flow-arrow-down {
            text-align: center;
            color: #00d4ff;
            font-size: 18px;
            line-height: 1;
            padding: 2px 0;
            position: relative;
        }
        .flow-arrow-down::after {
            content: '';
            display: block;
            width: 2px;
            height: 14px;
            background: linear-gradient(to bottom, rgba(0,212,255,0.5), rgba(0,212,255,0.2));
            margin: 0 auto;
        }
        .crewai-flow-tasks {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .crewai-flow-task {
            flex: 1;
            min-width: 180px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 12px;
        }
        .crewai-flow-task .task-header {
            font-size: 12px;
            font-weight: 600;
            color: #e2e8f0;
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        .crewai-flow-task .task-tools {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .crewai-flow-task .task-tools li {
            font-size: 11px;
            color: #94a3b8;
            padding: 3px 6px;
            margin: 2px 0;
            background: rgba(255,255,255,0.04);
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .crewai-flow-task .task-tools li .tool-check {
            color: #4caf50;
            font-weight: bold;
        }
        .crewai-flow-task .task-tools li .tool-pending {
            color: #64748b;
        }
        .crewai-flow-task .task-result {
            margin-top: 8px;
            padding: 6px 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 4px;
            font-size: 11px;
            color: #ff9800;
            text-align: center;
            border: 1px solid rgba(255,152,0,0.2);
        }
        .crewai-flow-task .task-result.done { color: #4caf50; border-color: rgba(76,175,80,0.2); }
        
        .trace-empty {
            text-align: center;
            padding: 40px 20px;
            color: #64748b;
        }
        .trace-empty h3 { color: #94a3b8; margin-bottom: 8px; font-size: 16px; }
        .trace-empty p { font-size: 13px; }
        
        @media (max-width: 600px) {
            .nav-tabs {
                flex-direction: column;
            }
            
            .nav-tab {
                text-align: center;
            }
        }
        /* === FIPA SIMULATION === */
        .fipa-container { display: flex; flex-direction: column; gap: 20px; margin-top: 20px; }
        .fipa-nodes { display: flex; justify-content: space-around; align-items: center; position: relative; height: 120px; background: rgba(0,212,255,0.05); border-radius: 10px; border: 1px solid rgba(0,212,255,0.2); }
        .fipa-node { text-align: center; z-index: 2; }
        .fipa-circle { width: 60px; height: 60px; border-radius: 50%; background: #16213e; border: 2px solid #00d4ff; display: flex; align-items: center; justify-content: center; font-size: 24px; margin: 0 auto; box-shadow: 0 0 10px rgba(0,212,255,0.5); transition: all 0.3s; }
        .fipa-node.active .fipa-circle { background: #00d4ff; color: #16213e; box-shadow: 0 0 20px #00d4ff; }
        .fipa-label { margin-top: 8px; font-size: 12px; font-weight: bold; color: #94a3b8; }
        .fipa-line { position: absolute; top: 50%; left: 10%; right: 10%; height: 2px; background: rgba(0,212,255,0.2); z-index: 1; transform: translateY(-50%); }
        .fipa-msg-anim { position: absolute; top: -15px; font-size: 20px; opacity: 0; transition: all 0.5s ease-in-out; z-index: 3; }
        
        .fipa-console { background: #0b1121; border-radius: 8px; border: 1px solid #334155; padding: 15px; font-family: monospace; height: 300px; overflow-y: auto; }
        .fipa-log-entry { margin-bottom: 8px; font-size: 13px; line-height: 1.4; border-left: 3px solid #334155; padding-left: 10px; }
        .fipa-log-entry .sender { color: #00d4ff; font-weight: bold; }
        .fipa-log-entry .receiver { color: #facc15; font-weight: bold; }
        .fipa-log-entry .performative { color: #ec4899; font-weight: bold; text-transform: uppercase; }
        .fipa-log-entry .content { color: #cbd5e1; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚁 Drone Uçuş Kontrol Listesi</h1>
        
        <div class="nav-tabs">
            <button class="nav-tab active" data-panel="active" onclick="showPanel('active')">Aktif Uçuş</button>
            <button class="nav-tab" data-panel="history" onclick="showPanel('history')">Geçmiş Uçuşlar</button>
            <button class="nav-tab" data-panel="reference" onclick="showPanel('reference')">Acil Durum Rehberi</button>
            <button class="nav-tab" id="tab-agentlog" data-panel="agentlog" onclick="showPanel('agentlog')" style="display:none;">🤖 Agent Log</button>
            <button class="nav-tab" data-panel="fipa" onclick="showPanel('fipa')">🌐 FIPA Simülasyonu</button>
        </div>
        
        <!-- Active Session Panel -->
        <div id="panel-active" class="panel active">
            <div id="session-info">
                <div class="empty-state" id="no-session">
                    <h3>Henüz Aktif Uçuş Yok</h3>
                    <p>Yeni bir uçuş başlatmak için aşağıdaki butona tıklayın</p>
                </div>
                
                <div id="active-session" style="display:none;">
                    <div class="session-header">
                        <h2>Uçuş Oturumu #<span id="session-id"></span></h2>
                        <p>Başlangıç: <span id="session-start"></span></p>
                        <p>Drone: <span id="session-drone"></span></p>
                    </div>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill" style="width: 0%;">0%</div>
                    </div>
                    
                    <!-- Agent Panels -->
                    <div class="agent-grid">
                        <div class="agent-card" id="risk-card">
                            <h3>🛡️ Risk Degerlendirmesi <button class="agent-refresh-btn" onclick="loadRiskAssessment()">Yenile</button></h3>
                            <div id="risk-content">
                                <div class="agent-loader">Analiz ediliyor...</div>
                            </div>
                        </div>
                        <div class="agent-card" id="advisor-card">
                            <h3>🎯 Checklist Danismani <button class="agent-refresh-btn" onclick="loadAdvisor()">Yenile</button></h3>
                            <div id="advisor-content">
                                <div class="agent-loader">Oneriler hazirlaniyor...</div>
                            </div>
                        </div>
                    </div>
                    
                    <div id="checklist-container"></div>
                    
                    <div style="margin-top: 20px; text-align: center;">
                        <button class="btn btn-success" onclick="closeSession()">Uçuşu Tamamla</button>
                        <button class="btn btn-danger" onclick="cancelSession()">İptal Et</button>
                    </div>
                </div>
            </div>
            
            <div id="start-session">
                <form action="/new-flight" method="POST" style="text-align: center; margin-top: 30px;">
                    <input type="text" name="drone_name" placeholder="Drone Adı (opsiyonel)" value="DJI Mavic 3">
                    <br><br>
                    <button type="submit" class="btn btn-primary">🚀 Yeni Uçuş Başlat</button>
                </form>
            </div>
        </div>
        
        <!-- History Panel -->
        <div id="panel-history" class="panel">
            <h2 style="color: #00d4ff; margin-bottom: 20px;">Geçmiş Uçuşlar</h2>
            <div id="history-list"></div>
        </div>
        
        <!-- Emergency Reference Panel -->
        <div id="panel-reference" class="panel reference-panel">
            <h2 style="color: #ff5722; margin-bottom: 20px;">Acil Durum Prosedürleri</h2>
            <p style="margin-bottom: 20px; color: #ff9800;">Bu bölüm referans amaçlıdır, her uçuşta işaretlenmesi gerekmez.</p>
            <div id="emergency-reference"></div>
        </div>
        
        <!-- Agent Log Panel -->
        <div id="panel-agentlog" class="panel">
            <h2 style="color: #00d4ff; margin-bottom: 20px;">Agent Düşünce Süreci</h2>
            
            <div class="trace-controls">
                <select id="trace-session-select" onchange="switchTraceSession()">
                    <option value="">Uçuş Seçin...</option>
                </select>
                <button class="agent-refresh-btn" onclick="loadAgentTrace()" style="font-size:13px; padding:6px 16px;">Yenile</button>
                <span class="trace-status" id="trace-status"></span>
            </div>
            
            <div class="trace-tabs">
                <button class="trace-tab active" id="trace-tab-log" onclick="switchTraceTab('log')">📋 İşlem Kaydı</button>
                <button class="trace-tab" id="trace-tab-flow" onclick="switchTraceTab('flow')">🔄 CrewAI Akışı</button>
            </div>
            
            <div id="trace-log-panel">
                <div id="trace-container">
                    <div class="trace-empty">
                        <h3>Henüz agent log kaydı yok</h3>
                        <p>Agent fonksiyonlarını çağırmak için checklist ile etkileşime geçin veya bir uçuş seçin</p>
                    </div>
                </div>
            </div>
            
            <div id="trace-flow-panel" style="display:none;">
                <div id="crewai-flow-container">
                    <div class="trace-empty">
                        <h3>CrewAI Akışı</h3>
                        <p>Bu panel CrewAI agent'ının task ve tool akışını görselleştirir. Bir uçuş seçin ve agent fonksiyonlarını çağırın.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- FIPA Simulation Panel -->
    <div id="panel-fipa" class="panel">
        <h2 style="color: #00d4ff; margin-bottom: 10px;">FIPA-ACL Çoklu Ajan Simülasyonu</h2>
        <p style="color: #94a3b8; margin-bottom: 20px;">Bu panel, GES uçuş denetimlerinde ajanlar arası iletişimi ve FIPA standartlarını gösterir.</p>
        
        <button class="btn btn-primary" onclick="runFipaSimulation()">▶ Simülasyonu Başlat</button>
        
        <div class="fipa-container">
            <div class="fipa-nodes">
                <div class="fipa-line"></div>
                <div class="fipa-node" id="fipa-co">
                    <div class="fipa-circle">👨‍✈️</div>
                    <div class="fipa-label">Koordinatör</div>
                </div>
                <div class="fipa-node" id="fipa-ra">
                    <div class="fipa-circle">🛡️</div>
                    <div class="fipa-label">Risk Analisti</div>
                </div>
                <div class="fipa-node" id="fipa-ad">
                    <div class="fipa-circle">🎯</div>
                    <div class="fipa-label">Uçuş Danışmanı</div>
                </div>
                <div class="fipa-node" id="fipa-rp">
                    <div class="fipa-circle">📊</div>
                    <div class="fipa-label">Raporlayıcı</div>
                </div>
            </div>
            
            <div class="fipa-console" id="fipa-console">
                <div style="color: #64748b;">[Sistem] Simülasyon bekleniyor...</div>
            </div>
        </div>
    </div>
    
    <!-- Session Detail Modal -->
    <div id="session-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modal-title">Uçuş Detayı</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div id="modal-body"></div>
        </div>
    </div>
    
    <script>
        let currentSession = null;
        
        async function api(url, options = {}) {
            const response = await fetch(url, options);
            if (!response.ok) throw new Error('HTTP ' + response.status);
            return response.json();
        }
        
        function showPanel(name) {
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.getElementById('panel-' + name).classList.add('active');
            // Find and activate the nav-tab by data attribute
            document.querySelectorAll('.nav-tab').forEach(function(t) {
                if (t.getAttribute('data-panel') === name) t.classList.add('active');
            });
            
            if (name === 'active') loadActiveSession();
            if (name === 'history') loadHistory();
            if (name === 'reference') loadEmergencyReference();
            if (name === 'agentlog') { loadTraceSessions(); loadAgentTrace(); }
        }
        
        // FIPA Simulation Logic
        async function runFipaSimulation() {
            const consoleEl = document.getElementById('fipa-console');
            consoleEl.innerHTML = '<div style="color: #64748b;">[Sistem] Simülasyon başlatıldı...</div>';
            
            const logs = [
                { s: 'Koordinatör', r: 'Risk Analisti', p: 'REQUEST', c: 'GES Site #3 için uçuş güvenliği analizini yap', nodeS: 'fipa-co', nodeR: 'fipa-ra', delay: 1000 },
                { s: 'Risk Analisti', r: 'Koordinatör', p: 'INFORM', c: 'Risk: LOW. Batarya %90, Rüzgar: 4m/s. Uçuşa Uygun (GO)', nodeS: 'fipa-ra', nodeR: 'fipa-co', delay: 2500 },
                { s: 'Koordinatör', r: 'Uçuş Danışmanı', p: 'REQUEST', c: 'Sonraki kritik adımları belirle', nodeS: 'fipa-co', nodeR: 'fipa-ad', delay: 4000 },
                { s: 'Uçuş Danışmanı', r: 'Koordinatör', p: 'PROPOSE', c: 'Öneri: Termal kamera kalibrasyonunu tamamlayın.', nodeS: 'fipa-ad', nodeR: 'fipa-co', delay: 5500 },
                { s: 'Koordinatör', r: 'Uçuş Danışmanı', p: 'ACCEPT_PROPOSAL', c: 'Öneri kabul edildi.', nodeS: 'fipa-co', nodeR: 'fipa-ad', delay: 6500 },
                { s: 'Koordinatör', r: 'Raporlayıcı', p: 'REQUEST', c: 'Uçuş özetini ve panel istatistiklerini derle', nodeS: 'fipa-co', nodeR: 'fipa-rp', delay: 8000 },
                { s: 'Raporlayıcı', r: 'Koordinatör', p: 'INFORM', c: 'Rapor hazır. 2 uyarı, 0 kritik eksik. Süre: 4dk.', nodeS: 'fipa-rp', nodeR: 'fipa-co', delay: 10000 }
            ];
            
            logs.forEach(log => {
                setTimeout(() => {
                    // Log to console
                    const entry = document.createElement('div');
                    entry.className = 'fipa-log-entry';
                    entry.innerHTML = `<span class="sender">${log.s}</span> -> <span class="receiver">${log.r}</span> | <span class="performative">[${log.p}]</span> <br><span class="content">"${log.c}"</span>`;
                    consoleEl.appendChild(entry);
                    consoleEl.scrollTop = consoleEl.scrollHeight;
                    
                    // Animate node
                    document.querySelectorAll('.fipa-node').forEach(n => n.classList.remove('active'));
                    document.getElementById(log.nodeS).classList.add('active');
                    setTimeout(() => document.getElementById(log.nodeR).classList.add('active'), 500);
                    
                }, log.delay);
            });
            
            setTimeout(() => {
                document.querySelectorAll('.fipa-node').forEach(n => n.classList.remove('active'));
                const end = document.createElement('div');
                end.innerHTML = '<div style="color: #4caf50; margin-top:10px;">[Sistem] Simülasyon tamamlandı.</div>';
                consoleEl.appendChild(end);
                consoleEl.scrollTop = consoleEl.scrollHeight;
            }, 11500);
        }
        
        function getCurrentSessionId() {
            return currentSession ? currentSession.id : null;
        }

        async function loadActiveSession() {
            try {
                const session = await api('/api/sessions/active');
                
                if (session) {
                    currentSession = session;
                    document.getElementById('no-session').style.display = 'none';
                    document.getElementById('start-session').style.display = 'none';
                    document.getElementById('active-session').style.display = 'block';
                    document.getElementById('tab-agentlog').style.display = 'inline-block';
                    
                    document.getElementById('session-id').textContent = session.id;
                    document.getElementById('session-start').textContent = new Date(session.start_time).toLocaleString('tr-TR');
                    document.getElementById('session-drone').textContent = session.drone_name;
                    
                    renderChecklist(session.items);
                    loadRiskAssessment();
                    loadAdvisor();
                } else {
                    currentSession = null;
                    document.getElementById('no-session').style.display = 'block';
                    document.getElementById('start-session').style.display = 'block';
                    document.getElementById('active-session').style.display = 'none';
                    document.getElementById('tab-agentlog').style.display = 'none';
                }
            } catch(e) {
                console.error('loadActiveSession error:', e);
                currentSession = null;
                document.getElementById('no-session').style.display = 'block';
                document.getElementById('start-session').style.display = 'block';
                document.getElementById('active-session').style.display = 'none';
                document.getElementById('tab-agentlog').style.display = 'none';
            }
        }
        
        async function loadRiskAssessment() {
            const sid = getCurrentSessionId();
            if (!sid) return;
            
            document.getElementById('risk-content').innerHTML = '<div class="agent-loader">Analiz ediliyor...</div>';
            
            try {
                const data = await api('/api/sessions/' + sid + '/assess-risk');
                let html = '';
                
                const decisionClass = data.decision === 'GO' ? 'decision-go' : data.decision === 'WARNING' ? 'decision-warning' : 'decision-nogo';
                html += `<div class="decision-badge ${decisionClass}">${data.decision}</div>`;
                html += `<div class="agent-stat"><span class="label">Tamamlanma</span><span class="value">%${data.completion_percentage}</span></div>`;
                
                for (const [phase, info] of Object.entries(data.phase_progress)) {
                    const pct = info.percentage;
                    const barClass = pct === 100 ? 'green' : pct >= 50 ? 'yellow' : 'red';
                    html += `<div style="margin-top:10px; font-size:12px; color:#94a3b8;">${phase}: %${pct}</div>`;
                    html += `<div class="agent-progress-bar"><div class="agent-progress-fill ${barClass}" style="width:${pct}%"></div></div>`;
                }
                
                if (data.warnings && data.warnings.length > 0) {
                    html += `<div style="margin-top:10px;"><strong style="color:#ff9800; font-size:12px;">Uyarilar</strong>`;
                    data.warnings.slice(0, 4).forEach(w => {
                        html += `<div class="agent-warning">${w}</div>`;
                    });
                    html += `</div>`;
                }
                
                document.getElementById('risk-content').innerHTML = html;
            } catch(e) {
                document.getElementById('risk-content').innerHTML = '<div style="color:#f44336; font-size:13px;">Analiz hatasi</div>';
            }
        }
        
        async function loadAdvisor() {
            const sid = getCurrentSessionId();
            if (!sid) return;
            
            document.getElementById('advisor-content').innerHTML = '<div class="agent-loader">Oneriler hazirlaniyor...</div>';
            
            try {
                const data = await api('/api/sessions/' + sid + '/advisor');
                let html = '';
                
                html += `<div class="agent-stat"><span class="label">Mevcut Faz</span><span class="value">${data.current_phase}</span></div>`;
                
                if (data.ai_advice) {
                    html += `<div style="margin-top:10px; padding:10px; background:rgba(0,212,255,0.1); border-left:3px solid #00d4ff; border-radius:4px;"><strong style="color:#00d4ff; font-size:12px;">🤖 AI Tavsiyesi</strong><div style="font-size:13px; margin-top:5px; color:#cbd5e1;">${data.ai_advice}</div></div>`;
                }
                
                if (data.next_steps && data.next_steps.length > 0) {
                    html += `<div style="margin-top:10px;"><strong style="color:#00d4ff; font-size:12px;">Sonraki Adimlar</strong>`;
                    data.next_steps.forEach(s => {
                        html += `<div class="agent-next-step">${s}</div>`;
                    });
                    html += `</div>`;
                }
                
                if (data.blockers && data.blockers.length > 0) {
                    html += `<div style="margin-top:10px;"><strong style="color:#f44336; font-size:12px;">Blokajlar</strong>`;
                    data.blockers.forEach(b => {
                        html += `<div class="agent-blocker">${b}</div>`;
                    });
                    html += `</div>`;
                }
                
                document.getElementById('advisor-content').innerHTML = html;
            } catch(e) {
                document.getElementById('advisor-content').innerHTML = '<div style="color:#f44336; font-size:13px;">Danisman hatasi</div>';
            }
        }
        
        var traceSessionHistory = [];
        
        async function loadTraceSessions() {
            try {
                const data = await api('/api/traced-sessions');
                traceSessionHistory = data.sessions || [];
                const sel = document.getElementById('trace-session-select');
                var currentVal = sel.value;
                sel.innerHTML = '<option value="">Ucus Secin...</option>';
                traceSessionHistory.forEach(function(s) {
                    var opt = document.createElement('option');
                    opt.value = s.id;
                    opt.textContent = '#' + s.id + ' ' + (s.drone_name || 'Drone') + ' (' + (s.status === 'active' ? 'Aktif' : 'Kapali') + ', ' + s.entry_count + ' kayit)';
                    sel.appendChild(opt);
                });
                if (currentVal && currentVal !== '') sel.value = currentVal;
            } catch(e) {}
        }
        
        function switchTraceSession() {
            loadAgentTrace();
        }
        
        function switchTraceTab(name) {
            document.querySelectorAll('.trace-tab').forEach(function(t) { t.classList.remove('active'); });
            document.getElementById('trace-tab-' + name).classList.add('active');
            document.getElementById('trace-log-panel').style.display = name === 'log' ? 'block' : 'none';
            document.getElementById('trace-flow-panel').style.display = name === 'flow' ? 'block' : 'none';
            if (name === 'flow') renderCrewAIFlow();
        }
        
        async function loadAgentTrace() {
            var sel = document.getElementById('trace-session-select');
            var sid = sel.value;
            var statusEl = document.getElementById('trace-status');
            
            if (!sid || sid === '') {
                sid = getCurrentSessionId();
                if (!sid) {
                    document.getElementById('trace-container').innerHTML = '<div class="trace-empty"><h3>Ucus secin</h3><p>Yukaridan bir ucus secin veya aktif ucus baslatin</p></div>';
                    statusEl.textContent = '';
                    return;
                }
                sel.value = sid;
            }
            
            statusEl.textContent = 'Yukleniyor...';
            
            try {
                const data = await api('/api/sessions/' + sid + '/agent-trace');
                var traces = data.traces || [];
                
                if (traces.length === 0) {
                    document.getElementById('trace-container').innerHTML = '<div class="trace-empty"><h3>Henuz agent log kaydi yok</h3><p>Agent fonksiyonlarini cagirmak icin checklist ile etkilesime gecin</p></div>';
                    statusEl.textContent = '0 kayit';
                    return;
                }
                
                // Group by group id
                var groups = {};
                traces.forEach(function(t) {
                    var g = t.group || 0;
                    if (!groups[g]) groups[g] = [];
                    groups[g].push(t);
                });
                
                statusEl.textContent = traces.length + ' adim, ' + Object.keys(groups).length + ' islem';
                
                var html = '';
                var groupKeys = Object.keys(groups);
                groupKeys.forEach(function(gk) {
                    var entries = groups[gk];
                    var first = entries[0];
                    var last = entries[entries.length - 1];
                    
                    // Determine group type
                    var badgeClass = 'info';
                    var badgeLabel = 'Agent';
                    if (first.function === 'query_db') {
                        // Check what follows to determine type
                        var hasDecide = entries.some(function(e) { return e.function === 'decide'; });
                        if (hasDecide) { badgeClass = 'assess'; badgeLabel = 'Risk Degerlendirme'; }
                        else if (entries.some(function(e) { return e.function === 'plan_steps'; })) { badgeClass = 'advice'; badgeLabel = 'Checklist Danismani'; }
                        else if (entries.some(function(e) { return e.function === 'generate_recommendations'; }) || entries.some(function(e) { return e.function === 'compute_stats'; })) { badgeClass = 'report'; badgeLabel = 'Rapor'; }
                    }
                    
                    var resultClass = '';
                    var resultLabel = '';
                    if (last && last.result) {
                        var r = last.result;
                        if (r === 'GO') { resultClass = 'go'; resultLabel = 'GO'; }
                        else if (r === 'NO-GO') { resultClass = 'no-go'; resultLabel = 'NO-GO'; }
                        else if (r === 'WARNING') { resultClass = 'warning'; resultLabel = 'UYARI'; }
                        else { resultClass = 'info'; resultLabel = r; }
                    }
                    
                    var groupId = 'trace-group-' + gk;
                    html += '<div class="trace-group">';
                    html += '<div class="trace-group-header" onclick="toggleTraceGroup(\\'' + groupId + '\\')">';
                    html += '<span class="trace-group-arrow" id="' + groupId + '-arrow">▶</span>';
                    html += '<span class="trace-group-badge ' + badgeClass + '">' + badgeLabel + '</span>';
                    html += '<span class="trace-group-title">#' + gk + ' - ' + (first.function || 'islem') + '()</span>';
                    html += '<span class="trace-group-meta">';
                    html += '<span>' + entries.length + ' adim</span>';
                    html += '<span>' + first.timestamp + '</span>';
                    if (resultLabel) {
                        html += '<span class="trace-group-result ' + resultClass + '">' + resultLabel + '</span>';
                    }
                    html += '</span>'; // meta
                    html += '</div>'; // header
                    
                    html += '<div class="trace-group-body" id="' + groupId + '">';
                    entries.forEach(function(t) {
                        var badgeColor = 'data';
                        if (t.action === 'Karar Verme' || t.action === 'Hata') badgeColor = 'decision';
                        if (t.action === 'Rapor Hazirlama' || t.action === 'Rapor Tamamlama' || t.action === 'Oneri Hazirlama') badgeColor = 'report';
                        if (t.action === 'Hata') badgeColor = 'error';
                        
                        var entryId = 'trace-entry-' + gk + '-' + entries.indexOf(t);
                        var crewaiMark = '';
                        if (t.is_crewai_flow) {
                            crewaiMark = '<span class="entry-crewai">CREW</span>';
                        }
                        
                        html += '<div class="trace-entry-compact">';
                        html += '<span class="entry-badge ' + badgeColor + '">' + t.action + '</span>';
                        html += '<div class="entry-line">';
                        html += '<span class="entry-fn">' + (t.function || '') + '()</span>' + crewaiMark;
                        if (t.result) {
                            html += '<span class="entry-result">→ ' + escapeHtml(t.result) + '</span>';
                        }
                        if (t.thought || t.detail) {
                            html += ' <button class="entry-toggle" onclick="toggleTraceEntry(\\'' + entryId + '\\', this)">[+]</button>';
                        }
                        if (t.thought) {
                            html += '<div class="entry-thought" id="' + entryId + '-thought">' + escapeHtml(t.thought) + '</div>';
                        }
                        if (t.detail) {
                            html += '<div class="entry-detail" id="' + entryId + '-detail">' + escapeHtml(JSON.stringify(t.detail, null, 2)) + '</div>';
                        }
                        html += '</div>'; // entry-line
                        html += '<span class="entry-time">' + t.timestamp + '</span>';
                        html += '</div>'; // trace-entry-compact
                    });
                    html += '</div>'; // trace-group-body
                    html += '</div>'; // trace-group
                });
                
                document.getElementById('trace-container').innerHTML = html;
            } catch(e) {
                statusEl.textContent = 'Yukleme hatasi';
                document.getElementById('trace-container').innerHTML = '<div class="trace-empty"><h3>Yukleme hatasi</h3><p>' + escapeHtml(e.message || 'Bilinmeyen hata') + '</p></div>';
            }
        }
        
        function toggleTraceGroup(id) {
            var body = document.getElementById(id);
            var arrow = document.getElementById(id + '-arrow');
            if (body) body.classList.toggle('open');
            if (arrow) arrow.classList.toggle('open');
        }
        
        function toggleTraceEntry(id, btn) {
            var thought = document.getElementById(id + '-thought');
            var detail = document.getElementById(id + '-detail');
            var openThought = thought && thought.classList.contains('open');
            var openDetail = detail && detail.classList.contains('open');
            
            if (thought) thought.classList.toggle('open');
            if (detail) detail.classList.toggle('open');
            
            if (btn) {
                if ((!openThought && !openDetail) || (thought && !thought.classList.contains('open') && detail && !detail.classList.contains('open'))) {
                    btn.textContent = '[-]';
                } else {
                    btn.textContent = '[+]';
                }
            }
        }
        
        function escapeHtml(str) {
            if (!str) return '';
            var div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }
        
        function renderCrewAIFlow() {
            var sel = document.getElementById('trace-session-select');
            var sid = sel.value;
            
            if (!sid || sid === '') {
                document.getElementById('crewai-flow-container').innerHTML = '<div class="trace-empty"><h3>Ucus secin</h3><p>Yukaridan bir ucus secin</p></div>';
                return;
            }
            
            // Fetch latest traces for this session and build flow
            api('/api/sessions/' + sid + '/agent-trace').then(function(data) {
                var traces = data.traces || [];
                if (traces.length === 0) {
                    document.getElementById('crewai-flow-container').innerHTML = '<div class="trace-empty"><h3>Henuz kayit yok</h3></div>';
                    return;
                }
                
                // Build task groups from trace
                var groups = {};
                traces.forEach(function(t) {
                    var g = t.group || 0;
                    if (!groups[g]) groups[g] = [];
                    groups[g].push(t);
                });
                
                // Classify each group into a CrewAI task
                var taskDefs = [];
                Object.keys(groups).forEach(function(gk) {
                    var entries = groups[gk];
                    var firstFn = entries[0] ? entries[0].function : '';
                    var lastEntry = entries[entries.length - 1];
                    
                    var taskName = 'Veri Isleme';
                    var tools = [];
                    var taskResult = lastEntry ? lastEntry.result : null;
                    
                    entries.forEach(function(t) {
                        if (t.function && tools.indexOf(t.function) === -1) {
                            tools.push(t.function);
                        }
                    });
                    
                    if (entries.some(function(e) { return e.function === 'decide'; })) {
                        taskName = 'Risk Degerlendirme';
                    } else if (entries.some(function(e) { return e.function === 'plan_steps'; })) {
                        taskName = 'Checklist Danismani';
                    } else if (entries.some(function(e) { return e.function === 'generate_recommendations'; }) || entries.some(function(e) { return e.function === 'compute_stats'; })) {
                        taskName = 'Rapor';
                    }
                    
                    taskDefs.push({
                        name: taskName,
                        tools: tools,
                        count: entries.length,
                        result: taskResult,
                    });
                });
                
                // Render flow
                var html = '<div class="crewai-flow">';
                
                // Agent node
                html += '<div class="crewai-flow-agent">';
                html += '<div class="flow-label">CrewAI Agent</div>';
                html += '<div class="flow-name">full_stack_developer</div>';
                html += '<div class="flow-role">Drone Flight Checklist Assistant</div>';
                html += '</div>';
                
                // Arrow
                html += '<div class="flow-arrow-down">▼</div>';
                
                // Tasks
                html += '<div class="crewai-flow-tasks">';
                taskDefs.forEach(function(task) {
                    var resultClass = '';
                    if (task.result === 'GO') resultClass = 'done';
                    else if (task.result === 'NO-GO') resultClass = '';
                    var resultColor = task.result === 'GO' ? 'done' : '';
                    
                    html += '<div class="crewai-flow-task">';
                    html += '<div class="task-header">📋 ' + task.name + '</div>';
                    html += '<ul class="task-tools">';
                    task.tools.forEach(function(fn) {
                        var isCrewai = traces.some(function(t) { return t.function === fn && t.is_crewai_flow; });
                        var check = isCrewai ? '<span class="tool-check">✓</span>' : '<span class="tool-pending">◷</span>';
                        html += '<li>' + check + ' ' + fn + '()</li>';
                    });
                    html += '</ul>';
                    if (task.result) {
                        html += '<div class="task-result ' + resultColor + '">→ ' + escapeHtml(task.result) + '</div>';
                    }
                    html += '</div>';
                });
                html += '</div>'; // crewai-flow-tasks
                html += '</div>'; // crewai-flow
                
                document.getElementById('crewai-flow-container').innerHTML = html;
            }).catch(function() {
                document.getElementById('crewai-flow-container').innerHTML = '<div class="trace-empty"><h3>Yukleme hatasi</h3></div>';
            });
        }
        
        function renderChecklist(items) {
            const container = document.getElementById('checklist-container');
            container.innerHTML = '';
            
            let currentSection = '';
            let totalItems = 0;
            let completedItems = 0;
            
            const sectionOrder = ['Ortam Kontrolu', 'Ucus Oncesi', 'Ucus Sirasinda', 'Acil Durum Prosedurleri', 'Ucus Sonrasi'];
            const sectionLabels = {
                'Ortam Kontrolu': 'Ortam Kontrolü',
                'Ucus Oncesi': 'Uçuş Öncesi',
                'Ucus Sirasinda': 'Uçuş Sırasında',
                'Acil Durum Prosedurleri': 'Acil Durum Prosedürleri',
                'Ucus Sonrasi': 'Uçuş Sonrası'
            };
            
            sectionOrder.forEach(section => {
                const sectionItems = items.filter(item => item.section === section);
                if (sectionItems.length === 0) return;
                
                const isReference = section === 'Acil Durum Prosedurleri';
                
                const sectionDiv = document.createElement('div');
                sectionDiv.innerHTML = `<div class="section-title">${sectionLabels[section]}</div>`;
                
                if (isReference) {
                    sectionDiv.innerHTML += '<p style="color: #ff9800; font-size: 13px; margin-bottom: 10px;">📖 Referans - İşaretlenmesi gerekmez</p>';
                }
                
                sectionItems.forEach(item => {
                    if (!item.is_reference) {
                        totalItems++;
                        if (item.completed) completedItems++;
                    }
                    
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'checklist-item' + (item.completed ? ' completed' : '');
                    itemDiv.id = 'item-' + item.session_item_id;
                    
                    const checkbox = isReference ? 
                        `<input type="checkbox" disabled title="Referans kalem">` :
                        `<input type="checkbox" ${item.completed ? 'checked' : ''} onchange="toggleItem(${item.session_item_id}, this.checked)">`;
                    
                    itemDiv.innerHTML = `
                        ${checkbox}
                        <label>${item.item_text}</label>
                    `;
                    
                    sectionDiv.appendChild(itemDiv);
                });
                
                container.appendChild(sectionDiv);
            });
            
            const progress = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;
            document.getElementById('progress-fill').style.width = progress + '%';
            document.getElementById('progress-fill').textContent = progress + '% Tamamlandı';
        }
        
        async function startSession() {
            try {
                const droneName = document.getElementById('drone-name').value || 'Varsayılan Drone';
                await api('/api/sessions', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({drone_name: droneName})
                });
                window.location.reload();
            } catch(e) {
                console.error('startSession error:', e);
                alert('Uçuş başlatılamadı: ' + (e.message || 'Bilinmeyen hata'));
            }
        }
        
        async function toggleItem(itemId, completed) {
            if (!currentSession) return;
            await api(`/api/sessions/${currentSession.id}/items/${itemId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({completed: completed})
            });
            await loadActiveSession();
        }
        
        async function closeSession() {
            if (!currentSession) return;
            
            const notes = prompt('Uçuş notları (opsiyonel):');
            await api(`/api/sessions/${currentSession.id}/close`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({notes: notes || ''})
            });
            const sid = currentSession.id;
            currentSession = null;
            await loadActiveSession();
            loadReport(sid);
        }
        
        async function loadReport(sessionId) {
            try {
                const data = await api('/api/sessions/' + sessionId + '/report');
                let html = '<div class="report-card">';
                html += '<h3>📊 Ucus Raporu</h3>';
                html += `<div class="report-stat"><span class="label">Durum</span><span class="value">${data.status}</span></div>`;
                html += `<div class="report-stat"><span class="label">Tamamlanma</span><span class="value">%${data.completion_percentage}</span></div>`;
                if (data.duration) html += `<div class="report-stat"><span class="label">Sure</span><span class="value">${data.duration}</span></div>`;
                if (data.drone_name) html += `<div class="report-stat"><span class="label">Drone</span><span class="value">${data.drone_name}</span></div>`;
                
                if (data.phases && Object.keys(data.phases).length > 0) {
                    html += '<div style="margin-top:15px;"><strong style="color:#00d4ff;">Fazlar</strong></div>';
                    for (const [phase, pct] of Object.entries(data.phases)) {
                        const barClass = pct === 100 ? 'green' : pct >= 50 ? 'yellow' : 'red';
                        html += `<div style="font-size:12px; color:#94a3b8; margin-top:8px;">${phase}: %${pct}</div>`;
                        html += `<div class="agent-progress-bar"><div class="agent-progress-fill ${barClass}" style="width:${pct}%"></div></div>`;
                    }
                }
                
                if (data.warnings && data.warnings.length > 0) {
                    html += '<div style="margin-top:15px;"><strong style="color:#ff9800; font-size:12px;">Uyarilar</strong>';
                    data.warnings.forEach(w => { html += `<div class="agent-warning">${w}</div>`; });
                    html += '</div>';
                }
                
                if (data.recommendations && data.recommendations.length > 0) {
                    html += '<div style="margin-top:10px;"><strong style="color:#4caf50; font-size:12px;">Oneriler</strong>';
                    data.recommendations.forEach(r => { html += `<div style="font-size:13px; padding:4px 0; color:#e2e8f0;">💡 ${r}</div>`; });
                    html += '</div>';
                }
                
                html += '</div>';
                
                document.getElementById('modal-title').textContent = 'Ucus Raporu #' + sessionId;
                document.getElementById('modal-body').innerHTML = html;
                document.getElementById('session-modal').classList.add('active');
            } catch(e) {
                console.error('Report error', e);
            }
        }
        
        async function cancelSession() {
            if (!currentSession) return;
            if (!confirm('Bu uçuş oturumu iptal edilecek. Emin misiniz?')) return;
            
            await api(`/api/sessions/${currentSession.id}/close`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({notes: 'İptal edildi'})
            });
            currentSession = null;
            loadActiveSession();
        }
        
        async function loadHistory() {
            const sessions = await api('/api/sessions/history');
            const container = document.getElementById('history-list');
            
            if (sessions.length === 0) {
                container.innerHTML = '<div class="empty-state"><h3>Henüz tamamlanmış uçuş yok</h3></div>';
                return;
            }
            
            container.innerHTML = sessions.map(s => `
                <div class="history-card" onclick="viewSession(${s.id})">
                    <h3>${s.drone_name} - #${s.id}</h3>
                    <div class="date">${new Date(s.start_time).toLocaleString('tr-TR')}</div>
                    <div class="stats">
                        <span class="stat">✅ ${s.completed_count}/${s.total_count} Tamamlandı</span>
                        <span class="stat">🕐 ${formatDuration(s.start_time, s.end_time)}</span>
                    </div>
                    ${s.notes ? `<div style="margin-top:10px; font-style:italic; color:#888;">${s.notes}</div>` : ''}
                </div>
            `).join('');
        }
        
        function formatDuration(start, end) {
            if (!end) return '-';
            const ms = new Date(end) - new Date(start);
            const mins = Math.floor(ms / 60000);
            const secs = Math.floor((ms % 60000) / 1000);
            return `${mins}dk ${secs}sn`;
        }
        
        async function viewSession(sessionId) {
            const session = await api(`/api/sessions/${sessionId}`);
            document.getElementById('modal-title').textContent = `${session.drone_name} - #${session.id}`;
            renderChecklistModal(session);
            if (session.status === 'completed') {
                const btnDiv = document.createElement('div');
                btnDiv.style.cssText = 'text-align:center; margin-bottom:15px;';
                btnDiv.innerHTML = '<button class="btn btn-primary" onclick="loadReport(' + sessionId + ')">📊 Raporu Goster</button>';
                document.getElementById('modal-body').prepend(btnDiv);
            }
            document.getElementById('session-modal').classList.add('active');
        }
        
        function renderChecklistModal(session) {
            const container = document.getElementById('modal-body');
            
            const existingBtn = container.querySelector('.btn-primary');
            
            let html = `
                <p><strong>Başlangıç:</strong> ${new Date(session.start_time).toLocaleString('tr-TR')}</p>
                <p><strong>Bitiş:</strong> ${session.end_time ? new Date(session.end_time).toLocaleString('tr-TR') : '-'}</p>
                ${session.notes ? `<p><strong>Notlar:</strong> ${session.notes}</p>` : ''}
                <hr style="margin: 20px 0; border-color: rgba(255,255,255,0.2);">
            `;
            
            const sectionOrder = ['Ortam Kontrolu', 'Ucus Oncesi', 'Ucus Sirasinda', 'Acil Durum Prosedurleri', 'Ucus Sonrasi'];
            const sectionLabels = {
                'Ortam Kontrolu': 'Ortam Kontrolü',
                'Ucus Oncesi': 'Uçuş Öncesi',
                'Ucus Sirasinda': 'Uçuş Sırasında',
                'Acil Durum Prosedurleri': 'Acil Durum Prosedürleri',
                'Ucus Sonrasi': 'Uçuş Sonrası'
            };
            
            sectionOrder.forEach(section => {
                const sectionItems = session.items.filter(item => item.section === section);
                if (sectionItems.length === 0) return;
                
                html += `<div class="section-title">${sectionLabels[section]}</div>`;
                
                sectionItems.forEach(item => {
                    html += `
                        <div class="checklist-item ${item.completed ? 'completed' : ''}">
                            <input type="checkbox" ${item.completed ? 'checked' : ''} disabled>
                            <label>${item.item_text}</label>
                        </div>
                    `;
                });
            });
            
            if (existingBtn) {
                container.innerHTML = existingBtn.outerHTML + html;
            } else {
                container.innerHTML = html;
            }
        }
        
        function closeModal() {
            document.getElementById('session-modal').classList.remove('active');
        }
        
        async function loadEmergencyReference() {
            const items = await api('/api/reference/emergency');
            const container = document.getElementById('emergency-reference');
            
            container.innerHTML = items.map(item => `
                <div class="reference-item">
                    <strong>⚠️ Durum:</strong> ${item.item_text}
                </div>
            `).join('');
        }
        
        // Initialize
        loadActiveSession();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
