import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Tuple

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
            return "Groq (openai/gpt-oss-120b)"
        if self.gemini_key:
            return "Google Gemini (gemini-flash-latest)"
        if self.openai_key:
            return "OpenAI (gpt-4o-mini)"
        if self.anthropic_key:
            return "Anthropic Claude (claude-3-5-sonnet)"
        return "Intervyn Domain Expert Engine (Local Deterministic)"

    def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Optional[str]:
        # 1. Groq (REST - Ultra-Fast openai/gpt-oss-120b)
        if self.groq_key:
            try:
                headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "openai/gpt-oss-120b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature
                }
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                    if resp.status_code == 200:
                        return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[LLMClient] Groq call failed or timed out: {e}")

        # 2. Google Gemini (REST - gemini-flash-latest with fallback)
        if self.gemini_key:
            for gmodel in ["gemini-flash-latest", "gemini-3.6-flash", "gemini-2.5-flash"]:
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
                    with httpx.Client(timeout=25.0) as client:
                        resp = client.post(url, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            if "candidates" in data and data["candidates"]:
                                return data["candidates"][0]["content"]["parts"][0]["text"]
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
            except Exception as e:
                print(f"[LLMClient] Anthropic call failed: {e}")

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
                "\n--- 1ST-GO SPECIFICATION CLARIFICATION DETECTION ---\n"
                "If the candidate provided an on-topic answer or high-level project summary, BUT is missing concrete expected "
                "specifications (e.g. they described web scraping generally but omitted the fallback mechanism details, or mentioned "
                "a database without specifying the primary database choice or schema reasons):\n"
                "   * set needs_specification_clarification = true\n"
                "   * set clarification_prompt_focus = \"<the exact 1-2 missing technical specifications that the interviewer should ask for in a 2nd go>\"\n"
                "   * NOTE: Do NOT trigger clarification for complete deflections (e.g. 'i don't know', 'i have no idea', zero answer). "
                "Only trigger when the user made a genuine attempt that simply lacked the technical specifics.\n"
            )

        system_prompt = (
            f"You are a seasoned Principal Technical Interviewer evaluating a candidate's answer for a {role} role at {company}.\n"
            "Evaluate with FAIR, SOUND, CONTEXT-AWARE ENGINEERING JUDGMENT. Do NOT be rigid or overfitted.\n\n"
            "1. SPEECH-TO-TEXT TYPO & PHONETIC NORMALIZATION (CRITICAL FOR FAIRNESS):\n"
            "   - The candidate may be answering via speech-to-text / voice recognition. Browsers often introduce phonetic typos "
            "(e.g. 'post grass SQL' -> PostgreSQL, 'superb is' -> Supabase, 'webs grapes' -> web scrapes, 'Wells drug' -> well structured, "
            "'duck duck GO light' -> DuckDuckGo Lite, 'hurastic' -> heuristic, 'CSE files' -> CSV files, 'pills the missing' -> fills the missing).\n"
            "   - You MUST reconstruct the candidate's true technical intent. Never penalize or call an answer 'incoherent' or 'lacks substance' "
            "simply due to phonetic misspellings or typographical slips. Evaluate what the candidate actually meant from an engineering standpoint!\n\n"
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
            "5. SOUND ENGINEERING LOGIC:\n"
            "   - In engineering, there are multiple valid architectural patterns and trade-offs. If what the candidate explained makes engineering sense for their project, evaluate it positively (Good or Excellent).\n"
            "   - If technically correct but high-level, award Good or Average (50%-70% points). Do NOT mark it Weak or Incorrect unless they display severe confusion or say nothing.\n"
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

                # Clarification flags
                needs_clar = parsed.get("needs_specification_clarification", False)
                if is_non_ans or is_clarification_attempt:
                    needs_clar = False
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
        transition_from: Optional[str] = None
    ) -> Optional[str]:
        """
        Generates a natural, human-like technical interview question (ChatGPT style).
        Speaks like an experienced, collaborative Senior Tech Lead.
        STRICT RULES:
        - ONE BITE-SIZED, FOCUSED QUESTION AT A TIME. NEVER ask compound questions with multiple sub-parts.
        - Total response must be 2 short sentences:
          Sentence 1: Acknowledge their previous answer warmly (or provide a smooth transition).
          Sentence 2: Ask ONE single, clear, focused question.
        - Start basic and progress step-by-step.
        """
        is_work_exp = (item_type == "WORK_EXPERIENCE" or phase == "EXPERIENCE_DEFENSE")
        
        system_prompt = (
            f"You are an empathetic, sharp Senior Tech Lead conducting a live technical interview for a {role} at {company}.\n"
            "You talk naturally like a real human engineer on a video call (how ChatGPT speaks in interview mode)—warm, conversational, concise, and focused. NEVER sound like a robotic questionnaire or pre-scripted automated form.\n\n"
            "CRITICAL RULES FOR QUESTION DESIGN:\n"
            "1. ONE BITE-SIZED QUESTION AT A TIME: Ask about ONE single thing. NEVER ask compound, overloaded questions. That overwhelms candidates.\n"
            "2. MAXIMUM 2 SHORT SENTENCES TOTAL:\n"
            "   - Sentence 1: Acknowledge what the candidate just said warmly (or bridge smoothly if transitioning to a new company/project).\n"
            "   - Sentence 2: Ask ONE direct, focused question.\n"
            "3. PROGRESSIVE DEPTH BASED ON ITEM TYPE:\n"
        )

        if is_work_exp:
            system_prompt += (
                "   - If this is a new Work Experience (Turn 1): Acknowledge and ask for a concise overview of their core responsibilities and the primary problem their team was solving at this company.\n"
                "   - If Depth 2: Ask about a specific service, feature, or database optimization they built there.\n"
                "   - If Depth 3: Ask about a concrete production engineering trade-off, latency bottleneck, or scaling challenge they had to navigate.\n"
                "   - If Depth 4+: Ask about failure handling, edge cases, or rollback strategies in that production environment.\n"
            )
        else:
            system_prompt += (
                "   - If this is a new Project (Turn 1): Ask for a simple, high-level summary of the core problem '{project_title}' solves.\n"
                "   - If Depth 2: Ask what primary tool, database, or framework they chose for it.\n"
                "   - If Depth 3: Ask why they chose that specific tool over an alternative, or how data flows through that component.\n"
                "   - If Depth 4: Ask about performance, latency, or bottleneck management.\n"
                "   - If Depth 5+: Ask about edge cases, data consistency, or failure handling.\n"
            )

        system_prompt += (
            "4. TRANSITIONS:\n"
            "   - When moving between work experiences or projects, Sentence 1 should bridge naturally (e.g., 'Thanks for detailing your work at Datastream—that makes sense.', 'That gives me a great picture of your work experience; let\\'s dive into your projects.').\n"
        )

        trends_context = "\n".join([f"- {t}" for t in (web_trends or [])[:3]]) if web_trends else "Standard industry hiring expectations"
        skills_str = ", ".join((role_skills or [])[:6]) if role_skills else "Core Software Engineering"

        label = "Work Experience" if is_work_exp else "Project"
        user_prompt = (
            f"Candidate: {candidate_name} | Role: {role} | Target Company: {company}\n"
            f"Interview Phase: {phase} | Depth Level: L{current_depth}\n"
            f"Current {label}: {project_title}\n"
            f"{label} Summary: {project_details or 'Production engineering work'}\n"
            f"Key Role Skills: {skills_str}\n"
            f"Recent Company Interview Trends:\n{trends_context}\n"
        )

        if transition_from:
            user_prompt += f"Transitioning from previous item: '{transition_from}'\n"

        if candidate_last_answer:
            user_prompt += (
                f"\nPrevious Question Asked:\n{previous_question or 'Overview'}\n\n"
                f"Candidate's Last Answer:\n\"{candidate_last_answer}\"\n\n"
                f"Evaluation Band: {quality_band or 'Good'} | Evaluator Notes: {detected_gap or 'None'}\n\n"
                "Formulate the next natural, bite-sized follow-up question (strictly 2 sentences: 1 acknowledge/bridge, 1 single focused question)."
            )
        else:
            if transition_from:
                user_prompt += (
                    f"\nThis is a transition to the next {label} '{project_title}'.\n"
                    f"Bridge warmly from '{transition_from}' in Sentence 1, then ask ONE clean opening question about '{project_title}' in Sentence 2."
                )
            else:
                user_prompt += (
                    f"\nThis is the opening question of the interview.\n"
                    f"Greet {candidate_name} warmly, mention their {label} '{project_title}', and ask a simple, friendly opening question about it."
                )

        return self.generate_completion(system_prompt, user_prompt, temperature=0.3)

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
            f"You are an expert Principal Technical Interviewer and Speech-to-Text Transcription Corrector for technical interviews at {company} ({role}).\n"
            "Candidates speak their answers using browser voice recognition, which frequently causes:\n"
            "1. Phonetic sound-alike mistranslations of technical tools, libraries, protocols, and architectural terms (e.g. 'post grass SQL' -> PostgreSQL, 'superb is' -> Supabase, 'duck duck GO light' -> DuckDuckGo Lite, 'wells drug' -> well structured, 'CSE files' -> CSV files, 'red is' -> Redis, 'pin corn' -> Pinecone, 'cooberneties' -> Kubernetes, 'g r p c' -> gRPC, 'mungo' -> MongoDB, etc.).\n"
            "2. Fragmented, run-on, or irregular sentence boundaries caused by speaking pauses.\n"
            "3. Punctuation, capitalization, and minor grammatical slips.\n\n"
            "YOUR TASK:\n"
            "- Cross-reference the candidate's spoken answer with the Question Asked and their Resume/Projects Context.\n"
            "- Correct all voice-to-text phonetic mishearings and restore the exact technical terms the candidate intended.\n"
            "- Clean up fragmented, run-on, or irregular sentences into a coherent, natural, well-formatted technical paragraph.\n"
            "- CRITICAL SAFETY RULE: PRESERVE THE CANDIDATE'S ACTUAL CLAIMS, ARCHITECTURE, AND INTENT. DO NOT invent new technologies, algorithms, metrics, or answers they did not attempt to state. Only fix the speech-to-text translation, grammar, and technical names.\n\n"
            "Output JSON strictly with this schema:\n"
            "{\n"
            '  "corrected_text": "<full cleaned paragraph of candidate\'s answer>",\n'
            '  "changes_made": ["<short description of term or grammar fix 1>", "<fix 2>"],\n'
            '  "has_corrections": true | false\n'
            "}"
        )

        # Pre-normalize known technical speech sound-alikes
        pre_normalized, did_prenorm = TranscriptNormalizer.normalize(raw_answer.strip())

        user_prompt = (
            f"Target Role: {role} | Company: {company}\n"
            f"Question Asked:\n{question_text or 'Technical architecture question'}\n"
            f"Topic: {topic or 'System Architecture'}\n\n"
            f"Candidate Resume Context (Projects, Skills, Technologies):\n{resume_context or 'Standard Engineering Stack'}\n\n"
            f"Raw Spoken Transcription:\n\"\"\"\n{raw_answer.strip()}\n\"\"\"\n\n"
            f"Phonetically Normalized Terms:\n\"\"\"\n{pre_normalized}\n\"\"\"\n"
        )

        try:
            resp_str = self.generate_completion(system_prompt, user_prompt, temperature=0.1)
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
                    # Run post-pass normalizer as a safety net
                    final_text, _ = TranscriptNormalizer.normalize(corrected)
                    changes = [c.replace('\u2011', '-').replace('\u2013', '-').replace('\u2018', "'").replace('\u2019', "'") for c in data.get("changes_made", [])]
                    has_changes = data.get("has_corrections", final_text != raw_answer.strip()) or (final_text != raw_answer.strip())
                    return {
                        "corrected_text": final_text,
                        "original_text": raw_answer.strip(),
                        "changes_made": changes,
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


