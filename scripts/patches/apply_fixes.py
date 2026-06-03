import re

with open("drone_checklist_app.py", "r") as f:
    code = f.read()

# Fix 1: GEMINI_API_KEY instead of OPENAI_API_KEY
code = code.replace('if os.environ.get("OPENAI_API_KEY"):', 'if os.environ.get("GEMINI_API_KEY"):')

new_html = '''HTML_TEMPLATE = """
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
                    const isChecked = item.completed ? 'completed' : '';
                    const checkIcon = item.completed ? '✅' : '⬜';
                    
                    if (item.is_reference === 1) {
                        itemDiv.innerHTML = `<div class="item-text" style="color:var(--text-muted)">ℹ️ ${item.item_text}</div>`;
                    } else {
                        itemDiv.innerHTML = `
                            <div class="item-text ${isChecked}" onclick="toggleItem(${currentSession.id}, ${item.session_item_id}, ${item.completed ? 0 : 1})">
                                ${checkIcon} ${item.item_text}
                            </div>
                        `;
                    }
                    secDiv.appendChild(itemDiv);
                });
                container.appendChild(secDiv);
            }
        }

        async function toggleItem(sessionId, itemId, status) {
            await api(`/api/sessions/${sessionId}/items/${itemId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ completed: status })
            });
            loadActiveSession();
        }

        async function closeSession(simulateMessage=false) {
            if(!currentSession) return;
            await api(`/api/sessions/${currentSession.id}/close`, {method: 'POST'});
            if(simulateMessage) {
                showToast('Uçuş simülasyonu başarıyla tamamlandı. Geçmişe kaydedildi.', 'success');
            } else {
                showToast('Uçuş başarıyla tamamlandı.', 'success');
            }
            loadActiveSession();
        }
        
        async function cancelSession() {
            if(!currentSession) return;
            await api(`/api/sessions/${currentSession.id}/close`, {method: 'POST'});
            showToast('Uçuş iptal edildi (RTH Devrede).', 'warning');
            loadActiveSession();
        }

        async function loadHistory() {
            const history = await api('/api/sessions');
            const container = document.getElementById('history-container');
            container.innerHTML = history.map(s => `
                <div class="panel" style="display:block; padding: 15px; margin-bottom: 10px;">
                    <div style="display:flex; justify-content:space-between;">
                        <strong>Oturum #${s.id} - ${s.drone_name}</strong>
                        <span style="color: ${s.status === 'completed' ? 'var(--success)' : 'var(--danger)'}">
                            ${s.status.toUpperCase()}
                        </span>
                    </div>
                    <div style="color:var(--text-muted); font-size:0.9em; margin-top:10px;">
                        Başlangıç: ${new Date(s.start_time).toLocaleString('tr-TR')}
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
"""'''

code = re.sub(r'HTML_TEMPLATE\s*=\s*"""\n<!DOCTYPE html>.*?</html>\n"""', new_html, code, flags=re.DOTALL)

with open("drone_checklist_app.py", "w") as f:
    f.write(code)

print("Applied fixes successfully.")
