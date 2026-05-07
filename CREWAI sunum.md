---
marp: true
theme: default
paginate: true
size: 16:9
title: MultiAgent Systems - Grup 4
description: Faz 1 Single-Agent Drone Flight Checklist Uygulamasi ve CrewAI
---

# MULTIAGENT SYSTEMS

## Grup 4 Sunumu

### Proje: Faz 1 Single-Agent Drone Flight Checklist Uygulamasi

- Framework: CrewAI
- Kuramsal temel: Wooldridge + FIPA standartlari
- Vaka calismasi: mevcut todo baseline'inin checklist urunune pivot edilmesi

---

# Sunum Akisi

1. MAS teorisi ve CrewAI mimarisi
2. FIPA ve ajan koordinasyonu
3. Hafiza, hata yonetimi ve insan onayi
4. Faz 1 case study: Drone checklist pivotu

---

# 1. Ajan Kavrami ve BDI

Wooldridge'e gore ajan ozellikleri:

- Ozerklik
- Sosyal yetenek
- Reaktiflik
- Proaktiflik

BDI modeli:

- Belief: dunya bilgisi
- Desire: hedef
- Intention: gorev planı

---

# BDI -> CrewAI Eslesmesi

| BDI | CrewAI karsiligi |
| --- | --- |
| Belief | `backstory`, gerekirse `memory` |
| Desire | `goal` |
| Intention | `task` |

```python
Agent(
    role="Full-Stack Developer",
    goal="Produce a runnable drone flight checklist app",
    backstory="Pragmatic engineer who ships small usable products",
)
```

---

# CrewAI'in Yapi Taslari

- `Agents`: rol tabanli uzmanlar
- `Tasks`: tanimli is birimleri
- `Tools`: dis dunya ile temas noktasi
- `Crew`: akisi yoneten orkestra

Bu projede Faz 1 icin akıs bilerek basit tutulur:

- tek agent
- tek ana task
- sequential process

---

# FIPA ile Baglanti

FIPA, ajanlar icin ortak kavramsal dil sunar:

- kimlik ve yasam dongusu
- yetenek tanitimi
- mesajlasma davranislari

CrewAI tarafi:

- agent listesi = kimler var
- task zinciri = kim ne zaman ne yapar
- tools = hangi yetenekler mevcut

---

# FIPA ACL -> Task Context

Temel speech act fikirleri:

- `REQUEST`
- `INFORM`
- `REFUSE`
- `FAILURE`

CrewAI benzetmesi:

```python
Task(
    description="Checklist uygulamasini uret",
    context=[planning_task]
)
```

Bir task'in output'u sonraki task'in girdisine donusebilir.

---

# Hafiza ve Hata Yonetimi

Kritik noktalar:

- short-term memory baglam korur
- long-term memory tekrar kullanimi destekler
- retry mekanizmasi agent'in oz-duzeltme yapmasini saglar
- insan onayi belirsiz veya kritik secimlerde devreye girer

CrewAI ornekleri:

```python
Crew(memory=True)
Agent(max_retry_limit=3)
Task(human_input=True)
```

---

# Faz 1 Case Study Baslangici

Mevcut repository baslangici:

- tek agentli CrewAI baseline
- cikti: tek dosya Flask uygulamasi
- veri modeli: basit todo listesi
- hedef: CRUD odakli genel amacli uygulama

---

# Mevcut Repo Mimarisi

```text
src/crewai_todo_app/
  config/
    agents.yaml
    tasks.yaml
  crew.py
  main.py
drone_checklist_app.py
```

Temel durum:

- `full_stack_developer` tek agent'tir
- gorev tek dosya Flask + SQLite uygulamasi uretmektir
- process sequential olsa da pratikte tek adimli akistir

---

# Neden Todo Yeterli Degildi?

Drone operasyonu icin eksikler:

- checklist her ucusta sifirlanmiyordu
- faz bazli akıs yoktu
- ortam kontrolu icin ayri bolum yoktu
- acil durum bilgileri referans olarak sunulmuyordu
- gecmis ucuslar session mantigiyla tutulmuyordu

Sonuc:

**Global todo modeli, ucus bazli operasyon mantigina uymadi.**

---

# Faz 1 Pivot Kararlari

- Paket adi ayni kaldi: `crewai_todo_app`
- Uygulama cikti adi degisti: `drone_checklist_app.py`
- UI Turkce olacak
- UI tek sayfa ve sade kalacak
- Sadece single-agent uygulanacak

---

# Yeni Urun Akisi

1. Kullanici yeni ucus baslatir
2. Sistem standart checklist sablonunu o oturuma kopyalar
3. Maddeler fazlara gore tamamlanir
4. Acil durum prosedurleri referans panelinde gorulur
5. Ucus sonrasinda oturum kapatilir
6. Gecmis ucuslar saklanir

---

# Checklist Fazlari

- `Ortam Kontrolu`
- `Ucus Oncesi`
- `Ucus Sirasinda`
- `Acil Durum Prosedurleri`
- `Ucus Sonrasi`

Tasarim karari:

- `Acil Durum Prosedurleri` checkbox listesi degil
- referans paneli olarak gosterilir

---

# Veri Modeli

Yeni yapinin cekirdegi uc tablo:

- `checklist_templates`
- `flight_sessions`
- `session_items`

Neden?

- ayni maddeler her ucusta tekrar kullanilsin
- tamamlanma durumu ucusa ozel olsun
- gecmis ucuslar silinmesin

---

# Faz 1 Single-Agent Akisi

Tek agent su gereksinimleri tasir:

- Flask backend
- SQLite veri modeli
- Turkce UI
- seed checklist verisi
- session bazli is akisi

Bu, Faz 1 icin bilincli bir secimdir:

- once urunu dogrulamak
- sonra ajanlari ayirmak

---

# Basit UI Karari

Arayuzde sadece su alanlar vardir:

- aktif ucus karti
- yeni ucus baslatma formu
- faz bazli checklist bolumleri
- acil durum referans paneli
- gecmis ucuslar listesi

Bilerek eklenmeyenler:

- kullanici sistemi
- coklu drone profili
- karmasik dashboard

---

# Faz 1 Dosya Ciktilari

- `drone_checklist_app.py`
- `PHASE1_DRONE_CHECKLIST_PLAN.md`
- guncel `README.md`
- guncel `CREWAI sunum.md`
- guncel `CREWAI sunum.html`

---

# Faz 1 Kabul Kriterleri

1. CrewAI yeni dosya adina yazar
2. Uygulama lokal olarak acilir
3. UI Turkcedir
4. Her ucus icin yeni checklist olusur
5. Gecmis ucuslar saklanir
6. Ortam Kontrolu ayri bolumdur
7. Acil Durum Prosedurleri referans panelidir

---

# Kapanis

Bu fazda amac Multi-Agent'i kurmak degil, dogru urun modelini single-agent ile netlestirmektir.

Sonraki mantikli adim, ayni urunu uzmanlasmis agent'lara bolmektir.

---

# Referanslar

- Wooldridge, M. *An Introduction to MultiAgent Systems*
- FIPA standartlari: `http://www.fipa.org/`
- CrewAI dokumantasyonu: `https://docs.crewai.com/`
- Repository temeli: `https://github.com/Shubuo/crewai-todo-app`
