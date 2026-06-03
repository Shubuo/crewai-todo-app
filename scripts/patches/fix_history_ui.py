import re

with open("drone_checklist_app.py", "r") as f:
    code = f.read()

# 1. Fix loadRiskAssessment rendering
old_risk = "content.innerHTML = `<pre style=\"white-space: pre-wrap; font-family: Inter; color: var(--text-main);\">${data.analysis}</pre>`;"
new_risk = """
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
"""
code = code.replace(old_risk, new_risk)


# 2. Make History Clickable & Add details
old_history = """
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
"""

new_history = """
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
"""

code = code.replace(old_history.strip(), new_history.strip())


# Add the toggleHistoryDetails function
js_funcs = """
        function toggleHistoryDetails(id) {
            const el = document.getElementById(`history-detail-${id}`);
            if(el.style.display === 'none') {
                el.style.display = 'block';
            } else {
                el.style.display = 'none';
            }
        }
"""
if "function toggleHistoryDetails" not in code:
    code = code.replace("        async function loadHistory()", js_funcs + "\n        async function loadHistory()")


with open("drone_checklist_app.py", "w") as f:
    f.write(code)

print("Applied History click and Risk UI fixes.")
