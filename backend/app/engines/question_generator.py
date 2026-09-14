from __future__ import annotations
import re
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

from backend.app.engines.question_profile import QuestionProfile, QuestionKind
from backend.app.engines.interview_state import InterviewState, Claim, ItemState
from backend.app.engines.adaptive_planner import PlannerAction, PlannerDecision
from backend.app.engines.answer_evaluator import SemanticEvaluationResult


class GeneratedQuestion(BaseModel):
    """
    Structured outcome of the Question Generator.
    Encapsulates the generated natural-language question text alongside
    the immutable QuestionProfile associated with it.
    """
    question_text: str
    question_profile: QuestionProfile
    turn_index: int
    focus_dimension: Optional[str] = None
    planner_action: str
    is_clarification: bool = False


class QuestionGenerator:
    """
    Stateful Natural-Language Question Generator.
    
    Consumes planner decisions, QuestionProfiles, and interview state context
    to generate sharp, natural, bite-sized technical interview questions.
    
    CRITICAL INVARIANTS:
    1. ONLY generates the natural-language question.
    2. NEVER decides planner actions.
    3. NEVER calculates scoring.
    4. NEVER invents a single expected answer.
    5. NEVER relies on hardcoded depth ladders (e.g. depth 2=database, depth 3=scale).
    6. NEVER hardcodes keyword-based branches (e.g. Redis -> invalidation, Postgres -> indexing).
    7. Strictly preserves alternative valid answers.
    8. Neutral and non-accusatory during clarification inquiries.
    9. Grounded in actual candidate context and assertions.
    10. Never leaks internal planner rationale or chain-of-thought.
    11. Every generated question has an associated QuestionProfile persisted in question history.
    """

    @classmethod
    def generate_question(
        cls,
        planner_action: Union[PlannerAction, str],
        question_profile: QuestionProfile,
        state: Optional[InterviewState] = None,
        current_item: Optional[Union[ItemState, Dict[str, Any]]] = None,
        candidate_claims: Optional[List[Any]] = None,
        candidate_topics: Optional[List[str]] = None,
        relevant_history: Optional[List[Dict[str, Any]]] = None,
        role_objective: Optional[Any] = None,
        evidence_gaps: Optional[List[str]] = None,
        contradiction_context: Optional[str] = None,
        candidate_name: str = "Candidate",
        company: str = "Target Company",
        role: str = "Software Engineer",
        llm_client_instance: Optional[Any] = None,
        persist_in_history: bool = True,
        latest_eval: Optional[SemanticEvaluationResult] = None
    ) -> GeneratedQuestion:
        """
        Generates the natural-language question targeting the planned action and profile.
        """
        # 1. Normalize action and dimension
        if hasattr(planner_action, "value"):
            action_str = str(planner_action.value)
        else:
            action_str = str(planner_action)

        focus_dim = question_profile.subtopic.lower() if question_profile.subtopic else "architecture"
        is_clarification = (
            action_str == "CLARIFY_CONTRADICTION"
            or question_profile.question_kind == QuestionKind.CONTRADICTION_RESOLUTION
            or bool(contradiction_context)
        )

        # 2. Extract item details
        item_title = "System Architecture"
        item_type = "PROJECT"
        item_details = ""
        if current_item:
            if hasattr(current_item, "title"):
                item_title = current_item.title
                item_type = getattr(current_item, "item_type", "PROJECT")
                item_details = getattr(current_item, "details", "")
            elif isinstance(current_item, dict):
                item_title = current_item.get("title", "System Architecture")
                item_type = current_item.get("item_type", "PROJECT")
                item_details = current_item.get("details", "")

        # 3. Extract candidate entities from assertions & topics
        candidate_entities = cls._extract_candidate_entities(
            candidate_claims=candidate_claims,
            candidate_topics=candidate_topics,
            relevant_history=relevant_history
        )

        # 4. Extract latest turn history context
        prev_q_text = None
        cand_last_ans = None
        if relevant_history:
            for turn in reversed(relevant_history[-10:] if relevant_history else []):
                if turn.get("sender") == "INTERVIEWER" and not prev_q_text:
                    prev_q_text = turn.get("text", "")
                elif turn.get("sender") == "CANDIDATE" and not cand_last_ans:
                    cand_last_ans = turn.get("text", "")
                if prev_q_text and cand_last_ans:
                    break

        # 5. Extract role requirements
        role_skills_str = cls._extract_role_skills_str(role_objective)

        # 6. Attempt Live LLM Generation if client available
        generated_text = None
        if llm_client_instance and hasattr(llm_client_instance, "generate_completion"):
            sys_prompt = cls._build_system_prompt(
                role=role,
                company=company,
                action_str=action_str,
                focus_dim=focus_dim,
                is_clarification=is_clarification,
                valid_alternatives=question_profile.valid_alternative_guidance,
                latest_eval=latest_eval
            )
            user_prompt = cls._build_user_prompt(
                candidate_name=candidate_name,
                role=role,
                company=company,
                phase=question_profile.phase,
                item_title=item_title,
                item_type=item_type,
                item_details=item_details,
                question_profile=question_profile,
                candidate_entities=candidate_entities,
                candidate_last_answer=cand_last_ans,
                previous_question=prev_q_text,
                evidence_gaps=evidence_gaps,
                contradiction_context=contradiction_context,
                role_skills_str=role_skills_str,
                action_str=action_str,
                focus_dim=focus_dim
            )
            try:
                completion = llm_client_instance.generate_completion(sys_prompt, user_prompt, temperature=0.25)
                if completion and len(completion.strip()) > 15:
                    generated_text = cls._clean_completion(completion.strip())
            except Exception as e:
                print(f"[QuestionGenerator] LLM generation failed, falling back: {e}")

        # 7. Fallback generation (derived strictly from planned dimension & candidate context, NO depth ladder)
        if not generated_text:
            raise RuntimeError("LLM API connection failed. Cannot generate natural language question offline. Please check your API keys or try again.")

        # 8. Persist associated QuestionProfile into question history if state is present
        turn_idx = (len(state.question_history) + 1) if state else 1
        if state and persist_in_history:
            state.record_turn(
                question_id=question_profile.question_id,
                turn_index=turn_idx,
                topic=question_profile.topic,
                question_text=generated_text,
                subtopic=question_profile.subtopic,
                planner_action=action_str,
                target_difficulty=str(question_profile.difficulty),
                question_profile=question_profile
            )

        return GeneratedQuestion(
            question_text=generated_text,
            question_profile=question_profile,
            turn_index=turn_idx,
            focus_dimension=focus_dim,
            planner_action=action_str,
            is_clarification=is_clarification
        )

    @classmethod
    def _extract_candidate_entities(
        cls,
        candidate_claims: Optional[List[Any]],
        candidate_topics: Optional[List[str]],
        relevant_history: Optional[List[Dict[str, Any]]]
    ) -> List[str]:
        entities: List[str] = []
        if candidate_claims:
            for c in candidate_claims:
                if isinstance(c, dict):
                    ent = c.get("entity")
                    if ent and ent not in entities and len(ent.strip()) > 1:
                        entities.append(ent.strip())
                elif hasattr(c, "entity") and c.entity:
                    if c.entity not in entities and len(c.entity.strip()) > 1:
                        entities.append(c.entity.strip())

        if candidate_topics:
            for t in candidate_topics:
                if t and t not in entities and len(t.strip()) > 1:
                    entities.append(t.strip())

        return entities

    @classmethod
    def _extract_role_skills_str(cls, role_obj: Optional[Any]) -> str:
        if not role_obj:
            return "Core Software Engineering & System Design"
        if isinstance(role_obj, str):
            return role_obj
        if hasattr(role_obj, "required_skills") and role_obj.required_skills:
            return ", ".join(role_obj.required_skills[:5])
        if isinstance(role_obj, dict):
            skills = role_obj.get("required_skills", [])
            if skills:
                return ", ".join(skills[:5])
        return "Core Software Engineering & System Design"

    @classmethod
    def _build_system_prompt(
        cls,
        role: str,
        company: str,
        action_str: str,
        focus_dim: str,
        is_clarification: bool,
        valid_alternatives: str,
        latest_eval: Optional[SemanticEvaluationResult] = None
    ) -> str:
        lines = [
            f"You are an empathetic, sharp Senior Technical Lead conducting a live technical interview for a {role} at {company}.",
            "You speak naturally like a principal engineer in video conversation—warm, concise, focused, and collaborative.",
            "",
            "CRITICAL INVARIANTS & RULES:",
            "1. ONE SINGLE QUESTION: Ask about exactly ONE focused technical topic or decision. Never ask compound questions with multiple sub-parts.",
            "2. NATURALNESS (PREFER <= 2 SHORT SENTENCES):",
            "   - Sentence 1: Acknowledge the candidate's answer. If they provided good technical details, validate them warmly. If they gave a joke, evaded, or gave a nonsensical answer, politely but firmly redirect them (e.g. 'Let's focus on the technical implementation...').",
            "   - Sentence 2: Ask ONE clear, focused question.",
            "3. NO GENERIC QUESTIONS: Avoid vague filler like 'Can you tell me more about that?' or 'What else did you do?'. Reference their actual technical choices.",
            f"4. ALTERNATIVE ARCHITECTURES MUST REMAIN VALID: Never imply there is only one textbook answer. Guidance: {valid_alternatives}",
            "5. NO INTERNAL LEAKS: Never expose chain-of-thought, internal planner rationale, difficulty numbers, or scoring models.",
            "6. TEST OWNERSHIP & PERSONAL CONTRIBUTION: When evaluating claimed responsibilities or projects, distinguish what the candidate personally designed and built versus what was already provided by the team or framework.",
            "7. SITUATIONAL & OPERATIONAL DEPTH: Ask concrete questions grounded in the candidate's actual tools, architecture, and operational constraints."
        ]

        if is_clarification:
            lines.extend([
                "8. NEUTRAL, NON-ACCUSATORY CLARIFICATION:",
                "   - An apparent ambiguity, discrepancy, or unclear service boundary was identified.",
                "   - Be curious, constructive, and completely neutral.",
                "   - NEVER accuse the candidate (e.g. NEVER say 'you contradict yourself' or 'your resume says X but you said Y').",
                "   - Ask how the components or services interact or fit together in their architecture."
            ])
        else:
            lines.append(f"8. FOCUS DIMENSION: Probe '{focus_dim}'. Directly target engineering mechanics, failure handling, trade-offs, concurrency, or scaling.")

        
        if latest_eval and latest_eval.is_non_answer:
            lines.append("9. THE CANDIDATE JUST GAVE A JOKE OR NON-ANSWER. You must firmly redirect them to technical matters before asking the next question.")
        elif latest_eval and latest_eval.correctness < 0.40:
            lines.append("9. THE CANDIDATE'S LAST ANSWER WAS WEAK OR INCORRECT. Push back logically or ask them to clarify the flaw in their reasoning.")

        lines.append("- Return ONLY the natural-language question text without quotes or role tags.")
        return "\n".join(lines)

    @classmethod
    def _build_user_prompt(
        cls,
        candidate_name: str,
        role: str,
        company: str,
        phase: str,
        item_title: str,
        item_type: str,
        item_details: str,
        question_profile: QuestionProfile,
        candidate_entities: List[str],
        candidate_last_answer: Optional[str],
        previous_question: Optional[str],
        evidence_gaps: Optional[List[str]],
        contradiction_context: Optional[str],
        role_skills_str: str,
        action_str: str,
        focus_dim: str
    ) -> str:
        entities_str = ", ".join(candidate_entities[:4]) if candidate_entities else item_title
        lines = [
            f"Candidate: {candidate_name} | Role: {role} | Company: {company}",
            f"Phase: {phase} | Item Type: {item_type} | Item: {item_title}",
            f"Item Summary: {item_details or 'Production engineering work'}",
            f"Candidate's Mentioned Components/Technologies: {entities_str}",
            f"Target Role Objectives: {role_skills_str}",
            f"Question Objective: {question_profile.objective}",
            f"Planned Dimension: {focus_dim} (Action: {action_str})"
        ]

        if contradiction_context:
            lines.append(f"Discrepancy / Scope Ambiguity to Clarify: {contradiction_context}")
        if evidence_gaps:
            lines.append(f"Evidence Gaps to Address: {', '.join(evidence_gaps[:2])}")

        if candidate_last_answer:
            lines.extend([
                "",
                "Previous Question Asked:",
                previous_question or "Overview",
                "",
                "Candidate's Last Answer:",
                f'"{candidate_last_answer}"',
                "",
                "Formulate the next natural, bite-sized follow-up question (strictly <= 2 sentences, 1 single question)."
            ])
        else:
            lines.extend([
                "",
                f"This is an opening question for {item_title}.",
                f"Greet {candidate_name} warmly and ask ONE focused opening question about it."
            ])

        return "\n".join(lines)

    @classmethod
    def _clean_completion(cls, text: str) -> str:
        cleaned = text.strip().strip('"').strip("'")
        if cleaned.startswith("Interviewer:"):
            cleaned = cleaned[12:].strip()
        return cleaned

    @classmethod
    def _format_fallback_question(
        cls,
        candidate_name: str,
        action_str: str,
        focus_dim: str,
        question_profile: QuestionProfile,
        item_title: str,
        item_type: str,
        candidate_entities: List[str],
        contradiction_context: Optional[str],
        relevant_history: Optional[List[Dict[str, Any]]]
    ) -> str:
        """
        Deterministic, natural ChatGPT-style fallback question.
        Completely eliminates the old hardcoded role/depth branches.
        Derived strictly from the planned action, dimension, and candidate assertions.
        """
        entity = candidate_entities[0] if candidate_entities else item_title

        # Case 1: Clarification (Neutral & Non-Accusatory)
        if action_str == "CLARIFY_CONTRADICTION" or contradiction_context:
            if entity != item_title:
                return (
                    f"Thanks for detailing that, {candidate_name}. "
                    f"To make sure I understand the architecture correctly, how does {entity} fit into the service boundaries alongside your other storage components?"
                )
            return (
                f"Thanks for explaining that, {candidate_name}. "
                f"To make sure I have a clear picture of the architecture, could you clarify how those components interact in {item_title}?"
            )

        # Case 2: Verification & Ownership Probe
        if action_str == "VERIFY_UNSUPPORTED_CLAIM" or focus_dim == "ownership":
            return (
                f"That gives helpful context on the team scope, {candidate_name}. "
                f"What specific part of {entity} did you personally design and implement versus relying on existing team libraries?"
            )

        # Case 3: Trade-off Analysis
        if focus_dim == "tradeoff" or action_str == "TEST_TRADEOFF":
            return (
                f"Regarding {entity}, {candidate_name}. "
                f"When evaluating that design for {item_title}, what was the primary engineering trade-off you had to make, and why did you settle on that choice?"
            )

        # Case 4: Architectural Reasoning & Justification
        if focus_dim == "reasoning" or action_str == "TEST_REASONING":
            return (
                f"Regarding {entity}, {candidate_name}. "
                f"Why did you choose {entity} over alternative approaches for {item_title}, and what technical constraints guided that choice?"
            )

        # Case 5: Failure & Fault Tolerance
        if focus_dim in ["failure", "reliability"] or action_str in ["TEST_FAILURE", "TEST_RELIABILITY"]:
            return (
                f""
                f"If {entity} experiences an unexpected node crash or network partition, how does your system fail gracefully to preserve state?"
            )

        # Case 6: Scale & Performance
        if focus_dim in ["scale", "performance"] or action_str in ["TEST_SCALE", "TEST_PERFORMANCE"]:
            return (
                f""
                f"If throughput or data volume scaled up by 10x, what specific bottleneck would emerge first in {entity}, and how would you optimize it?"
            )

        # Case 7: Concurrency & Thread Synchronization
        if focus_dim == "concurrency" or action_str == "TEST_CONCURRENCY":
            return (
                f"Got it, that clarifies the communication model for {entity}. "
                f"How do you guard against race conditions or data inconsistency when multiple concurrent requests mutate the same resource?"
            )

        # Case 8: Consistency & Distributed Transactions
        if focus_dim in ["consistency", "transactions"] or action_str == "TEST_CONSISTENCY":
            return (
                f"Understood on how data is distributed across {entity}. "
                f"What consistency guarantees does your design provide, and how do you handle partial writes or distributed rollbacks?"
            )

        # Case 9: Security & Authorization
        if focus_dim in ["security", "auth"] or action_str == "TEST_SECURITY":
            return (
                f"Got it, that clarifies the endpoint interaction, {candidate_name}. "
                f"How did you secure communications and enforce authentication and authorization across {entity}?"
            )

        # Case 10: Production Operations & Monitoring
        if focus_dim in ["operations", "monitoring"] or action_str == "TEST_OPERATIONS":
            return (
                f"Thanks for detailing that deployment flow, {candidate_name}. "
                f"In production, how do you monitor health metrics and manage rollout rollbacks for {entity} without impacting live traffic?"
            )

        # Case 11: Debugging & Diagnostics
        if focus_dim == "debugging" or action_str == "TEST_DEBUGGING":
            return (
                f"Thanks for breaking down that mechanism in {item_title}. "
                f"When latency spikes or memory leaks occur in {entity}, what specific metrics and diagnostic profiling tools do you use to isolate the root cause?"
            )

        # Case 12: Specification Probe
        if focus_dim == "specification" or action_str == "TEST_IMPLEMENTATION":
            return (
                f"Thanks for the high-level overview, {candidate_name}. "
                f"Could you specify the concrete technical configuration, schema, or API protocol you implemented for {entity}?"
            )

        # Case 13: Explore Candidate Topic
        if action_str == "EXPLORE_CANDIDATE_TOPIC":
            return (
                f"You brought up {entity} earlier, which is very relevant. "
                f"Could you dive into how {entity} is integrated and what role it plays in your overall architecture?"
            )

        # Case 14: Explore Resume Topic
        if action_str == "EXPLORE_RESUME_TOPIC":
            return (
                f"Your background highlights hands-on experience with {entity}. "
                f"How did you apply that knowledge to address key engineering hurdles in {item_title}?"
            )

        # Case 15: Subject Knowledge Stage
        if question_profile.phase == "SUBJECT_KNOWLEDGE" or action_str == "START_SUBJECT_STAGE":
            obj_target = question_profile.objective.rstrip(" .?!")
            return (
                f"We've covered your project experience in depth, {candidate_name}. "
                f"Turning to core engineering fundamentals in {question_profile.topic}: how would you approach designing a system to satisfy {obj_target}?"
            )

        # Case 16: Item Transition / Opening
        if action_str in ["START_NEXT_ITEM", "PIVOT_ITEM"]:
            if item_type == "WORK_EXPERIENCE":
                return (
                    f"Thanks for detailing your previous work, {candidate_name}! "
                    f"Looking at your time at {item_title}, could you give me a concise overview of your primary technical responsibilities and challenges there?"
                )
            return (
                f"That gives me a great picture of your previous work, {candidate_name}! "
                f"Let's explore '{item_title}'—could you give me a brief overview of the core problem it solves and why you chose to build it?"
            )

        # Case 17: General Architecture Deepening (Default)
        return (
            f"Thanks for breaking that down, {candidate_name}. "
            f"Could you walk me through how data flows through {entity} and how service boundaries are enforced?"
        )
