import re

with open("drone_checklist_app.py", "r") as f:
    code = f.read()

# 1. Fix loadAdvisor data.advice -> data.ai_advice
old_advisor = """                let adviceHtml = `<pre style="white-space: pre-wrap; font-family: Inter; color: var(--text-main); font-weight: bold;">${data.advice}</pre>`;
                
                if(data.advice.includes("NO-GO") || data.advice.includes("İPTAL") || data.advice.includes("İptal")) {
                     adviceHtml = `<div style="background: rgba(239, 68, 68, 0.2); border-left: 4px solid var(--danger); padding: 10px;">${adviceHtml}</div>`;
                } else if(data.advice.includes("GO")) {
                     adviceHtml = `<div style="background: rgba(16, 185, 129, 0.2); border-left: 4px solid var(--success); padding: 10px;">${adviceHtml}</div>`;
                }"""

new_advisor = """                let adviceTxt = data.ai_advice || "Öneri alınamadı.";
                let adviceHtml = `<pre style="white-space: pre-wrap; font-family: Inter; color: var(--text-main); font-weight: bold;">${adviceTxt}</pre>`;
                
                if(adviceTxt.includes("NO-GO") || adviceTxt.includes("İPTAL") || adviceTxt.includes("İptal")) {
                     adviceHtml = `<div style="background: rgba(239, 68, 68, 0.2); border-left: 4px solid var(--danger); padding: 10px;">${adviceHtml}</div>`;
                } else if(adviceTxt.includes("GO")) {
                     adviceHtml = `<div style="background: rgba(16, 185, 129, 0.2); border-left: 4px solid var(--success); padding: 10px;">${adviceHtml}</div>`;
                }"""

code = code.replace(old_advisor, new_advisor)

# 2. Fix closeSession not reloading history
old_close = """            if(simulateMessage) {
                showToast('Uçuş simülasyonu başarıyla tamamlandı. Geçmişe kaydedildi.', 'success');
            } else {
                showToast('Uçuş başarıyla tamamlandı.', 'success');
            }
            loadActiveSession();
        }"""

new_close = """            if(simulateMessage) {
                showToast('Uçuş simülasyonu başarıyla tamamlandı. Geçmişe kaydedildi.', 'success');
            } else {
                showToast('Uçuş başarıyla tamamlandı.', 'success');
            }
            loadActiveSession();
            loadHistory();
        }"""

code = code.replace(old_close, new_close)


with open("drone_checklist_app.py", "w") as f:
    f.write(code)

print("Applied UI fixes.")
