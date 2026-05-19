# PROJECT CONTEXT - Teknik Ozet

Bu dosya, `crewai-todo-app` reposundaki tum calismayi ozetler. Yeni bir sohbet/oturumda baglam kaybetmemek icin kullanilir.

---

## 1. Proje Amaci

Repo: `https://github.com/Shubuo/crewai-todo-app`
Konum: `/Users/buraky/1-CODE/personal/0-Lessons/crewai-todo-app`

Baslangic: Generic bir Todo App baseline'i, CrewAI single-agent ile uretilmis.
Pivot: Drone flight checklist uygulamasina cevrildi.

Hedefler:
- CrewAI ile single-agent uygulama uretimi
- Her ucus icin temiz baslayan session bazli checklist
- Turkce UI
- Uygulama ici agentic akislar (risk, danisman, rapor)
- Sunum materyalleri (md, html, pptx, speaker notes, png gorseller)

---

## 2. Teknoloji Yigini

| Katman | Teknoloji | Surum |
| --- | --- | --- |
| AI Framework | CrewAI | 1.9.3 (litellm ile) |
| Backend | Flask | >=3.1.0 |
| ORM | flask-sqlalchemy | 3.1.1 |
| Database | SQLite | |
| Frontend | Inline HTML/CSS/JS | Tek dosya |
| Runtime | Python | 3.12 |
| Package Manager | uv | |
| LLM | openai/minimax/minimax-m2.7 | OpenRouter uzerinden |

Dikey uyumsuzluk cozuldu:
- `onnxruntime` macOS x86_64 (Intel Mac) icin wheel yok
- Cozum: `uv.lock` override ile `onnxruntime>=1.19,<1.22` (universal2 wheel)
- `pyproject.toml` icine `[tool.uv] override-dependencies` eklendi

---

## 3. Proje Yapisı

```
crewai-todo-app/
├── src/crewai_todo_app/         # CrewAI uretim kaynagi (paket adi DEGISMEDI)
│   ├── config/
│   │   ├── agents.yaml          # Agent tanimi (full_stack_developer)
│   │   └── tasks.yaml           # Gorev tanimi (generate_drone_checklist_app_task)
│   ├── crew.py                  # CrewAIDroneChecklistApp sinifi
│   ├── main.py                  # Giris noktasi (_default_inputs, run, train, replay, test)
│   └── tools/
│       ├── __init__.py
│       └── custom_tool.py       # Placeholder, kullanilmiyor
├── drone_checklist_app.py       # Uygulama (1161 satir, Flask + SQLAlchemy + inline JS)
├── PHASE1_DRONE_CHECKLIST_PLAN.md  # Faz 1 plan dokumani
├── README.md                    # Kurulum ve kullanim
├── DEMO_ADIMLAR.md              # Adim adim demo talimatlari
├── CREWAI sunum.md              # Marp sunum (27 slayt, PNG referansli)
├── CREWAI sunum.html            # HTML sunum (27 slayt)
├── CREWAI sunum.pptx            # PowerPoint sunum (27 slayt, 27 speaker notes)
├── CREWAI sunum konusmaci notlari.md  # Ayri speaker notes dosyasi
├── CREWAI sunum canva paste.txt # Canva icin TXT outline (27 slayt)
├── assets/                      # 15 adet PNG gorsel
├── .env.example                 # OpenRouter API key sablonu
├── .env                         # (gitignore'da)
├── .gitignore
├── pyproject.toml
└── uv.lock
```

Paket adi neden degismedi: Kontrollu kapsam karari, ilk fazda urun modelini dogrulamak icin.

---

## 4. Veri Modeli

Flask-SQLAlchemy uzerinden uc tablo:

```python
class ChecklistTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    section = db.Column(db.String(100), nullable=False)     # Ortam Kontrolu, Ucus Oncesi, vs.
    item_text = db.Column(db.Text, nullable=False)
    order_index = db.Column(db.Integer, nullable=False)
    is_emergency = db.Column(db.Boolean, default=False)      # True = referans paneli

class FlightSession(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text, nullable=True)

class ChecklistItemCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('flight_session.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('checklist_template.id'), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
```

Bolumler (Sections):
- `Ortam Kontrolu` (6 madde)
- `Ucus Oncesi` (9 madde)
- `Ucus Sirasinda` (7 madde)
- `Acil Durum Prosedurleri` (7 madde, is_emergency=True, referans paneli)
- `Ucus Sonrasi` (7 madde)

Not: Emergency items session olusturulurken ChecklistItemCompletion'a KOPYALANMAZ. AyrI endpoint ile cekilir.

---

## 5. API Endpoint'leri

### CRUD
- `POST /api/sessions/start` - Yeni ucus olusturur
- `GET /api/sessions/active` - Aktif oturumu getirir
- `GET /api/sessions/<id>` - Spesifik oturum detayi
- `PUT /api/sessions/<session_id>/items/<template_id>` - Madde tamamlama durumu gunceller
- `POST /api/sessions/<id>/close` - Oturumu kapatir
- `GET /api/sessions/history` - Gecmis oturumlar listesi
- `GET /api/emergency/reference` - Acil durum referans maddeleri

### Agent Endpoint'leri (In-App Agentic)
- `GET /api/sessions/<id>/assess-risk` - Risk Degerlendirmesi Agent'i
- `GET /api/sessions/<id>/advisor` - Checklist Danismani Agent'i
- `GET /api/sessions/<id>/report` - Rapor Uretici Agent'i

---

## 6. Agent Siniflari (In-App Agentic Akis)

### RiskAssessmentAgent
- Checklist tamamlanma durumunu analiz eder
- Ortam kontrolu yuzdesi hesaplar
- Kritik madde eksikliklerini belirler (HIGH_RISK_ITEMS listesi)
- Karar verir: GO / NO-GO / WARNING
- JSON response dondurur

### ChecklistAdvisorAgent
- Faz bazli onceliklendirme yapar (Ortam Kontrolu > Ucus Oncesi > Ucus Sirasinda > Ucus Sonrasi)
- Ilk eksik faz tespit eder
- Sonraki 5 adimi onerir
- Bloklar listesi olusturur
- JSON response dondurur

### FlightReportAgent
- Tamamlanma yuzdesi hesaplar
- Faz bazli istatistikler olusturur
- Uyarilar listesi (eksik maddeler)
- Oneriler listesi (%80 alti uyari, eksik ortam kontrolu uyari)
- Sure hesaplamasi
- JSON response dondurur

---

## 7. CrewAI Konfigurasyonu

### Agent (src/crewai_todo_app/config/agents.yaml)
```yaml
full_stack_developer:
  role: Full-Stack Developer
  goal: Drone flight checklist app uretmek
  backstory: Pragmatic engineer, Turkce UI, tek dosya cikti
  llm: openai/minimax/minimax-m2.7
```

### Task (src/crewai_todo_app/config/tasks.yaml)
- Task adi: `generate_drone_checklist_app_task`
- Cikti dosyasi: `drone_checklist_app.py`
- Gereksinimler: Flask + SQLite + Turkce UI + session bazli checklist + 5 bolum + seed data

### Crew (src/crewai_todo_app/crew.py)
- Sinif: `CrewAIDroneChecklistApp` (not: eski ad `CrewAITodoApp`)
- 1 agent, 1 task, sequential process
- output_file: `drone_checklist_app.py`

### Main (src/crewai_todo_app/main.py)
- _default_inputs: `project_name = "Drone Flight Checklist App"`, `output_file = "drone_checklist_app.py"`
- Calisma komutlari: `uv run run_crew`, `uv run train`, `uv run replay`, `uv run test`

---

## 8. Basit UI Kararlari

Tek sayfa arayuz:
- Aktif ucus karti (ilerleme + sayac)
- Risk Degerlendirmesi Agent paneli (GO/NO-GO)
- Checklist Danismani Agent paneli (sonraki adimlar)
- 5 bolum tab'i (Ortam Kontrolu, Ucus Oncesi, Ucus Sirasinda, Acil Durum, Ucus Sonrasi)
- Acil durum referans paneli (checkbox degil, okunabilir liste)
- Gecmis ucuslar listesi (rapor gor butonu ile)
- Not ekleme modal'i

Turkce arayuz, dark tema, mobil uyumlu.

---

## 9. Sunum Materyalleri

Dosyalar:
- `CREWAI sunum.md` - Marp format, 27 slayt, PNG gorsel referansli
- `CREWAI sunum.html` - Browser'da goruntulenir, 27 slayt
- `CREWAI sunum.pptx` - PowerPoint, 27 slayt, 27 speaker notes, PNG gorsel gomulu
- `CREWAI sunum konusmaci notlari.md` - Ayri speaker notes
- `CREWAI sunum canva paste.txt` - Canva'ya kopyalanabilir TXT outline
- `assets/*.png` - 15 adet PNG gorsel (olcusu 1920x1080)

Sunum akisi 3 konusmaci:
1. MAS teorisi, BDI, CrewAI temel
2. FIPA, hafiza, guvenilirlik
3. Uygulama case study

---

## 10. Cozulen Kritik Bug'lar

### Bug 1: onnxruntime macOS x86_64 uyumsuzluk
- Sorun: `onnxruntime==1.25.1` macOS Intel icin wheel yok (sadece arm64)
- Cozum: `pyproject.toml` icine `[tool.uv] override-dependencies = ["onnxruntime>=1.19,<1.22"]` eklendi
- `uv lock && uv sync` ile `onnxruntime==1.21.1` (universal2) kuruldu

### Bug 2: SVG gorsel mod uyumsuzluk
- Sorun: Python PIL `alpha_composite` RGBA mod uyusmazligi (gorsel olusamadi)
- Cozum: `shadow_rect` fonksiyonu yeniden yazildi, blur/alpha_composite kaldirildi, offset shadow kullanildi

### Bug 3: GitHub email gizlilik
- Sorun: `git push` GitHub email privacy korumasinda reddedildi
- Cozum: GitHub'da "Keep my email addresses private" kapatilmali veya `git config user.email` noreply ile degistirilmeli
- Durum: Henuz cozulmedi, push atilmadi

### Bug 4: Port 5000 cakismasi
- Sorun: macOS AirPlay Receiver port 5000'i kullaniyor
- Cozum: `PORT=5001` env var ile calistir veya `app.run(port=port)` ile env'den oku
- `drone_checklist_app.py` icinde `os.environ.get('PORT', '5000')` eklendi

### Bug 5: CrewAI agent output markdown fences
- Sorun: Agent uretimi markdown code fence icinde uretiliyor (` ```python `)
- Cozum: Dosya basindaki ve sonundaki fence satirlari manuel olarak silindi
- Not: CrewAI her calistirmada overwrite eder, dikkatli olunmali

### Bug 6: ESLint/Code formatting
- Proje icinde formatter veya linter kurulu degil
- Python syntax kontrolu: `python3 -m py_compile`
- Diger kontroller: manuel

---

## 11. Git Durumu

Branch: `main`
Remote: `origin` -> `https://github.com/Shubuo/crewai-todo-app.git`

Commit'ler:
```
2b2e0c1 Fix onnxruntime compatibility for macOS x86_64 (commit yapildi, push BASARISIZ)
bd5c038 Add Canva-ready presentation assets
605da65 Pivot the Phase 1 baseline to a drone flight checklist app
d6c475c Refine the Todo baseline and align the Group 4 presentation
57de3b5 Set up single-agent CrewAI Todo App baseline
```

Push durumu:
- Son basarili push: `bd5c0c1` (Canva-ready presentation assets)
- `2b2e0c1` commit'i local'de var, push edilemedi (email privacy)

---

## 12. Kodlama Standartlari

- Python dosyalari tek dosya uygulama olarak tasarlanir (Faz 1)
- Turkce yorum ve UI metinleri
- ASCII disi karakterler minimal kullanilir
- Fonksiyon isimleri: snake_case (Python), camelCase (JS)
- Sinif isimleri: PascalCase
- API endpoint'leri: RESTful, noun-based
- ORM: Flask-SQLAlchemy (CrewAI agent uretiminde)
- Not: CrewAI agent her calistirmada dosyayi overwrite eder, dikkatli olunmali

---

## 13. Calistirme Komutlari

### CrewAI uygulama uretme
```bash
uv run run_crew
```

### Uygulama calistirma
```bash
PORT=5001 uv run python drone_checklist_app.py
```

### Bagimlilik yukleme
```bash
uv sync
```

### Port kontrolu
```bash
lsof -i :5000 -sTCP:LISTEN -P
```

---

## 14. Bilinen Sinirlar

1. Paket adi `crewai_todo_app` olarak kaldi, degismedi
2. CrewAI agent her calismada `drone_checklist_app.py`'yi overwrite eder (manually crafted versiyon korunmali)
3. `uv run` macOS Intel'de `onnxruntime` override gerektirir
4. GitHub email privacy nedeniyle son commit push edilemedi
5. Test dosyalari yok (`tests/` bos)
6. Formatter/linter konfigure degil
7. Emergency items session'a kopyalanmaz, ayri endpoint ile cekilir
8. UI dark tema, mobil uyumlu ama responsive breakpoints minimal

---

## 15. Goruntu Gorsel Uretim Araci

PNG gorseller Python PIL/Pillow ile uretildi:
- Tablo: 1920x1080
- Font: Arial (system font)
- Renk semasi: navy (#102033), blue (#2563EB), green (#16A34A), orange (#F97316), purple (#7C3AED)
- Stil: gradient background, rounded rectangle shadow, clean infographic
- Gorseller: covers, diagrams, flow charts, wireframes, ERD
