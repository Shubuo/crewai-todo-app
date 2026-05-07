# Drone Flight Checklist App - Faz 1

Bu repository, CrewAI ile uretilen tek dosyali bir Flask uygulamasini drone ucus checklist urunune pivot eder.

Bu fazda sistem bilerek `single-agent` olarak tutulur. Amac, generic todo uygulamasi yerine her ucus icin yeniden baslayan, Turkce arayuzlu bir checklist akisi kurmaktir.

## Faz 1 Hedefi

- tek agent ile uygulama uretmek
- ciktiyi `drone_checklist_app.py` dosyasina yazmak
- SQLite tabanli checklist template + flight session modeli kullanmak
- basit tek sayfa bir arayuz sunmak
- ucus gecmisini saklamak

## Uygulama Kapsami

Checklist bolumleri:

- `Ortam Kontrolu`
- `Ucus Oncesi`
- `Ucus Sirasinda`
- `Acil Durum Prosedurleri`
- `Ucus Sonrasi`

Temel davranislar:

- Her yeni ucus, ortak checklist sablonundan yeni bir oturum olusturur.
- Checklist maddeleri ucus bazli takip edilir.
- `Acil Durum Prosedurleri` referans paneli olarak gosterilir.
- Arayuz Turkcedir ve basit tutulur.

## Proje Yapisi

```text
src/crewai_todo_app/
  config/
    agents.yaml
    tasks.yaml
  crew.py
  main.py
drone_checklist_app.py
PHASE1_DRONE_CHECKLIST_PLAN.md
```

Not:

- Paket klasoru uyumluluk icin su an `crewai_todo_app` olarak kalir.
- Uygulama cikti dosyasi ise `drone_checklist_app.py` olarak degismistir.

## Kurulum

1. Python `>=3.10,<3.14` kullanin.
2. Gerekirse `uv` kurun:

```bash
pip install uv
```

3. Bagimliliklari yukleyin:

```bash
uv sync
```

4. `.env` dosyasini olusturun:

```bash
cp .env.example .env
```

5. OpenRouter bilgilerinizi ayarlayin:

```env
OPENAI_API_KEY=your-openrouter-api-key
OPENAI_API_BASE=https://openrouter.ai/api/v1
OPENAI_MODEL_NAME=openai/minimax/minimax-m2.7
```

## CrewAI Faz 1 Akisini Calistirma

Onerilen komut:

```bash
uv run run_crew
```

Beklenen sonuc:

- tek `Full-Stack Developer` agent calisir
- agent `drone_checklist_app.py` dosyasina Faz 1 urununu yazar

## Uygulamayi Calistirma

Crew cikisi olustuktan sonra:

```bash
uv run python drone_checklist_app.py
```

Ardindan terminalde gorunen yerel Flask adresini acin.

## Veri Modeli

Faz 1 uygulamasi uc tablo mantigina dayanir:

- `checklist_templates`: standart maddeler
- `flight_sessions`: her ucus icin oturum kaydi
- `session_items`: checklist tamamlanma durumu

Bu model sayesinde checklist her ucusta sifirdan baslar ama gecmis ucuslar korunur.

## Basit UI Kararlari

Bilerek sade tutuldu:

- tek sayfa arayuz
- aktif ucus karti
- faz bazli checklist bolumleri
- ayri acil durum referans paneli
- altta basit gecmis ucuslar listesi

Bilerek eklenmeyenler:

- kullanici sistemi
- coklu drone profili
- karmasik dashboard
- multi-agent orkestrasyonu

## Faz 1 Dosyalari

- Uygulama: `drone_checklist_app.py`
- Plan dokumani: `PHASE1_DRONE_CHECKLIST_PLAN.md`
- Sunumlar:
  - `CREWAI sunum.md`
  - `CREWAI sunum.html`

## Sonraki Adim

Bu faz tamamlandiktan sonra ayni urun, uzmanlasmis rollerle multi-agent mimariye bolunebilir. Bu repo icinde o gecis bu asamada uygulanmamistir.
