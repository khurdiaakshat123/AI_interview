# Intervyn (`intervyn.ai`)
> **Enterprise-Grade AI Technical Assessment & Adaptive Mock Interview Platform**  
> *Deterministic scoring, multi-agent evaluation, speech synthesis, and 18-point verification for high-bar engineering hiring.*

---

## 🌟 Overview

**Intervyn** is an end-to-end technical hiring and assessment system built according to the production specification in `AI-OA-Interview-Platform-Architecture.md`. It prepares candidates for elite engineering hiring pipelines (Google, Amazon, Microsoft, Uber, Stripe) across two unified subsystems:

1. **Company-Specific Online Assessment (OA) Engine**: Job-description parsing, weighted topic profiling, SHA-256 deduplicated practice banks, 7-day rolling test windows, and an automated 18-point quality verification pipeline.
2. **Adaptive AI Technical Interview Subsystem**: Multi-turn situational follow-ups (Level 1–5 depth), intelligent 2nd-go specification clarification, phonetic speech normalization, continuous speech recognition, and separate dual headline scorecards with an audit-grade evidence trail.

---

## 🚀 Key Platform Features

### 1. Adaptive AI Technical Interview Subsystem
- **Structured Resume Parser & Relevance Ranking**: Extracts Work Experience, Projects, Skills, and Education; dynamically sorts projects and experiences by JD relevance.
- **Situational Question Generation (Depth 1–5)**: Evaluates trade-offs, bottlenecks, failure modes, and distributed systems architecture instead of basic trivia recall.
- **Phonetic STT Normalization & Typo Autocorrection**:
  - Automatically maps browser speech recognition sound-alikes (e.g., *"post grass SQL"* → *PostgreSQL*, *"superb is"* → *Supabase*, *"duck duck GO light"* → *DuckDuckGo Lite*, *"webs grapes"* → *web scrapes*, *"wells drug"* → *well structured*, *"red is"* → *Redis*, *"pin corn"* → *Pinecone*) before grading.
  - Instructs the evaluation model to reconstruct technical intent and avoid false incoherence penalties.
- **2nd-Go Intelligent Clarification (No Immediate 0/10)**:
  - Detects when an answer is a valid high-level overview but lacks concrete implementation specifications (database choice, fallback mechanics, caching layer).
  - Prompts the candidate with a targeted 2nd-go question specifying exact details needed without logging an evidence deduction.
- **Asymmetric Deterministic Scoring**:
  - **Successful 2nd-Go**: Full points awarded with only a minute penalty (~10–12%).
  - **Failed / Dodged 2nd-Go**: Enforces high weightage (10.5 possible points) with 0.0 earned points.
- **Deterministic Scoring (§6.2)**:
  $$\text{correct\_possible}(L) = 5 + 3 \times (L - 1)$$
  $$\text{incorrect\_possible}(L) = \max(2, 10 - 2 \times (L - 1))$$
  Shallow blunders carry severe penalties; deep architectural insights earn maximum points.
- **One-Click "Correct Typos (AI)" Autocorrection**:
  - A dedicated button in the live interview room allows candidates to review their spoken response before submitting.
  - The LLM cross-references the spoken answer with the Question Asked and the Candidate's Resume/Projects, automatically correcting phonetic speech-to-text slips (e.g. *"post grass SQL"* → *PostgreSQL*, *"superb is"* → *Supabase*, *"duck duck GO light"* → *DuckDuckGo Lite*, *"red is"* → *Redis*, *"pin corn"* → *Pinecone*) and irregular sentence breaks.
- **Continuous Multi-Line Paragraph Speech Recognition**:
  - Live speech recognition streams and wraps words into a full, readable multi-line paragraph in real time.
  - Automatically scrolls to keep the latest spoken words in view, with live word and character counters.
  - Candidate has manual Start/Stop control so pauses to gather thoughts never cut off recording.
  - Web Speech API speech synthesis provides realistic spoken interviewer voice.
- **Dual Headline Scorecards & Evidence Trail**:
  - Reports **Resume Related Score /100** and **Subject Knowledge Score /100** separately (never averaged into a misleading blend).
  - Every point earned is linked to a permanent `interview_evidence` audit record (`EV-PRO-3-abc123`).

---

### 2. Company-Specific Online Assessment (OA) Engine
- **Agent 1 (Role Topic Profile Generator)**: Scans Job Descriptions and hiring patterns to calculate topic importance weights (0–1), difficulty distributions, and evidence provenance facts.
- **Agent 2 (Practice Question Engine)**: Deterministic question bank keyed by SHA-256 with hints, approaches, and complete solutions.
- **Agent 3 (Mock OA Engine)**: Enforces canonical 7-day rolling time windows and attempt isolation (`company, role, time_window_id, attempt_number`).
- **Agent 4 (Review & Validation)**: 18-point verification pipeline auditing every question for clarity, edge cases, and deterministic evaluation before publication.
- **Agent 5 (Evaluator Registry & Feedback)**: Sandboxed code execution, test cases, SQL execution, MCQ/MSQ verification, and topic accuracy breakdown.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Tailwind CSS, Vite, Lucide Icons |
| **Backend API** | FastAPI, Python 3.14 / 3.11+, Pydantic v2 |
| **Database & ORM** | SQLite (local zero-config) / PostgreSQL-ready SQLAlchemy |
| **AI & LLM Client** | Google Gemini (`gemini-flash-latest`), Groq, OpenAI, Anthropic |
| **Speech Processing** | Web Speech API (Synthesis & Continuous Recognition) + Phonetic STT Normalizer |
| **Document Parsing** | PyMuPDF (fitz) + Two-Column Layout Segmenter |

---

## 📂 Project Structure

```text
AI_interview/
├── backend/
│   ├── app/
│   │   ├── agents/               # Multi-agent orchestrators (interview, OA, practice)
│   │   ├── api/                  # FastAPI routers (candidate, interview, practice, oa, settings)
│   │   ├── engines/              # Deterministic scoring, STT normalizer, document parser
│   │   ├── llm/                  # Multi-provider LLM client with resilient fallbacks
│   │   ├── models/               # SQLAlchemy ORM models & audit tables
│   │   ├── seed/                 # Pre-populated questions, role profiles & rubrics
│   │   ├── database.py           # DB connection engine & session factory
│   │   └── main.py               # Application entry point & CORS configuration
│   ├── requirements.txt          # Python dependencies
│   └── .env.example              # Example environment configuration
├── frontend/
│   ├── src/
│   │   ├── components/           # UI components (DepthMeter, DocumentUploadInput, Modals)
│   │   ├── pages/                # Pages (LiveInterview, Dashboard, Intake, Practice, MockOA)
│   │   ├── services/             # Axios API clients & endpoints
│   │   ├── types/                # TypeScript interfaces and evidence records
│   │   ├── App.tsx               # Root view router & state
│   │   └── main.tsx              # React DOM entry
│   ├── package.json              # Node dependencies & Vite scripts
│   └── vite.config.ts            # Vite proxy & build configuration
├── AI-OA-Interview-Platform-Architecture.md  # Core architectural specification
├── .gitignore                    # Git exclusions
├── .env.example                  # Root environment reference
└── README.md                     # Documentation
```

---

## ⚡ Quickstart Guide

### Prerequisites
- **Python 3.11+** (Python 3.14 supported)
- **Node.js 18+** & **npm 9+**
- **Git**

---

### 1. Clone & Setup Environment
```bash
git clone <repo-url>
cd AI_interview
cp .env.example backend/.env
```

Edit `backend/.env` to configure optional API keys:
```env
DATABASE_URL=sqlite:///./intervyn.db
GEMINI_API_KEY=your_gemini_api_key_here
```

---

### 2. Backend Setup & Run
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 3. Frontend Setup & Run
In a new terminal:
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```
- **Web Application**: [http://127.0.0.1:3000](http://127.0.0.1:3000)

---

## 🧪 Testing & Verification

Run the automated test suite covering transcript normalization and asymmetric scoring:
```bash
python -c "import urllib.request; print('Backend healthy:', urllib.request.urlopen('http://127.0.0.1:8000/docs').status == 200)"
npm --prefix frontend run build
```

---

## 🔒 Security & Privacy

- All candidate resume uploads and session recordings are kept local and private.
- Never commit `.env` or sensitive database files (configured in `.gitignore`).
- Repositories and candidate audit logs should remain private.

---

## 📄 License
Private & Proprietary. All rights reserved.
