# Drone Flight Checklist App

CrewAI ile uretilen, drone ucus checklist'lerini yonetmek icin Flask tabanli tek dosya uygulama. Her ucus icin temiz baslayan session bazli checklist akisi sunar. Turkce arayuz, dark tema, mobil uyumlu.

---

## Proje Mimarisi (2 Katman)

```
crewai-todo-app/
├── src/crewai_todo_app/         # CREWAI URETIM KATI
│   ├── config/
│   │   ├── agents.yaml          # Agent: Full-Stack Developer
│   │   └── tasks.yaml           # Task: drone checklist app uretimi
│   ├── crew.py                  # CrewAIDroneChecklistApp (1 agent, 1 task, sequential)
│   └── main.py                  # run/train/replay/test komutlari
│
├── drone_checklist_app.py       # UYGULAMA KATI (Flask + SQLite + inline JS)
├── drone_checklist.db           # SQLite veritabani
│
├── README.md
├── PHASE1_DRONE_CHECKLIST_PLAN.md   # Faz 1 plan dokumani
├── DEMO_ADIMLAR.md                  # Adim adim demo talimatlari
├── CONTEXT_SUMMARY.md               # Kapsamli teknik ozet
│
├── sunum/                           # Sunum materyalleri
│   ├── CREWAI sunum.md              # Marp format (27 slayt)
│   ├── CREWAI sunum.html            # HTML sunum
│   ├── CREWAI sunum.pptx            # PowerPoint
│   ├── CREWAI sunum konusmaci notlari.md
│   └── CREWAI sunum canva paste.txt
│
├── pyproject.toml
├── .env.example
└── uv.lock
```

---

## Teknoloji Yigini

| Katman | Teknoloji | Surum |
| ------ | --------- | ----- |
| AI Framework | CrewAI | 1.9.3 (litellm ile) |
| Backend | Flask | >=3.1.0 |
| ORM | flask-sqlalchemy | 3.1.1 |
| Database | SQLite | - |
| Frontend | Inline HTML/CSS/JS | Tek dosya |
| Runtime | Python | 3.12 |
| Package Manager | uv | - |
| LLM | openai/minimax/minimax-m2.7 | OpenRouter uzerinden |

---

## Veri Modeli

Uc tablo, session tabanli checklist sistemi:

| Tablo | Gorev |
| ----- | ----- |
| `template_items` | Standart checklist maddelerini saklar (5 bolum, ~36 madde) |
| `flight_sessions` | Her ucus icin oturum kaydi (start/end time, status, notes) |
| `session_items` | O ucusa ait tamamlanma durumu (template_item_id, completed, completed_at) |

Bolumler: `Ortam Kontrolu` (6), `Ucus Oncesi` (12), `Ucus Sirasinda` (10), `Acil Durum` (10, referans paneli), `Ucus Sonrasi` (8).

Acil Durum maddeleri session'a kopyalanmaz, ayri endpoint ile cekilir.

---

## API Endpoint'leri

### CRUD
| Metot | Path | Aciklama |
| ----- | ---- | -------- |
| POST | `/api/sessions` | Yeni ucus baslat (body: drone_name) |
| GET | `/api/sessions/active` | Aktif oturumu getir |
| GET | `/api/sessions/<id>` | Spesifik oturum detayi |
| PUT | `/api/sessions/<id>/items/<item_id>` | Madde tamamlama (body: completed) |
| POST | `/api/sessions/<id>/close` | Oturumu kapat |
| GET | `/api/sessions/history` | Gecmis ucuslar |
| GET | `/api/reference/emergency` | Acil durum referans maddeleri |
| GET | `/api/template` | Tum sablon maddeleri |

### DroneChecklistAgent (Tek Agent, 3 Yetenek)
| Metot | Path | Yetenek | Gorev |
| ----- | ---- | ------- | ----- |
| GET | `/api/sessions/<id>/assess-risk` | Risk Degerlendirmesi | GO/NO-GO/WARNING karari, faz bazli ilerleme |
| GET | `/api/sessions/<id>/advisor` | Checklist Danismani | Mevcut faz, sonraki 5 adim, blokajlar |
| GET | `/api/sessions/<id>/report` | Rapor Uretici | Ucus ozeti, sure, eksikler, oneriler |

---

## DroneChecklistAgent

`drone_checklist_app.py` icinde tek bir `DroneChecklistAgent` sinifi bulunur. Bu sinifin 3 bagimsiz method'u, 3 farkli API endpoint'i uzerinden cagrilir:

### assess_risk() — Risk Degerlendirmesi
- Tüm maddeleri analiz eder
- Kritik fazlar (Ortam Kontrolu, Ucus Oncesi) tamamlanmadiysa → NO-GO
- Genel tamamlanma <%80 ise → WARNING
- Her sey tamam → GO
- Donus: karar, faz bazli ilerleme, uyarilar, eksik kritik maddeler

### get_advice() — Checklist Danismani
- Mevcut fazi tespit eder (ilk tamamlanmamis faz)
- Sonraki 5 adimi siralar
- Blokajlari gosterir
- Donus: mevcut faz, sonraki adimlar, blokajlar, faz ilerlemesi

### generate_report() — Rapor Uretici
- Ucus tamamlandiktan sonra calisir
- Sure hesaplar, faz bazli istatistik cikarir
- Eksik maddeleri, uyarilari ve iyilestirme onerilerini listeler
- Donus: ozet rapor, sure, faz istatistikleri, eksikler, oneriler

Bu 3 yetenek **Faz 2**'de ayri CrewAI agent'larina bolunmek uzere bagimsiz method'lar halinde tasarlandi.

---

## Kurulum

```bash
# 1. Python >=3.10,<3.14
# 2. Bagimliliklari yukle
uv sync

# 3. .env dosyasini olustur
cp .env.example .env

# 4. OpenRouter API key ayarla (.env)
OPENAI_API_KEY=your-openrouter-api-key
OPENAI_API_BASE=https://openrouter.ai/api/v1
OPENAI_MODEL_NAME=openai/minimax/minimax-m2.7
```

## Uygulamayi Calistirma

```bash
PORT=5001 uv run python drone_checklist_app.py
```

Tarayicida: `http://127.0.0.1:5001`

## CrewAI ile Uygulama Uretme

```bash
uv run run_crew
```

Agent `drone_checklist_app.py` dosyasini overwrite eder. Not: CrewAI her calistirmada dosyayi markdown fence icinde uretir, fence satirlari manuel temizlenmelidir.

---

## Bilinen Sinirlar / Sorunlar

1. Paket adi `crewai_todo_app` olarak kaldi (bilincli karar, ilk fazda urun dogrulama)
2. CrewAI agent her calismada `drone_checklist_app.py`'yi overwrite eder
3. `uv run` macOS Intel'de `onnxruntime` override gerektirir (`pyproject.toml`'da cozuldu)
4. Port 5000 macOS AirPlay Receiver ile cakisir, `PORT=5001` kullanin
5. CrewAI ciktisi markdown code fence icinde gelir, manuel temizlik gerekir
6. Test dosyalari yok, formatter/linter konfigure degil
7. GitHub email privacy son commit push'unu engelledi
8. Emergency items session'a kopyalanmaz, ayri endpoint

---

## Sonraki Adim (Faz 2)

Multi-agent mimariye gecis plani:

- Operasyon Planlayici
- Guvenlik ve Is Akisi Tasarimcisi
- Arayuz Tasarimcisi
- Full-Stack Gelistirici
- QA Gozden Gecirici
