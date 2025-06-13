# MED-ED-BOT • Design-Thinking Fundamentals  
---

## 1️⃣ User Persona

| Field | Details |
|-------|---------|
| **Name** | **Dr Eric Chen** (fictional) |
| **Age / Role** | 26 y o male, PGY1 doctor – public-hospital **ED** |
| **Context** | Works rotating night shifts; regularly treats Southeast-Asian patients/caregivers with little Mandarin/English. |
| **Quote** | “Are you having chest pain? Could you be pregnant? Appendicitis can look like gastroenteritis—please understand the difference.” |
| **Goals** | ① Take accurate histories ② Translate jargon into mother-tongue ③ Hand over printed, language-appropriate discharge sheets |
| **Needs** | • Real-time, jargon-aware translation<br>• One-click generation of multilingual education sheets<br>• Print flow that bypasses hospital internet restrictions<br>• Zero-setup, LINE-based interface |
| **Pain Points** | • Google Translate butchers medical terms<br>• Official handouts only in zh-TW and for common diseases only<br>• Leaflets are not patient-specific<br>• Resorting to gestures risks errors |
| **Personality** | Perpetually rushed, mildly anxious, tech-pragmatic |
| **Tools on Hand** | Smartphone ( LINE ), ward PC, occasional tablet, pen & paper |

---

## 2️⃣ Empathy Map

| Think & Feel | See | Hear | Say & Do |
|--------------|-----|------|----------|
| “I can’t let language slow critical care.”<br>“I need something that just works.” | Crowded ED, outdated PCs, language-barrier signage | Patients: “Doctor, I don’t understand.”<br>Nurses: “Next patient is waiting!” | Fires up LINE bot, types `new`, prints sheets, gestures less |

---

## 3️⃣ User Journey Map

| Stage | Key Actions | Emotion | Pain Point | Opportunity |
|-------|-------------|---------|------------|-------------|
| **Triage** | Identifies language mismatch | Alert | No interpreter | Auto-detect language + greeting card |
| **History & Exam** | Asks symptoms via Google Translate / gestures | Frustrated | Jargon mistranslated | Voice-to-text + dual-layer translation |
| **Investigations** | Orders labs / explains prep | Focused | Needs to re-explain fasting rules | Pre-built multilingual prep sheets |
| **Diagnosis** | Explains appendicitis vs GE | Anxious (time) | Misunderstanding delays consent | Pictorial summary via bot |
| **Discharge** | Generates & prints leaflet | Relieved / Rushed | Only zh-TW leaflet | `mail` PDF → ward printer |
| **Post-Visit** | Answers LINE queries | Calmer | No structured follow-up | Chat-mode dual-layer Q&A |

---

## 4️⃣ POV Statement

> **A rushed junior ED doctor in Taiwan** needs **an instant, jargon-sensitive translation and education tool that works inside the hospital firewall** because **current ad-hoc methods are slow, inaccurate, and endanger patient safety.**

---

## 5️⃣ How-Might-We Questions

- **HMW** let doctors create *patient-specific* multilingual discharge sheets in under a minute?  
- **HMW** embed a *dual-layer* medical translator directly into LINE so it works on any ward PC or phone without extra installs?  
- **HMW** output print-ready PDFs that bypass network restrictions yet still log to Google Sheets/Drive for audit?  

---

## 6️⃣ User Story Map (focused on current MED-ED-BOT functions)

| High-Level Activities | 1️⃣ Start Case | 2️⃣ Generate Sheet | 3️⃣ Refine Content | 4️⃣ Translate | 5️⃣ Deliver / Print | 6️⃣ Live Chat | 7️⃣ Log & Archive |
|-----------------------|---------------|-------------------|-------------------|---------------|---------------------|--------------|------------------|
| **MVP (already live)** | `new` → choose **add / chat** | In **add**, enter topic → Gemini returns plain-zh sheet | `modify` regenerates sheet per edits | `trans [lang]` dual-layer translation + “您聽得懂嗎？” | `mail [email]` emails PDF & LINE-formatted sheet for printing | **chat** branch auto dual-layer per turn | Sheet / email logged to Google Sheet & Drive |
| **Backlog** | — | Quick template picker (STEMI, DKA …) | Undo / redo stack | Auto-detect preferred language | Batch mail to nurse-station alias | Cache common Q&A | Scheduled CSV export for IRB |

---
