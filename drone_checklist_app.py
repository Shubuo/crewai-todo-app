import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, g

# Configuration
DATABASE = 'drone_checklist.db'
app = Flask(__name__)
app.config['DATABASE'] = DATABASE

# Database helpers
def get_db():
    """Get database connection for current request context."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection at end of request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database with tables and seed data."""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Create checklist template items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS template_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT NOT NULL,
                item_text TEXT NOT NULL,
                is_emergency BOOLEAN DEFAULT 0,
                sort_order INTEGER DEFAULT 0
            )
        ''')
        
        # Create flight sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flight_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT DEFAULT 'active',
                notes TEXT
            )
        ''')
        
        # Create session items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                template_item_id INTEGER NOT NULL,
                completed INTEGER DEFAULT 0,
                completed_at TEXT,
                FOREIGN KEY (session_id) REFERENCES flight_sessions(id),
                FOREIGN KEY (template_item_id) REFERENCES template_items(id),
                UNIQUE(session_id, template_item_id)
            )
        ''')
        
        db.commit()
        
        # Seed default items if table is empty
        cursor.execute('SELECT COUNT(*) FROM template_items')
        if cursor.fetchone()[0] == 0:
            seed_default_items(db)

def seed_default_items(db):
    """Populate database with default Turkish drone checklist items."""
    cursor = db.cursor()
    
    default_items = [
        # Ortam Kontrolu
        ('ortam_kontrolu', 'Hava durumu uygun mu? (ruzgar, yagmur, görüs mesafesi)', 0, 1),
        ('ortam_kontrolu', 'Ucus alani izinli mi?', 0, 2),
        ('ortam_kontrolu', 'Guvenli inis/kalkis alani mevcut mu?', 0, 3),
        ('ortam_kontrolu', 'Elektromanyetik girisim riski var mi?', 0, 4),
        ('ortam_kontrolu', 'Ucus alaninda insan veya hayvan var mi?', 0, 5),
        ('ortam_kontrolu', 'GPS engeli veya parazit kaynagi var mi?', 0, 6),
        
        # Ucus Oncesi
        ('ucus_oncesi', 'Pil sarj seviyesi kontrol edildi mi? (en az %80)', 0, 1),
        ('ucus_oncesi', 'Pil sicakligi normal aralikta mi?', 0, 2),
        ('ucus_oncesi', 'Pervane ve motorlar saglam mi? (catlak, hasar kontrolu)', 0, 3),
        ('ucus_oncesi', 'Pervaneler dogru sekilde takili mi?', 0, 4),
        ('ucus_oncesi', 'GPS sinyali yeterli mi? (en az 8 uydu)', 0, 5),
        ('ucus_oncesi', 'Kumanda pili kontrol edildi mi?', 0, 6),
        ('ucus_oncesi', 'Kalkis noktasinda engel var mi?', 0, 7),
        ('ucus_oncesi', 'Uzaktan kumanda baglantisi test edildi mi?', 0, 8),
        ('ucus_oncesi', 'Kamera ve gimbal fonksiyonel mi?', 0, 9),
        ('ucus_oncesi', 'Hafiza karti takili ve bos alan var mi?', 0, 10),
        ('ucus_oncesi', 'Firmware guncellemesi gerekli mi?', 0, 11),
        ('ucus_oncesi', 'Ev noktasi (Home Point) ayari yapildi mi?', 0, 12),
        
        # Ucus Sirasinda
        ('ucus_sirasinda', 'Kalkis normal mi? (titreme, gurultu kontrolu)', 0, 1),
        ('ucus_sirasinda', 'Ses ve titreşim normal mi?', 0, 2),
        ('ucus_sirasinda', 'ucus yuksekligi ve mesafe guvenli mi?', 0, 3),
        ('ucus_sirasinda', 'Pil seviyesi yeterli mi? (en az %30 kalacak)', 0, 4),
        ('ucus_sirasinda', 'GPS ve navigasyon dogru calisiyor mu?', 0, 5),
        ('ucus_sirasinda', 'Hava kosullarinda degisiklik oldu mu?', 0, 6),
        ('ucus_sirasinda', 'Manevra ve kontroller duzgun calisiyor mu?', 0, 7),
        ('ucus_sirasinda', 'Kamera göruntuü kalitesi нормал mu?', 0, 8),
        ('ucus_sirasinda', 'Ruzgar direnci yeterli mi?', 0, 9),
        ('ucus_sirasinda', 'Sinyal gücü stabil mi?', 0, 10),
        
        # Acil Durum Prosedurleri (reference only)
        ('acil_durum', 'Acil inis proseduru: Yavasca alcagmaya baslayin', 1, 1),
        ('acil_durum', 'Sinyal kaybi durumunda: Otomatik geri dönüsü bekleyin', 1, 2),
        ('acil_durum', 'Pil uyarisi: Derhal inise gecin', 1, 3),
        ('acil_durum', 'Kritik ariza: Motorlari kapatin ve düsüsü izleyin', 1, 4),
        ('acil_durum', 'Yasadisi bolge girisi: Derhal cikis yapin', 1, 5),
        ('acil_durum', 'Uzaktan kumanda pil uyarisi: Acil iniş baslayin', 1, 6),
        ('acil_durum', 'GPS kaybi: Manuel modda yavasca inis yapin', 1, 7),
        ('acil_durum', 'Firmware arizasi: Motorlari durdurun', 1, 8),
        ('acil_durum', 'Kaza durumu: Motorlari hemen kapatin', 1, 9),
        ('acil_durum', 'Uzaktan kumanda baglanti kopmasi: 3 dakika bekleyin', 1, 10),
        
        # Ucus Sonrasi
        ('ucus_sonrasi', 'Drone hasar kontrol edildi mi?', 0, 1),
        ('ucus_sonrasi', 'Pil sicakligi normal mi?', 0, 2),
        ('ucus_sonrasi', 'Veriler güvenli bir sekilde kaydedildi mi?', 0, 3),
        ('ucus_sonrasi', 'Ekipman temizligi yapildi mi?', 0, 4),
        ('ucus_sonrasi', 'Ucus günlügü dolduruldu mu?', 0, 5),
        ('ucus_sonrasi', 'Piller saglam mi ve dogru saklandi mi?', 0, 6),
        ('ucus_sonrasi', 'Hafiza karti yedeklendi mi?', 0, 7),
        ('ucus_sonrasi', 'Ekipman eksik veya hasarli var mi?', 0, 8),
    ]
    
    for item in default_items:
        cursor.execute('''
            INSERT INTO template_items (section, item_text, is_emergency, sort_order)
            VALUES (?, ?, ?, ?)
        ''', item)
    
    db.commit()

# API Routes
@app.route('/api/session/start', methods=['POST'])
def start_session():
    """Start a new flight session."""
    db = get_db()
    cursor = db.cursor()
    
    start_time = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO flight_sessions (start_time, status)
        VALUES (?, 'active')
    ''', (start_time,))
    
    session_id = cursor.lastrowid
    db.commit()
    
    return jsonify({
        'success': True,
        'session': {
            'id': session_id,
            'start_time': start_time,
            'status': 'active'
        }
    })

@app.route('/api/session/active', methods=['GET'])
def get_active_session():
    """Get the current active flight session."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT id, start_time, end_time, status, notes
        FROM flight_sessions
        WHERE status = 'active'
        ORDER BY id DESC
        LIMIT 1
    ''')
    
    session = cursor.fetchone()
    if not session:
        return jsonify({'session': None, 'items': []})
    
    cursor.execute('''
        SELECT ti.id, ti.item_text, ti.section, ti.is_emergency, ti.sort_order,
               COALESCE(si.completed, 0) as completed, si.completed_at
        FROM template_items ti
        LEFT JOIN session_items si ON ti.id = si.template_item_id AND si.session_id = ?
        ORDER BY ti.section, ti.sort_order
    ''', (session['id'],))
    
    items = cursor.fetchall()
    
    return jsonify({
        'session': dict(session),
        'items': [dict(item) for item in items]
    })

@app.route('/api/session/items', methods=['GET'])
def get_session_items():
    """Get checklist items for a session."""
    session_id = request.args.get('session_id', type=int)
    
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT ti.id, ti.item_text, ti.section, ti.is_emergency, ti.sort_order,
               COALESCE(si.completed, 0) as completed, si.completed_at
        FROM template_items ti
        LEFT JOIN session_items si ON ti.id = si.template_item_id AND si.session_id = ?
        ORDER BY ti.section, ti.sort_order
    ''', (session_id,))
    
    items = cursor.fetchall()
    return jsonify([dict(item) for item in items])

@app.route('/api/session/update', methods=['POST'])
def update_session_item():
    """Update a checklist item completion status."""
    data = request.get_json()
    
    if not all(k in data for k in ['session_id', 'template_item_id', 'completed']):
        return jsonify({'error': 'Missing required fields: session_id, template_item_id, completed'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    if data['completed']:
        completed_at = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO session_items (session_id, template_item_id, completed, completed_at)
            VALUES (?, ?, 1, ?)
        ''', (data['session_id'], data['template_item_id'], completed_at))
    else:
        cursor.execute('''
            DELETE FROM session_items 
            WHERE session_id = ? AND template_item_id = ?
        ''', (data['session_id'], data['template_item_id']))
    
    db.commit()
    return jsonify({'success': True})

@app.route('/api/session/close', methods=['POST'])
def close_session():
    """Close an active flight session."""
    data = request.get_json()
    session_id = data.get('session_id')
    notes = data.get('notes', '')
    
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        UPDATE flight_sessions 
        SET status = 'completed', end_time = ?, notes = ?
        WHERE id = ? AND status = 'active'
    ''', (datetime.now().isoformat(), notes, session_id))
    
    db.commit()
    
    if cursor.rowcount == 0:
        return jsonify({'error': 'Session not found or already closed'}), 404
    
    return jsonify({'success': True})

@app.route('/api/session/history', methods=['GET'])
def get_session_history():
    """Get list of past flight sessions."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT id, start_time, end_time, status, notes
        FROM flight_sessions
        ORDER BY start_time DESC
        LIMIT 100
    ''')
    
    sessions = cursor.fetchall()
    return jsonify([dict(row) for row in sessions])

@app.route('/api/session/<int:session_id>', methods=['GET'])
def get_session_detail(session_id):
    """Get details of a specific session."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT id, start_time, end_time, status, notes
        FROM flight_sessions
        WHERE id = ?
    ''', (session_id,))
    
    session = cursor.fetchone()
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    cursor.execute('''
        SELECT ti.id, ti.item_text, ti.section, ti.is_emergency, ti.sort_order,
               COALESCE(si.completed, 0) as completed, si.completed_at
        FROM template_items ti
        LEFT JOIN session_items si ON ti.id = si.template_item_id AND si.session_id = ?
        ORDER BY ti.section, ti.sort_order
    ''', (session_id,))
    
    items = cursor.fetchall()
    
    return jsonify({
        'session': dict(session),
        'items': [dict(item) for item in items]
    })

@app.route('/api/emergency/reference', methods=['GET'])
def get_emergency_reference():
    """Get emergency procedures as reference panel items."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT id, item_text, sort_order
        FROM template_items
        WHERE is_emergency = 1
        ORDER BY sort_order
    ''')
    
    items = cursor.fetchall()
    return jsonify([dict(row) for row in items])

# HTML Template - Single Page Turkish UI
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drone Ucus Kontrol Listesi</title>
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
            padding: 20px;
            color: #fff;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        h1 {
            font-size: 2em;
            color: #4ade80;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #94a3b8;
        }
        
        .session-info {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .session-timer {
            font-size: 1.5em;
            color: #4ade80;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .btn-group {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: #4ade80;
            color: #1a1a2e;
        }
        
        .btn-primary:hover {
            background: #22c55e;
            transform: translateY(-2px);
        }
        
        .btn-danger {
            background: #ef4444;
            color: white;
        }
        
        .btn-danger:hover {
            background: #dc2626;
        }
        
        .btn-secondary {
            background: #64748b;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #475569;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 350px;
            gap: 20px;
        }
        
        @media (max-width: 900px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .checklist-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .section-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }
        
        .section-title {
            font-size: 1.2em;
            color: #60a5fa;
        }
        
        .section-icon {
            font-size: 1.5em;
        }
        
        .checklist-item {
            display: flex;
            align-items: center;
            padding: 12px;
            margin-bottom: 8px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .checklist-item:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        
        .checklist-item.completed {
            background: rgba(74, 222, 128, 0.1);
            border-left: 4px solid #4ade80;
        }
        
        .checklist-item.completed .item-text {
            text-decoration: line-through;
            opacity: 0.7;
        }
        
        .checkbox {
            width: 24px;
            height: 24px;
            border: 2px solid #64748b;
            border-radius: 6px;
            margin-right: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            flex-shrink: 0;
        }
        
        .checklist-item.completed .checkbox {
            background: #4ade80;
            border-color: #4ade80;
        }
        
        .checkmark {
            display: none;
            color: #1a1a2e;
            font-weight: bold;
        }
        
        .checklist-item.completed .checkmark {
            display: block;
        }
        
        .item-text {
            flex: 1;
        }
        
        .reference-panel {
            background: linear-gradient(135deg, #7c2d12 0%, #9a3412 100%);
            border-radius: 12px;
            padding: 20px;
            position: sticky;
            top: 20px;
            max-height: calc(100vh - 40px);
            overflow-y: auto;
        }
        
        .reference-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .reference-title {
            font-size: 1.1em;
            color: #fed7aa;
        }
        
        .reference-item {
            padding: 12px;
            margin-bottom: 8px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            border-left: 3px solid #f97316;
            font-size: 14px;
            line-height: 1.4;
        }
        
        .reference-number {
            display: inline-block;
            width: 24px;
            height: 24px;
            background: #f97316;
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 24px;
            font-size: 12px;
            margin-right: 10px;
            flex-shrink: 0;
        }
        
        .history-panel {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
        }
        
        .history-title {
            font-size: 1.1em;
            color: #94a3b8;
            margin-bottom: 15px;
        }
        
        .history-item {
            padding: 12px;
            margin-bottom: 8px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .history-item:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        
        .history-date {
            color: #60a5fa;
        }
        
        .history-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
        }
        
        .status-completed {
            background: rgba(74, 222, 128, 0.2);
            color: #4ade80;
        }
        
        .status-active {
            background: rgba(96, 165, 250, 0.2);
            color: #60a5fa;
        }
        
        .no-session {
            text-align: center;
            padding: 60px 20px;
            color: #94a3b8;
        }
        
        .no-session-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        
        .progress-container {
            margin-bottom: 15px;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4ade80, #22c55e);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        .progress-text {
            text-align: right;
            font-size: 12px;
            color: #94a3b8;
            margin-top: 5px;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
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
            padding: 0;
        }
        
        .overall-progress {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        
        .overall-progress-title {
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 10px;
        }
        
        .completion-rate {
            font-size: 2em;
            font-weight: bold;
            color: #4ade80;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Drone Ucus Kontrol Listesi</h1>
            <p class="subtitle">Güvenli ucuslar icin kontrol listenizi tamamlayin</p>
        </header>
        
        <div class="session-info" id="sessionInfo">
            <p>Henüz aktif bir ucus oturumu bulunmuyor</p>
        </div>
        
        <div class="btn-group" id="btnGroup">
            <button class="btn-primary" onclick="startSession()">Yeni Ucus Baslat</button>
            <button class="btn-secondary" onclick="showHistory()">Gecmis Ucuslar</button>
        </div>
        
        <div class="main-grid">
            <div class="checklist-area" id="checklistArea">
                <div class="no-session" id="noSession">
                    <div class="no-session-icon">&#128640;</div>
                    <p>Ucus kontrol listesini göruntulemek icin yeni bir oturum baslatin</p>
                </div>
                
                <div id="checklistSections" style="display: none;">
                    <div class="overall-progress" id="overallProgress">
                        <div class="overall-progress-title">Genel Tamamlama</div>
                        <div class="completion-rate" id="completionRate">0%</div>
                        <div class="progress-bar" style="margin-top: 10px;">
                            <div class="progress-fill" id="overallProgressFill" style="width: 0%"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="reference-panel">
                <div class="reference-header">
                    <span class="section-icon">&#9888;</span>
                    <span class="reference-title">Acil Durum Prosedürleri</span>
                </div>
                <div id="emergencyReference">
                </div>
            </div>
        </div>
        
        <div class="history-panel" id="historyPanel" style="display: none;">
            <h3 class="history-title">Gecmis Ucuslar</h3>
            <div id="historyList"></div>
        </div>
    </div>
    
    <div class="modal" id="historyModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modalTitle">Ucus Detaylari</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div id="modalContent"></div>
        </div>
    </div>
    
    <script>
        const API_BASE = '/api';
        let currentSession = null;
        let sessionStartTime = null;
        let timerInterval = null;
        let allItems = [];
        
        const sections = [
            { id: 'ortam_kontrolu', name: 'Ortam Kontrolu', icon: '&#127781;' },
            { id: 'ucus_oncesi', name: 'Ucus Oncesi', icon: '&#128736;' },
            { id: 'ucus_sirasinda', name: 'Ucus Sirasinda', icon: '&#9992;' },
            { id: 'ucus_sonrasi', name: 'Ucus Sonrasi', icon: '&#127937;' }
        ];
        
        async function startSession() {
            try {
                const response = await fetch(`${API_BASE}/session/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                currentSession = data.session;
                sessionStartTime = new Date(data.session.start_time);
                loadActiveSession();
                startTimer();
            } catch (error) {
                console.error('Oturum baslatma hatasi:', error);
                alert('Oturum baslatilamadi');
            }
        }
        
        async function loadActiveSession() {
            try {
                const response = await fetch(`${API_BASE}/session/active`);
                const data = await response.json();
                
                if (data.session) {
                    currentSession = data.session;
                    sessionStartTime = new Date(data.session.start_time);
                }
                
                allItems = data.items || [];
                renderChecklist(allItems);
                document.getElementById('noSession').style.display = 'none';
                document.getElementById('checklistSections').style.display = 'block';
                updateSessionInfo();
                updateOverallProgress();
            } catch (error) {
                console.error('Oturum yukleme hatasi:', error);
            }
        }
        
        function updateSessionInfo() {
            const sessionInfo = document.getElementById('sessionInfo');
            const btnGroup = document.getElementById('btnGroup');
            
            if (currentSession && currentSession.status === 'active') {
                sessionInfo.innerHTML = `
                    <p>Ucus Oturumu Aktif</p>
                    <div class="session-timer" id="sessionTimer">00:00:00</div>
                    <div class="btn-group">
                        <button class="btn-danger" onclick="closeSession()">Ucusu Bitir</button>
                        <button class="btn-secondary" onclick="showHistory()">Gecmis Ucuslar</button>
                    </div>
                `;
                startTimer();
            } else {
                sessionInfo.innerHTML = '<p>Henuz aktif bir ucus oturumu bulunmuyor</p>';
                btnGroup.innerHTML = `
                    <button class="btn-primary" onclick="startSession()">Yeni Ucus Baslat</button>
                    <button class="btn-secondary" onclick="showHistory()">Gecmis Ucuslar</button>
                `;
            }
        }
        
        function startTimer() {
            if (timerInterval) clearInterval(timerInterval);
            
            timerInterval = setInterval(() => {
                const now = new Date();
                const diff = now - sessionStartTime;
                const hours = Math.floor(diff / 3600000);
                const minutes = Math.floor((diff % 3600000) / 60000);
                const seconds = Math.floor((diff % 60000) / 1000);
                
                const timer = document.getElementById('sessionTimer');
                if (timer) {
                    timer.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
                }
            }, 1000);
        }
        
        async function closeSession() {
            if (!currentSession) return;
            
            if (!confirm('Ucus oturumunu kapatmak istediginizden emin misiniz?')) return;
            
            try {
                await fetch(`${API_BASE}/session/close`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: currentSession.id })
                });
                
                if (timerInterval) clearInterval(timerInterval);
                currentSession = null;
                allItems = [];
                document.getElementById('noSession').style.display = 'block';
                document.getElementById('checklistSections').style.display = 'none';
                updateSessionInfo();
                loadEmergencyReference();
            } catch (error) {
                console.error('Oturum kapatma hatasi:', error);
                alert('Oturum kapatilamadi');
            }
        }
        
        function renderChecklist(items) {
            const container = document.getElementById('checklistSections');
            
            // Keep the overall progress element
            const overallProgress = document.getElementById('overallProgress');
            container.innerHTML = '';
            container.appendChild(overallProgress);
            
            sections.forEach(section => {
                const sectionItems = items.filter(item => item.section === section.id);
                if (sectionItems.length === 0) return;
                
                const completedCount = sectionItems.filter(item => item.completed).length;
                const progress = Math.round((completedCount / sectionItems.length) * 100);
                
                const sectionDiv = document.createElement('div');
                sectionDiv.className = 'checklist-section';
                sectionDiv.innerHTML = `
                    <div class="section-header">
                        <span class="section-icon">${section.icon}</span>
                        <span class="section-title">${section.name}</span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progress}%"></div>
                        </div>
                        <div class="progress-text">${completedCount}/${sectionItems.length} tamamlandi (${progress}%)</div>
                    </div>
                    <div class="section-items"></div>
                `;
                
                const itemsContainer = sectionDiv.querySelector('.section-items');
                sectionItems.forEach(item => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = `checklist-item ${item.completed ? 'completed' : ''}`;
                    itemDiv.onclick = () => toggleItem(item.id, !item.completed);
                    itemDiv.innerHTML = `
                        <div class="checkbox">
                            <span class="checkmark">&#10003;</span>
                        </div>
                        <span class="item-text">${item.item_text}</span>
                    `;
                    itemsContainer.appendChild(itemDiv);
                });
                
                container.appendChild(sectionDiv);
            });
        }
        
        function updateOverallProgress() {
            const nonEmergencyItems = allItems.filter(item => !item.is_emergency);
            const completedItems = nonEmergencyItems.filter(item => item.completed);
            const totalItems = nonEmergencyItems.length;
            const completedCount = completedItems.length;
            const percentage = totalItems > 0 ? Math.round((completedCount / totalItems) * 100) : 0;
            
            const rateEl = document.getElementById('completionRate');
            const fillEl = document.getElementById('overallProgressFill');
            
            if (rateEl) rateEl.textContent = `${percentage}%`;
            if (fillEl) fillEl.style.width = `${percentage}%`;
        }
        
        async function toggleItem(itemId, completed) {
            if (!currentSession) return;
            
            try {
                await fetch(`${API_BASE}/session/update`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: currentSession.id,
                        template_item_id: itemId,
                        completed: completed
                    })
                });
                
                // Update local state
                const item = allItems.find(i => i.id === itemId);
                if (item) item.completed = completed;
                
                renderChecklist(allItems);
                updateOverallProgress();
            } catch (error) {
                console.error('Ogëe guncelleme hatasi:', error);
            }
        }
        
        async function loadEmergencyReference() {
            try {
                const response = await fetch(`${API_BASE}/emergency/reference`);
                const items = await response.json();
                
                const container = document.getElementById('emergencyReference');
                container.innerHTML = '';
                
                items.forEach((item, index) => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'reference-item';
                    itemDiv.innerHTML = `
                        <span class="reference-number">${index + 1}</span>
                        ${item.item_text}
                    `;
                    container.appendChild(itemDiv);
                });
            } catch (error) {
                console.error('Acil durum referansi yukleme hatasi:', error);
            }
        }
        
        async function showHistory() {
            const historyPanel = document.getElementById('historyPanel');
            historyPanel.style.display = historyPanel.style.display === 'none' ? 'block' : 'none';
            
            if (historyPanel.style.display === 'block') {
                try {
                    const response = await fetch(`${API_BASE}/session/history`);
                    const sessions = await response.json();
                    
                    const listContainer = document.getElementById('historyList');
                    listContainer.innerHTML = '';
                    
                    if (sessions.length === 0) {
                        listContainer.innerHTML = '<p style="color: #94a3b8;">Henuz kayitli ucus bulunmuyor</p>';
                        return;
                    }
                    
                    sessions.forEach(session => {
                        const startDate = new Date(session.start_time);
                        const endDate = session.end_time ? new Date(session.end_time) : null;
                        const duration = endDate ? Math.round((endDate - startDate) / 60000) : '-';
                        
                        const itemDiv = document.createElement('div');
                        itemDiv.className = 'history-item';
                        itemDiv.onclick = () => showSessionDetail(session.id);
                        itemDiv.innerHTML = `
                            <div>
                                <div class="history-date">${startDate.toLocaleDateString('tr-TR')} ${startDate.toLocaleTimeString('tr-TR')}</div>
                                <div style="color: #94a3b8; font-size: 12px; margin-top: 4px;">Sure: ${duration} dakika</div>
                            </div>
                            <span class="history-status ${session.status === 'completed' ? 'status-completed' : 'status-active'}">
                                ${session.status === 'completed' ? 'Tamamlandi' : 'Aktif'}
                            </span>
                        `;
                        listContainer.appendChild(itemDiv);
                    });
                } catch (error) {
                    console.error('Gecmis yukleme hatasi:', error);
                }
            }
        }
        
        async function showSessionDetail(sessionId) {
            try {
                const response = await fetch(`${API_BASE}/session/${sessionId}`);
                const data = await response.json();
                
                const modal = document.getElementById('historyModal');
                const modalTitle = document.getElementById('modalTitle');
                const modalContent = document.getElementById('modalContent');
                
                const startDate = new Date(data.session.start_time);
                const endDate = data.session.end_time ? new Date(data.session.end_time) : null;
                const duration = endDate ? Math.round((endDate - startDate) / 60000) : '-';
                
                modalTitle.textContent = `Ucus Detaylari - ${startDate.toLocaleDateString('tr-TR')}`;
                
                let html = `
                    <p style="color: #94a3b8; margin-bottom: 20px;">
                        Baslangic: ${startDate.toLocaleDateString('tr-TR')} ${startDate.toLocaleTimeString('tr-TR')}<br>
                        Bitis: ${endDate ? endDate.toLocaleDateString('tr-TR') + ' ' + endDate.toLocaleTimeString('tr-TR') : 'Devam ediyor'}<br>
                        Sure: ${duration} dakika
                    </p>
                `;
                
                sections.forEach(section => {
                    const sectionItems = data.items.filter(item => item.section === section.id);
                    if (sectionItems.length === 0) return;
                    
                    const completedCount = sectionItems.filter(item => item.completed).length;
                    const progress = Math.round((completedCount / sectionItems.length) * 100);
                    
                    html += `
                        <div style="margin-bottom: 20px;">
                            <h4 style="color: #60a5fa; margin-bottom: 10px;">${section.name} (${progress}%)</h4>
                    `;
                    
                    sectionItems.forEach(item => {
                        const status = item.completed ? 'Tamamlandi' : 'Tamamlanmadi';
                        const color = item.completed ? '#4ade80' : '#ef4444';
                        html += `
                            <div style="padding: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; margin-bottom: 4px;">
                                <span style="color: ${color}; margin-right: 8px;">${item.completed ? '&#10003;' : '&#10007;'}</span>
                                ${item.item_text}
                            </div>
                        `;
                    });
                    
                    html += '</div>';
                });
                
                modalContent.innerHTML = html;
                modal.classList.add('active');
            } catch (error) {
                console.error('Oturum detay yukleme hatasi:', error);
            }
        }
        
        function closeModal() {
            document.getElementById('historyModal').classList.remove('active');
        }
        
        // Close modal on outside click
        document.getElementById('historyModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });
        
        // Initialize
        document.addEventListener('DOMContentLoaded', async () => {
            loadEmergencyReference();
            
            try {
                const response = await fetch(`${API_BASE}/session/active`);
                const data = await response.json();
                
                if (data.session) {
                    currentSession = data.session;
                    sessionStartTime = new Date(data.session.start_time);
                    loadActiveSession();
                    updateSessionInfo();
                }
            } catch (error) {
                console.error('Aktif oturum kontrolu hatasi:', error);
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Serve the main application page."""
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    init_db()
    print("Drone Ucus Kontrol Listesi baslatiliyor...")
    print("Tarayicida http://localhost:5000 adresini acin")
    app.run(debug=True, host='0.0.0.0', port=5000)