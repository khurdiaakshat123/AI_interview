from __future__ import annotations
import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Tuple, List

# Automatically load from backend/.env or root .env
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)
load_dotenv()

class LLMClient:
    """
    Unified LLM Client for Intervyn AI Agents.
    Supports Google Gemini, Groq, OpenAI, and Anthropic Claude via high-speed REST APIs.
    Falls back gracefully to the Domain Expert Engine when no external key is configured.
    """
    def __init__(self):
        self.reload_keys()

    def reload_keys(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    def update_keys(self, keys: Dict[str, str], persist: bool = True):
        if "gemini_key" in keys and keys["gemini_key"]:
            self.gemini_key = keys["gemini_key"].strip()
            os.environ["GEMINI_API_KEY"] = self.gemini_key
        if "groq_key" in keys and keys["groq_key"]:
            self.groq_key = keys["groq_key"].strip()
            os.environ["GROQ_API_KEY"] = self.groq_key
        if "openai_key" in keys and keys["openai_key"]:
            self.openai_key = keys["openai_key"].strip()
            os.environ["OPENAI_API_KEY"] = self.openai_key
        if "anthropic_key" in keys and keys["anthropic_key"]:
            self.anthropic_key = keys["anthropic_key"].strip()
            os.environ["ANTHROPIC_API_KEY"] = self.anthropic_key

        if persist:
            self._save_to_env()

    def _save_to_env(self):
        try:
            target_env = Path(__file__).resolve().parent.parent.parent / ".env"
            lines = []
            if target_env.exists():
                with open(target_env, "r", encoding="utf-8") as f:
                    for line in f:
                        key_name = line.split("=")[0].strip() if "=" in line else ""
                        if key_name not in ["GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
                            lines.append(line.rstrip())

            if self.gemini_key:
                lines.append(f"GEMINI_API_KEY={self.gemini_key}")
            if self.groq_key:
                lines.append(f"GROQ_API_KEY={self.groq_key}")
            if self.openai_key:
                lines.append(f"OPENAI_API_KEY={self.openai_key}")
            if self.anthropic_key:
                lines.append(f"ANTHROPIC_API_KEY={self.anthropic_key}")

            with open(target_env, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception as e:
            print(f"[LLMClient] Failed to persist keys to .env: {e}")

    def get_active_provider(self) -> str:
        if self.groq_key:
            return "Groq (llama-3.3-70b-versatile)"
        if self.gemini_key:
            return "Google Gemini (gemini-flash-latest)"
        if self.openai_key:
            return "OpenAI (gpt-4o-mini)"
        if self.anthropic_key:
            return "Anthropic Claude (claude-3-5-sonnet)"
        return "Intervyn Domain Expert Engine (Local Deterministic)"

    def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Optional[str]:
        import time
        for attempt in range(3):
            # 1. Groq (REST - Ultra-Fast LLaMA 3.3/3.1)
            if self.groq_key:
                for g_model in ["gemma2-9b-it", "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-8b-8192", "mixtral-8x7b-32768"]:
                    try:
                        headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
                        payload = {
                            "model": g_model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": temperature
                        }
                        with httpx.Client(timeout=15.0) as client:
                            resp = client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                            if resp.status_code == 200:
                                return resp.json()["choices"][0]["message"]["content"]
                            else:
                                print(f"[LLMClient] Groq {g_model} HTTP {resp.status_code}: {resp.text}")
                    except Exception as e:
                        print(f"[LLMClient] Groq call ({g_model}) failed or timed out: {e}")

            # 2. Google Gemini (REST - gemini-flash-latest with fallback)
            if self.gemini_key:
                # In 2026, older models like 1.5-flash return 404. Google counts 404s against the 20 RPM free tier quota!
                # If we put them first, we exhaust the user's quota before even hitting a valid model.
                # 'gemini-flash-latest' always resolves to the current valid model, so we put it FIRST.
                for gmodel in ["gemini-flash-latest"]:
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gmodel}:generateContent?key={self.gemini_key}"
                        payload = {
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": [{"text": f"System Instructions:\n{system_prompt}\n\nTask:\n{user_prompt}"}]
                                }
                            ],
                            "generationConfig": {"temperature": temperature}
                        }
                        with httpx.Client(timeout=15.0) as client:
                            resp = client.post(url, json=payload)
                            if resp.status_code == 200:
                                data = resp.json()
                                if "candidates" in data and data["candidates"]:
                                    return data["candidates"][0]["content"]["parts"][0]["text"]
                            elif resp.status_code == 429:
                                print(f"[LLMClient] Gemini Rate Limit 429 on {gmodel}. Backing off to prevent spam.")
                                import time
                                time.sleep(3) # Slow down to prevent 18x spam
                                break # Stop looping models this attempt
                            else:
                                print(f"[LLMClient] Gemini {gmodel} HTTP {resp.status_code}: {resp.text}")
                    except Exception as e:
                        print(f"[LLMClient] Gemini call ({gmodel}) failed: {e}")

            # 3. OpenAI (REST - GPT-4o-mini)
            if self.openai_key:
                try:
                    headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": temperature
                    }
                    with httpx.Client(timeout=25.0) as client:
                        resp = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                        if resp.status_code == 200:
                            return resp.json()["choices"][0]["message"]["content"]
                        else:
                            print(f"[LLMClient] OpenAI HTTP {resp.status_code}: {resp.text}")
                except Exception as e:
                    print(f"[LLMClient] OpenAI call failed: {e}")

            # 4. Anthropic Claude (REST)
            if self.anthropic_key:
                try:
                    headers = {
                        "x-api-key": self.anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    }
                    payload = {
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 1024,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_prompt}],
                        "temperature": temperature
                    }
                    with httpx.Client(timeout=25.0) as client:
                        resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                        if resp.status_code == 200:
                            return resp.json()["content"][0]["text"]
                        else:
                            print(f"[LLMClient] Anthropic HTTP {resp.status_code}: {resp.text}")
                except Exception as e:
                    print(f"[LLMClient] Anthropic call failed: {e}")

            print(f"[LLMClient] Attempt {attempt + 1}/3 failed across all providers. Retrying in 1s...")
            time.sleep(1)
        return None

    def evaluate_candidate_answer(
        self,
        question_text: str,
        topic: str,
        candidate_answer: str,
        depth: int = 1,
        role: str = "Software Engineer",
        company: str = "Target Company",
        project_context: str = "",
        phase: str = "PROJECT_DEFENSE",
        is_clarification_attempt: bool = False,
        missing_specs_context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Uses live LLM to evaluate the candidate's technical response with sound engineering sense.
        Reconstructs speech-to-text / typo intent so candidates are evaluated fairly.
        Detects missing specifications to allow a 2nd-go precision clarification before finalizing deductions.
        """
        clarification_directive = ""
        if is_clarification_attempt:
            clarification_directive = (
                f"\n--- 2ND-GO SPECIFICATION ATTEMPT DIRECTIVE ---\n"
                f"The candidate was explicitly asked to provide missing technical specifications: '{missing_specs_context}'.\n"
                f"1. If the candidate now provided the expected technical details, architecture, or choices:\n"
                f"   * Award a strong, fair grade (quality_band = 'Good' or 'Excellent', score_percentage = 82 to 95).\n"
                f"   * Minute penalty will be handled programmatically. Do NOT heavily penalize them for needing the prompt.\n"
                f"   * set needs_specification_clarification = false\n"
                f"2. If the candidate STILL answers badly, dodges, or gives no concrete specifications after being explicitly asked:\n"
                f"   * Award a very low score with high weightage (quality_band = 'Incorrect' or 'Weak', score_percentage = 0 to 20, "
                f"suggested_possible_points = 10.0 to 12.0, suggested_earned_points = 0.0).\n"
                f"   * set needs_specification_clarification = false\n"
            )
        else:
            clarification_directive = (
                "\n--- 1ST-GO SPECIFICATION CLARIFICATION DETECTION RULES ---\n"
                "Trigger a 2nd-go clarification (needs_specification_clarification = true) ONLY IF ALL THREE CONDITIONS ARE SATISFIED:\n"
                "1. RELEVANT: The candidate's response is directly relevant and on-topic to the specific question asked or resume project.\n"
                "2. SENSIBLE ATTEMPT: The candidate showed genuine comprehension and gave a coherent, sensible answer with basic technical validity.\n"
                "3. NOT PINPOINT, BUT CLOSE: The answer is good/average in general direction, but missing 1-2 specific concrete parameters or implementation choices (e.g., they explained the data flow well, but omitted the cache eviction policy).\n\n"
                "CRITICAL NEGATIVE RULES - NEVER TRIGGER CLARIFICATION IF:\n"
                "- The answer is NOT relevant to the question asked or the candidate's resume.\n"
                "- The answer is nonsensical, random, disconnected, or buzzword soup.\n"
                "- The answer makes an assertion with an inappropriate or disconnected reason (e.g., claiming bot detection and port routing explains how 100k events/sec throughput and 42ms latency was achieved).\n"
                "- The answer is fundamentally wrong, flawed, or a deflection.\n"
                "In ALL such cases: set needs_specification_clarification = false. Do NOT ask for clarification. Cut marks immediately (quality_band = 'Weak' or 'Incorrect', score_percentage <= 20) and move to the next question.\n"
            )

        system_prompt = (
            f"You are a seasoned Principal Technical Interviewer evaluating a candidate's answer for a {role} role at {company}.\n"
            "Evaluate with FAIR, SOUND, CONTEXT-AWARE ENGINEERING JUDGMENT. Do NOT be rigid or overfitted.\n\n"
            "1. SPEECH-TO-TEXT PHONETIC TYPOS (FAIRNESS WITHOUT HALLUCINATION):\n"
            "   - The candidate may have answered using speech-to-text voice recognition, which may have minor acoustic phonetic mishearings "
            "(e.g. 'post grass' -> Postgres, 'cloud player' -> Cloudflare, 'birds' -> bots, 'in the next' -> Nginx, 'CSE' -> CSV, 'red is' -> Redis).\n"
            "   - Understand their phonetic intent at the word level, BUT DO NOT hallucinate missing logic or invent technical details they never spoke. Evaluate ONLY the technical claims they actually attempted to make.\n\n"
            "2. DETECT NON-ANSWERS & DEFLECTIONS (CRITICAL FOR INTEGRITY):\n"
            "   - If the candidate provided NO real explanation, dodged the question, gave zero technical substance, or said phrases like "
            "\"i am totally aware about this\", \"i know this\", \"i don't know\", \"no idea\", or pure generic buzzwords:\n"
            "     * set is_non_answer = true\n"
            "     * set quality_band = \"Incorrect\" or \"Weak\"\n"
            "     * set score_percentage = 0\n"
            "     * set suggested_earned_points = 0.0 (STRICT: NEVER award free points like 1.1 for empty answers/deflections!)\n\n"
            "3. INTRINSIC QUESTION DIFFICULTY CLASSIFICATION:\n"
            "   - 'easy': Introductory questions, basic conceptual definitions, high-level project walkthroughs, standard syntax, basic tool names.\n"
            "   - 'medium': Standard architectural trade-offs, standard component choices, common caching, basic query optimization.\n"
            "   - 'hard': In-depth follow-ups, low-level database configs (e.g. Pinecone cosine vs dot-product, vector dimensions, pod types/sizing), latency/SLA observability pipelines (Prometheus, Grafana, alerts), vector database zero-downtime updates, lock-free concurrency, distributed consensus/split-brain, low-level cache stampedes, memory leak diagnosis.\n\n"
            "4. DYNAMIC INTELLIGENT SCORING PRINCIPLES (Decide suggested_possible_points and suggested_earned_points):\n"
            "   - Principle A (EASY question + GOOD answer): Modest positive impact. suggested_possible_points between 3.5 and 5.5 pts. suggested_earned_points = (score_percentage / 100) * possible.\n"
            "   - Principle B (EASY question + WRONG/NON-ANSWER): Heavy negative drag. Basics were expected. suggested_possible_points between 9.0 and 12.0 pts. suggested_earned_points = 0.0.\n"
            "   - Principle C (HARD/IN-DEPTH question + GOOD answer): Strong positive impact. Rewards depth. suggested_possible_points between 12.0 and 18.0 pts. suggested_earned_points = (score_percentage / 100) * possible.\n"
            "   - Principle D (HARD/IN-DEPTH question + WRONG/NON-ANSWER): Low negative drag. Candidate is protected from tough questions. suggested_possible_points between 2.0 and 3.2 pts. suggested_earned_points = 0.0 to 0.5 (or 0.0 if non-answer).\n"
            "   - Medium questions: suggested_possible_points between 5.5 and 8.5 pts.\n"
            "   - Tailor points fluidly to project context and relevance (e.g., 2.7, 4.3, 7.8, 13.5). Avoid rigid repetitive numbers.\n\n"
            "5. LOGICAL RIGOR & CAUSALITY CHECKING (ASSERTION VS REASON):\n"
            "   - You MUST test whether the candidate's answer actually makes sense as an engineering solution.\n"
            "   - Check Assertion vs Reason causality: If the candidate states an assertion and provides a reason (e.g., 'we did X by using Y because Z'):\n"
            "     * Both assertion and reason might contain valid-sounding technical buzzwords individually, BUT if the reason is NOT appropriate to the assertion, or does not logically achieve the stated outcome, evaluate the statement as WRONG.\n"
            "     * Example: If the question asks how an event pipeline achieved 100k events/sec throughput and 42ms p99 latency, and the candidate claims Cloudflare bot detection and Nginx host port routing achieved it: bot detection and port routing DO NOT explain high-throughput batching, queue buffering, or 42ms p99 latency. The reason is inappropriate to the assertion. Mark as 'Weak' or 'Incorrect', score_percentage <= 15%, suggested_earned_points = 0.0 to 0.5 pts.\n"
            "   - Evaluate ONLY the words the candidate actually stated. NEVER assume, hallucinate, or credit architectures, technologies, or numbers that the candidate did not explicitly explain.\n"
            "   - If the answer has multiple parts, grade proportionally: give credit only for the specific parts of the reason that are factually and causally correct. If none of the reason explains the assertion, award minimal/zero points.\n"
            "   - In engineering, there are multiple valid architectural patterns and trade-offs. If what the candidate explained makes sound engineering sense for their project, evaluate it positively (Good or Excellent).\n"
            f"{clarification_directive}\n"
            "Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "question_difficulty": "easy" | "medium" | "hard",\n'
            '  "is_non_answer": true | false,\n'
            '  "needs_specification_clarification": true | false,\n'
            '  "clarification_prompt_focus": "<specific missing technical specifications to ask in 2nd go, or null>",\n'
            '  "quality_band": "Excellent" | "Good" | "Average" | "Weak" | "Incorrect",\n'
            '  "score_percentage": <integer from 0 to 100>,\n'
            '  "suggested_possible_points": <float reflecting question weightage per the 4 principles>,\n'
            '  "suggested_earned_points": <float reflecting marks earned>,\n'
            '  "actual_topic": "<specific topic of the asked question>",\n'
            '  "evaluator_reason": "<2-3 sentence fair, honest assessment highlighting candidate\'s logic and gaps>",\n'
            '  "detected_gap": "<specific technical omission if any, or null>",\n'
            '  "expected_concept": "<the core technical concept, algorithm, or trade-off pertinent to the asked question>"\n'
            "}"
        )

        user_prompt = (
            f"Role: {role} | Company: {company} | Phase: {phase} | Depth Level: L{depth} | Topic: {topic}\n"
            f"Project / Domain Context: {project_context or 'Not specified'}\n"
            f"Attempt Type: {'2nd-Go Clarification Attempt' if is_clarification_attempt else 'Initial 1st Attempt'}\n\n"
            f"Question Asked:\n{question_text}\n\n"
            f"Candidate Response:\n\"{candidate_answer}\""
        )

        completion = self.generate_completion(system_prompt, user_prompt, temperature=0.1)
        if completion:
            try:
                clean = completion.strip()
                if clean.startswith("```json"):
                    clean = clean[7:]
                if clean.startswith("```"):
                    clean = clean[3:]
                if clean.endswith("```"):
                    clean = clean[:-3]
                clean = clean.strip()
                parsed = json.loads(clean)
                # Ensure valid quality band format
                band = parsed.get("quality_band", "Average").strip().capitalize()
                if band not in ["Excellent", "Good", "Average", "Weak", "Incorrect"]:
                    band = "Average"
                parsed["quality_band"] = band

                # Ensure valid difficulty
                diff = parsed.get("question_difficulty", "").strip().lower()
                if diff not in ["easy", "medium", "hard"]:
                    diff = "hard" if depth >= 3 else ("easy" if depth == 1 else "medium")
                parsed["question_difficulty"] = diff

                # Detect non-answers (e.g. empty or deflection)
                is_non_ans = parsed.get("is_non_answer", False)
                ans_lower = candidate_answer.strip().lower()
                if (
                    "aware about" in ans_lower
                    or "totally aware" in ans_lower
                    or "no idea" in ans_lower
                    or "dont know" in ans_lower
                    or len(ans_lower.split()) < 3
                ):
                    is_non_ans = True

                parsed["is_non_answer"] = bool(is_non_ans)

                # Ensure valid score percentage
                raw_pct = parsed.get("score_percentage")
                try:
                    score_pct = float(raw_pct) if raw_pct is not None else None
                except (ValueError, TypeError):
                    score_pct = None

                if is_non_ans or band == "Incorrect":
                    score_pct = 0.0
                parsed["score_percentage"] = score_pct

                # Clarification flags: NEVER clarify on Weak, Incorrect, or low-scoring responses
                needs_clar = parsed.get("needs_specification_clarification", False)
                if is_non_ans or is_clarification_attempt or band in ["Incorrect", "Weak"] or (score_pct is not None and score_pct < 40.0):
                    needs_clar = False
                    parsed["clarification_prompt_focus"] = None
                parsed["needs_specification_clarification"] = bool(needs_clar)

                # Suggested possible points
                try:
                    sug_poss = float(parsed.get("suggested_possible_points", 0.0))
                except (ValueError, TypeError):
                    sug_poss = None
                parsed["suggested_possible_points"] = sug_poss

                # Suggested earned points
                try:
                    sug_earn = float(parsed.get("suggested_earned_points", 0.0))
                except (ValueError, TypeError):
                    sug_earn = None
                if is_non_ans or band == "Incorrect":
                    sug_earn = 0.0
                elif band == "Weak" and sug_poss and sug_earn is not None:
                    sug_earn = min(sug_earn, sug_poss * 0.25)
                parsed["suggested_earned_points"] = sug_earn

                return parsed
            except Exception as e:
                print(f"[LLMClient] Failed to parse LLM evaluation JSON: {e}")

        return None

    def generate_specification_clarification_question(
        self,
        candidate_name: str,
        company: str,
        role: str,
        project_title: str,
        candidate_answer: str,
        expected_concept: str,
        missing_specs: str
    ) -> str:
        """
        Generates a sharp, natural, conversational 2nd-go precision question asking the candidate
        specifically for the missing technical specifications rather than immediately docking points.
        """
        system_prompt = (
            f"You are a friendly, sharp Principal Technical Interviewer conducting an interview for {company} ({role}).\n"
            "The candidate just gave a high-level overview or partial answer, but omitted specific technical parameters or specifications.\n"
            "Ask a direct, conversational 2nd-chance question prompting them to clarify those specific missing points.\n"
            "Guidelines:\n"
            "- Acknowledge their initial answer briefly and encouragingly.\n"
            "- Ask precisely what you want to know about the missing technical specifications.\n"
            "- Keep it to 1-2 sentences maximum. Natural, human ChatGPT conversational tone.\n"
            "- Return ONLY the interviewer's question text without quotation marks or conversational tags."
        )
        user_prompt = (
            f"Candidate Name: {candidate_name}\n"
            f"Project/Experience: {project_title}\n"
            f"Candidate's First Answer: \"{candidate_answer}\"\n"
            f"Expected Concept: {expected_concept}\n"
            f"Missing Specifications to Ask For: {missing_specs}"
        )
        completion = self.generate_completion(system_prompt, user_prompt, temperature=0.2)
        if completion and len(completion.strip()) > 10:
            return completion.strip().strip('"')
        return (
            f"Thanks for the overview, {candidate_name}! To dive into the specific details: "
            f"could you clarify {missing_specs}?"
        )

    def generate_interview_question(
        self,
        candidate_name: str,
        company: str,
        role: str,
        phase: str,
        current_depth: int,
        project_title: str = "",
        project_details: str = "",
        candidate_last_answer: Optional[str] = None,
        previous_question: Optional[str] = None,
        quality_band: Optional[str] = None,
        detected_gap: Optional[str] = None,
        role_skills: Optional[List[str]] = None,
        web_trends: Optional[List[str]] = None,
        item_type: str = "PROJECT",
        transition_from: Optional[str] = None,
        planner_decision: Optional[Any] = None,
        focus_dimension: Optional[str] = None,
        discrepancy_context: Optional[str] = None,
        question_profile: Optional[Any] = None,
        state: Optional[Any] = None,
        candidate_claims: Optional[List[Any]] = None,
        candidate_topics: Optional[List[str]] = None,
        relevant_history: Optional[List[Dict[str, Any]]] = None,
        role_objective: Optional[Any] = None,
        evidence_gaps: Optional[List[str]] = None,
        contradiction_context: Optional[str] = None,
        persist_in_history: bool = True
    ) -> Optional[str]:
        """
        Generates a natural, human-like technical interview question (ChatGPT style).
        Delegates to the QuestionGenerator engine using stateful adaptive planning inputs,
        QuestionProfiles, and candidate assertions.
        """
        from backend.app.engines.question_generator import QuestionGenerator
        from backend.app.engines.question_profile import QuestionProfile, QuestionKind

        q_profile = question_profile
        contra = contradiction_context or discrepancy_context
        action_val = "DEEPEN_CURRENT_TOPIC"
        target_dim = focus_dimension
        if planner_decision:
            if hasattr(planner_decision, "action"):
                action_val = planner_decision.action.value if hasattr(planner_decision.action, "value") else str(planner_decision.action)
            elif isinstance(planner_decision, str):
                action_val = planner_decision
            if not target_dim and hasattr(planner_decision, "focus_dimension"):
                target_dim = planner_decision.focus_dimension

        if not q_profile:
            q_kind = QuestionKind.ARCHITECTURAL_CHOICE
            if action_val == "CLARIFY_CONTRADICTION" or contra:
                q_kind = QuestionKind.CONTRADICTION_RESOLUTION
            elif action_val in ["START_NEXT_ITEM", "PIVOT_ITEM"]:
                q_kind = QuestionKind.CONCEPTUAL_OVERVIEW
            elif action_val == "TEST_TRADEOFF":
                q_kind = QuestionKind.TRADE_OFF_ANALYSIS
            elif action_val in ["TEST_FAILURE", "TEST_RELIABILITY"]:
                q_kind = QuestionKind.FAILURE_RECOVERY
            elif action_val in ["TEST_SCALE", "TEST_PERFORMANCE"]:
                q_kind = QuestionKind.SCALE_PERFORMANCE
            elif action_val == "TEST_CONCURRENCY":
                q_kind = QuestionKind.CONCURRENCY_SYNC
            elif action_val == "TEST_DEBUGGING":
                q_kind = QuestionKind.DEBUGGING_DIAGNOSTIC
            elif action_val == "TEST_IMPLEMENTATION":
                q_kind = QuestionKind.SPECIFICATION_PROBE
            elif phase == "SUBJECT_KNOWLEDGE":
                q_kind = QuestionKind.CONCEPTUAL_OVERVIEW

            q_profile = QuestionProfile(
                question_id=f"q_{phase}_{current_depth}_{action_val}",
                objective=f"Evaluate candidate knowledge regarding {target_dim or 'engineering design'} on {project_title or 'system'}",
                evidence_units=[f"Demonstrates clear grasp of {target_dim or 'technical execution'}"],
                phase=phase,
                item_id=project_title or "item_1",
                item_type=item_type,
                topic=project_title or "System Architecture",
                subtopic=target_dim or "architecture",
                difficulty=min(1.0, max(0.1, 0.2 + 0.2 * current_depth)),
                follow_up_depth=current_depth,
                question_kind=q_kind
            )

        # Assemble history if not supplied
        rel_hist = relevant_history
        if rel_hist is None:
            rel_hist = []
            if previous_question:
                rel_hist.append({"sender": "INTERVIEWER", "text": previous_question})
            if candidate_last_answer:
                rel_hist.append({"sender": "CANDIDATE", "text": candidate_last_answer})

        # Assemble gaps
        ev_gaps = evidence_gaps if evidence_gaps is not None else ([detected_gap] if detected_gap else [])

        # Call QuestionGenerator
        result = QuestionGenerator.generate_question(
            planner_action=planner_decision or action_val,
            question_profile=q_profile,
            state=state,
            current_item={"title": project_title, "item_type": item_type, "details": project_details},
            candidate_claims=candidate_claims,
            candidate_topics=candidate_topics,
            relevant_history=rel_hist,
            role_objective=role_objective or role_skills,
            evidence_gaps=ev_gaps,
            contradiction_context=contra,
            candidate_name=candidate_name,
            company=company,
            role=role,
            llm_client_instance=self,
            persist_in_history=persist_in_history
        )
        return result.question_text

    def correct_candidate_answer_typos(
        self,
        raw_answer: str,
        question_text: str,
        resume_context: Optional[str] = None,
        role: Optional[str] = "Software Engineer",
        company: Optional[str] = "Tech Company",
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Technical voice-to-text typo & grammar autocorrection engine powered by LLM.
        Takes candidate's raw spoken/typed transcription, question asked, and resume context.
        Detects phonetic mistranslations, broken/fragmented pause boundaries, and grammar slips,
        and reconstructs a coherent, natural paragraph reflecting candidate's intended technical answer.
        """
        from backend.app.engines.transcript_normalizer import TranscriptNormalizer

        if not raw_answer or not raw_answer.strip():
            return {
                "corrected_text": "",
                "original_text": raw_answer or "",
                "changes_made": [],
                "has_corrections": False
            }

        system_prompt = (
            f"You are a strict Word-Level Speech Recognition Acoustic Typo Corrector for technical interviews at {company} ({role}).\n"
            "Candidates speak their answers using browser voice recognition, which frequently mishears spoken words as acoustically similar words.\n\n"
            "YOUR STRICT INSTRUCTIONS:\n"
            "1. ONLY FIX PHONETIC ACOUSTIC TYPOS: Only replace specific words or short groups of words that sound phonetically similar to what the user actually said (e.g. 'cloud player' -> 'Cloudflare', 'birds' -> 'bots', 'bohat sitting' -> 'bots hitting', 'in the next' -> 'Nginx', 'consisting or' -> 'consisting of', 'post grass' -> 'Postgres', 'superb is' -> 'Supabase', 'CSE files' -> 'CSV files', 'red is' -> 'Redis', 'wells drug' -> 'well structured').\n"
            "2. DO NOT REWRITE OR MODIFY THE COMPLETE SENTENCE: You must preserve the candidate's exact sentence structure, grammar, word order, and phrasing.\n"
            "3. DO NOT EXPAND OR INVENT NEW CONTENT: DO NOT add new sentences. DO NOT answer the interview question. DO NOT inject technologies, frameworks, metrics, numbers, or architectural details that the candidate did not explicitly utter.\n"
            "4. PRESERVE FLAWED OR NONSENSICAL LOGIC: If the candidate gave a random, weak, or nonsensical answer, KEEP IT THAT WAY! Your motive is strictly to fix speech recognition phonetic sound-alikes, NEVER to rewrite, enhance, or polish the candidate's answer into a model answer.\n"
            "5. OUTPUT LENGTH MUST MATCH INPUT LENGTH: The output sentence count and word count must be virtually identical to the input.\n\n"
            "EXAMPLE:\n"
            "Raw: \"architecture existed of five levels consisting or cloud player used to detect all the birds and reduce the hit rate of the port followed by in the next to read out the host port so that the relevant user only gets into the server other than bohat sitting the server.\"\n"
            "Corrected: \"Architecture existed of five levels consisting of Cloudflare used to detect all the bots and reduce the hit rate of the port followed by Nginx to read out the host port so that the relevant user only gets into the server other than bots hitting the server.\"\n"
            "(Notice: Only phonetic words were corrected. The sentences were NOT rewritten or expanded into a new pipeline explanation.)\n\n"
            "Output JSON strictly with this schema:\n"
            "{\n"
            '  "corrected_text": "<exact candidate text with only acoustic phonetic typos fixed>",\n'
            '  "changes_made": ["<word 1> -> <word 2>"],\n'
            '  "has_corrections": true | false\n'
            "}"
        )

        # Pre-normalize known technical speech sound-alikes
        pre_normalized, did_prenorm = TranscriptNormalizer.normalize(raw_answer.strip())

        context_parts = []
        if question_text:
            context_parts.append(f"Question Asked: {question_text.strip()}")
        if topic:
            context_parts.append(f"Topic: {topic.strip()}")
        if resume_context:
            context_parts.append(f"Candidate Resume Tech Stack & Projects: {resume_context.strip()[:400]}")
        context_block = "\n".join(context_parts) if context_parts else "General Technical Context"

        user_prompt = (
            f"Technical Context:\n{context_block}\n\n"
            f"Candidate Spoken Transcription:\n\"\"\"\n{raw_answer.strip()}\n\"\"\"\n\n"
            f"Phonetic Baseline:\n\"\"\"\n{pre_normalized}\n\"\"\"\n\n"
            "Use the technical context above strictly to identify which engineering tools or architectural words were spoken. "
            "Correct ONLY phonetic acoustic sound-alikes at the word level. Keep the candidate's exact sentence phrasing, word order, and logic."
        )

        try:
            resp_str = self.generate_completion(system_prompt, user_prompt, temperature=0.0)
            if resp_str:
                cleaned_resp = resp_str.strip()
                if cleaned_resp.startswith("```json"):
                    cleaned_resp = cleaned_resp[7:]
                if cleaned_resp.startswith("```"):
                    cleaned_resp = cleaned_resp[3:]
                if cleaned_resp.endswith("```"):
                    cleaned_resp = cleaned_resp[:-3]
                data = json.loads(cleaned_resp.strip())
                corrected = data.get("corrected_text", "").strip()
                if corrected:
                    # Run post-pass normalizer
                    final_text, _ = TranscriptNormalizer.normalize(corrected)

                    # Programmatic Guardrail: Reject if the model expanded or hallucinated content
                    raw_words = len(raw_answer.strip().split())
                    corrected_words = len(final_text.split())
                    if corrected_words > (raw_words * 1.25 + 4) or corrected_words < (raw_words * 0.75 - 3):
                        print(f"[LLMClient] Rejected LLM correction due to length deviation (raw: {raw_words}, corrected: {corrected_words}). Falling back to deterministic phonetic normalizer.")
                        final_text = pre_normalized

                    changes = [c.replace('\u2011', '-').replace('\u2013', '-').replace('\u2018', "'").replace('\u2019', "'") for c in data.get("changes_made", [])]
                    has_changes = (final_text != raw_answer.strip())
                    return {
                        "corrected_text": final_text,
                        "original_text": raw_answer.strip(),
                        "changes_made": changes if changes else (["Corrected phonetic speech terms"] if has_changes else []),
                        "has_corrections": has_changes
                    }
        except Exception as e:
            print(f"[LLMClient] Typo correction via LLM failed: {e}")

        # Deterministic fallback
        final_fallback, changed = TranscriptNormalizer.normalize(raw_answer.strip())
        return {
            "corrected_text": final_fallback,
            "original_text": raw_answer.strip(),
            "changes_made": ["Applied technical phonetic normalization rules"] if changed else [],
            "has_corrections": changed or (final_fallback != raw_answer.strip())
        }

# Global singleton
llm_client = LLMClient()


