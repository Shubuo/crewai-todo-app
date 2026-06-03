import re

with open("drone_checklist_app.py", "r") as f:
    code = f.read()

# 1. Replace HTML panels
old_panels = """                <!-- AGENT PANELS RESTORED -->
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
                </div>"""

new_panels = """                <!-- COMBINED AGENT PANEL -->
                <div class="agent-grid" style="margin-bottom: 20px;">
                    <div class="agent-card" id="combined-risk-card" style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 12px; border: 1px solid var(--glass-border);">
                        <h3 style="color: var(--accent); margin-bottom: 10px;">🛡️ Otonom Risk ve Uçuş Analizi <button onclick="loadRiskAssessment()" style="float:right; background:transparent; border:1px solid var(--accent); color:var(--accent); border-radius:10px; padding:2px 8px; cursor:pointer;">Yenile</button></h3>
                        <div id="risk-content" style="color: var(--text-muted); font-size: 0.9em;">
                            Analiz ediliyor...
                        </div>
                    </div>
                </div>"""

code = code.replace(old_panels, new_panels)


# 2. Replace JS loadRiskAssessment and remove loadAdvisor
old_js_funcs = """        async function loadRiskAssessment() {
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
        }"""

new_js_funcs = """        async function loadRiskAssessment() {
            if (!currentSession) return;
            const content = document.getElementById('risk-content');
            content.innerHTML = '<span style="color: var(--accent)">Kural tabanlı risk hesaplanıyor...</span>';
            try {
                const riskData = await api(`/api/sessions/${currentSession.id}/assess-risk`);
                if (riskData.error) throw new Error(riskData.error);

                let riskHtml = `
                    <div style="margin-bottom:15px; padding-bottom:15px; border-bottom:1px solid rgba(255,255,255,0.1);">
                        <strong>Sistem Kararı (Kurallar):</strong> <span style="color: ${riskData.decision === 'GO' ? 'var(--success)' : (riskData.decision === 'WARNING' ? '#f59e0b' : 'var(--danger)')}; font-weight:bold;">${riskData.decision}</span><br>
                        <strong>Checklist Tamamlanma:</strong> %${riskData.completion_percentage}<br>
                `;
                if(riskData.warnings && riskData.warnings.length > 0) {
                    riskHtml += `<br><strong>Eksik Kritik Kontroller:</strong><ul style="margin-left: 20px; color: var(--danger);">`;
                    riskData.warnings.forEach(w => { riskHtml += `<li>${w}</li>`; });
                    riskHtml += `</ul></div>`;
                } else {
                    riskHtml += `<br><span style="color:var(--success);">Tüm kritik kontroller tamamlandı.</span></div>`;
                }

                content.innerHTML = riskHtml + '<span style="color: var(--accent)">Yapay Zeka (CrewAI) uçuş danışmanı değerlendiriyor...</span>';

                try {
                    const advData = await api(`/api/sessions/${currentSession.id}/advisor`);
                    let adviceTxt = "";
                    if (advData.error) {
                        adviceTxt = "AI Bağlantı Hatası: " + advData.error;
                    } else {
                        adviceTxt = advData.ai_advice || "Öneri alınamadı.";
                    }

                    let adviceHtml = `<strong>🤖 Yapay Zeka Uçuş Danışmanı:</strong><br><pre style="white-space: pre-wrap; font-family: Inter; color: var(--text-main); margin-top:5px; font-weight:bold;">${adviceTxt}</pre>`;
                    
                    if(adviceTxt.includes("NO-GO") || adviceTxt.includes("İPTAL") || adviceTxt.includes("İptal") || adviceTxt.includes("Hata:") || adviceTxt.includes("AuthenticationError")) {
                         adviceHtml = `<div style="background: rgba(239, 68, 68, 0.2); border-left: 4px solid var(--danger); padding: 10px; border-radius: 5px;">${adviceHtml}</div>`;
                    } else if(adviceTxt.includes("GO") || adviceTxt.includes("Devam edebilirsiniz")) {
                         adviceHtml = `<div style="background: rgba(16, 185, 129, 0.2); border-left: 4px solid var(--success); padding: 10px; border-radius: 5px;">${adviceHtml}</div>`;
                    } else {
                         adviceHtml = `<div style="background: rgba(255, 255, 255, 0.05); border-left: 4px solid var(--accent); padding: 10px; border-radius: 5px;">${adviceHtml}</div>`;
                    }
                    
                    content.innerHTML = riskHtml + adviceHtml;
                } catch(aiError) {
                    content.innerHTML = riskHtml + `<div style="background: rgba(239, 68, 68, 0.2); border-left: 4px solid var(--danger); padding: 10px; border-radius: 5px;"><strong>🤖 Yapay Zeka Uçuş Danışmanı:</strong><br>Bağlantı Hatası: ${aiError.message}</div>`;
                }

            } catch(e) {
                content.innerHTML = `<span style="color: var(--danger)">Hata: ${e.message}</span>`;
            }
        }"""

code = code.replace(old_js_funcs, new_js_funcs)

# 3. Remove loadAdvisor() from loadActiveSession() 
code = code.replace("loadRiskAssessment();\n                    loadAdvisor();", "loadRiskAssessment();")

# 4. Modify python get_advice to actually return the error object to JS if crewai throws auth error
old_py_catch = """        except Exception as e:
            AgentTraceLogger.log(session_id, 'LLM Error', str(e), function='crew_kickoff')

        return jsonify({"""

new_py_catch = """        except Exception as e:
            AgentTraceLogger.log(session_id, 'LLM Error', str(e), function='crew_kickoff')
            return jsonify({'error': str(e)})

        return jsonify({"""

code = code.replace(old_py_catch, new_py_catch)

with open("drone_checklist_app.py", "w") as f:
    f.write(code)

print("Combined panels and updated error handling.")
