# Intervyn — Complete Model Architecture

> Built exclusively from reading source code on GitHub (khurdiaakshat123/AI_interview @ main).
> No guessing. No local-only files included.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [GitHub Repository Structure](#2-github-repository-structure)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Environment Variables & API Keys](#5-environment-variables--api-keys)
6. [Database Design](#6-database-design)
7. [Backend — Folder Structure](#7-backend--folder-structure)
8. [LLM Client & Key Pool](#8-llm-client--key-pool)
9. [Agents](#9-agents)
10. [Engines](#10-engines)
11. [Interview Flow — Step by Step](#11-interview-flow--step-by-step)
12. [Scoring System (Math)](#12-scoring-system-math)
13. [API Endpoints](#13-api-endpoints)
14. [Frontend Architecture](#14-frontend-architecture)
15. [Proctoring System](#15-proctoring-system)
16. [Test Suite](#16-test-suite)
17. [Deployment](#17-deployment)
18. [Key Design Invariants](#18-key-design-invariants)

---

## 1. Project Overview

**Intervyn** is a full-stack AI-powered technical interview and assessment platform. It simulates a real technical interview — resume-grounded adaptive questioning, consistency checking, deterministic scoring, and a final evidence-backed report — using LLMs as the backbone.

**4 core product flows:**

| Flow | What it does |
|------|-------------|
| **AI Mock Interview** | Adaptive multi-turn technical interview grounded in the candidate's own resume |
| **Mock Online Assessment (OA)** | Time-boxed coding + MCQ/SQL OA simulating real company assessments |
| **Practice Mode** | Topic-by-topic question practice from a curated question bank |
| **Interview Report** | Evidence-backed scoring report with per-item scorecards and star ratings |

---

## 2. GitHub Repository Structure

The exact file tree on GitHub (main branch) — `local_host_optimized` folder excluded:

```
AI_interview/
+-- .env.example
+-- .gitignore
+-- AI-OA-Interview-Platform-Architecture.md
+-- Dockerfile
+-- README.md
+-- render.yaml
+-- requirements.txt
+-- backend/
|   +-- Dockerfile
|   +-- Procfile
|   +-- __init__.py
|   +-- requirements.txt
|   +-- test_system.py
|   +-- app/
|   |   +-- __init__.py
|   |   +-- main.py
|   |   +-- database.py
|   |   +-- agents/
|   |   |   +-- __init__.py
|   |   |   +-- evaluator_agent.py
|   |   |   +-- interview_agent.py       (37 KB — master orchestrator)
|   |   |   +-- mock_oa_agent.py
|   |   |   +-- practice_agent.py
|   |   |   +-- review_agent.py
|   |   |   +-- role_profile_agent.py
|   |   +-- api/
|   |   |   +-- __init__.py
|   |   |   +-- admin.py
|   |   |   +-- auth.py
|   |   |   +-- candidate.py
|   |   |   +-- deps.py
|   |   |   +-- interview.py
|   |   |   +-- mock_oa.py
|   |   |   +-- practice.py
|   |   |   +-- role_profiles.py
|   |   |   +-- settings.py
|   |   +-- engines/
|   |   |   +-- __init__.py
|   |   |   +-- adaptive_planner.py     (20 KB)
|   |   |   +-- answer_evaluator.py     (18 KB)
|   |   |   +-- consistency_engine.py   (17 KB)
|   |   |   +-- document_parser.py      (10 KB)
|   |   |   +-- evaluator_registry.py   (7.9 KB)
|   |   |   +-- follow_up_fsm.py        (2 KB)
|   |   |   +-- interview_state.py      (25 KB)
|   |   |   +-- question_generator.py   (23 KB)
|   |   |   +-- question_profile.py     (12 KB)
|   |   |   +-- report_generator.py     (19 KB)
|   |   |   +-- resume_parser.py        (41 KB — largest engine)
|   |   |   +-- sandbox_runner.py       (46 KB — largest file)
|   |   |   +-- scoring_engine.py       (4.6 KB)
|   |   |   +-- scoring_policy.py       (7.6 KB)
|   |   |   +-- transcript_normalizer.py(10 KB)
|   |   |   +-- web_search.py           (2.2 KB)
|   |   +-- llm/
|   |   |   +-- client.py               (36 KB)
|   |   |   +-- key_pool.py             (4.3 KB)
|   |   +-- models/
|   |   |   +-- __init__.py
|   |   |   +-- models.py               (8.7 KB — all ORM tables)
|   |   +-- schemas/
|   |   |   +-- __init__.py
|   |   |   +-- schemas.py              (10 KB — all Pydantic schemas)
|   |   +-- seed/
|   |       +-- seed_data.py            (36 KB — question bank seed)
|   +-- tests/                          (13 test files)
|       +-- test_adaptive_interview.py
|       +-- test_adaptive_planner.py
|       +-- test_answer_evaluator.py
|       +-- test_behavioral_invariants_40.py
|       +-- test_consistency_engine.py
|       +-- test_interview_api_contracts.py
|       +-- test_interview_state.py
|       +-- test_live_interview_agent.py
|       +-- test_question_generator.py
|       +-- test_question_profile.py
|       +-- test_report_generator.py
|       +-- test_resume_parser.py
|       +-- test_resume_parser_robustness.py
|       +-- test_scoring_policy.py
|       +-- test_simulated_adaptive_interview.py
+-- frontend/
    +-- index.html
    +-- package.json
    +-- package-lock.json
    +-- postcss.config.js
    +-- tailwind.config.js
    +-- tsconfig.json
    +-- vercel.json
    +-- vite.config.ts
    +-- src/
        +-- App.tsx
        +-- main.tsx
        +-- index.css
        +-- vite-env.d.ts
        +-- components/
        |   +-- AuthModal.tsx
        |   +-- CandidateSetupModal.tsx
        |   +-- CodeEditor.tsx
        |   +-- DepthMeter.tsx
        |   +-- DocumentUploadInput.tsx
        |   +-- Navbar.tsx
        |   +-- ProctoringBadge.tsx
        |   +-- StarRating.tsx
        |   +-- Timer.tsx
        +-- hooks/
        |   +-- useProctoring.ts
        +-- pages/
        |   +-- AdminReviewPage.tsx
        |   +-- DashboardPage.tsx
        |   +-- InterviewIntakePage.tsx
        |   +-- InterviewReportPage.tsx
        |   +-- JDIntakePage.tsx
        |   +-- LandingPage.tsx
        |   +-- LiveInterviewPage.tsx      (41 KB — most complex page)
        |   +-- MockOARunnerPage.tsx       (57 KB — largest file in frontend)
        |   +-- OAReportPage.tsx
        |   +-- PracticeConfigPage.tsx
        |   +-- PracticeRunnerPage.tsx
        +-- services/
        |   +-- api.ts
        +-- types/
        |   +-- index.ts
        +-- utils/
            +-- boilerplate_generator.ts
```

---

## 3. High-Level Architecture

```
+--------------------------------------------------------------+
|                     FRONTEND (React/TS)                      |
|  Vercel-hosted SPA  |  11 Pages  |  9 Components             |
|  1 Hook (Proctoring) | 1 Service Layer | 1 Type File         |
+-----------------------------+--------------------------------+
                              | REST + SSE (streaming)
                              v
+--------------------------------------------------------------+
|                  BACKEND (FastAPI / Python)                   |
|                                                              |
|  Auth API  |  Interview API  |  Mock OA API  |  Practice API |
|  Role Profiles API  |  Candidate API  |  Admin API           |
|                              |                               |
|  +---------------------------v---------------------------+   |
|  |                    AGENT LAYER                        |   |
|  |  InterviewAgent (master) | RoleProfileAgent           |   |
|  |  MockOAAgent | PracticeAgent | ReviewAgent            |   |
|  |  EvaluatorAgent                                       |   |
|  +---------------------------+---------------------------+   |
|                              |                               |
|  +---------------------------v---------------------------+   |
|  |                   ENGINE LAYER                        |   |
|  |  ResumeParser | AnswerEvaluator | AdaptivePlanner     |   |
|  |  ConsistencyEngine | ScoringPolicy | QuestionGen      |   |
|  |  InterviewState | ReportGenerator | SandboxRunner     |   |
|  |  TranscriptNormalizer | DocumentParser | WebSearch     |   |
|  +---------------------------+---------------------------+   |
|                              |                               |
|  +---------------------------v---------------------------+   |
|  |              LLM CLIENT + KEY POOL                    |   |
|  |  Gemini (preferred) -> Groq (fallback) -> OpenAI     |   |
|  |  Round-robin rotation | 30s cooldowns | 4 retries    |   |
|  +---------------------------+---------------------------+   |
|                              |                               |
|  +---------------------------v---------------------------+   |
|  |                    DATABASE                           |   |
|  |  SQLite (local dev) / PostgreSQL via Supabase (prod) |   |
|  +-------------------------------------------------------+   |
+--------------------------------------------------------------+
```

---

## 4. Tech Stack

### Backend

| Layer | Technology | Version (from requirements.txt) |
|-------|-----------|--------------------------------|
| Web Framework | FastAPI | >= 0.110.0 |
| ASGI Server | Uvicorn (standard extras) | >= 0.28.0 |
| ORM | SQLAlchemy | >= 2.0.0 |
| Schema Validation | Pydantic v2 | >= 2.6.0 |
| Pydantic Settings | pydantic-settings | >= 2.2.0 |
| HTTP Client | httpx (synchronous) | >= 0.27.0 |
| Auth Tokens | PyJWT | >= 2.8.0 |
| PDF Parsing | PyMuPDF | >= 1.23.0 |
| Multipart Forms | python-multipart | >= 0.0.9 |
| Env Management | python-dotenv | >= 1.0.0 |
| PostgreSQL Driver | psycopg2-binary | latest |
| Image Processing | Pillow | latest |
| HTML Parsing | BeautifulSoup4 | latest |
| Language | Python | 3.11.9 |

### Frontend (from package.json)

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

| Provider | Model | Role |
|----------|-------|------|
| Google Gemini | `gemini-flash-latest` | Primary (preferred first) |
| Groq | `llama-3.3-70b-versatile` | Fallback when Gemini fails |
| OpenAI | `gpt-4o-mini` | Last-resort fallback |

> No MCP, no tool-calling, no agent framework. All LLM calls are direct HTTPS REST via `httpx`.

---

## 5. Environment Variables & API Keys

### From `.env.example` (what GitHub documents)

```
DATABASE_URL=sqlite:///./intervyn.db

GEMINI_API_KEY=
GROQ_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### Full key pool convention (from `key_pool.py`)

The `KeyPool` scans for numbered variants of each key automatically:

| Variable Pattern | Provider | Count (in production) |
|-----------------|---------|----------------------|
| `GEMINI_API_KEY` | Google AI Studio | Base fallback |
| `GEMINI_API_KEY_1` ... `GEMINI_API_KEY_5` | Google AI Studio | 5 pool keys |
| `GROQ_API_KEY` | Groq | Base fallback |
| `GROQ_API_KEY_1` ... `GROQ_API_KEY_6` | Groq | 6 pool keys |
| `OPENAI_API_KEY` | OpenAI | Optional last resort |
| `ANTHROPIC_API_KEY` | Anthropic | Optional, supported |
| `DATABASE_URL` | Supabase/Render | PostgreSQL connection string |

> The code scans up to `_14` suffix — 14 slots per provider — but only those that are non-empty get added to the pool.

### Key Rotation Logic

- Keys shuffle randomly at startup
- Gemini preferred first on every call
- If all Gemini keys rate-limited, switches to Groq
- Per-key rate tracking: Groq < 28 RPM, Gemini < 14 RPM and < 480 RPD
- On HTTP 429 / 401 / 404: key goes on **30-second cooldown**
- Retry: 4 attempts, exponential backoff `2^attempt + random(0.5, 1.5)s`
- If all 4 attempts fail: `generate_completion()` returns `None`

---

## 6. Database Design

### Connection Strategy (from `database.py`)

- **Local dev**: SQLite (`intervyn.db`) with `PRAGMA foreign_keys=ON`
- **Production**: PostgreSQL via `DATABASE_URL`, auto-appends `sslmode=require` for cloud hosts
- Pool config (cloud): `pool_size=10`, `max_overflow=20`, `pool_recycle=300`, `pool_pre_ping=True`
- `Base.metadata.create_all()` on startup (no Alembic migrations)

### All Tables (from `models.py`)

#### `users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | String (UUID) | Primary key |
| `email` | String(255) | Unique |
| `password_hash` | String(255) | `"google_oauth"` for OAuth users |
| `name` | String(255) | |
| `google_id` | String(255) | Unique, nullable |
| `avatar_url` | String(500) | Nullable |
| `created_at` | DateTime | UTC |

> Google OAuth users are also mirrored to Supabase `auth.users` table via raw SQL in `auth.py`.

#### `time_windows`

| Column | Type | Notes |
|--------|------|-------|
| `company` | String | |
| `role` | String | |
| `window_length_days` | Integer | Default: 7 |
| `status` | String | ACTIVE / CLOSED |

#### `role_topic_profiles`

| Column | Type | Notes |
|--------|------|-------|
| `company` / `role` | String | |
| `job_type` | String | |
| `experience_requirement` | String | |
| `required_skills` | JSON | List of skill strings |
| `subjects_json` | JSON | Nested: subject → topics → subtopics → importance score + question types |
| `evidence_json` | JSON | Provenance facts about the company's hiring pattern |

#### `question_bank`

| Column | Type | Notes |
|--------|------|-------|
| `question_type` | String | MCQ, MSQ, DSA, SQL, System Design, Debugging |
| `difficulty` | String | easy / medium / hard |
| `prompt` | Text | Question text |
| `options_json` | JSON | MCQ/MSQ options |
| `starter_code` | Text | Boilerplate for DSA/SQL |
| `test_cases_json` | JSON | Visible + hidden test cases |
| `status` | String | GENERATING / REVIEWING / PUBLISHED / FAILED |
| `review_report_json` | JSON | 18-point admin review checklist |

#### `practice_sessions`
Tracks per-user topic-based practice runs with selected topics, question allocations, and answers.

#### `mock_oa_variants`
A specific set of generated OA questions for a company+role within a time window.

#### `mock_oa_attempts`
A user's actual OA attempt: submitted answers, per-question results, total score, time taken.

#### `structured_resumes`

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | FK → users | |
| `raw_text` | Text | Original paste |
| `sections_json` | JSON | `{work_experience, projects, skills, education, certifications, achievements}` |
| `section_weights_json` | JSON | Relevance weight per section for target role |

#### `interview_sessions`

| Column | Type | Notes |
|--------|------|-------|
| `status` | String | INIT / IN_PROGRESS / COMPLETED |
| `current_phase` | String | EXPERIENCE_DEFENSE / PROJECT_DEFENSE / SUBJECT_KNOWLEDGE / COMPLETED |
| `transcript_json` | JSON | Full conversation transcript |
| `agent1_report_json` | JSON | Experience + Project Defense phase report |
| `agent2_report_json` | JSON | Subject Knowledge phase report |
| `final_report_json` | JSON | Merged dual-headline final report |
| `target_company` | String | |
| `target_role` | String | |

#### `interview_evidence`
One row per answer turn. The audit trail.

| Column | Type | Notes |
|--------|------|-------|
| `session_id` | FK → interview_sessions | |
| `turn_index` | Integer | |
| `earned_points` | Float | |
| `possible_points` | Float | |
| `severity` | String | NONE / MINOR / MODERATE / SEVERE |
| `evaluator_reason` | Text | LLM's reasoning |
| `evidence_ref` | String | Human-readable reference ID |

---

## 7. Backend — Folder Structure

### `main.py`
FastAPI app entry point. Registers all 8 routers, sets up CORS, runs `create_all()` + `seed_database()` on startup via `@asynccontextmanager lifespan`.

**Routers registered:**
- `auth_router` (`/api/auth`)
- `role_profiles_router` (`/api/role-profiles`)
- `practice_router` (`/api/practice`)
- `mock_oa_router` (`/api/mock-oa`)
- `interview_router` (`/api/interview`)
- `admin_router` (`/api/admin`)
- `settings_router` (`/api/settings`)
- `candidate_router` (`/api/candidate`)

### `database.py`
SQLAlchemy engine + session factory with SQLite/PostgreSQL dual mode.

### `agents/`

| File | Role |
|------|------|
| `interview_agent.py` | Master interview orchestrator. 810 lines. Controls the full 3-phase interview lifecycle. |
| `role_profile_agent.py` | Generates topic profiles from JD text or deterministic fallbacks |
| `mock_oa_agent.py` | Generates OA question sets for a company+role |
| `practice_agent.py` | Generates practice questions for selected topics |
| `review_agent.py` | Admin 18-point review of generated questions |
| `evaluator_agent.py` | Evaluates OA submissions (MCQ/MSQ/DSA/SQL) |

### `engines/`

| File | Role |
|------|------|
| `resume_parser.py` | LLM + deterministic resume extraction (41 KB) |
| `answer_evaluator.py` | SemanticEvaluationResult Pydantic schema + LLM evaluator |
| `adaptive_planner.py` | PlannerAction decision engine (21 actions) |
| `consistency_engine.py` | Cross-turn contradiction detection (6 dimensions) |
| `scoring_policy.py` | Deterministic math scoring (W_i, E_i, M_i) |
| `scoring_engine.py` | Score aggregation utilities |
| `question_generator.py` | LLM question generation + deterministic fallback |
| `question_profile.py` | QuestionProfile schema (6 continuous dimensions) |
| `interview_state.py` | Full session state: claims, turns, items, contradictions |
| `report_generator.py` | Evidence-backed final report builder |
| `transcript_normalizer.py` | 80+ phonetic regex substitutions for STT correction |
| `sandbox_runner.py` | Secure multi-language code execution (46 KB) |
| `document_parser.py` | PDF/DOCX file upload resume parsing |
| `evaluator_registry.py` | OA answer grading registry |
| `follow_up_fsm.py` | Simple FSM tracking follow-up depth per item |
| `web_search.py` | Lightweight web search for context enrichment |

### `llm/`

| File | Role |
|------|------|
| `client.py` | LLMClient singleton — all LLM calls (36 KB) |
| `key_pool.py` | APIKey + KeyPool — round-robin rotation + cooldowns |

### `seed/seed_data.py`
Seeds the question bank with DSA, MCQ, SQL, System Design questions on first startup (36 KB).

### `tests/` (15 test files)

| File | What it tests |
|------|-------------|
| `test_adaptive_interview.py` | Full adaptive interview flows |
| `test_adaptive_planner.py` | PlannerAction decision logic |
| `test_answer_evaluator.py` | SemanticEvaluationResult parsing |
| `test_behavioral_invariants_40.py` | 40 behavioral invariant assertions |
| `test_consistency_engine.py` | Contradiction detection |
| `test_interview_api_contracts.py` | API request/response contracts |
| `test_interview_state.py` | Claim lifecycle state machine |
| `test_live_interview_agent.py` | End-to-end interview agent |
| `test_question_generator.py` | LLM + fallback question generation |
| `test_question_profile.py` | QuestionProfile schema |
| `test_report_generator.py` | Final report generation |
| `test_resume_parser.py` | Resume parsing correctness |
| `test_resume_parser_robustness.py` | Edge cases and malformed inputs |
| `test_scoring_policy.py` | Scoring math correctness |
| `test_simulated_adaptive_interview.py` | Full simulated multi-turn session |

---

## 8. LLM Client & Key Pool

### `LLMClient` (`client.py`) — Singleton

**Core method:** `generate_completion(system_prompt, user_prompt, temperature) -> Optional[str]`

**Call flow:**
```
Attempt 1 to 4:
  -> KeyPool.get_available_key(prefer="gemini")
  -> If Gemini: POST https://generativelanguage.googleapis.com/
                    v1beta/models/gemini-flash-latest:generateContent?key={k}
  -> If Groq:   POST https://api.groq.com/openai/v1/chat/completions
                    model: llama-3.3-70b-versatile
  -> On 429/401/404: KeyPool.trigger_cooldown(key, 30s)
  -> Exponential backoff: sleep(2^attempt + uniform(0.5, 1.5))
  -> Alternate preferred provider on each retry
If all 4 fail -> return None
```

**Specialized methods built on top:**

| Method | Purpose |
|--------|---------|
| `evaluate_candidate_answer()` | Calls LLM for semantic evaluation, returns dict |
| `generate_interview_question()` | Calls LLM for next question text |
| `correct_candidate_answer_typos()` | STT correction via LLM |
| `generate_specification_clarification_question()` | Follow-up for missing technical specs |
| `generate_completion()` | Base method — everything else calls this |

### `KeyPool` (`key_pool.py`) — Singleton

- Scans `PROVIDER_API_KEY_1` through `PROVIDER_API_KEY_14` on init
- Falls back to base `PROVIDER_API_KEY` if no numbered keys found
- Shuffles all keys randomly at startup
- Tracks per-key: `requests_this_minute`, `requests_today`, `cooldown_until`
- `get_available_key(prefer)` returns the first key not in cooldown and under rate limits

---

## 9. Agents

### `InterviewAgent` — Master Orchestrator

**`start_session()` — called once:**
1. Load structured resume from DB
2. Load role topic profile
3. Build Interview Agenda (experience items → projects sorted by relevance → subject topics)
4. Seed `InterviewState` with all resume claims as `UNEXPLORED`
5. Generate opening question
6. Save session + state to DB, return first question

**Interview Agenda phases:**

| Phase | Items included | Order |
|-------|---------------|-------|
| `EXPERIENCE_DEFENSE` | All work experience entries | Resume/chronological order |
| `PROJECT_DEFENSE` | All projects | Descending by `overall_relevance` |
| `SUBJECT_KNOWLEDGE` | Role-specific CS fundamentals | From role profile |

**`process_answer()` — called on every answer turn (15 steps):**
```
1.  Load session + state from DB
2.  TranscriptNormalizer.normalize() — phonetic STT correction
3.  Determine active phase + active item
4.  Build resume context string for LLM
5.  AnswerEvaluator.evaluate() -> SemanticEvaluationResult
6.  ConsistencyEngine.analyze() -> DiscrepancyRecords
7.  Reconcile contradictions in InterviewState
8.  Update claims, topics, entities in state
9.  Record turn in InterviewState
10. ScoringPolicy.calculate_turn_score() -> (earned, possible, severity)
11. Save InterviewEvidence row to DB
12. AdaptivePlanner.plan_next_action() -> PlannerDecision
13. QuestionGenerator.generate() -> next question text
14. Save question to transcript
15. Persist full state + session to DB, return InterviewTurnOut
```

**MAX_DEPTH:** 7 follow-up turns per agenda item before forced pivot.

### `RoleProfileAgent`

- If JD text provided: LLM extracts subjects, topics, subtopics, importance scores, question type distributions
- Fallback (no JD or LLM fail): deterministic defaults — DSA, System Design, Core Fundamentals (OS, CN, DBMS, SQL)
- Provenance evidence (hiring facts) stored alongside profile

### `EvaluatorAgent`
Grades OA submissions — MCQ/MSQ (exact match), DSA/SQL (via SandboxRunner + test cases).

### `MockOAAgent`
Generates OA question sets (DSA + MCQ + SQL mix) for a company+role pair. Checks against existing question bank before generating new ones.

### `PracticeAgent`
Generates topic-targeted practice questions based on user's selected subjects and difficulty distribution.

### `ReviewAgent`
Runs a 18-point checklist review on generated questions before they reach PUBLISHED status.

---

## 10. Engines

### `ResumeParser`

Converts raw resume text → structured `sections_json`.

**Flow:**
1. Unicode normalization (dashes, fancy quotes, bullets)
2. Heuristic name + email extraction from first 5 lines
3. LLM parsing → `{work_experience, projects, skills, education, certifications, achievements}`
4. Deterministic regex fallback if LLM fails or is unavailable
5. Stable deterministic IDs per item (e.g., `proj_1_neurascale`) — no random UUIDs
6. Calculates `overall_relevance` scores per item relative to target role

**Critical invariants:**
- Resume is context evidence, NOT an answer key
- Never fabricates data (empty preferred over invented)
- All resume claims start as `UNEXPLORED` in InterviewState

### `AnswerEvaluator`

**`SemanticEvaluationResult` — Pydantic schema (3 scored dimensions):**

| Field | Type | Notes |
|-------|------|-------|
| `answer_understanding` | str | Summary of what candidate communicated |
| `candidate_claims` | List[CandidateClaimExtraction] | Discrete technical assertions |
| `entities` | List[str] | Technologies/systems mentioned |
| `candidate_topics` | List[str] | Topics introduced |
| `relationships` | List[str] | Causal/architectural links stated |
| `reasoning_summary` | str | Audit-ready evaluation rationale |
| `objective_evidence` | List[str] | Evidence satisfying the question goal |
| `missing_evidence` | List[str] | Expected criteria not addressed |
| `technical_validity` | float [0,1] | **Weight: 50%** — Correctness |
| `completeness` | float [0,1] | **Weight: 30%** — Coverage |
| `communication` | float [0,1] | **Weight: 20%** — Clarity |
| `clarification_needed` | bool | Whether a follow-up is warranted |
| `is_non_answer` | bool | True if candidate evaded/gave nothing |

**Evaluation flow:**
1. Check for evasion patterns ("I don't know", deflection) → `is_non_answer=True`, score=0
2. `_evaluate_via_llm()` → LLM returns JSON, parsed into schema
3. Pydantic validation + clamping all floats to [0, 1]
4. LLM failure → graceful fallback object (0.5 defaults, `clarification_needed=True`)

### `AdaptivePlanner`

Outputs a `PlannerDecision` telling `QuestionGenerator` what to ask next.

**All 21 `PlannerAction` values:**

```
Claim-targeted:
  CLARIFY_CONTRADICTION      # Candidate contradicted a prior claim
  VERIFY_UNSUPPORTED_CLAIM   # Candidate made an unverifiable bold claim
  DEEPEN_CURRENT_TOPIC       # Go deeper on what they just said
  EXPLORE_CANDIDATE_TOPIC    # Pick up a technology they mentioned
  EXPLORE_RESUME_TOPIC       # Probe an unexplored resume claim

Cognitive dimension probing:
  TEST_IMPLEMENTATION        # How exactly was it built?
  TEST_REASONING             # Why this approach?
  TEST_TRADEOFF              # What are the trade-offs?
  TEST_PERFORMANCE           # How does it scale?
  TEST_SCALE                 # 10x traffic — what breaks?
  TEST_RELIABILITY           # How does it handle failure?
  TEST_FAILURE               # Failure modes + recovery?
  TEST_SECURITY              # Security considerations?
  TEST_CONCURRENCY           # Thread safety, race conditions?
  TEST_CONSISTENCY           # Data consistency guarantees?
  TEST_ARCHITECTURE          # Component boundaries, modularity?
  TEST_OPERATIONS            # Observability, deployment, monitoring?
  TEST_DEBUGGING             # How would you diagnose X?

Navigation:
  PIVOT_ITEM                 # Move to next agenda item
  START_NEXT_ITEM            # Start next project/experience
  START_SUBJECT_STAGE        # Begin subject knowledge phase
  END_INTERVIEW              # Conclude and trigger report
```

**Decision priority:**
1. Open unresolved contradictions → `CLARIFY_CONTRADICTION`
2. `technical_validity < 0.40` → deepen or pivot based on depth
3. `technical_validity >= 0.70` + turns remaining → probe next cognitive dimension
4. Unexplored resume claims exist → `EXPLORE_RESUME_TOPIC`
5. MAX_DEPTH (7) reached → `PIVOT_ITEM` / `START_NEXT_ITEM`
6. All items done → `START_SUBJECT_STAGE` / `END_INTERVIEW`

### `ConsistencyEngine`

Cross-references every new statement against the full claim history.

**6 contextual dimensions checked before flagging a contradiction:**
1. Project/Item context (same project or different?)
2. Component/Service context (OLTP vs OLAP vs cache keywords)
3. Role context (author vs collaborator?)
4. Time/Migration context (v1 vs v2? "migrated", "initially")
5. Architectural scope (read replica vs primary?)
6. Specificity and certainty level of statement

**On detected contradiction:**
- `DiscrepancyRecord` created
- `InterviewState.record_contradiction()` called
- Score for the contradicted claim retroactively revoked in state
- If resolved via clarification → `state.resolve_contradiction()`
- Unresolved at interview end → appear as verified gaps in report

### `ScoringPolicy`

100% deterministic. LLM never touches points.

See Section 12 for full math.

### `QuestionGenerator`

- Receives `PlannerDecision` (action, topic, context, depth)
- Builds a rich system + user prompt with: candidate entities, prior answer, contradiction context, role skills, resume context
- Calls `llm_client.generate_completion(temperature=0.25)`
- LLM failure → `_format_fallback_question()` — deterministic string built from planner context

### `TranscriptNormalizer`

Pre-processes voice/text input before evaluation.

**80+ hardcoded phonetic regex substitutions including:**
- `"post grass sql"` / `"postgress"` → `"PostgreSQL"`
- `"read is"` / `"redis"` → `"Redis"`
- `"in the next"` / `"engine x"` → `"Nginx"`
- `"mungodb"` / `"mongo dB"` → `"MongoDB"`
- `"cloud player"` → `"Cloudflare"`
- `"pine corn"` → `"Pinecone"`
- `"CSE files"` → `"CSV files"`
- `"cue bernetties"` → `"Kubernetes"`
- ... and many more

LLM-assisted correction also available for complex cases.

### `SandboxRunner`

Secure multi-language code execution for OA/Practice DSA problems.

**Supported languages:** Python 3, C, C++ (17/20/23), Java, JavaScript (Node.js), TypeScript, Go, Rust, C#

**Security layers (in order):**
1. **Python**: AST scan blocking `os`, `sys`, `subprocess`, `socket`, `eval`, `exec`, `open`, `__import__`, reflection attrs
2. **C/C++**: Regex patterns blocking `system()`, `popen()`, `fork()`, `socket()`, `ifstream`, file I/O
3. **Java**: Regex patterns blocking `Runtime.exec()`, `ProcessBuilder`, reflection
4. **Process isolation**: Subprocess in sterile temp directories, isolated env
5. **Wall-clock timeout**: 4.0 seconds — prevents infinite loops
6. **Deterministic fallback**: If toolchain missing on host, simulates execution with syntax validation

### `InterviewState`

Full session state serialized to JSON in DB. Held in memory during a turn.

**Contains:**
- `items: Dict[str, ItemState]` — per-experience/project tracking
- `claims: Dict[str, Claim]` — all resume + candidate claims
- `contradictions: List[Contradiction]` — all detected conflicts
- `question_history: List[QuestionTurn]` — all questions asked
- `topics_covered: List[str]` — deduplicated
- `active_item_id: str` — what is being explored now

**Claim lifecycle (`ClaimStatus` enum):**
```
UNEXPLORED
  -> MENTIONED
  -> PARTIALLY_SUPPORTED
  -> SUPPORTED
  -> STRONGLY_SUPPORTED
  -> UNVERIFIED
  -> CONTRADICTED
  -> CLARIFICATION_REQUIRED
```

### `DocumentParser`

Handles PDF and DOCX resume file uploads (as opposed to text paste). Uses PyMuPDF for PDF extraction and BeautifulSoup4 for HTML/DOCX content.

### `ReportGenerator`

Builds the final report after `END_INTERVIEW`.

**Report structure:**
- Per-item scorecards (every explored work experience + project)
- Claim status summary per item
- Dual headline scores: Experience Score + Subject Knowledge Score (always separate)
- Specific evidence-backed strengths and gaps (never generic)
- Star ratings per item and overall (`score / 20`, capped at 5.0)
- Recommendations derived only from demonstrated gaps

### `WebSearch` (`web_search.py`)

Lightweight utility for fetching public context (e.g., company tech stack info to enrich role profiles). Used by `RoleProfileAgent`.

### `FollowUpFSM` (`follow_up_fsm.py`)

Simple finite state machine tracking follow-up depth per agenda item. Used by `AdaptivePlanner` to decide when to force a pivot.

### `EvaluatorRegistry` (`evaluator_registry.py`)

Registry mapping question types to graders:
- MCQ/MSQ → exact option match
- DSA/SQL → SandboxRunner test case execution
- System Design / Debugging → LLM rubric grading

---

## 11. Interview Flow — Step by Step

```
User pastes resume + sets company/role
            |
            v
POST /api/interview/parse-resume
  -> DocumentParser (if file upload) OR direct text
  -> ResumeParser.parse_resume() [LLM then deterministic fallback]
  -> Saved as StructuredResume in DB
            |
            v
POST /api/interview/sessions
  -> InterviewAgent.start_session()
  -> Agenda built: experience -> projects (sorted by relevance) -> subjects
  -> InterviewState seeded (all resume claims UNEXPLORED)
  -> First question generated
  -> Returns InterviewTurnOut
            |
            v
[Frontend displays question to candidate]
            |
            v
Candidate speaks (Web Speech API) or types
            |
            v
POST /api/interview/sessions/{id}/answer          <- sync
  OR
POST /api/interview/sessions/{id}/answer-stream   <- SSE streaming
  -> InterviewAgent.process_answer() [15-step pipeline]
  -> Returns InterviewTurnOut (next question + scoring info)
            |
            v
[Repeat until END_INTERVIEW]
            |
            v
GET /api/interview/sessions/{id}/report
  -> ReportGenerator.generate_report()
  -> Returns InterviewFinalReportOut
```

---

## 12. Scoring System (Math)

### Evidence Score `E_i`

```
E_i = (technical_validity * 0.50 + completeness * 0.30 + communication * 0.20)

Special cases:
  is_non_answer = True  ->  E_i = 0.0
  All dimensions = 0    ->  E_i = 0.0
```

### Question Complexity `C`

```
C = 0.35 * cognitive_complexity
  + 0.35 * technical_complexity
  + 0.30 * reasoning_requirement

All dimensions from QuestionProfile [0, 1]
```

### Asymmetry Factor `A`

```
A = D * Q + (1 - D) * (1 - Q)
  where D = question difficulty [0, 1]
        Q = E_i

Properties:
  Hard (D~1) + Strong answer (Q~1)  ->  A~1.0  (high reward)
  Hard (D~1) + Weak answer  (Q~0)  ->  A~0.0  (protected — no large penalty)
  Easy (D~0) + Weak answer  (Q~0)  ->  A~1.0  (penalty for weak answer to easy Q)
  Easy (D~0) + Strong answer (Q~1) ->  A~0.0  (modest reward)
```

### Question Weight `W_i` (Possible Points)

```
W_i = clamp(W_MIN + (W_MAX - W_MIN) * (0.65 * A + 0.35 * C), W_MIN, W_MAX)

W_MIN = 1.0
W_MAX = 10.0
```

### Earned Points `M_i`

```
M_i = W_i * E_i    (minimum 0.0, maximum W_i)
```

### Severity Classification

```
E_i >= 0.75  ->  NONE
E_i >= 0.50  ->  MINOR
E_i >= 0.25  ->  MODERATE
E_i <  0.25  ->  SEVERE
```

### Item Score

```
Item Score = (sum of M_i across all turns for item) / (sum of W_i) * 100
```

### Experience Score (Headline 1)

```
Experience Score = sum(item_score * item_relevance_weight) / sum(item_relevance_weight)

Includes: ALL work experience items AND project items
Excludes: Subject knowledge phase
Untested items: excluded entirely (not scored as 0)
```

### Subject Knowledge Score (Headline 2)

```
Subject Score = sum(earned_pts) / sum(possible_pts) * 100

Completely separate from Experience Score — never blended
```

### Star Rating

```
Stars = min(5.0, score / 20)
```

---

## 13. API Endpoints

### Auth — `/api/auth`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/signup` | Email + password registration |
| POST | `/login` | Email + password login → JWT token |
| POST | `/google` | Google OAuth login/register → JWT token |

### Interview — `/api/interview`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/parse-resume` | Upload resume text or file, get structured resume |
| GET | `/resumes/sample` | Fetch sample resume for demo |
| POST | `/sessions` | Create interview session, get first question |
| GET | `/sessions` | List all user's sessions |
| GET | `/sessions/{id}` | Get session details |
| POST | `/sessions/{id}/answer` | Submit answer → get next question (sync JSON) |
| POST | `/sessions/{id}/answer-stream` | Submit answer → get next question (SSE streaming) |
| POST | `/sessions/{id}/correct-transcript` | Correct a single transcript turn |
| GET | `/sessions/{id}/report` | Get final report |
| POST | `/correct-transcript` | Standalone STT correction endpoint |

### Mock OA — `/api/mock-oa`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/start` | Start a mock OA variant for company+role |
| POST | `/run-code` | Execute code against test cases in sandbox |
| POST | `/{attempt_id}/submit` | Submit all answers, get full OA score |
| GET | `/{attempt_id}/report` | Fetch OA result report |

### Practice — `/api/practice`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions` | Create practice session with topic selection |
| POST | `/check-answer` | Check a single practice answer |
| GET | `/sessions/{id}` | Get practice session details |

### Role Profiles — `/api/role-profiles`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate` | Generate topic profile from JD text |
| GET | `/` | List all stored role profiles |

### Candidate — `/api/candidate`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/setup` | One-shot onboarding: create user + role profile + resume + start interview |

### Admin — `/api/admin`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/questions/review-queue` | Get questions pending 18-point review |
| POST | `/questions/{id}/review` | Submit review result for a question |

### Settings — `/api/settings`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/keys` | Update API keys live (writes to .env) |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server liveness check |

---

## 14. Frontend Architecture

**Deployed on:** Vercel. `vercel.json` rewrites all paths to `index.html` (SPA routing).

### Routing

No React Router library. Routing is done via state in `App.tsx` (custom state-based navigation).

### 11 Pages

| Page | Description |
|------|-------------|
| `LandingPage.tsx` | Marketing homepage |
| `DashboardPage.tsx` | User session history and quick-start |
| `JDIntakePage.tsx` | JD text input + role profile generation |
| `InterviewIntakePage.tsx` | Resume upload + session configuration |
| `LiveInterviewPage.tsx` | Real-time interview (41 KB — most complex) |
| `InterviewReportPage.tsx` | Scorecard + evidence-backed report |
| `PracticeConfigPage.tsx` | Topic selection for practice mode |
| `PracticeRunnerPage.tsx` | Practice question runner |
| `MockOARunnerPage.tsx` | Full OA with Monaco editor (57 KB — largest) |
| `OAReportPage.tsx` | OA score report |
| `AdminReviewPage.tsx` | Admin 18-point question review queue |

### 9 Shared Components

| Component | Purpose |
|-----------|---------|
| `AuthModal.tsx` | Email/password + Google OAuth login/signup modal |
| `CandidateSetupModal.tsx` | One-shot candidate onboarding form |
| `CodeEditor.tsx` | Monaco editor wrapper for OA coding problems |
| `DepthMeter.tsx` | Visual indicator of interview depth per item |
| `DocumentUploadInput.tsx` | PDF/DOCX resume file upload input |
| `Navbar.tsx` | Global navigation bar |
| `ProctoringBadge.tsx` | Live proctoring status badge/display |
| `StarRating.tsx` | Star display widget for scores |
| `Timer.tsx` | Countdown timer for OA sessions |

### 1 Hook

| Hook | Purpose |
|------|---------|
| `useProctoring.ts` | Tracks tab switches, window blur, paste bursts, fullscreen exits, total time away during OA/interview |

### 1 Utility

| File | Purpose |
|------|---------|
| `boilerplate_generator.ts` | Generates language-specific starter code boilerplate for DSA problems (C, C++, Java, Python, JS, Go, Rust, TypeScript, C#) |

### API Service

`src/services/api.ts` — single file, all backend calls go through here using the browser `fetch` API.

### Type Definitions

`src/types/index.ts` — TypeScript interfaces for all data models including: `User`, `RoleTopicProfile`, `Question`, `TestCase`, `PracticeSession`, `MockOAVariant`, `ProctoringIncident`, `ProctoringSummary`, etc.

---

## 15. Proctoring System

Available in both **Mock OA** and **Live Interview** modes.

**`useProctoring` hook tracks:**

| Event | What it detects |
|-------|----------------|
| Tab Switch | `visibilitychange` event — counts how many times candidate left the tab |
| Window Blur | `window.blur` — counts how many times browser window lost focus |
| Paste Burst | Rapid large paste events — `pasteBurstCount` |
| Fullscreen Exit | `fullscreenchange` event — counts exits from fullscreen mode |
| Time Away | Total seconds spent with tab inactive |

**Config options:**
- `warnOnTabSwitch`: Show warning on tab switch (default: true)
- `warnOnPaste`: Warn on paste (default: true)
- `maxAllowedTabSwitches`: Default 3 — after this, `danger` alert fires
- `isEnabled`: Can be disabled for non-proctored sessions

**Outputs:**
- `ProctoringAlert` — live 6-second dismissible alert (warning / danger)
- `ProctoringSummary` — full session incident log stored in OA attempt

**Frontend components:**
- `ProctoringBadge.tsx` — live badge showing current proctoring status
- Alerts rendered inline on `LiveInterviewPage` and `MockOARunnerPage`

---

## 16. Test Suite

Located in `backend/tests/`. All tests are Python unittest/pytest files.

**15 test files covering:**
- Full adaptive interview simulations (multi-turn)
- 40 behavioral invariants (the non-negotiable design rules)
- API contract tests (request/response shape validation)
- Engine unit tests (planner, evaluator, consistency, scoring, state, report, question gen, resume parser)
- Robustness tests (malformed inputs, edge cases)

**`backend/test_system.py`** — standalone integration test script at the backend root.

---

## 17. Deployment

### Backend — Render.com

```yaml
# render.yaml (from GitHub)
services:
  - type: web
    name: intervyn-backend
    runtime: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
    plan: free
    autoDeploy: true
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: PYTHONPATH
        value: .
      - key: DATABASE_URL   (set via Render dashboard)
      - key: GEMINI_API_KEY (set via Render dashboard)
      - key: GROQ_API_KEY   (set via Render dashboard)
      # + GEMINI_API_KEY_1..5, GROQ_API_KEY_1..6 set in dashboard
```

**`backend/Procfile`** (for Heroku-compatible hosts):
```
web: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

**`Dockerfile`** (root + `backend/`) — Python 3.11-slim, installs requirements, exposes `$PORT`.

### Frontend — Vercel

- Deployed as static SPA
- `vercel.json` rewrites all routes to `index.html`
- Build: `vite build` → `dist/`

### Database — Supabase (PostgreSQL)

- Cloud PostgreSQL
- Connection via `DATABASE_URL` env var
- `sslmode=require` auto-added for cloud hosts by `database.py`
- Google OAuth users mirrored to `auth.users` schema in Supabase

---

## 18. Key Design Invariants

These rules are baked into the code. Any new feature must respect all of them.

1. **Resume != Proof.** Resume claims are never treated as demonstrated knowledge. They start `UNEXPLORED`. Only real dialogue evidence can promote a claim.

2. **No LLM point hallucination.** The LLM evaluates 3 dimensions (floats 0-1). Scoring math is 100% deterministic Python in `ScoringPolicy`. LLM never outputs points or scores.

3. **Untested != Zero.** Items not explored during the interview receive `None` — they are excluded from final score calculations, not scored as 0.

4. **No negative points.** Minimum earned is 0.0. The asymmetry factor `A` mathematically protects candidates on hard questions.

5. **No chain-of-thought exposure.** `rationale` in `PlannerDecision` is internal/audit-only. Never sent to frontend.

6. **No fabricated resume data.** `ResumeParser` returns empty fields rather than inventing projects, certifications, or achievements.

7. **Stable deterministic IDs.** Resume items use slug-based IDs (e.g., `proj_1_neurascale`), not random UUIDs. This prevents `InterviewState` corruption across re-parses within the same session.

8. **Difficulty is independent of depth.** A follow-up question at depth 5 can be easy. An opener at depth 1 can be hard. These are orthogonal dimensions on `QuestionProfile`.

9. **Dual headline scores are never blended.** Experience Score (resume/projects, relevance-weighted) and Subject Knowledge Score are always separate. They are never averaged together.

10. **No MCP or agent framework.** All LLM calls are direct synchronous HTTPS REST calls via `httpx.Client`. No orchestration layer, LangChain, tool-calling protocol, or function-calling is used.
