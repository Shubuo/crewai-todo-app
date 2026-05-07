# Phase 1 Drone Checklist Plan

## Amac

Bu fazda mevcut CrewAI todo baseline'i, Turkce arayuzlu bir drone flight checklist uygulamasina pivot edilir.

Kapsam bilerek `single-agent` ile sinirli tutulur.

## Faz 1 Sinirlari

- Paket adi `crewai_todo_app` olarak kalir.
- Cikti uygulama dosyasi `drone_checklist_app.py` olur.
- UI basit tutulur.
- Multi-agent mimari bu fazda uygulanmaz.

## Urun Kararlari

Checklist bolumleri:

- `Ortam Kontrolu`
- `Ucus Oncesi`
- `Ucus Sirasinda`
- `Acil Durum Prosedurleri`
- `Ucus Sonrasi`

Kurallar:

- Her ucus icin yeni oturum acilir.
- Checklist ayni sablondan her ucusta yeniden olusur.
- `Acil Durum Prosedurleri` referans paneli olarak gosterilir.
- `Ortam Kontrolu` ayri ana bolumdur.

## Veri Modeli

### checklist_templates

Standart checklist maddelerini saklar.

Alanlar:

- `id`
- `category`
- `title`
- `sort_order`
- `required`
- `is_reference_only`

### flight_sessions

Her yeni ucus icin bir oturum kaydi tutar.

Alanlar:

- `id`
- `flight_name`
- `status`
- `started_at`
- `completed_at`

### session_items

Bir ucusa ait checklist durumunu saklar.

Alanlar:

- `id`
- `session_id`
- `template_id`
- `category`
- `title`
- `sort_order`
- `required`
- `completed`
- `completed_at`

## API Plani

Faz 1'de sade bir API kullanilir:

- `GET /api/active-session`
- `POST /api/sessions`
- `GET /api/sessions/<id>/items`
- `PUT /api/session-items/<id>`
- `POST /api/sessions/<id>/close`
- `GET /api/history`
- `GET /api/reference-items`

## UI Plani

Ana ekran tek sayfada calisir.

Bolumler:

- aktif ucus karti
- yeni ucus baslatma alani
- checklist bolumleri
- acil durum referans paneli
- gecmis ucuslar listesi

Bilerek disarida birakilanlar:

- kullanici sistemi
- coklu drone profili
- gelismis raporlama
- surukle-birak siralama

## CrewAI Tarafi Degisiklikleri

Degisecek dosyalar:

- `src/crewai_todo_app/config/agents.yaml`
- `src/crewai_todo_app/config/tasks.yaml`
- `src/crewai_todo_app/main.py`
- `src/crewai_todo_app/crew.py`

Yapilan ana degisiklikler:

- agent hedefi todo yerine drone checklist app uretmeye cevrilir
- gorev tanimi session bazli checklist mantigini ister
- output hedefi `drone_checklist_app.py` olur

## Uygulama Tarafi Degisiklikleri

Ana dosya:

- `drone_checklist_app.py`

Yapilan ana degisiklikler:

- `todos` modelinden cikis
- template + session mimarisina gecis
- varsayilan checklist seed verisi eklenmesi
- Turkce UI
- basit checklist tamamlama akisi
- gecmis ucuslar listesi

## Dokumantasyon ve Sunumlar

Guncellenecek dosyalar:

- `README.md`
- `CREWAI sunum.md`
- `CREWAI sunum.html`

Odak:

- todo case study yerine drone checklist case study
- Faz 1 single-agent kapsamı
- session bazli urun gerekcesi

## Kabul Kriterleri

Faz 1 tamamlandi sayilmasi icin:

1. CrewAI yeni cikti dosyasi adini kullanir.
2. Uygulama `drone_checklist_app.py` olarak calisir.
3. UI Turkcedir.
4. Her yeni ucus icin yeni checklist olusur.
5. Gecmis ucuslar saklanir.
6. `Ortam Kontrolu` ayri bolum olarak gorunur.
7. `Acil Durum Prosedurleri` referans paneli olarak gorunur.
8. README ve sunum dosyalari yeni anlatimla uyumludur.
