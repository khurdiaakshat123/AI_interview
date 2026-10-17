# Intervyn — Full Model Architecture

> **Read this to understand how the entire platform is built, end to end.**  
> Written from reading every source file in the repo. No guessing.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Tech Stack](#3-tech-stack)
4. [API Keys Used](#4-api-keys-used)
5. [Database Design](#5-database-design)
6. [Backend — Folder Structure](#6-backend--folder-structure)
7. [LLM Client & Key Pool](#7-llm-client--key-pool)
8. [Agents](#8-agents)
9. [Engines](#9-engines)
10. [Interview Flow — Step by Step](#10-interview-flow--step-by-step)
11. [Scoring System (Math)](#11-scoring-system-math)
12. [API Endpoints](#12-api-endpoints)
13. [Frontend Architecture](#13-frontend-architecture)
14. [Deployment](#14-deployment)
15. [Key Design Invariants](#15-key-design-invariants)

---

## 1. Project Overview

**Intervyn** is a full-stack AI-powered technical interview simulation platform. It mimics a real technical interview experience — resume-based questioning, adaptive depth, scoring, consistency checking, and a final audit report — using LLMs as the backbone.

**The platform has 4 core product flows:**

| Flow | What it does |
|------|-------------|
| **AI Mock Interview** | Adaptive multi-turn spoken/typed technical interview grounded in the candidate's resume |
| **Mock Online Assessment (OA)** | Time-boxed coding + MCQ/SQL assessment simulating company OAs |
| **Practice Mode** | Topic-by-topic question practice from a question bank |
| **Interview Report** | Fully evidence-backed scoring report with per-project scorecards |

---

## 2. High-Level Architecture

```
+-------------------------------------------------------------+
|                      FRONTEND (React/TS)                    |
|  Vercel-hosted SPA  |  11 Pages  |  1 API service layer     |
+----------------------------+--------------------------------+
                             |  REST + SSE (streaming)
                             v
+-------------------------------------------------------------+
|                   BACKEND (FastAPI / Python)                |
|                                                             |
|  +----------+  +----------+  +---------+  +-------------+  |
|  | Auth API |  |Interview |  | Mock OA |  |  Practice   |  |
|  |  /JWT    |  |   API    |  |   API   |  |    API      |  |
|  +----------+  +----+-----+  +----+----+  +------+------+  |
|                     |             |               |         |
|              +------v-------------v---------------v------+  |
|              |            AGENT LAYER                    |  |
|              |  InterviewAgent | RoleProfileAgent | ...  |  |
|              +-------------------------------+-----------+  |
|                                             |               |
|              +------------------------------v-----------+   |
|              |              ENGINE LAYER               |   |
|              |  ResumeParser | AnswerEvaluator | ...   |   |
|              |  AdaptivePlanner | ConsistencyEngine    |   |
|              +------------------------------+-----------+   |
|                                             |               |
|              +------------------------------v-----------+   |
|              |         LLM CLIENT + KEY POOL            |   |
|              |  Gemini (preferred) -> Groq fallback     |   |
|              |  11 API keys, round-robin, 30s cooldowns |   |
|              +-----------------------------------------+   |
|                                                             |
|              +-----------------------------------------+   |
|              |              DATABASE                    |   |
|              |  SQLite (local) / PostgreSQL + Supabase  |   |
|              +-----------------------------------------+   |
+-------------------------------------------------------------+
```

---

## 3. Tech Stack

### Backend

| Layer | Technology | Version |
|-------|-----------|---------|
| Web Framework | FastAPI | >= 0.110.0 |
| ASGI Server | Uvicorn (with standard extras) | >= 0.28.0 |
| ORM | SQLAlchemy | >= 2.0.0 |
| Schema Validation | Pydantic v2 | >= 2.6.0 |
| HTTP Client (LLM calls) | httpx (synchronous) | >= 0.27.0 |
| Auth Tokens | PyJWT | >= 2.8.0 |
| PDF Parsing | PyMuPDF | >= 1.23.0 |
| HTML Parsing | BeautifulSoup4 | >= 4.12.0 |
| PostgreSQL Driver | psycopg2-binary | >= 2.9.9 |
| Image Processing | Pillow | >= 10.2.0 |
| Env Management | python-dotenv | >= 1.0.0 |
| Language | Python | 3.11.9 (on Render) |

### Frontend

| Layer | Technology | Version |
|-------|-----------|---------|
| UI Framework | React | ^18.3.1 |
| Language | TypeScript | ^5.7.3 |
| Build Tool | Vite | ^6.0.7 |
| Styling | Tailwind CSS | ^3.4.17 |
| Code Editor | Monaco Editor (React) | ^4.7.0 |
| Icons | Lucide React | ^1.16.0 |
| CSS Utilities | clsx + tailwind-merge | latest |
| Animations | canvas-confetti | ^1.9.4 |

### LLM Providers

| Provider | Model Used | Use Case |
|----------|-----------|----------|
| **Google Gemini** (preferred) | `gemini-flash-latest` | All LLM calls (questions, evaluation, parsing) |
| **Groq** (fallback) | `llama-3.3-70b-versatile` | Fallback when Gemini keys are rate-limited |
| **OpenAI** (legacy fallback) | `gpt-4o-mini` | Last-resort fallback if pool is exhausted |

> **Important:** No MCP (Model Context Protocol) is used. All LLM calls are direct HTTPS REST API calls via `httpx`.

---

## 4. API Keys Used

### Environment Variables

| Variable | Provider | Purpose |
|----------|---------|---------|
| `GEMINI_API_KEY` | Google AI Studio | Base fallback Gemini key |
| `GEMINI_API_KEY_1` to `GEMINI_API_KEY_5` | Google AI Studio | Numbered pool keys (5 keys) |
| `GROQ_API_KEY` | Groq | Base fallback Groq key |
| `GROQ_API_KEY_1` to `GROQ_API_KEY_6` | Groq | Numbered pool keys (6 keys) |
| `OPENAI_API_KEY` | OpenAI | Optional last-resort fallback |
| `ANTHROPIC_API_KEY` | Anthropic | Optional, supported but not primary |
| `DATABASE_URL` | Supabase / Render | PostgreSQL connection string |

**Total Active Keys (local `.env`):** 5 Gemini + 6 Groq = **11 pool keys** + 1 base Gemini fallback.

### Key Rotation Logic (KeyPool)

- Keys are loaded from numbered environment variables (`GROQ_API_KEY_1`, `GROQ_API_KEY_2`, ...)
- If no numbered keys are found (e.g., old Render deployment), falls back to base `GROQ_API_KEY` / `GEMINI_API_KEY`
- Keys are shuffled on startup to distribute load
- **Gemini is preferred first** (user preference set in client)
- If all Gemini keys are rate-limited → falls back to Groq
- Rate limits tracked per-key:
  - Groq: max 28 requests/minute per key
  - Gemini: max 14 requests/minute AND 480 requests/day per key
- On HTTP 429 / 401 / 404 → key goes on **30-second cooldown**
- Each failed attempt uses **exponential backoff with jitter**: `2^attempt + random(0.5, 1.5)` seconds
- Up to **4 retry attempts** per call before returning `None`

---

## 5. Database Design

### Adapter

- **Local / development**: SQLite (`intervyn.db` in repo root) with `PRAGMA foreign_keys=ON`
- **Production (Render)**: PostgreSQL via Supabase, with `sslmode=require`, `pool_size=10`, `max_overflow=20`, `pool_recycle=300s`

### Tables

#### `users`
Stores all registered users (email/password OR Google OAuth).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID string | Primary key |
| `email` | String(255) | Unique |
| `password_hash` | String(255) | "google_oauth" if OAuth login |
| `name` | String(255) | |
| `google_id` | String(255) | Unique, nullable |
| `avatar_url` | String(500) | Nullable |
| `created_at` | DateTime | UTC |

#### `time_windows`
Tracks company hiring windows for Mock OA question pool freshness.

| Column | Type | Notes |
|--------|------|-------|
| `company` | String | |
| `role` | String | |
| `window_length_days` | Integer | Default 7 |
| `status` | String | ACTIVE | CLOSED |

#### `role_topic_profiles`
Stores the LLM-generated or deterministic topic profile for a company+role combination.

| Column | Type | Notes |
|--------|------|-------|
| `company` / `role` | String | |
| `required_skills` | JSON | List of skill strings |
| `subjects_json` | JSON | Nested: subject > topics > subtopics with importance scores |
| `evidence_json` | JSON | Provenance facts about the company's hiring pattern |

#### `question_bank`
Holds all OA/Practice questions.

| Column | Type | Notes |
|--------|------|-------|
| `question_type` | String | MCQ, MSQ, DSA, SQL, System Design, Debugging |
| `difficulty` | String | easy, medium, hard |
| `test_cases_json` | JSON | Visible + hidden test cases for DSA/SQL |
| `options_json` | JSON | For MCQ/MSQ |
| `starter_code` | Text | Starter code template |
| `status` | String | GENERATING | REVIEWING | PUBLISHED | FAILED |
| `review_report_json` | JSON | 18-point verification checklist result |

#### `practice_sessions`
Tracks per-user practice runs.

#### `mock_oa_variants`
A specific set of questions for a company+role for a time window (attempt-based).

#### `mock_oa_attempts`
Tracks a user's actual OA attempt with submitted answers, evaluation, and score.

#### `structured_resumes`
Stores the LLM-parsed resume as structured JSON.

| Column | Type | Notes |
|--------|------|-------|
| `raw_text` | Text | Original resume paste |
| `sections_json` | JSON | `{work_experience, projects, skills, education, certifications, ...}` |
| `section_weights_json` | JSON | Relevance weighting per section |

#### `interview_sessions`
The primary interview session table.

| Column | Type | Notes |
|--------|------|-------|
| `status` | String | INIT | IN_PROGRESS | COMPLETED |
| `current_phase` | String | EXPERIENCE_DEFENSE | PROJECT_DEFENSE | SUBJECT_KNOWLEDGE | COMPLETED |
| `transcript_json` | JSON | Full conversation transcript (list of turns) |
| `agent1_report_json` | JSON | Experience/Project Defense report |
| `agent2_report_json` | JSON | Subject Knowledge report |
| `final_report_json` | JSON | Combined dual-headline final report |

#### `interview_evidence`
One row per evaluated answer turn. The audit trail.

| Column | Type | Notes |
|--------|------|-------|
| `earned_points` | Float | Points earned this turn |
| `possible_points` | Float | Maximum possible points this turn |
| `severity` | String | NONE | MINOR | MODERATE | SEVERE |
| `evaluator_reason` | Text | LLM's reasoning for the score |
| `evidence_ref` | String | Unique human-readable reference ID |

---

## 6. Backend — Folder Structure

```
backend/
+-- app/
|   +-- main.py                  # FastAPI app entry point, CORS, routers
|   +-- database.py              # SQLAlchemy engine, session, SQLite/PG adapter
|   +-- agents/
|   |   +-- interview_agent.py   # Master interview orchestrator (810 lines)
|   |   +-- role_profile_agent.py # JD/role topic profile generator
|   |   +-- evaluator_agent.py   # OA evaluation agent
|   |   +-- mock_oa_agent.py     # Mock OA question generation
|   |   +-- practice_agent.py    # Practice question generation
|   |   +-- review_agent.py      # Admin 18-point question review
|   +-- engines/
|   |   +-- resume_parser.py     # LLM + deterministic resume parser
|   |   +-- answer_evaluator.py  # SemanticEvaluationResult schema + LLM evaluator
|   |   +-- adaptive_planner.py  # Next-question decision engine (PlannerAction enum)
|   |   +-- consistency_engine.py # Cross-turn contradiction detection
|   |   +-- scoring_policy.py    # Deterministic math scoring (W_i, E_i, M_i)
|   |   +-- scoring_engine.py    # Score aggregation utilities
|   |   +-- question_generator.py # LLM question generation + deterministic fallback
|   |   +-- question_profile.py  # QuestionProfile schema (multidimensional)
|   |   +-- interview_state.py   # Full session state: claims, turns, items, contradictions
|   |   +-- report_generator.py  # Final evidence-backed report builder
|   |   +-- transcript_normalizer.py # Speech-to-text phonetic correction
|   |   +-- sandbox_runner.py    # Secure multi-language code execution (DSA/OA)
|   |   +-- document_parser.py   # PDF/DOC resume file parser
|   |   +-- evaluator_registry.py # OA answer grading engine
|   |   +-- follow_up_fsm.py     # Simple FSM for follow-up depth tracking
|   |   +-- web_search.py        # Lightweight web search for context
|   +-- llm/
|   |   +-- client.py            # LLMClient: all LLM calls (completion, evaluation, questions)
|   |   +-- key_pool.py          # APIKey + KeyPool: round-robin rotation + cooldowns
|   +-- models/
|   |   +-- models.py            # All SQLAlchemy ORM models (8 tables)
|   +-- schemas/
|   |   +-- schemas.py           # All Pydantic request/response schemas
|   +-- api/
|   |   +-- auth.py              # /api/auth — signup, login, Google OAuth
|   |   +-- interview.py         # /api/interview — sessions, answers, reports
|   |   +-- practice.py          # /api/practice — question bank, sessions
|   |   +-- mock_oa.py           # /api/mock-oa — OA variants, code runner, submit
|   |   +-- role_profiles.py     # /api/role-profiles — profile generation
|   |   +-- candidate.py         # /api/candidate — unified onboarding
|   |   +-- admin.py             # /api/admin — review queue
|   |   +-- settings.py          # /api/settings — live key updates
|   |   +-- deps.py              # JWT auth dependency
|   +-- seed/
|       +-- seed_data.py         # DB seed on startup
```

---

## 7. LLM Client & Key Pool

### `LLMClient` (`client.py`)

A singleton instance (`llm_client`) used everywhere in the backend. Stateless, synchronous.

**Key methods:**

| Method | Purpose |
|--------|---------|
| `generate_completion(system_prompt, user_prompt, temperature)` | Core method for all LLM calls. Returns `Optional[str]`. |
| `evaluate_candidate_answer(...)` | Evaluates a candidate's answer, returns structured JSON dict |
| `generate_interview_question(...)` | Generates the next interview question text |
| `correct_candidate_answer_typos(...)` | Phonetic + LLM typo correction |
| `generate_specification_clarification_question(...)` | Generates a 2nd-chance follow-up for missing technical specs |

**Provider call flow inside `generate_completion`:**
```
Attempt 1-4 (max):
  -> Get next key from KeyPool (prefers Gemini)
  -> If Gemini key: POST to generativelanguage.googleapis.com
  -> If Groq key:   POST to api.groq.com/openai/v1/chat/completions
  -> On 429/401:    trigger_cooldown(30s) on that key
  -> Exponential backoff: 2^attempt + random(0.5, 1.5) seconds
  -> Switch preferred provider on each failure (Gemini->Groq->Gemini...)
If all 4 attempts fail -> return None
```

**API Endpoints Called:**

- Gemini: `https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={key}`
- Groq: `https://api.groq.com/openai/v1/chat/completions` (model: `llama-3.3-70b-versatile`)
- OpenAI fallback: `https://api.openai.com/v1/chat/completions` (model: `gpt-4o-mini`)

### `KeyPool` (`key_pool.py`)

- Scans env vars `GROQ_API_KEY_1` through `GROQ_API_KEY_14` and `GEMINI_API_KEY_1` through `GEMINI_API_KEY_14`
- Falls back to base `GROQ_API_KEY` / `GEMINI_API_KEY` if no numbered keys exist
- Shuffles keys randomly on startup
- Round-robin with real-time availability checks
- Per-key rate tracking: `requests_this_minute`, `requests_today`, `cooldown_until`

---

## 8. Agents

### `InterviewAgent` — The Master Orchestrator

The most complex file (810 lines). Called synchronously on every answer submission.

**`process_answer()` pipeline (per turn):**

```
1.  Load session + state from DB
2.  Transcript autocorrection (TranscriptNormalizer)
3.  Phase routing: EXPERIENCE_DEFENSE -> PROJECT_DEFENSE -> SUBJECT_KNOWLEDGE
4.  Prepare resume context string (for LLM evaluation)
5.  AnswerEvaluator.evaluate() -> SemanticEvaluationResult
6.  ConsistencyEngine.analyze() -> DiscrepancyRecords
7.  Reconcile contradictions -> update state
8.  Update state: claims, topics, entities
9.  Record turn in InterviewState
10. ScoringPolicy.calculate_turn_score() -> (earned_pts, possible_pts, severity)
11. Persist InterviewEvidence row to DB
12. AdaptivePlanner.plan_next_action() -> PlannerDecision
13. QuestionGenerator.generate() -> next question text
14. Persist question to transcript
15. Persist state + session to DB
16. Return InterviewTurnOut (response to frontend)
```

**Interview Phases:**

| Phase | What's tested | Ordering |
|-------|--------------|----------|
| `EXPERIENCE_DEFENSE` | All work experience (companies, roles) | Resume order (chronological) |
| `PROJECT_DEFENSE` | All projects | Descending by `overall_relevance` |
| `SUBJECT_KNOWLEDGE` | Core CS/role fundamentals | From role profile |

**MAX_DEPTH:** 7 follow-up turns per item before forced pivot.

### `RoleProfileAgent`

Generates a structured topic profile for a company+role combination.

- If JD text provided and LLM configured → LLM extracts subjects/topics/importance scores/question types
- Fallback → 3 hardcoded subject areas: DSA, System Design, Core Fundamentals (OS, CN, DBMS, SQL)
- Stores provenance evidence (hiring pattern facts) with the profile

### `MockOAAgent`, `PracticeAgent`, `ReviewAgent`, `EvaluatorAgent`

- Handle question generation, grading, and 18-point admin review flows
- All use the same `llm_client.generate_completion()` internally

---

## 9. Engines

### `ResumeParser`

Converts raw resume text -> structured `sections_json`.

**Flow:**
1. Unicode normalization (dashes, bullets)
2. Extract name + email heuristically from first 5 lines
3. **LLM parsing** (if any key configured): extracts `work_experience`, `projects`, `skills`, `education`, `certifications`, `achievements`
4. Deterministic regex fallback if LLM fails
5. Generates **stable deterministic IDs** for each item (e.g., `proj_1_neurascale`) — prevents UUID churn
6. Calculates `overall_relevance` scores per work experience and project relative to target role

**Critical invariant:** Resume claims start as `UNEXPLORED`. Never marked demonstrated without evidence.

---

### `AnswerEvaluator`

**`SemanticEvaluationResult` schema (current, 3 scored dimensions):**

| Field | Type | Description |
|-------|------|-------------|
| `answer_understanding` | str | What the candidate conveyed |
| `candidate_claims` | List[CandidateClaimExtraction] | Discrete technical assertions made |
| `entities` | List[str] | Technologies/systems mentioned |
| `candidate_topics` | List[str] | Topics introduced |
| `relationships` | List[str] | Causal/architectural linkages stated |
| `reasoning_summary` | str | Audit-ready evaluation summary |
| `objective_evidence` | List[str] | Evidence satisfying the question objective |
| `missing_evidence` | List[str] | Expected criteria not addressed |
| `technical_validity` | float [0,1] | **Weight: 50%** — Is the answer technically correct? |
| `completeness` | float [0,1] | **Weight: 30%** — Did it cover all required aspects? |
| `communication` | float [0,1] | **Weight: 20%** — Clarity and precision of explanation |
| `clarification_needed` | bool | Whether a clarification follow-up is warranted |
| `is_non_answer` | bool | True if candidate deflected/gave no substance |

**Evaluation flow:**
1. Check for explicit evasion (e.g., "I don't know", deflection) -> instant `is_non_answer=True`, score=0
2. Call `_evaluate_via_llm()` -> LLM returns JSON matching schema
3. Parse and validate into `SemanticEvaluationResult`
4. If LLM fails -> graceful fallback object (zeros, `is_non_answer=True`)

---

### `AdaptivePlanner`

Decides what to ask next based on the full `InterviewState`. Outputs a `PlannerDecision`.

**`PlannerAction` enum (21 possible actions):**

```
CLARIFY_CONTRADICTION      # Candidate contradicted themselves
VERIFY_UNSUPPORTED_CLAIM   # Candidate made an unverified bold claim
DEEPEN_CURRENT_TOPIC       # Go deeper on same topic
EXPLORE_CANDIDATE_TOPIC    # Pick up a tech/concept they mentioned
EXPLORE_RESUME_TOPIC       # Probe an unexplored resume claim

TEST_IMPLEMENTATION         # How exactly was it built?
TEST_REASONING              # Why did you choose this approach?
TEST_TRADEOFF               # What are the trade-offs?
TEST_PERFORMANCE            # How does it scale/perform?
TEST_SCALE                  # 10x traffic — what breaks?
TEST_RELIABILITY            # How does it handle failure?
TEST_FAILURE                # Failure modes and recovery?
TEST_SECURITY               # Security considerations?
TEST_CONCURRENCY            # Thread safety, race conditions?
TEST_CONSISTENCY            # Data consistency guarantees?
TEST_ARCHITECTURE           # Component boundaries, modularity?
TEST_OPERATIONS             # Observability, deployment, monitoring?
TEST_DEBUGGING              # How would you diagnose X issue?

PIVOT_ITEM                  # Move to next agenda item (low score or exhausted)
START_NEXT_ITEM             # Begin next project/experience
START_SUBJECT_STAGE         # Begin subject knowledge phase
END_INTERVIEW               # Conclude and generate report
```

**Decision logic:**
- Open contradictions exist -> `CLARIFY_CONTRADICTION`
- `technical_validity < 0.40` -> pivot or deepen depending on depth
- `technical_validity >= 0.70` + turns remaining -> probe next unexplored dimension
- Unexplored resume claims exist -> `EXPLORE_RESUME_TOPIC`
- MAX_DEPTH (7) reached -> `PIVOT_ITEM` or `START_NEXT_ITEM`

---

### `ConsistencyEngine`

Cross-references every new statement against the full claim history.

**6 contextual dimensions checked:**
1. Project/Item context (same project or different?)
2. Component/Service context (OLTP vs OLAP vs cache keywords)
3. Role context (author vs collaborator?)
4. Time/Migration context (v1 vs v2 architecture? "migrated", "initially")
5. Architectural scope (read replica vs primary?)
6. Specificity & certainty level

**Contradiction handling:**
- Detected -> `DiscrepancyRecord` created
- `InterviewState.record_contradiction()` called
- Score for the contradicted claim is **retroactively revoked** in state
- If candidate resolves via clarification -> `state.resolve_contradiction()`
- Unresolved contradictions at interview end -> verified gaps in report

---

### `ScoringPolicy`

100% deterministic. The LLM never touches points.

**See Section 11 for the full scoring math.**

---

### `QuestionGenerator`

Generates the next interview question text.

- Takes `PlannerDecision` as input (what dimension/action/topic to target)
- Builds system + user prompt with full context (candidate entities, previous answer, contradiction context, role skills)
- Calls `llm_client.generate_completion(temperature=0.25)`
- If LLM fails -> deterministic `_format_fallback_question()` built from planner context

---

### `TranscriptNormalizer`

Pre-processes speech-to-text input before evaluation.

- **80+ hardcoded phonetic regex replacements:**
  - "post grass sql" -> "PostgreSQL"
  - "read is" -> "Redis"
  - "cloud player" -> "Cloudflare"
  - "in the next" -> "Nginx"
  - "CSE files" -> "CSV files"
  - "pine corn" -> "Pinecone"
  - "mungodb" -> "MongoDB"
  - ...and many more
- LLM-assisted correction for complex/ambiguous cases
- Candidates are evaluated on **intent**, not speech recognition mishearing

---

### `SandboxRunner`

Secure multi-language code execution for DSA and OA problems.

**Supported languages:** Python 3, C, C++ (17/20/23), Java, JavaScript (Node.js), TypeScript, Go, Rust, C#

**Security layers:**
1. **Static AST scan** for forbidden modules/calls in Python (blocks `os`, `sys`, `subprocess`, `socket`, `eval`, `exec`, etc.)
2. C/C++ forbidden patterns (blocks `system()`, `popen()`, `fork()`, `socket()`, file I/O)
3. Java forbidden patterns (blocks `Runtime.exec()`, `ProcessBuilder`, reflection)
4. **Process isolation** in sterile temp directories
5. **4.0-second wall-clock timeout** preventing infinite loops and CPU exhaustion
6. Deterministic fallback simulation if native toolchain unavailable on host

---

### `InterviewState`

The full in-memory session state serialized into DB JSON columns.

**Contains:**
- `items: Dict[item_id, ItemState]` — per-experience/project state
- `claims: Dict[claim_id, Claim]` — all resume + candidate claims with lifecycle status
- `contradictions: List[Contradiction]` — all detected contradictions
- `question_history: List[QuestionTurn]` — all questions asked
- `topics_covered: List[str]` — all topics touched
- `active_item_id: str` — what's being explored right now

**Claim lifecycle:**
```
UNEXPLORED -> MENTIONED -> PARTIALLY_SUPPORTED -> SUPPORTED -> STRONGLY_SUPPORTED
                        -> UNVERIFIED -> CONTRADICTED -> CLARIFICATION_REQUIRED
```

---

### `ReportGenerator`

Builds the final report after `END_INTERVIEW`.

**Report contains:**
- Per-item scorecards (every work experience + every project)
- Dual headline scores: Experience Score + Subject Knowledge Score
- Claim status summary per item (how many supported, contradicted, unexplored, etc.)
- Strengths + gaps traced to specific evidence turns (never generic text)
- Recommendations based only on demonstrated gaps
- Star ratings per item and overall (score / 20)

---

## 10. Interview Flow — Step by Step

```
User pastes resume text + enters company/role
        |
        v
POST /api/interview/parse-resume
  -> ResumeParser.parse_resume() [LLM or deterministic]
  -> Saved as StructuredResume in DB
        |
        v
POST /api/interview/sessions
  -> InterviewAgent.start_session()
  -> Builds Interview Agenda (exp -> projects sorted by relevance -> subjects)
  -> Seeds InterviewState with resume claims (all UNEXPLORED)
  -> Generates opening question via QuestionGenerator
  -> Returns first InterviewTurnOut
        |
        v
[Frontend shows question]
        |
        v
User speaks (Web Speech API) or types answer
        |
        v
POST /api/interview/sessions/{id}/answer     <- regular
POST /api/interview/sessions/{id}/answer-stream  <- SSE streaming
  -> InterviewAgent.process_answer()
      [Full 15-step pipeline — see Section 8]
  -> Returns next InterviewTurnOut
        |
        v
[Repeat until phase = COMPLETED, max_depth reached, all items explored]
        |
        v
GET /api/interview/sessions/{id}/report
  -> ReportGenerator.generate_report()
  -> Returns InterviewFinalReportOut
```

---

## 11. Scoring System (Math)

### Evidence Score `E_i`

```
E_i = sum(dim_value * dim_weight) / sum(active_weights)

Dimensions:
  technical_validity  weight=0.50
  completeness        weight=0.30
  communication       weight=0.20

If is_non_answer=True -> E_i = 0.0
```

### Question Complexity `C`

```
C = 0.35 * cognitive_complexity
  + 0.35 * technical_complexity
  + 0.30 * reasoning_requirement

All from QuestionProfile [0, 1]
```

### Asymmetry Factor `A`

```
A = D*Q + (1-D)*(1-Q)
  where D = question difficulty [0,1], Q = E_i

Properties:
  Hard (D~1) + Strong (Q~1) -> A~1.0 (high reward)
  Hard (D~1) + Weak  (Q~0) -> A~0.0 (protected, low penalty)
  Easy (D~0) + Weak  (Q~0) -> A~1.0 (heavy penalty)
  Easy (D~0) + Strong(Q~1) -> A~0.0 (modest reward)
```

### Question Weight `W_i` (Possible Points)

```
W_i = clamp(W_MIN + (W_MAX - W_MIN) * (0.65*A + 0.35*C), W_MIN, W_MAX)

W_MIN = 1.0 points
W_MAX = 10.0 points
```

### Earned Points `M_i`

```
M_i = W_i * E_i   (clamped to [0, W_i])
```

### Severity

```
E_i >= 0.75 -> NONE
E_i >= 0.50 -> MINOR
E_i >= 0.25 -> MODERATE
E_i <  0.25 -> SEVERE
```

### Item Score

```
Item Score = (sum of M_i) / (sum of W_i) * 100   [out of 100]
```

### Experience Score (Final Headline)

```
Experience Score = sum(item_score * item_relevance_weight) / sum(item_relevance_weight)
[Includes BOTH work experience AND projects]
[Untested items excluded — never given 0]
```

### Subject Knowledge Score (Final Headline)

```
Subject Score = sum(subject_earned) / sum(subject_possible) * 100
[Completely separate from experience score, never blended]
```

### Star Rating

```
Star = min(5.0, score / 20)
```

---

## 12. API Endpoints

### Auth (`/api/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/signup` | Email/password registration |
| POST | `/login` | Email/password login -> JWT |
| POST | `/google` | Google OAuth login |

### Interview (`/api/interview`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/parse-resume` | Upload + parse resume text |
| GET | `/resumes/sample` | Get sample resume |
| POST | `/sessions` | Create interview session + first question |
| POST | `/sessions/{id}/answer` | Submit answer -> get next question |
| POST | `/sessions/{id}/answer-stream` | SSE streaming version of answer |
| POST | `/sessions/{id}/correct-transcript` | Autocorrect a transcript turn |
| GET | `/sessions/{id}/report` | Get final interview report |
| GET | `/sessions/{id}` | Get session details |
| GET | `/sessions` | List user's sessions |
| POST | `/correct-transcript` | Standalone transcript correction |

### Mock OA (`/api/mock-oa`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/start` | Start an OA variant |
| POST | `/run-code` | Execute code in sandbox |
| POST | `/{attempt_id}/submit` | Submit OA answers |
| GET | `/{attempt_id}/report` | Get OA report |

### Practice (`/api/practice`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions` | Create practice session |
| POST | `/check-answer` | Check a practice answer |
| GET | `/sessions/{id}` | Get practice session |

### Role Profiles (`/api/role-profiles`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate` | Generate topic profile from JD |
| GET | `/` | List profiles |

### Candidate (`/api/candidate`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/setup` | Unified onboarding: user + profile + resume + interview start in one call |

### Settings (`/api/settings`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/keys` | Update API keys live (persisted to .env) |

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server health check |

---

## 13. Frontend Architecture

**Hosted on:** Vercel (SPA with `vercel.json` rewrite config for React Router)

### 11 Pages

| Page | Route | Description |
|------|-------|-------------|
| `LandingPage` | `/` | Marketing/home page |
| `DashboardPage` | `/dashboard` | User dashboard with session history |
| `JDIntakePage` | `/jd` | JD text input + role profile generation |
| `InterviewIntakePage` | `/interview/setup` | Resume upload + session setup |
| `LiveInterviewPage` | `/interview/:id` | Real-time interview UI (voice + text) |
| `InterviewReportPage` | `/interview/:id/report` | Final report with scorecards |
| `PracticeConfigPage` | `/practice/config` | Practice topic selection |
| `PracticeRunnerPage` | `/practice/:id` | Practice question runner |
| `MockOARunnerPage` | `/oa/:id` | Full Mock OA with Monaco code editor |
| `OAReportPage` | `/oa/:id/report` | OA score report |
| `AdminReviewPage` | `/admin/review` | Admin 18-point question review queue |

### Key Frontend Features

- **Monaco Editor** for coding problems (syntax highlighting, multi-language)
- **Voice input** (browser Web Speech API) on Live Interview page
- **SSE (Server-Sent Events)** for sentence-by-sentence streaming of AI questions
- **Real-time scoring display** (earned/possible points after each turn)
- **Sidebar panels**: Exploration Dimension + Adaptive Scoring Policy
- **Confetti animation** on interview completion (canvas-confetti)
- **Tailwind CSS** dark theme throughout

### API Service Layer

Single file: `src/services/api.ts` — all backend calls go through this one file. Uses the `fetch` API.

---

## 14. Deployment

### Backend — Render.com

```yaml
# render.yaml
type: web
runtime: python
buildCommand: pip install -r backend/requirements.txt
startCommand: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
autoDeploy: true

Environment Variables (set in Render dashboard):
  DATABASE_URL          # Supabase PostgreSQL URL
  GEMINI_API_KEY        # base fallback
  GROQ_API_KEY          # base fallback
  GEMINI_API_KEY_1 to _5
  GROQ_API_KEY_1 to _6
  PYTHON_VERSION=3.11.9
  PYTHONPATH=.
```

### Frontend — Vercel

Deployed as a static SPA. `vercel.json` rewrites all routes to `index.html` for React Router support.

### Database — Supabase (PostgreSQL)

- Cloud PostgreSQL instance
- Connection via `DATABASE_URL` env variable (auto-encoded by `database.py`)
- `sslmode=require` auto-appended for cloud connections
- Google OAuth users mirrored to Supabase `auth.users` table
- Pool: size=10, max_overflow=20, recycle=300s

### Dockerfile

The repo has a Dockerfile in `backend/` using Python 3.11-slim, installs requirements, and runs uvicorn on `$PORT`.

---

## 15. Key Design Invariants

These are the non-negotiable rules baked into the architecture. Any new feature must respect all of these.

1. **Resume != Proof**: Resume claims are never treated as demonstrated knowledge. They start `UNEXPLORED`. Only real-time dialogue evidence promotes a claim status.

2. **No LLM Point Hallucination**: The LLM evaluates dimensions only (float 0-1). Points math is 100% deterministic Python in `ScoringPolicy`. LLM never outputs points.

3. **Untested != Zero**: Items not explored during the interview receive `None` score, not 0. They are strictly excluded from final score calculations.

4. **No Negative Points**: Minimum earned is `0.0`. The asymmetry factor `A` mathematically protects candidates on genuinely hard questions.

5. **No Chain-of-Thought Exposure**: `rationale` fields in `PlannerDecision` are internal/audit-only and never sent to the frontend.

6. **No Fake Data**: Resume parser never invents projects, certifications, or achievements. An empty field is preferred over fabricated content.

7. **Stable IDs**: Resume items use deterministic slug-based IDs (e.g., `proj_1_neurascale`) — not random UUIDs — preventing state corruption across re-parses within a session.

8. **Difficulty != Depth**: A follow-up question (depth=5) can be easy. An opening question (depth=1) can be hard. These are independent dimensions on `QuestionProfile`.

9. **Dual Headline Scores**: Experience Score (resume/projects, relevance-weighted) and Subject Knowledge Score are completely separate. Never blended into a single score.

10. **No MCP**: All LLM calls are direct synchronous HTTPS REST calls via `httpx`. No orchestration layer, tool-calling protocol, or agent framework is used.
