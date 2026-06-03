import re

with open("drone_checklist_app.py", "r") as f:
    code = f.read()

# 1. Restore the OpenRouter / OPENAI_API_KEY logic
code = code.replace('if os.environ.get("GEMINI_API_KEY"):', 'if os.environ.get("OPENAI_API_KEY"):')
# Remove the hardcoded llm
code = code.replace('llm="google/gemini-2.5-flash:free"', '')

# 2. Fix the closeSession JS payload
code = code.replace("await api(`/api/sessions/${currentSession.id}/close`, {method: 'POST'});", 
                    "await api(`/api/sessions/${currentSession.id}/close`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});")
code = code.replace("await api(`/api/sessions/${currentSession.id}/close`, {method: 'POST'});", 
                    "await api(`/api/sessions/${currentSession.id}/close`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});")


# 3. Add Agent Panels back to HTML
agent_panels_html = """
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
                
                <!-- AGENT PANELS RESTORED -->
                <div class="agent-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                    <div class="agent-card" id="risk-card" style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 12px; border: 1px solid var(--glass-border);">
                        <h3 style="color: var(--accent); margin-bottom: 10px;">🛡️ Risk Değerlendirmesi <button onclick="loadRiskAssessment()" style="float:right; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:10px; padding:2px 8px; cursor:pointer;">Yenile</button></h3>
                        <div id="risk-content" style="color: var(--text-muted); font-size: 0.9em;">
                            Analiz ediliyor...
                        </div>
                    </div>
                    <div class="agent-card" id="advisor-card" style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 12px; border: 1px solid var(--glass-border);">
                        <h3 style="color: var(--accent); margin-bottom: 10px;">🎯 Checklist Danışmanı <button onclick="loadAdvisor()" style="float:right; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:10px; padding:2px 8px; cursor:pointer;">Yenile</button></h3>
                        <div id="advisor-content" style="color: var(--text-muted); font-size: 0.9em;">
                            Öneriler hazırlanıyor...
                        </div>
                    </div>
                </div>
"""

code = code.replace("""                <div class="telemetry-panel">
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
                </div>""", agent_panels_html)


# 4. Add loadRiskAssessment and loadAdvisor functions back
agent_functions_js = """
        async function loadRiskAssessment() {
            if (!currentSession) return;
            const content = document.getElementById('risk-content');
            content.innerHTML = '<span style="color: var(--accent)">Analiz ediliyor...</span>';
            try {
                const data = await api(`/api/sessions/${currentSession.id}/assess-risk`);
                if (data.error) throw new Error(data.error);
                content.innerHTML = `<pre style="white-space: pre-wrap; font-family: Inter; color: var(--text-main);">${data.analysis}</pre>`;
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
                
                let adviceHtml = `<pre style="white-space: pre-wrap; font-family: Inter; color: var(--text-main); font-weight: bold;">${data.advice}</pre>`;
                
                if(data.advice.includes("NO-GO") || data.advice.includes("İPTAL") || data.advice.includes("İptal")) {
                     adviceHtml = `<div style="background: rgba(239, 68, 68, 0.2); border-left: 4px solid var(--danger); padding: 10px;">${adviceHtml}</div>`;
                } else if(data.advice.includes("GO")) {
                     adviceHtml = `<div style="background: rgba(16, 185, 129, 0.2); border-left: 4px solid var(--success); padding: 10px;">${adviceHtml}</div>`;
                }
                content.innerHTML = adviceHtml;
            } catch(e) {
                content.innerHTML = `<span style="color: var(--danger)">Hata: ${e.message}</span>`;
            }
        }

        async function toggleItem
"""

code = code.replace("        async function toggleItem", agent_functions_js)

# Also ensure these are called on loadActiveSession
code = code.replace("renderChecklist(session.items);", "renderChecklist(session.items);\n                    loadRiskAssessment();\n                    loadAdvisor();")


with open("drone_checklist_app.py", "w") as f:
    f.write(code)

print("Restored successfully.")
