# Neuro-Synthetix

**A voice bridge between patients and the clinical trials that could help them.**

Neuro-Synthetix lets anyone describe how they feel, by voice or text, in their own
language, and finds real clinical trials that are recruiting, near them. It does not
diagnose. It orients toward trials, always reminding the patient to confirm with a doctor.

Built for **HackHazards '26** — theme HealthTech & Bio Platforms.
Live: https://neuro.shadrakbessanh.me

## 📱 Mobile app (Expo)

The same assistant runs as a native app. Install **Expo Go** on your phone, then
scan the QR code below (or open the link inside Expo Go):

<img src="mobile/expo-qr.png" width="200" alt="Scan with Expo Go" />

```
exp://qzkabn0-bsh54-8081.exp.direct
```

The app hosts the same backend, so voice, AI search and real trials work out of the box.
Source: [`mobile/`](mobile/) · built with Expo / React Native.

---

## What it does

1. A conversational AI (DeepSeek, tool calling) leads a short, clinician-like conversation:
   it asks progressive questions, understands any wording (slang, a drug name, a body part,
   a clue, another language, a misspelling) and normalizes it into clean search terms.
2. **Retrieval + AI re-ranking (RAG):** a fast retrieval pulls real candidate trials from a
   base of ~5000 unified from public registries; DeepSeek then re-ranks them, keeping only
   the genuinely relevant ones and explaining why each fits. It can only choose from real
   candidates, so it never invents a trial.
3. **Eligibility:** age and sex are taken into account to drop trials the patient cannot join.
4. **Next steps:** every trial shows a clear "how to proceed" path (reference, see your
   doctor, contact the site, eligibility check, participation is free) plus the official link.
5. **Multilingual voice:** speech to text and text to speech in Hindi via Sarvam AI;
   translation is used only for Hindi (English and French are handled natively by the model).
6. A **graph** (Neo4j) visualizes the care pathway of the chosen results.

## Data sources (unified)

- ClinicalTrials.gov (global + a dedicated India pull)
- CTIS — EU Clinical Trials Information System (public API)
- ISRCTN (UK / international)

Refreshed automatically every 12 hours. Every trial keeps its official reference
(NCT / CTIS / ISRCTN) so it can be verified at the source.

## Stack

- **Backend:** FastAPI (Python), Docker
- **Graph:** Neo4j
- **AI:** DeepSeek (conversation + re-ranking), Sarvam AI (STT / TTS), translation API
- **Frontend:** static HTML/CSS/JS (chat, voice mode, map, proof page)
- **Data:** unified clinical-trial knowledge base (built by `app/kb_builder.py`)

## Project layout

```
backend/
  app/
    main.py            FastAPI app and routes
    deepseek.py        conversation + tool calling + RAG re-rank
    retrieval.py       candidate retrieval + ranking (RAG step 1)
    kb_search.py       keyword search helper
    kb_builder.py      builds the unified knowledge base from the registries
    sarvam.py          Sarvam STT / TTS
    translate.py       translation (Hindi only)
    graph.py           Neo4j queries + graph payload
    extract.py         multilingual symptom lexicon
    stats.py           metrics + map locations for the proof page
    conditions.py      condition / symptom data backbone
    static/            landing.html, index.html (chat), proof.html
  requirements.txt
  Dockerfile
deploy/                deployment helpers (SSH via paramiko)
docs/                  PLAN.md, AI_SEARCH_DESIGN.md, SCENARIO_TEST.txt
```

## Run locally

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env      # fill in Neo4j, Sarvam, translation and DeepSeek keys
python -m app.kb_builder  # build the knowledge base (~5000 real trials)
uvicorn app.main:app --reload
```

Then open http://localhost:8000

### Environment variables (`.env`)

```
NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
SARVAM_API_KEY
TRANSLATE_API_URL, TRANSLATE_API_KEY
DEEPSEEK_API_KEY
```

No secret is committed. `.env` and any key files are git-ignored.

## Endpoints

- `GET  /`            landing page
- `GET  /app`         the assistant (chat + voice)
- `GET  /proof`       data metrics + world map of research sites
- `POST /chat`        conversational search (AI + RAG)
- `POST /tts` `/stt`  Sarvam voice
- `GET  /stats` `/locations` `/site`  data for the proof page and map

## Disclaimer

Neuro-Synthetix is an orientation tool. It does not provide a medical diagnosis and does
not replace a doctor's advice.
