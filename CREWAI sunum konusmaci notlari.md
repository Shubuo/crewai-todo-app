# CREWAI Sunum Konusmaci Notlari

Bu dosya sunumu takip etmek icin hazirlandi. `CREWAI sunum.md` slayt icerigini, bu dosya ise anlatim notlarini ve gorsel onerilerini icerir.

## Genel Akis

- Konusmaci 1: MAS teorisi, BDI, CrewAI yapi taslari, process yonetimi
- Konusmaci 2: FIPA, AMS, DF, ACL, memory, retry, human-in-the-loop
- Konusmaci 3: Drone checklist uygulamasi, veri modeli, API, UI, sonuc

Toplam hedef sure: 18-22 dakika

## Slayt 1 - Kapak

Konusmaci: 1

Anlatim Notu:
Sunuma projenin ana hedefini net soyleyerek basla. Bu calisma, CrewAI ile tek agentli bir drone flight checklist uygulamasinin nasil tasarlandigini ve calisan uygulamaya nasil donustugunu anlatir.

Gecis Cumlesi:
"Once teorik zemini kuracagiz, sonra bu zemini CrewAI ve uygulama mimarimizle baglayacagiz."

Gorsel:
`assets/01-cover-drone-checklist.png`

## Slayt 2 - Sunum Akisi

Konusmaci: 1

Anlatim Notu:
Uc kisilik dagilimi anlat. Her konusmacinin ayni hikayenin farkli bir katmanini anlattigini belirt: teori, standartlar, uygulama.

Gecis Cumlesi:
"Ilk bolumde ajan kavramini ve CrewAI'in bu kavrama nasil pratik bir model sundugunu gorecegiz."

Gorsel:
`assets/02-three-speaker-flow.png`

## Slayt 3 - Konusmaci 1 Bolum Girisi

Konusmaci: 1

Anlatim Notu:
Kendi bolumunun amacini acikla. Bu kisimda kod detayina girmeden once agent kavramini akademik olarak konumlandiracaksin.

Gecis Cumlesi:
"Ajan kavrami klasik yazilim modullerinden farkli bir dusunme bicimi getirir."

Gorsel Onerisi:
Bu slayt metin agirlikli kalabilir. Arka planda hafif bir teori -> uygulama ok gorseli kullanilabilir.

## Slayt 4 - Ajan Kavrami

Konusmaci: 1

Anlatim Notu:
Ajanin sadece fonksiyon calistiran kod olmadigini vurgula. Ozerklik, reaktiflik ve proaktiflik kavramlarini kisa orneklerle acikla.

Gecis Cumlesi:
"Bu davranis modelini daha sistematik aciklamak icin BDI modelini kullaniyoruz."

Gorsel Onerisi:
Ortada agent, etrafinda environment, goal, action ve feedback oklarindan olusan dongu.

## Slayt 5 - BDI Modeli

Konusmaci: 1

Anlatim Notu:
Belief, Desire ve Intention kavramlarini sirayla anlat. Projedeki karsiliklarini kullan: Flask/SQLite bilgisi, checklist app hedefi, tek dosya app uretme task'i.

Gecis Cumlesi:
"CrewAI'de agent tanimlari aslinda bu BDI mantigina cok benzer sekilde kurulur."

Gorsel:
`assets/03-bdi-crewai-mapping.png`

## Slayt 6 - CrewAI Agent Ornegi

Konusmaci: 1

Anlatim Notu:
Kodun tamamini okumadan role, goal ve backstory alanlarinin ne ise yaradigini anlat. Goal alaninin agent'in uretmesi gereken nihai sonucu belirledigini vurgula.

Gecis Cumlesi:
"Tek bir agent tanimi yeterli degil; CrewAI bu agent'i task ve crew yapilariyla calistirir."

Gorsel Onerisi:
Kod snippet'i yaninda role-goal-backstory etiketleri.

## Slayt 7 - CrewAI Yapi Taslari

Konusmaci: 1

Anlatim Notu:
Agent, Task, Tools ve Crew kavramlarini uygulama gelistirme akisi olarak anlat. Tek agent olsa bile bu yapinin multi-agent'a genisleyebilecegini belirt.

Gecis Cumlesi:
"Bu yapilarin nasil calisacagini belirleyen kisim process yonetimidir."

Gorsel:
`assets/04-crewai-building-blocks.png`

## Slayt 8 - Process Yonetimi

Konusmaci: 1

Anlatim Notu:
Sequential ve hierarchical yaklasimlari karsilastir. Faz 1 icin sequential tercihinin bilincli olarak daha sade ve kontrol edilebilir oldugunu soyle.

Gecis Cumlesi:
"Simdi bu agent kavramlarini standartlar tarafindan nasil ele alindigina bakalim."

Gorsel:
`assets/05-sequential-vs-hierarchical.png`

## Slayt 9 - Konusmaci 2 Bolum Girisi

Konusmaci: 2

Anlatim Notu:
Bu bolumde teoriyi standartlar ve guvenilirlik mekanizmalariyla baglayacagini soyle. FIPA, memory ve human-in-the-loop'u birbirinden kopuk degil, agent sistemini guvenilir yapan parcaciklar olarak anlat.

Gecis Cumlesi:
"FIPA, ajan sistemleri icin ortak bir dil ve standart seti sunar."

Gorsel Onerisi:
FIPA -> CrewAI -> uygulama seklinde uc katmanli basit sema.

## Slayt 10 - FIPA Nedir?

Konusmaci: 2

Anlatim Notu:
FIPA'yi teorik bir standart olarak tanit. Ajanlarin kimlik, yetenek ve mesajlasma acisindan nasil dusunulmesi gerektigini anlattigini belirt.

Gecis Cumlesi:
"Bu kavramlar CrewAI'de daha pratik karsiliklarla gorulur."

Gorsel Onerisi:
FIPA yazisi etrafinda identity, service, message, lifecycle ikonlari.

## Slayt 11 - FIPA -> CrewAI Karsiliklari

Konusmaci: 2

Anlatim Notu:
AMS'i agent listesi, DF'i tools listesi, ACL'i task context akisi ile eslestir. Birebir ayni sistem olmadigini ama kavramsal benzerlik oldugunu vurgula.

Gecis Cumlesi:
"Bu eslesmenin en guzel ornegi, FIPA ACL mesajlarinin CrewAI task akisi ile benzetilmesidir."

Gorsel:
`assets/06-fipa-crewai-mapping.png`

## Slayt 12 - FIPA ACL ve CrewAI Context

Konusmaci: 2

Anlatim Notu:
REQUEST, INFORM, REFUSE ve FAILURE kavramlarini kisa anlat. CrewAI'de bir task ciktisinin sonraki task icin bilgi tasidigini soyle.

Gecis Cumlesi:
"Sadece mesajlasma yetmez; agent sistemlerinde baglam ve hata yonetimi de kritik hale gelir."

Gorsel:
`assets/07-fipa-acl-context-flow.png`

## Slayt 13 - Memory Sistemleri

Konusmaci: 2

Anlatim Notu:
Short-term memory'nin oturum baglamini, long-term memory'nin ise onceki deneyimlerden yararlanmayi ifade ettigini anlat. Bu projede Faz 1 basit tutulsa da memory kavraminin sonraki faz icin onemli oldugunu belirt.

Gecis Cumlesi:
"Memory kadar onemli diger konu, agent'in hata durumunda nasil davranacagidir."

Gorsel Onerisi:
Kisa sureli hafiza ve uzun sureli hafiza icin iki kutulu diagram.

## Slayt 14 - Retry ve Human-in-the-Loop

Konusmaci: 2

Anlatim Notu:
Retry'nin teknik hata durumunda, human-in-the-loop'un ise kritik karar durumunda kullanildigini anlat. Drone domain'inde guvenlik kararlari icin insan onayinin onemli olabilecegini vurgula.

Gecis Cumlesi:
"Bu teorik ve standart temelden sonra artik uygulamanin nasil kurulduguna gecebiliriz."

Gorsel:
`assets/08-memory-retry-hitl.png`

## Slayt 15 - Konusmaci 3 Bolum Girisi

Konusmaci: 3

Anlatim Notu:
Bu bolumun tamamen uygulama odakli oldugunu soyle. Artik ortaya cikan `drone_checklist_app.py` dosyasi, veri modeli, API ve UI akisi anlatilacak.

Gecis Cumlesi:
"Uygulama mimarisi tek dosyada ama icinde backend, veritabani ve UI birlikte calisiyor."

Gorsel Onerisi:
Uygulama ana ekranindan bir screenshot veya wireframe.

## Slayt 16 - Faz 1 Uygulama Mimarisi

Konusmaci: 3

Anlatim Notu:
`drone_checklist_app.py` dosyasinin Flask server, SQLite baglantisi ve HTML/CSS/JS arayuzunu tek dosyada tuttugunu anlat. Bu Faz 1 icin bilerek sade tutuldu.

Gecis Cumlesi:
"Bu mimaride kullanici acisindan ana akis yeni bir ucus oturumu baslatmakla basliyor."

Gorsel:
`assets/09-app-architecture.png`

## Slayt 17 - Drone Checklist Urun Akisi

Konusmaci: 3

Anlatim Notu:
Pilotun uygulamayi nasil kullanacagini hikaye gibi anlat. Yeni ucus, checklist kopyalama, maddeleri tamamlama, acil durum paneli, ucus kapatma ve history adimlarini takip et.

Gecis Cumlesi:
"Bu akisin temelinde, checklist maddelerinin operasyonel fazlara ayrilmasi var."

Gorsel:
`assets/10-flight-session-flow.png`

## Slayt 18 - Checklist Fazlari

Konusmaci: 3

Anlatim Notu:
Ortam Kontrolu, Ucus Oncesi, Ucus Sirasinda ve Ucus Sonrasi bolumlerini acikla. Acil Durum Prosedurleri'nin checkbox degil referans paneli oldugunu net vurgula.

Gecis Cumlesi:
"Bu fazlarin her ucusta yeniden calisabilmesi icin veri modeli session tabanli kuruldu."

Gorsel:
`assets/11-checklist-phases.png`

## Slayt 19 - Veri Modeli

Konusmaci: 3

Anlatim Notu:
Uc tabloyu basitce anlat. `checklist_templates` sablon, `flight_sessions` ucus, `session_items` o ucusun checklist kopyasidir.

Gecis Cumlesi:
"Bu modelin en onemli katkisi, her ucusun temiz checklist ile baslamasini saglamasidir."

Gorsel:
`assets/12-data-model-erd.png`

## Slayt 20 - Session Mantigi

Konusmaci: 3

Anlatim Notu:
Session olmadan onceki ucusun tamamlanmis maddelerinin yeni ucusa tasinabilecegini anlat. Session sayesinde her ucusun ayri takip edildigini vurgula.

Gecis Cumlesi:
"Bu session mantigi API endpoint'lerine de dogrudan yansiyor."

Gorsel Onerisi:
Iki ayri ucus karti: Ucus 1 tamamlandi, Ucus 2 temiz basliyor.

## Slayt 21 - API Akisi

Konusmaci: 3

Anlatim Notu:
Endpoint'leri tek tek uzun anlatma. Grupla: aktif session okuma, session baslatma, item guncelleme, session kapatma, history ve reference items.

Gecis Cumlesi:
"Bu API'ler sade bir Turkce UI tarafindan kullaniliyor."

Gorsel:
`assets/13-api-flow.png`

## Slayt 22 - Basit Turkce UI

Konusmaci: 3

Anlatim Notu:
UI'in bilerek sade tutuldugunu soyle. Faz 1 icin hedef cok ozellikli dashboard degil, operasyonel akisi net gosteren calisan bir uygulama.

Gecis Cumlesi:
"Uygulamanin temel akislarini smoke test ile kontrol ettik."

Gorsel:
`assets/14-ui-wireframe.png`

## Slayt 23 - Dogrulama

Konusmaci: 3

Anlatim Notu:
Compile kontrolu ve Flask API smoke test yapildigini anlat. `uv run` probleminin uygulama bug'i degil, `onnxruntime` platform bagimliligi oldugunu belirt.

Gecis Cumlesi:
"Bu kontrollerden sonra Faz 1 icin ortaya cikan ciktilari ozetleyebiliriz."

Gorsel Onerisi:
Terminalde `smoke ok` ciktisi veya dogrulama checklist'i.

## Slayt 24 - Faz 1 Ciktilari

Konusmaci: 3

Anlatim Notu:
Ana ciktilari tek tek goster. `drone_checklist_app.py`, plan dokumani, README, HTML sunum, speaker notes ve assets klasorunun hazir oldugunu belirt.

Gecis Cumlesi:
"Bu Faz 1 ciktisi, sonraki multi-agent faz icin referans noktasi olacak."

Gorsel Onerisi:
Dosya agaci gorseli veya repository screenshot'i.

## Slayt 25 - Sonraki Adim

Konusmaci: 3

Anlatim Notu:
Faz 2'de roller ayrilabilir: operasyon planlayici, guvenlik akisi tasarimcisi, arayuz tasarimcisi, full-stack gelistirici, QA gozden gecirici. Bu fazda amac rolleri uygulamak degil, bu rollere anlamli bir urun hedefi hazirlamakti.

Gecis Cumlesi:
"Son olarak sunumun genel sonucunu ozetleyelim."

Gorsel:
`assets/15-phase2-roadmap.png`

## Slayt 26 - Kapanis

Konusmaci: 3

Anlatim Notu:
Ana mesaji ver: MAS teorisi, FIPA standartlari ve CrewAI pratigi, calisan bir drone checklist uygulamasinda birlestirildi. Faz 1, multi-agent calismasi icin saglam baseline olusturdu.

Gecis Cumlesi:
"Tesekkurler, sorularinizi alabiliriz."

Gorsel Onerisi:
Theory -> Standards -> App -> Next Phase akisi.

## Slayt 27 - Referanslar

Konusmaci: 3

Anlatim Notu:
Referanslari hizli goster. Sorular gelirse Wooldridge, FIPA ve CrewAI docs uzerinden yanitlanabilir.

Gecis Cumlesi:
"Bu referanslar hem teorik hem uygulama tarafinda kullandigimiz kaynaklari gosteriyor."

Gorsel Onerisi:
Sade referans slayti yeterli.
