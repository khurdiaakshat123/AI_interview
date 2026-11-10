from __future__ import annotations
import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from backend.app.engines.question_profile import QuestionProfile, QuestionKind
from backend.app.engines.interview_state import InterviewState, ClaimStatus


class CandidateClaimExtraction(BaseModel):
    statement: str
    entity: Optional[str] = None
    attribute_or_action: Optional[str] = None
    causality_valid: bool = True
    is_alternative_pattern: bool = False


class SemanticEvaluationResult(BaseModel):
    """
    Pure Semantic Evaluation Result.
    Represents strictly what the candidate demonstrated.
    
    INVARIANTS:
    - Never calculates or contains earned/possible numeric points.
    - Never decides flow or next question.
    - Never exposes private chain-of-thought.
    """
    answer_understanding: str = Field(
        description="Concise summary of what the candidate conveyed."
    )
    candidate_claims: List[CandidateClaimExtraction] = Field(
        default_factory=list,
        description="Discrete technical assertions made by the candidate."
    )
    entities: List[str] = Field(
        default_factory=list,
        description="Concrete technologies, protocols, algorithms, or systems mentioned."
    )
    candidate_topics: List[str] = Field(
        default_factory=list,
        description="Technical topics or concepts introduced in the answer."
    )
    relationships: List[str] = Field(
        default_factory=list,
        description="Causal or architectural linkages (e.g. A buffers B, C invalidates D)."
    )
    reasoning_summary: str = Field(
        description="Concise, audit-ready summary of the candidate's engineering reasoning."
    )
    objective_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence directly satisfying the question's objective."
    )
    missing_evidence: List[str] = Field(
        default_factory=list,
        description="Expected criteria or technical aspects not addressed."
    )

    # Normalized semantic metrics [0, 1]
    technical_validity: float = Field(default=0.5, ge=0.0, le=1.0)
    completeness: float = Field(default=0.5, ge=0.0, le=1.0)
    communication: float = Field(default=0.5, ge=0.0, le=1.0)
    correctness: Optional[float] = Field(default=None)

    model_config = {"extra": "allow"}

    # Discrepancies and Inconsistencies
    contradictions_with_previous_answers: List[str] = Field(default_factory=list)
    resume_discrepancies: List[str] = Field(default_factory=list)
    technically_valid_alternative: bool = Field(default=False)
    clarification_needed: bool = Field(default=False)
    clarification_reason: Optional[str] = None
    uncertainty_notes: Optional[str] = None
    is_non_answer: bool = Field(default=False)

    @field_validator(
        "technical_validity",
        "completeness",
        "communication",
        mode="before"
    )
    @classmethod
    def clamp_normalized(cls, v: Any) -> float:
        if v is None:
            return 0.5
        try:
            val = float(v)
        except (ValueError, TypeError):
            val = 0.5
        return max(0.0, min(1.0, round(val, 4)))



    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticEvaluationResult":
        return cls.model_validate(data)


class AnswerEvaluator:
    """
    Semantic Answer Evaluator.
    Analyzes candidate responses without keyword bias, length heuristics, or point scoring.
    """

    @classmethod
    def evaluate(
        cls,
        question_profile: QuestionProfile,
        candidate_answer: str,
        history: Optional[List[Dict[str, Any]]] = None,
        state: Optional[InterviewState] = None,
        resume_context: Optional[str] = None,
        role_profile: Optional[Dict[str, Any]] = None,
        llm_client_instance: Any = None
    ) -> SemanticEvaluationResult:
        cleaned_answer = (candidate_answer or "").strip()

        # 1. Definite Non-Answer Detection (Semantic evading, NOT based on word count)
        if cls._is_explicit_evasion(cleaned_answer):
            return SemanticEvaluationResult(
                answer_understanding="Candidate deflected or stated they do not know the answer.",
                reasoning_summary="Candidate provided no technical substance, explicitly indicating lack of knowledge or deflecting.",
                missing_evidence=["Candidate did not answer the question asked."],
                completeness=0.0,
                technical_validity=0.0,
                is_non_answer=True,
                uncertainty_notes=None
            )

        # 2. Attempt Live LLM Semantic Extraction if available
        if llm_client_instance is not None:
            result = cls._evaluate_via_llm(
                question_profile=question_profile,
                candidate_answer=cleaned_answer,
                history=history or [],
                state=state,
                resume_context=resume_context,
                role_profile=role_profile,
                llm_client=llm_client_instance
            )
            if result:
                return result
            
            # If LLM parsing fails (e.g. ValidationError due to jokes breaking the schema), fallback gracefully instead of crashing.
            return SemanticEvaluationResult(
                answer_understanding="LLM encountered an error parsing the semantic evaluation (likely due to an evasion).",
                reasoning_summary="System gracefully caught an LLM validation error and assigned a default zero score.",
                missing_evidence=[],
                completeness=0.0,
                technical_validity=0.0,
                is_non_answer=True,
                uncertainty_notes=None
            )
            
        return SemanticEvaluationResult(
            answer_understanding="No LLM client provided.",
            reasoning_summary="Strict LLM evaluation enforced but no client found.",
            missing_evidence=[],
            completeness=0.0,
            technical_validity=0.0,
            is_non_answer=True,
            uncertainty_notes=None
        )

    @classmethod
    def _is_explicit_evasion(cls, text: str) -> bool:
        """
        Delegating all evasion and joke detection to the LLM to avoid keyword brittleness.
        """
        return False

    @classmethod
    def _old_is_explicit_evasion(cls, text: str) -> bool:
        """
        Legacy method.
        """
        if not text:
            return True

        lower = text.lower().strip()
        evasion_keywords = [
            "i don't know", "i dont know", "dont know", "no idea", "not sure",
            "haven't heard", "havent heard", "never used", "cannot answer", "can't answer",
            "pass", "skip", "i am totally aware about this", "totally aware",
            "i know this very well"
        ]
        if lower in evasion_keywords:
            return True

        words = lower.split()
        if any(e in lower for e in ["dont know", "no idea", "not sure", "never used", "havent heard", "haven't heard"]):
            if len(words) <= 12 and not any(kw in lower for kw in ["because", "whereas", "however", "instead"]):
                return True

        return False

    @classmethod
    def _evaluate_via_llm(
        cls,
        question_profile: QuestionProfile,
        candidate_answer: str,
        history: List[Dict[str, Any]],
        state: Optional[InterviewState],
        resume_context: Optional[str],
        role_profile: Optional[Dict[str, Any]],
        llm_client: Any
    ) -> Optional[SemanticEvaluationResult]:
        """
        Prompts LLM to evaluate strictly according to semantic evidence principles.
        """
        recent_turns = ""
        branch_summary = ""
        pruned_topics = []
        if state and hasattr(state, "get_active_branch_summary"):
            branch_summary = state.get_active_branch_summary(question_profile.item_id)
            if hasattr(state, "get_pruned_topics_for_item") and question_profile.item_id:
                pruned_topics = state.get_pruned_topics_for_item(question_profile.item_id)

        if branch_summary:
            recent_turns = f"- Active Branch Summary Tree: {branch_summary}"
            if pruned_topics:
                recent_turns += f"\n- Pruned Sibling Branches (Explored): {', '.join(pruned_topics)}"
        elif history:
            recent_turns = "\n".join([
                f"- Turn {t.get('turn_index', i+1)} ({t.get('sender', 'INTERVIEWER')}): {t.get('text', '')}"
                for i, t in enumerate(history[-8:])
            ])

        prior_claims_str = ""
        if state and state.claims:
            prior_claims_str = "\n".join([
                f"- Claim [{c.source.value}]: {c.statement} ({c.status.value})"
                for c in list(state.claims.values())[-6:]
            ])

        system_prompt = (
            "You are a Principal Technical Interview Evaluator. Evaluate what the candidate demonstrated semantically.\n\n"
            "CRITICAL CONSTRAINTS & INVARIANTS:\n"
            "1. NEVER calculate or output final marks, points, or scoring formulas.\n"
            "2. NEVER output hidden chain-of-thought. Return concise, audit-ready reasoning summaries.\n"
            "3. RESUME IS CONTEXT, NOT AN ANSWER KEY: Do NOT penalize the candidate for omitting resume technologies or bullet points.\n"
            "4. CANDIDATE CAN INTRODUCE NEW TECHNOLOGIES/TOPICS: Extract them faithfully. Retain candidate-introduced topics.\n"
            "5. CANDIDATE CLAIMS ARE ASSERTIONS: Do not treat raw claims as proven knowledge until supported by explanation.\n"
            "6. VALID ALTERNATIVE ARCHITECTURES MUST RECEIVE CREDIT: If the candidate explains an alternative valid design "
            f"(e.g. {question_profile.valid_alternative_guidance}), mark technically_valid_alternative = true and credit objective_coverage.\n"
            f"7. PROHIBITED ASSUMPTIONS: Do NOT make any of these assumptions: {json.dumps(question_profile.prohibited_assumptions)}.\n"
            "8. CONTEXTUAL CONTRADICTIONS: Evaluate contradictions in full context: technology + project + component + role + time + scope. "
            "If scope is ambiguous or uncertain, set clarification_needed = true with clarification_reason rather than declaring the candidate wrong.\n"
            "9. FACTUAL VS REASONING OBJECTIVES:\n"
            "   - If question asks for a factual component/name (e.g. 'Which database did you use?'), a one-word answer (e.g. 'PostgreSQL') "
            "is FULLY CORRECT (correctness = 1.0, objective_coverage = 1.0, is_non_answer = false).\n"
            "   - If question asks for reasoning/trade-offs (e.g. 'Why did you choose PostgreSQL?'), a one-word answer ('PostgreSQL') "
            "has low objective_coverage because reasoning was not provided.\n"
            "10. NEVER use word count or \'<3 words\' as a non-answer indicator.\n11. EVASIONS & JOKES: If the candidate gives a non-technical joke (e.g. \'traded my bitcoins\'), deflects (e.g. \'idk\', \'I was just a technician\'), or fails to attempt a technical answer, YOU MUST set is_non_answer = true and all scores to 0.0.\n\n"
            "Output ONLY valid raw JSON matching this schema:\n"
            "{\n"
            '  "answer_understanding": "<summary of what candidate expressed>",\n'
            '  "candidate_claims": [\n'
            '    {"statement": "<claim text>", "entity": "<tech/component>", "attribute_or_action": "<detail>", "causality_valid": true|false, "is_alternative_pattern": true|false}\n'
            '  ],\n'
            '  "entities": ["<entity1>", "<entity2>"],\n'
            '  "candidate_topics": ["<topic1>", "<topic2>"],\n'
            '  "relationships": ["<relationship1>"],\n'
            '  "reasoning_summary": "<concise audit summary of technical reasoning>",\n'
            '  "objective_evidence": ["<evidence satisfying objective>"],\n'
            '  "missing_evidence": ["<specific gap in expected objective>"],\n'
            '  "correctness": <float 0.0 to 1.0>,\n'
            '  "objective_coverage": <float 0.0 to 1.0>,\n'
            '  "completeness": <float 0.0 to 1.0>,\n'
            '  "technical_validity": <float 0.0 to 1.0>,\n'
            '  "depth_demonstrated": <float 0.0 to 1.0>,\n'
            '  "reasoning_quality": <float 0.0 to 1.0 or null>,\n'
            '  "specificity": <float 0.0 to 1.0 or null>,\n'
            '  "ownership": <float 0.0 to 1.0 or null>,\n'
            '  "directness": <float 0.0 to 1.0>,\n'
            '  "confidence": <float 0.0 to 1.0>,\n'
            '  "contradictions_with_previous_answers": ["<contradiction description if any>"],\n'
            '  "resume_discrepancies": ["<neutral discrepancy description if any>"],\n'
            '  "technically_valid_alternative": true|false,\n'
            '  "clarification_needed": true|false,\n'
            '  "clarification_reason": "<reason or null>",\n'
            '  "uncertainty_notes": "<notes or null>",\n'
            '  "is_non_answer": true|false\n'
            "}"
        )

        user_prompt = (
            f"Question Profile:\n"
            f"- Question Kind: {question_profile.question_kind.value}\n"
            f"- Phase: {question_profile.phase} | Item: {question_profile.item_id or 'General'}\n"
            f"- Topic: {question_profile.topic} | Subtopic: {question_profile.subtopic or 'N/A'}\n"
            f"- Objective: {question_profile.objective}\n"
            f"- Evidence Units: {json.dumps(question_profile.evidence_units)}\n"
            f"- Expected Answer Shape: {question_profile.expected_answer_shape}\n"
            f"- Valid Alternative Guidance: {question_profile.valid_alternative_guidance}\n"
            f"- Difficulty: {question_profile.difficulty} | Follow-up Depth: {question_profile.follow_up_depth}\n"
            f"- Reasoning Requirement: {question_profile.reasoning_requirement}\n"
            f"- Specificity Requirement: {question_profile.specificity_requirement}\n\n"
            f"Prior Context:\n"
            f"Recent Turns:\n{recent_turns or 'None'}\n\n"
            f"Established State Claims:\n{prior_claims_str or 'None'}\n\n"
            f"Candidate Response:\n\"{candidate_answer}\""
        )

        try:
            completion = llm_client.generate_completion(system_prompt, user_prompt, temperature=0.1)
            if not completion:
                return None

            clean = completion.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]

            parsed = json.loads(clean.strip())
            return SemanticEvaluationResult.from_dict(parsed)
        except Exception as e:
            print(f"[AnswerEvaluator] LLM semantic evaluation parsing failed: {e}")
            return None
