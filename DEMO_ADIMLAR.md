# Drone Flight Checklist App - Demo Adimlari

## BOLUM 1: Agent Konfigurasyonu

### Adim 1: Agent Tanimini Goster

```bash
cat src/crewai_todo_app/config/agents.yaml
```

Agent: Full-Stack Developer
Gorev: Drone flight checklist app uretmek

**Sunum notu:** "Tek agent, tek gorev. Bu agent uygulamayi uretiyor."

### Adim 2: Gorev Tanimini Goster

```bash
cat src/crewai_todo_app/config/tasks.yaml
```

- Session bazli checklist modeli
- Turkce UI
- 5 bolum
- Zorunlu maddeler tamamlanmadan ucus kapatilamaz

### Adim 3: Agent'i Calistir

```bash
uv run run_crew
```

Agent uygulamayi uretir.

---

## BOLUM 2: Uygulama ve In-App Agent'lar

### Adim 4: Uygulamayi Baslat

```bash
PORT=5001 uv run python drone_checklist_app.py
```

Tarayicida: `http://127.0.0.1:5001`

### Adim 5: Bos Ekran

- "Aktif Ucus Oturumu Yok" mesaji
- Acil Durum Prosedurleri referans paneli gorunecek
- Gecmis Ucuslar bolumu bos

**Sunum notu:** "Uygulama 3 agent ile calisiyor. Ilk olarak acil durum referans panelini goruyorsunuz."

### Adim 6: Yeni Ucus Baslat

"Yeni Ucus Baslat" butonuna bas.

Ekran gorunecekler:
- Aktif ucus karti
- Checklist bolumleri
- **Agent 1: Risk Degerlendirmesi** - GO/NO-GO karar karti
- **Agent 2: Checklist Danismani** - sonraki adimlar listesi
- Acil Durum referans paneli

**Sunum notu:** "Iki agent ayni anda calisiyor. Risk agent'i GO/NO-GO karari veriyor, danisman agent sonraki adimlari oneriyor."

### Adim 7: Risk Agent'i Incele

Risk Degerlendirmesi paneline bak:
- NO-GO / WARNING / GO karari
- Genel tamamlanma yuzdesi
- Ortam kontrolu yuzdesi
- Kritik eksik madde sayisi
- Uyarilar listesi

**Sunum notu:** "Risk agent'i checklist durumunu analiz ediyor ve guvenlik karari veriyor."

### Adim 8: Danisman Agent'i Incele

Akil'li Checklist Danismani paneline bak:
- Mevcut faz (Ortam Kontrolu)
- Sonraki 5 adim
- Bloklar listesi

**Sunum notu:** "Danisman agent hangi adimlarin oncelikli oldugunu soyluyor."

### Adim 9: Kontrolleri Yap

Ortam Kontrolu maddelerini isaretle:
- Hava durumu kontrol edildi
- Ucus bolgesi kontrol edildi
- GPS sinyal gucu

**Sunum notu:** "Maddeleri isaretledikce agent'lar otomatik guncellenecek."

### Adim 10: Risk Agent'i Guncelle

"Yenile" butonuna bas veya baska bir maddeyi isaretle.

Risk karari degisecek:
- NO-GO -> WARNING -> GO

**Sunum notu:** "Agent'lar canli olarak checklist durumunu degerlendiriyor."

### Adim 11: Danisman Agent'i Guncelle

"Yenile" butonuna bas veya faz degisikligi gor.

- Mevcut faz degisebilir
- Sonraki adimlar guncellenecek

**Sunum notu:** "Danisman agent faz degisikligini takip ediyor."

### Adim 12: Tum Kontrolleri Tamamla

Diğer bolumleri de isaretle:
- Ucus Oncesi
- Ucus Sirasinda
- Ucus Sonrasi

Risk agent'i GO degerlendirmesi verecek.

**Sunum notu:** "Tum kontroller tamamlandiginda risk agent'i GO karari veriyor."

### Adim 13: Ucusu Kapat

"Oturumu Kapat" butonuna bas.

### Adim 14: Gecmis Ucus Raporu

Gecmis Ucuslar bolumunde ucus gorunecek. "Rapor Gor" butonuna bas.

Rapor Agent'i gorunecek:
- Tamamlanma yuzdesi
- Sure
- Faz degerlendirmesi (her faz icin tamamlanma yuzdesi)
- Eksik maddeler listesi
- Uyarilar
- Oneriler

**Sunum notu:** "3. agent: Rapor uretici. Ucus tamamlandiginda ozet rapor olusturuyor."

---

## BOLUM 3: API Demo (Opsiyonel)

```bash
# Risk Degerlendirmesi
curl http://127.0.0.1:5001/api/sessions/1/assess-risk

# Checklist Danismani
curl http://127.0.0.1:5001/api/sessions/1/advisor

# Ucus Raporu
curl http://127.0.0.1:5001/api/sessions/1/report

# Acil Durum Referans
curl http://127.0.0.1:5001/api/emergency/reference
```

---

## BOLUM 4: Ozet

Demo sirasinda gosterilen 3 Agent:

| Agent | Gorev | API | Ani Degerlendirme |
| --- | --- | --- | --- |
| Risk Degerlendirmesi | GO/NO-GO karari | /api/sessions/<id>/assess-risk | Canli |
| Checklist Danismani | Sonraki adimlar | /api/sessions/<id>/advisor | Canli |
| Rapor Uretici | Ozet rapor | /api/sessions/<id>/report | Kapanis |

**Sunum notu:** "Uygulama ici 3 agent calisiyor. Bunlar CrewAI'nin urettigi uygulama icindeki agentic akislar. CrewAI agent uretiyor, bu agent'lar calistiriyor."

---

## Port Notu

```bash
PORT=5001 uv run python drone_checklist_app.py
```
