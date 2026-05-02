---
marp: true
theme: default
paginate: true
size: 16:9
title: MultiAgent Systems - Grup 4
description: Single vs Multi-Agent Karsilastirmali TODO Uygulamasi ve CrewAI
---

# MULTIAGENT SYSTEMS

## Grup 4 Sunumu

### Proje: Single vs Multi-Agent Karsilastirmali TODO Uygulamasi

- Framework: CrewAI
- Kuramsal temel: Wooldridge + FIPA standartlari
- Vaka calismasi: `Shubuo/crewai-todo-app`

---

# Sunum Akisi

1. MAS Teorisi ve CrewAI Mimarisi
2. FIPA Standartlari ile CrewAI Entegrasyonu
3. Hafiza ve Hata Yonetimi
4. Uygulama: Single Agent Case Study ve Multi-Agent gecis motivasyonu

---

# BOLUM 1

## MAS Teorisi ve CrewAI Mimarisi

### KONU

Wooldridge'in akademik temelleri ile CrewAI'in eslestirilmesi

---

# 1.1 Ajan Kavrami ve BDI Modeli

Wooldridge'e gore ajan ozellikleri:

- Ozerklik: Kendi kararlarini verir
- Sosyal yetenek: Diger ajanlarla iletisim kurabilir
- Reaktiflik: Cevreyi algilar ve tepki verir
- Proaktiflik: Hedef odakli davranir

BDI modeli:

- Belief: Ajanin dunya hakkindaki bilgisi
- Desire: Ajanin ulasmak istedigi hedefler
- Intention: Gerceklestirmeye karar verdigi eylemler

---

# BDI -> CrewAI Eslesmesi

| BDI | CrewAI Karsiligi |
| --- | --- |
| Belief | `backstory` ve gerekiyorsa `memory` |
| Desire | `goal` |
| Intention | `task` tanimi |

```python
Agent(
    role="Full-Stack Developer",
    goal="Produce a complete, runnable Todo App",
    backstory="Pragmatic engineer who values clean code",
)
```

Sunum notu: Bu tabloda BDI kavramlarini solda, CrewAI alanlarini sagda gostermek akisi netlestirir.

---

# 1.2 CrewAI'in Yapi Taslari

- `Agents`: Rol tabanli uzmanlar
- `Tasks`: Tanimli is birimleri
- `Tools`: Ajanin dis dunya ile temas noktalari
- `Crew`: Sistemi baslatan ve yoneten orkestra

Bu yapi, soyut MAS kavramlarini calisan bir yazilim modeline donusturur.

---

# 1.3 Surec Yonetimi

## Sequential

- Her task bir oncekinin ciktisini alir
- Klasik pipeline mantigi
- Mevcut projede kullandigimiz yontem
- Ornek akis: Planlama -> Gelistirme -> Test -> Review

## Hierarchical

- Manager Agent sistemi yonetir
- Hangi agent'in ne zaman calisacagina karar verir
- Dinamik is dagitimi saglar
- Daha karmasik ama daha esnektir

---

# BOLUM 2

## FIPA Standartlari ile CrewAI Entegrasyonu

### KONU

Projenin akademik derinligini gostermek

---

# 2.1 FIPA Nedir?

FIPA: Foundation for Intelligent Physical Agents

- Ajan sistemleri icin uluslararasi standartlar sunar
- Ajanlarin iletisimini tanimlar
- Ajanlarin kimlik ve hizmet tanitimini standartlastirir
- MAS teorisini uygulamaya tasiyan ortak bir sozluk olusturur

---

# 2.2 Yasam Dongusu ve Kayit

## AMS - Agent Management System

FIPA'da:

- Her agent sisteme kaydolur
- Kimlik alir
- Yasam dongusu takip edilir

CrewAI karsiligi:

```python
Crew(agents=[developer, tester, reviewer])
```

- Bu liste, FIPA'daki White Pages mantigina benzetilebilir
- Sistemde hangi agent'larin oldugu burada tanimlanir

---

# 2.3 Yeteneklerin Kesfi

## DF - Directory Facilitator

FIPA'da:

- Agent'lar yeteneklerini bir dizine kaydeder
- Diger agent'lar bu dizinden "kim ne yapabilir" diye sorgular

CrewAI karsiligi:

```python
Agent(tools=[search_tool, code_tool, db_tool])
```

- `tools` listesi, FIPA'daki Yellow Pages benzeri dusunulebilir
- Hangi agent'in hangi yeteneklere sahip oldugu burada gorulur

---

# 2.4 Ajanlar Arasi Iletisim

## FIPA ACL ve Speech Acts

Temel eylem tipleri:

- `REQUEST`: Sunu yap
- `INFORM`: Sunu ogrendim
- `REFUSE`: Bunu yapamam
- `FAILURE`: Denedim ama basarisiz oldum

CrewAI karsiligi:

```python
Task(
    description="Backend kodunu yaz",
    context=[planning_task]
)
```

- Bir task'in output'u sonraki task'in input'u olur
- Bu, mesaj yukunun bir task'tan digerine aktarilmasina benzer

Sunum notu: FIPA diyagrami ile `context` kullanan CrewAI kodunu yan yana koy.

---

# BOLUM 3

## Hafiza ve Hata Yonetimi

### KONU

Sistemin sadece calismasini degil, akilli calismasini saglayan mekanizmalar

---

# 3.1 Hafiza Sistemleri

## Short-term Memory

- Gorev sirasinda ogrenilen bilgiler
- Gorev boyunca baglami korur
- Ornek: Agent, uygulamanin Flask kullandigini o oturum boyunca hatirlar

## Long-term Memory

- Onceki oturumlardan verileri tasiyabilir
- RAG ve vector database entegrasyonlari ile calisir
- Ornek: Daha onceki benzer bir bug'in cozumunu yeniden kullanmak

CrewAI aktivasyonu:

```python
Crew(memory=True)
Crew(memory=True, embedder={...})
```

---

# 3.2 Hata Yonetimi ve Oz-Duzeltme

Surec:

1. Agent bir tool cagirir
2. Tool hata dondurur
3. Agent hatayi analiz eder
4. Farkli bir stratejiyle tekrar dener
5. Sinira ulasinca gorevi basarisiz isaretler

TODO App uzerinden ornek:

- SQLite baglantisi ilk denemede hata verebilir
- Agent dosya yolunu veya parametreyi duzeltip tekrar deneyebilir

CrewAI ayari:

```python
Agent(max_retry_limit=3)
```

---

# 3.3 Human-in-the-Loop

Ne zaman gerekli?

- Geri donusu olmayan islemler
- Belirsiz tercih noktalarinda
- Guvenlik gerektiren kararlarda

Surec:

1. Agent kritik bir noktaya gelir
2. Durur ve insandan onay ister
3. Onaya gore devam eder veya alternatif arar

CrewAI aktivasyonu:

```python
Task(human_input=True)
```

Sunum notu: Burada bir e-posta gonderme veya veri silme senaryosu canlandirilabilir.

---

# BOLUM 4

## Uygulama - Single Agent Case Study

### KONU

Mevcut projenin analizi ve Multi-Agent'a gecisin motivasyonu

---

# 4.1 Mevcut Projenin Mimarisi

Repository:

- `https://github.com/Shubuo/crewai-todo-app`

Yapi:

```text
src/crewai_todo_app/
├── config/
│   ├── agents.yaml
│   └── tasks.yaml
├── crew.py
└── main.py
```

Agent:

- `full_stack_developer`
- Model: `minimax-m2.7` (OpenRouter uzerinden)
- Gorev: Flask + SQLite + HTML/CSS/JS ile tek dosya Todo App yazmak
- Process: Sequential

---

# Single-Agent Baseline'da Uretilen Uygulama

- Cikti dosyasi: `todo_app.py`
- Flask API endpoint'leri uretildi
- SQLite persistence kuruldu
- Inline HTML/CSS/JS arayuz uretildi
- CRUD akislarinin tamami calisir hale geldi

Refinement turunda:

- JSON payload dogrulamasi eklendi
- `completed` alani boolean hale getirildi
- `created_at` bilgisi UI'da gosterildi
- `PORT` env destegi korundu

---

# 4.2 Single Agent'in Sinirlamalari

Gozlemlenen sorunlar:

- Tek agent ayni anda backend, frontend, veri modeli ve test dusunuyor
- Dikkat dagildiginda eksik veya hatali kod uretebiliyor
- Kod kalitesi butun kisimlarda esit olmuyor
- Hata ciktiginda ayri bir review veya test role'u yok
- Memory kullanimi bu baseline'da yok

Temel sorun:

**Tek agent = Tek dikkat noktasi = Karmasik gorevlerde performans dususu**

---

# 4.3 Sorunlarin Gorsel Kaniti

Bu bolumde slayta eklenebilecek materyaller:

- Ekran goruntusu 1: Single agent ciktisi veya ilk ham kod
- Ekran goruntusu 2: Uretim sirasinda alinmis hata mesaji ya da tutarsiz output
- Ekran goruntusu 3: CrewAI terminal ciktisi

Sunum teknigi:

- Once hatali ya da eksik bolumu goster
- Izleyiciye "neden yetersiz?" sorusunu sor
- Cevabi bir sonraki slaytta Multi-Agent onizlemesiyle bagla

---

# 4.4 Buyuk Final Duyurusu

"Bu sunumda Single Agent'in neden yetersiz kaldigini gorduk.

Final projemizde, CrewAI kullanarak tasarladigimiz Multi-Agent sistemin bu problemleri nasil cozdugunu ve ikisi arasindaki performans farkini canli verilerle sunacagiz."

---

# Multi-Agent Final Projesi Onizlemesi

- Product Planner Agent: Gereksinimleri analiz eder
- Backend Developer Agent: Flask + SQLite kodunu yazar
- Frontend Developer Agent: HTML/CSS/JS kodunu yazar
- Test Agent: Uygulamayi test eder
- Review Agent: Kalite kontrolu yapar

Karsilastirma metrikleri:

- Kod kalitesi
- Tamamlanma suresi
- Cikti tutarliligi
- Token kullanimi

---

# Genel Sunum Notlari

Akis:

- Bolum 1 -> Bolum 2 -> Bolum 3 -> Bolum 4

Sure:

- Her bolum: 5-7 dakika
- Toplam: 20-28 dakika

Gorsel oneriler:

- BDI <-> CrewAI eslestirme tablosu
- FIPA diyagrami ve CrewAI kodu
- Memory turleri diyagrami
- Single vs Multi-Agent mimari semasi
- Terminal ciktilari ekran goruntuleri

---

# Referanslar

- Wooldridge, M. *An Introduction to MultiAgent Systems*
- FIPA standartlari: `http://www.fipa.org/`
- CrewAI dokumantasyonu: `https://docs.crewai.com/`
- GitHub repo: `https://github.com/Shubuo/crewai-todo-app`

## Kapanis Mesaji

Single-agent baseline, Multi-Agent sisteme gecisin neden gerekli oldugunu gosteren pratik bir ilk adimdir.
