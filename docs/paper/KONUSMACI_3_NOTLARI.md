# Konusmaci 3 Notlari

Genel kapsam: Drone checklist uygulamasi, veri modeli, API, UI, sonuc.

---

## Slayt 15 - Konusmaci 3 Bolum Girisi

**Anlatim Notu:**
- Bu bolum tamamen uygulama odakli 
- `drone_checklist_app.py` dosyasi, veri modeli, API ve UI akisi anlatilacak.

**Gorsel Onerisi:**
Uygulama ana ekranindan bir screenshot veya wireframe.

## Slayt 16 - Faz 1 Uygulama Mimarisi

**Anlatim Notu:**
- "drone_checklist_app.py` dosyasinin Flask server, SQLite baglantisi ve HTML/CSS/JS arayuzunu tek dosyada tutuyor. Bu Faz 1 icin bilerek sade tutuldu. 
Bu mimaride kullanici acisindan ana akis yeni bir ucus oturumu baslatmakla basliyor."

**Gorsel:**
`assets/09-app-architecture.png`

## Slayt 17 - Drone Checklist Urun Akisi

**Anlatim Notu:**
Pilotun uygulamayi nasil kullanacagini burada görebiliriz.
Yeni ucus, checklist kopyalama, maddeleri tamamlama, acil durum paneli, ucus kapatma ve history adimlarini takip eder.
"Bu akisin temelinde, checklist maddelerinin operasyonel fazlara ayrilmasi yatmakta."

**Gorsel:**
`assets/10-flight-session-flow.png`

## Slayt 18 - Checklist Fazlari

**Anlatim Notu:**
- Ortam Kontrolu, Ucus Oncesi, Ucus Sirasinda ve Ucus Sonrasi bolumleri.
- Acil Durum Prosedurleri checkbox degil referans paneli 
- Bu fazlarin her ucusta yeniden calisabilmesi icin veri modeli session tabanli kuruldu."

**Gorsel:**
`assets/11-checklist-phases.png`

## Slayt 19 - Veri Modeli

**Anlatim Notu:**
Uc tablo var. 
- `checklist_templates` sablon,
- `flight_sessions` ucus,
- `session_items` o ucusun checklist kopyasidir.
"Bu modelin en onemli katkisi, her ucusun temiz checklist ile baslamasidır."

**Gorsel:**
`assets/12-data-model-erd.png`

## Slayt 20 - Session Mantigi
**Anlatim Notu:**
Session olmadan onceki ucusun tamamlanmis maddelerinin yeni ucusa tasinabilir. Session ile her ucusun ayri takip edilir.
"Bu session mantigi API endpoint'lerine de dogrudan yansiyor."

**Gorsel Onerisi:**
Iki ayri ucus karti: Ucus 1 tamamlandi, Ucus 2 temiz basliyor.

## Slayt 21 - API Akisi
**Anlatim Notu:**
Endpoint'ler Grupla: 
- aktif session okuma, 
- session baslatma, 
- item guncelleme, 
- session kapatma, 
- history ve reference items.
"Bu API'ler sade bir Turkce UI tarafindan kullaniliyor."

**Gorsel:**
`assets/13-api-flow.png`

## Slayt 22 - Basit Turkce UI
**Anlatim Notu:**
UI bilerek sade tutuldu. Faz 1 icin hedef cok ozellikli dashboard degil, operasyonel akisi net gosteren calisan bir uygulama.
"Uygulamanin temel akislarini smoke test ile kontrol ettik."

**Gorsel:**
`assets/14-ui-wireframe.png`

## Slayt 23 - Dogrulama
**Anlatim Notu:**
Compile kontrolu ve Flask API smoke test yapildi. `uv run` probleminin uygulama bug'i degil, `onnxruntime` platform bagimliligi
"Bu kontrollerden sonra Faz 1 icin ortaya cikan ciktilari ozetleyebiliriz."

**Gorsel Onerisi:**
Terminalde `smoke ok` ciktisi veya dogrulama checklist'i.

## Slayt 24 - Faz 1 Ciktilari
**Anlatim Notu:**
Ana ciktilar `drone_checklist_app.py`, plan dokumani, README, HTML sunum, speaker notes ve assets klasorunun hazir oldugunu belirt.
Bu Faz 1 ciktisi, sonraki multi-agent faz icin referans noktasi olacak"

**Gorsel Onerisi:**
Dosya agaci gorseli veya repository screenshot'i.

## Slayt 25 - Sonraki Adim
**Anlatim Notu:**
Faz 2'de roller ayrilabilir: 
- operasyon planlayici, 
- guvenlik akisi tasarimcisi, 
- arayuz tasarimcisi, 
- full-stack gelistirici, 
- QA gozden gecirici. Bu fazda amac rolleri uygulamak degil, bu rollere anlamli bir urun hedefi hazirlamakti.


**Gorsel:**
`assets/15-phase2-roadmap.png`

## Slayt 26 - Kapanis

**Anlatim Notu:**
- Ana mesaji ver: MAS teorisi, FIPA standartlari ve CrewAI pratigi, calisan bir drone checklist uygulamasinda birlestirildi. Faz 1, multi-agent calismasi icin saglam baseline olusturdu
- Tesekkurler, sorularinizi alabiliriz."

**Gorsel Onerisi:**
Theory -> Standards -> App -> Next Phase akisi.


