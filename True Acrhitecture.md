# True Architecture — Intervyn AI Platform

> **Source of Truth:** This document is built strictly by reading the live, deployed codebase from the GitHub repository (`main` branch).
> **No hallucinations, no memory shortcuts.** Every component listed here maps exactly to a `.py`, `.ts`, or configuration file in the project.

---

## 1. System Overview & Invariants

Intervyn is a dual-purpose platform:
1. **Mock Online Assessment (OA) / Practice Engine:** Timed, sandboxed code execution and MCQ evaluation.
2. **AI-Driven Voice/Text Technical Interviewer:** A multi-turn, adaptive engine that grounds questions in the candidate's actual resume and evaluates answers deterministically.

### Hard Architectural Truths
*   **Database:** SQLite (`intervyn.db`) for local, PostgreSQL (via Supabase) for production.
*   **No Redis / No Message Queues:** The system does NOT use Redis for caching, locks, or databases. (The word "Redis" only appears in the code as a string to correct speech-to-text typos like *"read is"* -> *"Redis"*, and in dummy database seed strings).
*   **No LangChain / No Agent Frameworks:** All LLM interactions are raw HTTPS REST calls via the standard Python `httpx` library to Google (Gemini), Groq, or OpenAI.
*   **Deterministic Math, Not LLM Points:** The LLM never assigns a numeric score. The LLM only evaluates 3 semantic dimensions (validity, completeness, communication) on a `[0,1]` scale. All final weights, math, and severity classifications are executed in pure Python (`scoring_policy.py`).

---

## 2. Infrastructure & Tech Stack

**Backend (Python 3.11.9):**
*   `fastapi` (>=0.110.0) / `uvicorn[standard]` (>=0.28.0)
*   `sqlalchemy` (>=2.0.0) + `psycopg2-binary` (PostgreSQL driver)
*   `pydantic` (v2) / `pydantic-settings`
*   `httpx` (Synchronous HTTP requests to LLM APIs)
*   `pymupdf` (PDF extraction) + `beautifulsoup4` (HTML parsing)
*   `pyjwt` (JSON Web Tokens for auth)

**Frontend (React 18 / TypeScript):**
*   `vite` (Bundler)
*   `tailwindcss` (Styling)
*   `@monaco-editor/react` (Code editor for OA)
*   `lucide-react` (Icons)

**Deployment (`render.yaml` & `vercel.json`):**
*   Backend is deployed on Render as a Web Service. Entry point: `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
*   Frontend is deployed as a Single Page Application (SPA) on Vercel with all routes rewriting to `index.html`.

---

## 3. Database Schema (SQLAlchemy ORM)

Located in `backend/app/models/models.py`. The tables are generated dynamically via `Base.metadata.create_all()` on application startup.

1.  **`users`**: `id`, `email`, `password_hash`, `name`, `google_id`, `avatar_url`.
2.  **`time_windows`**: Restricts OA access. `company`, `role`, `window_start`, `window_end`, `status`.
3.  **`role_topic_profiles`**: The knowledge requirements. `job_type`, `experience_requirement`, `required_skills`, `subjects_json`, `evidence_json`.
4.  **`question_bank`**: Stores verified questions. `question_type` (MCQ, DSA, SQL, etc.), `difficulty`, `prompt`, `options_json`, `test_cases_json`, `starter_code`, `status` (PUBLISHED/REVIEWING/etc).
5.  **`practice_sessions`**: Tracks non-OA practice. `selected_topics_json`, `allocation_mode`, `user_answers_json`.
6.  **`mock_oa_variants`**: A specific generated test. `question_ids`, `duration_minutes`, `answer_key_json`.
7.  **`mock_oa_attempts`**: A candidate's OA run. `started_at`, `submitted_at`, `answers_json`, `score`.
8.  **`structured_resumes`**: Output of the parser. `raw_text`, `sections_json` (Work Exp, Projects, etc.), `section_weights_json`.
9.  **`interview_sessions`**: The live interview state. `status`, `current_phase`, `current_depth`, `transcript_json`, `agent1_report_json` (Experience phase), `agent2_report_json` (Subject phase), `final_report_json`.
10. **`interview_evidence`**: The turn-by-turn audit trail. `user_answer`, `expected_concept`, `detected_gap`, `severity`, `earned_points`, `possible_points`, `evaluator_reason`.

---

## 4. LLM API Key Management & Rotation

Located in `backend/app/llm/key_pool.py` and `client.py`.

*   **Pool Loading:** Automatically scans `.env` for keys ending in `_1` through `_14` (e.g., `GEMINI_API_KEY_1`, `GROQ_API_KEY_5`).
*   **Rotation Strategy:** Keys are randomly shuffled at initialization. The system iterates round-robin.
*   **Priority:** `gemini-flash-latest` is strictly preferred. If Gemini keys hit limits, it falls back to Groq (`llama-3.3-70b-versatile`).
*   **Rate Limits:** Enforces 14 Req/Min and 480 Req/Day for Gemini; 28 Req/Min for Groq.
*   **Cooldowns:** HTTP 429 (Too Many Requests), 401, or 404 trigger a strict **30-second cooldown** on the offending key before it can be retried. The engine retries up to 4 times with exponential backoff (`2^attempt + random(0.5, 1.5)`).

---

## 5. Live Interview Engine (The Core Loop)

Orchestrated entirely by `InterviewAgent` (`backend/app/agents/interview_agent.py`).

### Phase 1: Initialization (`start_session`)
1. Fetches the `StructuredResume` and `RoleTopicProfile`.
2. Calls `_build_interview_agenda()` to sequence topics:
   *   All Work Experience (chronological order)
   *   All Projects (sorted by `overall_relevance` descending)
   *   Subject Knowledge (from role profile)
3. Seeds the `InterviewState` setting all resume claims to `UNEXPLORED`.
4. Dispatches the opening question.

### Phase 2: Processing the Answer (`process_answer`)
When the candidate submits a voice/text answer, the engine executes a strict synchronous pipeline:

1.  **Transcript Normalization:** Replaces acoustic speech-to-text typos via 80+ regex rules in `transcript_normalizer.py`. (e.g., *"read is"* -> *"Redis"*, *"cue bernetties"* -> *"Kubernetes"*).
2.  **Semantic Evaluation:** `AnswerEvaluator` passes the normalized text to the LLM. The LLM extracts:
    *   `technical_validity` [0.0 - 1.0]
    *   `completeness` [0.0 - 1.0]
    *   `communication` [0.0 - 1.0]
    *   `is_non_answer` (bool - true if candidate dodges the question or says "I don't know")
3.  **Contradiction Checking:** `ConsistencyEngine` compares extracted entities against the history across 6 dimensions (role, time, scope, component, specificity). If a contradiction is found, it creates a `DiscrepancyRecord`.
4.  **State Update:** Updates the `InterviewState` (memory graph). Contradicted claims have their scores temporarily revoked.
5.  **Deterministic Scoring:** `ScoringPolicy.calculate_turn_score()` computes points mathematically (details in section 6).
6.  **Evidence Logging:** Writes the outcome directly to the `interview_evidence` DB table.
7.  **Adaptive Planning:** `AdaptivePlanner` decides the very next move.
8.  **Question Generation:** `QuestionGenerator` builds the specific prompt to ask based on the planner's decision.

### The 21 Adaptive Planner Actions
Located in `adaptive_planner.py`. The system forces a pivot when a topic hits a depth of 7 turns (`MAX_DEPTH`).

*   **Resolutions:** `CLARIFY_CONTRADICTION`, `VERIFY_UNSUPPORTED_CLAIM`
*   **Exploration:** `EXPLORE_RESUME_TOPIC`, `EXPLORE_CANDIDATE_TOPIC`, `DEEPEN_CURRENT_TOPIC`
*   **Stress Testing (Cognitive Probes):** `TEST_IMPLEMENTATION`, `TEST_REASONING`, `TEST_TRADEOFF`, `TEST_PERFORMANCE`, `TEST_SCALE`, `TEST_RELIABILITY`, `TEST_FAILURE`, `TEST_SECURITY`, `TEST_CONCURRENCY`, `TEST_CONSISTENCY`, `TEST_ARCHITECTURE`, `TEST_OPERATIONS`, `TEST_DEBUGGING`
*   **Navigation:** `PIVOT_ITEM`, `START_NEXT_ITEM`

---

## 6. The Deterministic Math (Scoring System)

Located in `backend/app/engines/scoring_policy.py`.

**1. Evidence Base (`E_i`)**
```python
if is_non_answer:
    E_i = 0.0
else:
    E_i = (technical_validity * 0.50) + (completeness * 0.30) + (communication * 0.20)
```

**2. Question Complexity (`C`)**
Computed using the `QuestionProfile` dimensions assigned to the question when it was generated.
```python
C = (cognitive_complexity * 0.35) + (technical_complexity * 0.35) + (reasoning_requirement * 0.30)
```

**3. Asymmetry Factor (`A`)**
Defines how much to reward/punish based on question difficulty (`D`).
```python
A = (D * E_i) + ((1 - D) * (1 - E_i))
```
*   *Hard Q + Wrong Answer (E_i=0) -> A=0 (Candidate is protected)*
*   *Easy Q + Wrong Answer (E_i=0) -> A=1 (Maximum penalty)*

**4. Possible Points / Weight (`W_i`)**
```python
W_i = 1.0 + 9.0 * (0.65 * A + 0.35 * C)
# Clamped strictly between 1.0 and 10.0
```

**5. Earned Points (`M_i`)**
```python
M_i = W_i * E_i
```

**6. Severity Tiers**
Assigned to the `InterviewEvidence` row for the final report based on `E_i`:
*   `E_i < 0.25`: **SEVERE** (0 points earned, full weight retained)
*   `E_i < 0.50`: **MODERATE**
*   `E_i < 0.75`: **MINOR**
*   `E_i >= 0.75`: **NONE** (Demonstrated strength)

**7. Final Dual-Headline Scores**
The system computes an **Experience Score** (averaging weights of resume/projects) and a **Subject Knowledge Score**. These two are *never* blended together.

---

## 7. Security Sandbox for OA (`sandbox_runner.py`)

Executes code submissions for Data Structures & Algorithms and SQL.
It runs as an OS subprocess with strict timeouts and lexical blocks.

*   **Wall-clock Timeout:** 4.0 seconds (hard kill).
*   **Languages:** Python 3, C, C++ (17/20/23), Java, JavaScript (Node.js), TypeScript, Go, Rust, C#.
*   **Python Restrictions (AST scanning):** Rejects any code containing `os`, `sys`, `subprocess`, `socket`, `eval`, `exec`, `open`, `__import__`, or accessing `__class__`, `__subclasses__`.
*   **C/C++/Java Restrictions (Regex):** Rejects `system()`, `popen()`, `fork()`, `Runtime.exec()`, `ProcessBuilder`.

---

## 8. Frontend Deep Dive (Vite / React)

### Components (9)
`AuthModal`, `CandidateSetupModal`, `CodeEditor` (Monaco wrapper), `DepthMeter`, `DocumentUploadInput`, `Navbar`, `ProctoringBadge`, `StarRating`, `Timer`.

### Pages (11)
*   `LandingPage`
*   `DashboardPage`
*   `JDIntakePage`
*   `InterviewIntakePage`
*   `LiveInterviewPage` (Streams audio/text back and forth)
*   `InterviewReportPage`
*   `PracticeConfigPage`
*   `PracticeRunnerPage`
*   `MockOARunnerPage` (Largest frontend file)
*   `OAReportPage`
*   `AdminReviewPage`

### Proctoring Hook (`useProctoring.ts`)
Tracks test integrity silently during OAs and Interviews.
Monitors:
*   `visibilitychange` (Tab switching)
*   `window.blur` (Window losing focus)
*   `fullscreenchange` (Exiting full screen)
*   Rapid Paste Bursts
*   Total time spent away from tab

---

## 9. Code Quality & Testing

Located in `backend/tests/`. The platform runs a rigorous test suite of 15 files.
Key files include:
*   `test_behavioral_invariants_40.py` - Enforces 40 hardcoded constraints (e.g., ensuring `E_i=0` when `is_non_answer` is True, verifying math boundaries, proving that empty resume fields don't cause crashes).
*   `test_scoring_policy.py` - Mathematically proves the asymmetry factor.
*   `test_consistency_engine.py` - Verifies the contradiction detection logic over the 6 contextual dimensions.
*   `test_system.py` - A standalone CLI integration test that bypasses the FastAPI layer entirely to test end-to-end LLM flow.
