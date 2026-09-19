# AI-Powered OA & Mock Interview Preparation Platform
## Architecture & Product Specification

---

## 1. Product Overview

The platform prepares candidates for company-specific technical hiring
pipelines through two integrated systems:

**OA (Online Assessment) Preparation** — extracts the topics, subtopics,
and priorities that actually matter for a target company/role from its Job
Description, generates unlimited personalized practice questions at the
candidate's chosen proficiency, and reproduces a realistic, company-specific
Mock OA that every candidate applying to the same role in the same hiring
window receives identically — exactly as a real OA would be administered.

**AI Mock Interview** — parses a candidate's resume against the JD,
interviews them the way a real technical interviewer would: starting with
their most relevant project or work experience, asking situational and
trade-off questions that require reasoning rather than recall, adaptively
going deeper when the candidate is strong and backing off when they are
not, then separately evaluates their fundamental/subject-matter knowledge
(DSA, system design, CN/OS/DBMS/OOPS, ML/AI, SQL, etc.) relevant to the
role. Every score the candidate receives is deterministic, auditable, and
backed by a stored evidence trail — never a generic LLM verdict.

The result is a single platform that turns "practice for company X" from
generic question banks into a reproducible, evidence-grounded, and
adaptive preparation experience.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (React), Tailwind |
| Backend API | FastAPI (Python) |
| Agent orchestration | LangGraph — every agent below is a LangGraph state graph with checkpointed, resumable session state |
| Primary datastore (source of truth) | PostgreSQL |
| Cache / locks / rate limiting / ephemeral state | Redis |
| Large object storage (resumes, transcripts, exports) | S3 / Cloudflare R2 |
| Sandboxed code execution | Judge0 |
| LLM provider | Claude API (Anthropic), abstracted behind an internal `LLMClient` so the model/version can change without touching agent logic |
| Auth | JWT session tokens, standard email/password + OAuth (Google) |
| Realtime interview channel | Server-Sent Events (SSE) or WebSocket per interview session |

---

## 3. High-Level Architecture

```
                        ┌─────────────────────┐
                        │   Next.js Frontend   │
                        └──────────┬───────────┘
                                   │ REST / SSE
                        ┌──────────▼───────────┐
                        │     FastAPI Gateway    │
                        └──────────┬───────────┘
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
   ┌─────────▼────────┐  ┌─────────▼────────┐   ┌──────────▼─────────┐
   │   OA Subsystem     │  │ Interview Subsystem│   │  Shared Engines     │
   │  (LangGraph agents)│  │ (LangGraph agents)│   │ (used by both)      │
   │  1 Role Profile     │  │ Resume/Project     │   │ - Evaluator Registry│
   │  2 Practice Engine   │  │ Subject/Fundamental│   │ - Follow-up FSM      │
   │  3 Mock OA Engine     │  │ Knowledge          │   │ - Scoring Engine     │
   │  4 Review Agent        │  └────────────────┘   │ - Evidence Layer     │
   │  5 Eval + Feedback      │                       └────────────────────┘
   └───────────┬────────┘
               │
   ┌───────────▼────────────────────────────────────────────┐
   │ PostgreSQL (source of truth)  |  Redis (locks/cache)     │
   │ S3/R2 (objects)               |  Judge0 (code execution)  │
   └──────────────────────────────────────────────────────────┘
```

Every agent is implemented as a LangGraph graph invoked by a FastAPI
endpoint. Long-running or multi-turn agents (Practice/Mock OA generation,
both interview agents) persist their graph state as Postgres-backed
checkpoints so a session can be paused/resumed/retried without losing
progress. Redis is used only for short-lived locks (preventing two
concurrent requests from double-generating the same canonical object),
caching hot reads, and rate limiting — it holds no source-of-truth data.

---

## 4. Core Data Model

```
users(id, email, password_hash, name, created_at)

role_topic_profiles(
  id, company, role, job_type, experience_requirement,
  required_skills[], time_window_id,
  subjects_json,        -- nested subjects > topics > subtopics,
                         -- each with importance_score, expected_question_types,
                         -- expected_difficulty_distribution
  evidence_json,        -- provenance: source, trust_level, timestamp per fact
  created_at, refreshed_at
)

time_windows(
  id, company, role, window_length_days, window_start, window_end,
  status  -- ACTIVE | CLOSED
)

question_bank(
  id, subject, topic, subtopic, question_type, difficulty,
  prompt, hint, approach, solution, test_cases_json,
  status,       -- GENERATING | REVIEWING | PUBLISHED | FAILED
  review_report_json,
  question_generator_version
)

practice_sessions(
  id, user_id, practice_generation_key, company, role, time_window_id,
  selected_topics_json, proficiency_vector_json, total_questions,
  allocation_mode, question_bank_level, question_generator_version,
  question_ids[], created_at
)

mock_oa_variants(
  id, company, role, time_window_id, attempt_number,   -- unique on (company, role, time_window_id, attempt_number)
  question_ids[], answer_key_json, status,             -- PUBLISHED | STALE | FAILED
  created_at
)

mock_oa_attempts(
  id, user_id, mock_oa_variant_id, user_attempt_count,
  started_at, submitted_at, answers_json, evaluation_json, score
)

structured_resumes(
  id, user_id, sections_json,   -- Work Exp / Projects / Education / Skills /
                                  -- Achievements / Extracurricular / Certifications / Other
  section_weights_json,
  created_at
)

interview_sessions(
  id, user_id, resume_id, role_topic_profile_id, status,
  agent1_report_json,   -- resume/project interview
  agent2_report_json,   -- subject/fundamental knowledge interview
  final_report_json,
  created_at, completed_at
)

interview_evidence(
  id, session_id, project_id_or_topic, question_id, follow_up_index,
  topic, subtopic, user_answer, expected_concept, detected_gap, severity,
  earned_points, possible_points, evaluator_reason, evidence_ref
)
```

---

## 5. Part A — OA System

### 5.1 Agent 1 — Role Topic Profile Generator

Input: company, role, job type, JD text, (optionally) trusted external
sources (past OA reports, interview experiences, company engineering
blogs).

Output — a single structured `role_topic_profiles` record:

```
{
  company, role, job_type, experience_requirement, required_skills[],
  subjects: [
    {
      subject,
      topics: [
        {
          topic,
          subtopics: [...],
          importance_score,             // 0-1, relative priority
          expected_question_types[],    // MCQ, MSQ, DSA, SQL, System Design...
          expected_difficulty_distribution: { easy, medium, hard }
        }
      ]
    }
  ],
  evidence: [ { fact, source, trust_level, timestamp } ]
}
```

This is the single shared object consumed by the Practice Engine, the Mock
OA Engine, and the Subject/Fundamental Knowledge interview agent — topic
importance is computed once, here, and reused everywhere else.

### 5.2 Agent 2 — Practice Question Engine

**User-facing controls:**
- select subjects / topics / subtopics
- set proficiency per selected topic
- set total question count
- choose allocation mode: `manual` (user sets per-topic counts) or `auto`
  (importance-weighted allocation from the Role Topic Profile)
- alternatively, request a full auto-generated question bank at a single
  chosen overall level
- question difficulty and style scale with the proficiency set for each
  topic

**Determinism.** Practice sets are generated once per unique combination of
inputs and reused thereafter:

```
practice_generation_key = SHA256(
    company, role, time_window_id,
    selected_topics, proficiency_vector,
    total_questions, allocation_mode,
    question_bank_level, question_generator_version
)
```

On request: look up `practice_sessions` by `practice_generation_key`
(unique constraint) — if found, return the existing question set; if not,
acquire a short Redis lock on the key, generate via the Question-Gen Core,
persist, release the lock. This guarantees any two users with identical
inputs receive an identical practice set, and is entirely independent of
the Mock OA key/lifecycle below.

**Per-question features:** Check Answer, Hint (guides toward the approach
without revealing the final answer), Approach, Full Solution (final
answer/code + explanation appropriate to the question type).

### 5.3 Agent 3 — Mock OA Engine

**Time windows.** Each (company, role) has a rolling time window (default
7 days — see §11, configurable per role) tracked in `time_windows`. All
Mock OA generation for that company/role is scoped to the active window.

**Attempt numbering.** Two counters exist:
- `user_attempt_count` — private, per user: how many times this user has
  taken the OA for this company/role/time_window.
- `attempt_number` — the canonical OA sequence/variant identifier used as
  the generation key.

`attempt_number` is set equal to the requesting user's current
`user_attempt_count + 1` at request time, and is used directly as the
lookup/generation key:

```
mock_oa_key = (company, role, time_window_id, attempt_number)
```

Whenever two different users reach the same `attempt_number` for the same
(company, role, time_window), they are served the identical canonical
`mock_oa_variants` row — Mock OA content never depends on user
proficiency, profile, or practice history, only on company/role/
time-window evidence and the OA configuration.

**Generation flow:** on request, look up `mock_oa_variants` by
`mock_oa_key` (unique constraint). If PUBLISHED, serve it. If absent,
acquire a Redis lock on the key, run the generation graph (question
selection + answer key + optimal approach/solution), pass through Agent 4
review, mark PUBLISHED, release the lock. Concurrent requests for the same
key wait on the lock and then read the now-published row (no duplicate
generation).

**Window refresh.** When a time window closes:
- new company/role evidence may be collected from trusted sources
- the Role Topic Profile is refreshed
- new Mock OA variants may be generated under the new window's canonical
  generation context
- practice-question generation may receive minor updates from the same
  new evidence
- all `mock_oa_variants` rows from the closed window move to `STALE`
  (never deleted) so any user mid-attempt can still complete it

### 5.4 Agent 4 — Review & Validation

Lifecycle: `GENERATING → REVIEWING → PUBLISHED | FAILED`. A question is
approved only once it passes every check:

1. Question correctness
2. Answer-key correctness
3. Hint correctness
4. Approach correctness
5. Solution correctness
6. Explanation correctness
7. Difficulty correctness
8. Subject/topic/subtopic classification correctness
9. JD/role relevance
10. Ambiguity detection
11. Duplicate-question detection
12. Hidden-answer leakage detection
13. Adequacy of test cases
14. Code compilation validity
15. SQL correctness
16. Expected complexity correctness
17. Formatting/rendering validity
18. Detection of missing information required to solve the question

Failures route back to regeneration with the failure reason attached;
persistent failures mark the item `FAILED` and exclude it from the bank.

### 5.5 Agent 5 — Evaluation & Feedback

**Evaluator Registry** — the evaluation strategy is selected from question
metadata, never left to free-form LLM judgment:

| Question type | Evaluation method |
|---|---|
| MCQ | Exact answer comparison |
| MSQ | Exact selected-set comparison |
| DSA / Coding | Compilation, visible + hidden test cases, edge cases, time/memory limits, runtime, complexity analysis (Judge0) |
| SQL | Execute against a controlled seeded database; compare result sets; fixtures for NULL, empty, duplicate, boundary cases |
| Debugging / code-fixing | Compile + execute against expected behavioral test cases |
| System Design / CN / OS / OOPS / DBMS / ML / AI / LLM / RAG | Structured rubric-based evaluation |

**Feedback** is generated only from actual attempt evidence: time spent
per question, topic/subtopic, correctness, test cases passed, difficulty,
question type, resulting strong/weak topics, accuracy, efficiency where
measurable, and overall score.

---

## 6. Part B — Interview System

### 6.1 Structured Resume Object

Parsed from the uploaded resume into sections: Work Experience, Projects,
Education, Skills, Achievements, Extracurricular Activities,
Certifications, Other. Each Work Experience / Project entry additionally
stores:

- overall relevance to the JD/role
- relevant topics[] and irrelevant topics[]
- topic-level relevance scores
- questioning priority
- relevant technologies/skills

### 6.2 Interview Agent 1 — Resume / Project Interview

**Ordering.** All Work Experience and Project entries are ranked by
overall relevance; the interview proceeds from most to least relevant.
Entries wholly irrelevant to the role are skipped. For each entry: the
candidate is first asked for a brief description, then technical/
situational questions targeting only its relevant topics — a project with
topics A (low relevance), B (very high), C (irrelevant) is questioned
mostly on B, lightly on A, and not on C.

**Situational questioning.** Every question and follow-up is designed to
require reasoning rather than recall: why this technology was chosen, what
would happen if a component failed, what if scale increased significantly,
what would be replaced and why, what bottleneck would appear first, what
trade-off the design made, what would change on a rebuild, what
additional feature would be added and why.

**Adaptive follow-up state machine** (shared with Agent 2, §6.3):

```
Question → Evaluate Answer →
  Excellent → deeper follow-up
  Good      → follow-up
  Average   → limited follow-up
  Weak      → shallow follow-up or stop
  Incorrect → stop / move to another area
```

Maximum follow-up depth per thread: 5 (configurable 3–6). A weak/incorrect
answer at any depth stops further descent into that thread; a strong
answer continues until either the depth cap or sufficient topic coverage
is reached.

**Scoring engine** (deterministic, backend-computed — the LLM supplies
only the qualitative `answer_quality` band):

```
correct_possible(L)   = 5 + 3*(L - 1)              // grows with depth
incorrect_possible(L) = max(2, 10 - 2*(L - 1))     // shrinks with depth
midpoint(L)           = (correct_possible(L) + incorrect_possible(L)) / 2

quality band → fraction earned, possible-points curve used:
  Excellent   → 0.90 × correct_possible(L)
  Good        → 0.70 × correct_possible(L)
  Average     → 0.50 × midpoint(L)
  Weak        → 0.30 × incorrect_possible(L)
  Incorrect   → 0.00 × incorrect_possible(L)
```

`possible_points` for a question/follow-up is the curve value used above;
`earned_points` is the fraction of it earned. This makes a wrong answer on
a shallow, easy question contribute a large possible-points penalty (large
denominator, near-zero numerator), while a wrong answer on a deep, hard
follow-up contributes only a small possible-points penalty — and
symmetrically rewards a correct deep answer far more than a correct
shallow one.

```
project_score = SUM(earned_points) / SUM(possible_points) × 100
```

Each question/follow-up additionally stores `difficulty`, `relevance`,
`depth_level`, `topic`, `subtopic` for reporting.

**5-star rating:**

```
star_rating = project_score / 20     // fractional, not rounded
```

**Evidence record**, one per evaluated question/follow-up:

```
answer_evidence {
  session_id, project_id_or_work_experience_id, question_id,
  follow_up_index, topic, subtopic, user_answer, expected_concept,
  detected_gap, severity, earned_points, possible_points,
  evaluator_reason, evidence_ref
}
```

**Weighted Resume-Related Interview Score:**

```
resume_related_score =
  SUM(item_score × item_relevance_weight) / SUM(item_relevance_weight)
```
across all evaluated projects, work-experience items, and weighted resume
sections (§6.4).

### 6.3 Interview Agent 2 — Subject / Fundamental Knowledge Interview

Produces an independent /100 score for technical/fundamental knowledge —
DSA, code optimization, debugging, system design, CN, OS, OOPS, DBMS,
ML/AI/LLM/RAG, SQL, software design — kept separate from project defense.

- Relevant subjects/topics/subtopics are derived jointly from the JD and
  resume, using the same relevance/priority logic as the Role Topic
  Profile (§5.1); topics irrelevant to the role/JD/resume are never asked.
- Question types depend on role/topic: conceptual, DSA, code optimization,
  debugging, system design, SQL, situational, architecture/trade-off.
- Evaluation reuses the Evaluator Registry (§5.5) per question type: DSA
  via Judge0 (tests/complexity/optimality), SQL via controlled seeded-DB
  result-set comparison, debugging via fix correctness + root-cause
  explanation, design/theory subjects via structured rubric.
- Depth/follow-up behavior reuses the adaptive follow-up state machine
  (§6.2): strong answers go deeper on the same topic; weak/incorrect
  answers stop deepening and the agent moves to another relevant topic.
- Scoring reuses the same engine and evidence schema (§6.2):

```
subject_knowledge_score = SUM(earned_points) / SUM(possible_points) × 100
```
with a subject-wise/topic-wise breakdown of strong / weak / partially-
understood / insufficiently-tested topics.

### 6.4 Resume Section Weighting

Default weights (configurable per role family via admin config):

| Section | Weight |
|---|---|
| Work Experience | 30% |
| Projects | 30% |
| Skills | 15% |
| Education | 10% |
| Certifications | 5% |
| Achievements | 5% |
| Extracurricular | 5% |
| Other | 0% |

### 6.5 Final Interview Report

Two headline scores are shown separately and never averaged into one
number:

- **Resume Related Interview Score /100** (§6.2)
- **Subject/Fundamental Knowledge Score /100** (§6.3)

The combined report includes: both scores, section-wise scores,
project/work-experience scores with 5-star ratings and relevance notes,
subject/topic strong/weak/partial/untested breakdown, specific questions
where the candidate performed well or poorly (pulled from evidence
records), follow-up performance, technical reasoning quality, and an
evidence-grounded strengths/weaknesses/improvement-areas summary. Every
claim in the report is traceable to a stored `interview_evidence` row.

---

## 7. Shared Engines (used by both OA and Interview subsystems)

- **Relevance/priority ranking** — Role Topic Profile (§5.1) and
  resume/topic relevance (§6.1) both compute importance the same way.
- **Evaluator Registry** (§5.5) — used by OA grading and by Interview
  Agent 2's technical questions.
- **Adaptive follow-up state machine** (§6.2) — used by both interview
  agents.
- **Deterministic scoring engine** (§6.2) — used by both interview
  agents' scores.
- **Evidence/provenance layer** — backs Role Topic Profile provenance, OA
  feedback, and interview evidence records alike.

---

## 8. API Surface

```
POST   /api/auth/signup
POST   /api/auth/login

POST   /api/role-profiles                  { company, role, job_type, jd_text }
GET    /api/role-profiles/{id}

POST   /api/practice/sessions              { role_profile_id, selected_topics,
                                              proficiency_vector, total_questions,
                                              allocation_mode, question_bank_level }
GET    /api/practice/sessions/{id}
POST   /api/practice/questions/{id}/check-answer
GET    /api/practice/questions/{id}/hint
GET    /api/practice/questions/{id}/approach
GET    /api/practice/questions/{id}/solution

POST   /api/mock-oa/start                  { company, role }
POST   /api/mock-oa/attempts/{id}/submit
GET    /api/mock-oa/attempts/{id}/report

POST   /api/interview/sessions             { resume_file, company, role, job_type }
POST   /api/interview/sessions/{id}/start
POST   /api/interview/sessions/{id}/answer { current_question_id, answer }
GET    /api/interview/sessions/{id}/report
```

Internal/admin:

```
GET    /api/admin/review-queue
POST   /api/admin/review-queue/{id}/approve
POST   /api/admin/review-queue/{id}/reject
```

---

## 9. Frontend Pages & User Flows

1. **Landing page** — product pitch, sign up / log in.
2. **Dashboard** — company/role selector, recent sessions, scores over time.
3. **JD Intake** — paste/upload JD → triggers Role Topic Profile
   generation → displays ranked subjects/topics with importance.
4. **Practice Configurator** — topic/subtopic multiselect, per-topic
   proficiency sliders, total question count, allocation mode toggle,
   "generate full bank" option with level selector.
5. **Practice Runner** — one question at a time or list view; Check
   Answer / Hint / Approach / Solution controls per question.
6. **Mock OA Runner** — timed, exam-style UI; no hints/solutions visible
   during the attempt; auto-submits at time limit.
7. **OA Report** — score, per-topic breakdown, time-per-question,
   strong/weak topics, review of each question with the answer key.
8. **Interview Intake** — resume upload + JD paste/company-role selection.
9. **Interview Session (chat-style)** — one question/follow-up at a time,
   candidate types (or speaks, if voice is added later) their answer,
   next prompt streamed in via SSE/WebSocket.
10. **Interview Final Report** — Resume-Related Score and
    Subject/Fundamental Score shown side by side, per-project 5-star
    cards with relevance notes, topic strength breakdown, and specific
    evidence-backed strengths/weaknesses.

---

## 10. Non-Functional Requirements

- **Determinism.** Practice sets and Mock OA variants are generated
  exactly once per unique key and reused thereafter; regeneration only
  occurs on window refresh or explicit generator-version bump.
- **Concurrency safety.** Postgres uniqueness constraints on
  `practice_generation_key` and `(company, role, time_window_id,
  attempt_number)` are the correctness mechanism; Redis locks are a
  performance optimization on top, not the source of truth.
- **Idempotent generation.** Any generation request that races against an
  in-flight or already-completed generation for the same key returns the
  existing result rather than producing a duplicate.
- **Auditability.** Every score (OA or interview) must be reconstructable
  from stored evidence rows; no score is accepted directly from an LLM's
  free-form output.
- **Trust boundaries.** External evidence sources feeding the Role Topic
  Profile are tagged with a trust level and provenance; low-trust sources
  are weighted down or excluded from question generation.
- **Session resumability.** All multi-turn agent graphs (practice/mock OA
  generation, both interview agents) checkpoint to Postgres so a session
  can be resumed after a disconnect without losing state.

---

## 11. Configuration Defaults

| Setting | Default | Notes |
|---|---|---|
| Time window length | 7 days | Configurable per company/role |
| Max follow-up depth | 5 | Configurable 3–6 per interview type |
| Resume section weights | See §6.4 | Configurable per role family |
| `question_generator_version` | Integer, starts at 1 | Bumped whenever the generation prompt template, model, or generation logic changes in a way that could alter output; stored on every generated item and folded into `practice_generation_key` |

---

## 12. Deployment Topology

- Frontend: static/SSR Next.js deployment (Vercel or containerized).
- Backend: containerized FastAPI services behind a load balancer,
  horizontally scalable (stateless — all state in Postgres/Redis).
- LangGraph agent workers: same FastAPI containers or separate worker
  pool, checkpointing to Postgres.
- PostgreSQL: managed instance, primary + read replica for reporting
  queries.
- Redis: managed instance, locks/cache/rate-limit only.
- Judge0: isolated sandbox cluster, network-restricted, no outbound
  access from executed code.
- S3/R2: resume uploads, generated PDFs/exports, transcript archives.


---

## 13. Deep-Dive: Adaptive Interview & Semantic Evaluation Architecture

To ensure any AI agent or developer can fully understand the runtime behavior of the Interview Subsystem, the following details the exact execution pipeline for a single interview turn.

### 13.1 LLM Fallback Client (`LLMClient`)
The system abstracts all AI calls behind `LLMClient`. It employs a highly robust fallback waterfall to bypass strict rate limits (like Groq's 1000 OTPM limit):
1. **Groq (Primary)**: Attempts ultra-fast inference using models like `llama3-70b-8192` or `qwen-2.5`. Catches `429 Rate Limit` errors.
2. **Gemini (Fallback)**: If Groq hits a rate limit or goes down, instantly falls back to `gemini-flash-latest` via Google's API, handling its safety filters and `503 Unavailable` demand spikes gracefully.

### 13.2 The Resume Ingestion & Claim Storage
1. `ResumeParser` extracts text into a `StructuredResume`.
2. An LLM passes over the text, breaking it into discrete **Contextual Resume Claims** (e.g., "Candidate used React for E-commerce project").
3. These are saved in the `InterviewState` under `state.claims` — a dual-layer store that keeps pre-verified resume claims separate from live candidate assertions.

### 13.3 The Evaluation Engine (`AnswerEvaluator`)
When the candidate answers, the `AnswerEvaluator` injects the Question Profile, Interview History, and candidate text into a massive LLM prompt. 
**Crucially, the LLM DOES NOT CALCULATE MARKS.** It acts strictly as a semantic extractor, outputting a JSON schema (`SemanticEvaluationResult`) with:
*   `candidate_claims`: Technical assertions made in the answer.
*   **8 Dimension Parameters [0.0 - 1.0]**: 
    - `correctness_validity` (Technical truth, 100% credit for 'Technically Valid Alternatives' differing from expectation)
    - `objective_coverage` (Did they answer the core question?)
    - `completeness` (Were edge cases covered?)
    - `reasoning_quality` (Architectural thinking)
    - `depth_demonstrated` 
    - `specificity`
    - `ownership`
    - `directness`
*   `is_non_answer`: Boolean flag triggered if the user deflects (e.g., "idk") or jokes.

### 13.4 The Consistency Engine (`ConsistencyEngine`)
Before scoring, the engine cross-references the newly extracted `candidate_claims` against the stored resume claims in `InterviewState`.
It checks three dimensions:
*   **Project Context**: Correct project attribution?
*   **Component Context**: Correct tech stack?
*   **Role Context**: Appropriate complexity for the claimed role?
If an explicit contradiction is found (e.g., claiming Python backend experience when the resume explicitly lists Node.js), it sets a `clarification_needed` flag and records a contradiction in the state.

### 13.5 The Deterministic Scoring Engine (`ScoringPolicy`)
The Python backend takes the semantic decimals [0.0-1.0] and runs a hardcoded mathematical weighted average:
*   Correctness/Validity: 30%
*   Objective Coverage: 20%
*   Completeness: 15%
*   Reasoning Quality: 10%
*   Depth Demonstrated: 10%
*   Specificity: 5%
*   Ownership: 5%
*   Directness: 5%

*(If `is_non_answer` is true, this math is bypassed and the score is forced to 0.0)*

### 13.6 The Adaptive Planner (`AdaptivePlanner`)
Based on the computed score and consistency flags, the planner triggers a state machine action:
*   **DRILL_DOWN**: (Score > 70%) Asks a harder follow-up question on the exact same topic to find the candidate's ceiling.
*   **PIVOT**: (Score < 70% or Evasive) Abandons the current topic and moves to a different project or fundamental area.
*   **CLARIFY_CONTRADICTION**: If the `ConsistencyEngine` flagged a discrepancy, the planner forces a gentle confrontational question (e.g., "Your resume mentions Node.js, but you just mentioned Python. Can you clarify?").

This continuous loop guarantees that every score is deterministic, auditable via the semantic JSON parameters, and immune to standard LLM mathematical hallucinations.
