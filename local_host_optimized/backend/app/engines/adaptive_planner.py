from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from backend.app.engines.interview_state import (
    InterviewState,
    ItemState,
    Claim,
    ClaimStatus,
    ClaimSource
)
from backend.app.engines.answer_evaluator import SemanticEvaluationResult


class PlannerAction(str, Enum):
    # Direct Claim & Contradiction Resolution
    CLARIFY_CONTRADICTION = "CLARIFY_CONTRADICTION"
    VERIFY_UNSUPPORTED_CLAIM = "VERIFY_UNSUPPORTED_CLAIM"
    DEEPEN_CURRENT_TOPIC = "DEEPEN_CURRENT_TOPIC"
    EXPLORE_CANDIDATE_TOPIC = "EXPLORE_CANDIDATE_TOPIC"
    EXPLORE_RESUME_TOPIC = "EXPLORE_RESUME_TOPIC"

    # Targeted Cognitive & System Dimensions
    TEST_IMPLEMENTATION = "TEST_IMPLEMENTATION"
    TEST_REASONING = "TEST_REASONING"
    TEST_TRADEOFF = "TEST_TRADEOFF"
    TEST_PERFORMANCE = "TEST_PERFORMANCE"
    TEST_SCALE = "TEST_SCALE"
    TEST_RELIABILITY = "TEST_RELIABILITY"
    TEST_FAILURE = "TEST_FAILURE"
    TEST_SECURITY = "TEST_SECURITY"
    TEST_CONCURRENCY = "TEST_CONCURRENCY"
    TEST_CONSISTENCY = "TEST_CONSISTENCY"
    TEST_ARCHITECTURE = "TEST_ARCHITECTURE"
    TEST_OPERATIONS = "TEST_OPERATIONS"
    TEST_DEBUGGING = "TEST_DEBUGGING"

    # Agenda & Phase Navigation
    PIVOT_ITEM = "PIVOT_ITEM"
    START_NEXT_ITEM = "START_NEXT_ITEM"
    START_SUBJECT_STAGE = "START_SUBJECT_STAGE"
    END_INTERVIEW = "END_INTERVIEW"


class PlannerDecision(BaseModel):
    """
    Actionable instruction produced by the AdaptivePlanner.
    Determines WHAT evidence to seek next without generating natural language.
    
    INVARIANT:
    `rationale` is stored internally for debugging and audit logs.
    It is NEVER exposed as a hidden chain-of-thought to the frontend.
    """
    action: PlannerAction
    focus_topic: str
    focus_claim_id: Optional[str] = None
    focus_entity: Optional[str] = None
    focus_dimension: str = "architecture"
    target_difficulty: float = Field(default=0.5, ge=0.0, le=1.0)
    target_depth: int = Field(default=1, ge=1)
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AdaptivePlanner:
    """
    Adaptive Interview Planning Engine.
    Dynamically orchestrates evidence-gathering based on the unified interview state.
    """

    SYSTEM_DIMENSIONS = [
        "tradeoff",
        "failure",
        "scale",
        "concurrency",
        "consistency",
        "performance",
        "reliability",
        "operations",
        "security",
        "debugging"
    ]

    @classmethod
    def plan_next_action(
        cls,
        state: InterviewState,
        latest_eval: Optional[SemanticEvaluationResult] = None,
        current_item: Optional[ItemState] = None,
        role_objectives: Optional[List[str]] = None
    ) -> PlannerDecision:
        """
        Determines the next evidence-gathering action based on current state and latest evaluation.
        """
        active_item_id = state.active_item_id
        active_item = current_item or (state.items.get(active_item_id) if active_item_id else None)
        item_title = active_item.title if active_item else "System Architecture"
        item_relevance = active_item.relevance_weight if active_item else 0.80

        # Retrieve turns spent on current item
        turns_on_item = active_item.turns_spent if active_item else state.guardrails.turns_on_current_item
        next_depth = turns_on_item + 1

        # Track previously tested dimensions on current item to avoid repetition (Rule 17)
        tested_dimensions = cls._get_tested_dimensions_for_item(state, active_item_id)

        # ----------------------------------------------------------------------
        # Priority 1: Contradictions & Clarifications (Rules 5 & 8)
        # Contradictions must be clarified before score penalty.
        # ----------------------------------------------------------------------
        if latest_eval and latest_eval.clarification_needed:
            return PlannerDecision(
                action=PlannerAction.CLARIFY_CONTRADICTION,
                focus_topic=item_title,
                focus_dimension="consistency",
                target_difficulty=0.50,
                target_depth=next_depth,
                rationale=f"Clarification required: {latest_eval.clarification_reason or 'Contextual scope ambiguity'}."
            )

        unresolved_contra = next(
            (c for c in state.contradictions if c.status in ["UNRESOLVED", "CLARIFICATION_REQUIRED"]),
            None
        )
        if unresolved_contra:
            return PlannerDecision(
                action=PlannerAction.CLARIFY_CONTRADICTION,
                focus_topic=item_title,
                focus_claim_id=unresolved_contra.claim_id_a,
                focus_dimension="consistency",
                target_difficulty=0.50,
                target_depth=next_depth,
                rationale=f"Resolving open contradiction: {unresolved_contra.description}."
            )

        # ----------------------------------------------------------------------
        # Priority 2: Non-Answer Handling (Rule 4)
        # Non-answers should not cause repeated pathological drilling.
        # ----------------------------------------------------------------------
        if latest_eval and latest_eval.is_non_answer:
            if turns_on_item >= 1:
                return cls._advance_agenda_or_phase(state, reason="Candidate deflected or stated lack of knowledge.")
            else:
                # One gentle introductory reset if at turn 1
                return PlannerDecision(
                    action=PlannerAction.TEST_IMPLEMENTATION,
                    focus_topic=item_title,
                    focus_dimension="implementation",
                    target_difficulty=0.20,
                    target_depth=1,
                    rationale="Candidate indicated lack of knowledge on initial question; offering one baseline inquiry before pivoting."
                )

        # ----------------------------------------------------------------------
        # Priority 3: Local Exploration Guardrails & Relevance Bounds (Rules 13, 14, 17)
        # Higher-relevance items receive more exploration; lower-relevance items pivot sooner.
        # ----------------------------------------------------------------------
        max_turns_for_item = cls._compute_max_turns_for_relevance(item_relevance)
        has_high_value_unresolved_claim = cls._has_high_value_unresolved_claim(state, active_item_id)

        if turns_on_item >= max_turns_for_item and not has_high_value_unresolved_claim:
            return cls._advance_agenda_or_phase(state, reason="Exploration turn budget reached for item relevance.")

        # ----------------------------------------------------------------------
        # Priority 4: Weak Evidence Handling (Rule 2)
        # Weak evidence receives at most one focused repair probe and then moves on.
        # ----------------------------------------------------------------------
        if latest_eval and latest_eval.correctness < 0.40:
            if turns_on_item >= 2:
                return cls._advance_agenda_or_phase(state, reason="Limited exploration after weak evidence response.")
            else:
                return PlannerDecision(
                    action=PlannerAction.TEST_IMPLEMENTATION,
                    focus_topic=item_title,
                    focus_dimension="implementation",
                    target_difficulty=0.30,
                    target_depth=next_depth,
                    rationale="Candidate provided weak evidence; offering one focused concrete implementation check."
                )

        # ----------------------------------------------------------------------
        # Priority 5: Candidate-Created High-Value Topics (Rule 7)
        # Candidate-volunteered topics can become active inquiry threads.
        # ----------------------------------------------------------------------
        if latest_eval and latest_eval.candidate_topics:
            untried_candidate_topics = [
                t for t in latest_eval.candidate_topics
                if t not in state.topics_covered and t in state.candidate_created_topics
            ]
            if untried_candidate_topics:
                chosen_topic = untried_candidate_topics[0]
                return PlannerDecision(
                    action=PlannerAction.EXPLORE_CANDIDATE_TOPIC,
                    focus_topic=chosen_topic,
                    focus_dimension="architecture",
                    target_difficulty=0.60,
                    target_depth=next_depth,
                    rationale=f"Candidate volunteered new topic '{chosen_topic}'. Probing its integration in this system."
                )

        # ----------------------------------------------------------------------
        # Priority 6: High-Impact Unsupported Candidate Claims (Rule 6)
        # Claims that candidate made but have not yet verified under trade-off probing.
        # ----------------------------------------------------------------------
        unsupported_claims = [
            c for c in state.claims.values()
            if c.source == ClaimSource.CANDIDATE
            and (c.item_id == active_item_id or not c.item_id)
            and c.status == ClaimStatus.MENTIONED
        ]
        if unsupported_claims and turns_on_item < max_turns_for_item:
            target_claim = unsupported_claims[0]
            dimension = cls._pick_next_untried_dimension(
                tested_dimensions,
                preferred_first=["tradeoff", "failure", "concurrency", "scale"]
            )
            return PlannerDecision(
                action=PlannerAction.VERIFY_UNSUPPORTED_CLAIM,
                focus_topic=target_claim.entity or item_title,
                focus_claim_id=target_claim.claim_id,
                focus_entity=target_claim.entity,
                focus_dimension=dimension,
                target_difficulty=0.75,
                target_depth=next_depth,
                rationale=f"Candidate asserted '{target_claim.statement}'. Verifying engineering trade-offs under {dimension}."
            )

        # ----------------------------------------------------------------------
        # Priority 7: Strong Evidence -> Deepen Meaningful Dimensions (Rules 1, 11, 12)
        # Follow-ups target situational failure, scale, concurrency, and trade-offs.
        # ----------------------------------------------------------------------
        if latest_eval and latest_eval.correctness >= 0.70 and turns_on_item < max_turns_for_item:
            dimension = cls._select_situational_dimension(
                eval_result=latest_eval,
                tested_dimensions=tested_dimensions
            )
            action_map = {
                "tradeoff": PlannerAction.TEST_TRADEOFF,
                "failure": PlannerAction.TEST_FAILURE,
                "scale": PlannerAction.TEST_SCALE,
                "concurrency": PlannerAction.TEST_CONCURRENCY,
                "consistency": PlannerAction.TEST_CONSISTENCY,
                "performance": PlannerAction.TEST_PERFORMANCE,
                "reliability": PlannerAction.TEST_RELIABILITY,
                "operations": PlannerAction.TEST_OPERATIONS,
                "security": PlannerAction.TEST_SECURITY,
                "debugging": PlannerAction.TEST_DEBUGGING,
            }
            chosen_action = action_map.get(dimension, PlannerAction.DEEPEN_CURRENT_TOPIC)
            focus_entity = latest_eval.entities[0] if latest_eval.entities else None

            return PlannerDecision(
                action=chosen_action,
                focus_topic=focus_entity or item_title,
                focus_entity=focus_entity,
                focus_dimension=dimension,
                target_difficulty=min(0.90, 0.50 + 0.15 * next_depth),
                target_depth=next_depth,
                rationale=f"Strong prior evidence demonstrated. Deepening exploration into situational {dimension}."
            )

        # ----------------------------------------------------------------------
        # Priority 8: Unexplored Resume Claims on Active Item (Rule 8)
        # Resume topics remain available and can be explored.
        # ----------------------------------------------------------------------
        unexplored_resume_claims = [
            c for c in state.claims.values()
            if c.source == ClaimSource.RESUME
            and c.item_id == active_item_id
            and c.status == ClaimStatus.UNEXPLORED
        ]
        if unexplored_resume_claims and turns_on_item < max_turns_for_item:
            target_rc = unexplored_resume_claims[0]
            return PlannerDecision(
                action=PlannerAction.EXPLORE_RESUME_TOPIC,
                focus_topic=target_rc.entity or item_title,
                focus_claim_id=target_rc.claim_id,
                focus_entity=target_rc.entity,
                focus_dimension="architecture",
                target_difficulty=0.55,
                target_depth=next_depth,
                rationale=f"Exploring unvisited resume background claim '{target_rc.statement}'."
            )

        # ----------------------------------------------------------------------
        # Priority 9: Item Exhausted -> Advance Agenda or Phase (Rules 19 & 20)
        # Pivots through all Work Experience & Projects before Subject Knowledge.
        # ----------------------------------------------------------------------
        return cls._advance_agenda_or_phase(state, reason="Active item exploration concluded.")

    @classmethod
    def _compute_max_turns_for_relevance(cls, relevance: float) -> int:
        """
        Rules 13 & 14: Higher-relevance items receive more turns; lower-relevance items fewer.
        """
        if relevance >= 0.85:
            return 5
        elif relevance >= 0.70:
            return 4
        elif relevance >= 0.50:
            return 3
        else:
            return 2

    @classmethod
    def _has_high_value_unresolved_claim(cls, state: InterviewState, item_id: Optional[str]) -> bool:
        """
        Rule 18: Strong unresolved high-value evidence can override normal exploration limits.
        """
        for c in state.claims.values():
            if (c.item_id == item_id or not item_id) and c.status == ClaimStatus.CLARIFICATION_REQUIRED:
                return True
        return False

    @classmethod
    def _get_tested_dimensions_for_item(cls, state: InterviewState, item_id: Optional[str]) -> Set[str]:
        """
        Extracts all dimensions already tested on this specific item to prevent repetition (Rule 17).
        """
        tested = set()
        for p in state.planner_history:
            # Check matching planner entries for current item thread
            action_name = p.action.lower()
            for dim in cls.SYSTEM_DIMENSIONS:
                if dim in action_name or dim in p.rationale.lower():
                    tested.add(dim)
        return tested

    @classmethod
    def _pick_next_untried_dimension(
        cls,
        tested_dimensions: Set[str],
        preferred_first: List[str]
    ) -> str:
        """
        Rule 17: Prevents repeatedly testing the same dimension.
        """
        for pref in preferred_first:
            if pref not in tested_dimensions:
                return pref

        for fallback in cls.SYSTEM_DIMENSIONS:
            if fallback not in tested_dimensions:
                return fallback

        return "tradeoff"

    @classmethod
    def _select_situational_dimension(
        cls,
        eval_result: SemanticEvaluationResult,
        tested_dimensions: Set[str]
    ) -> str:
        """
        Rule 12: Derives situational dimensions from actual candidate claims/entities.
        Example: Redis -> failure/invalidation; Kafka -> scale/partitioning; PostgreSQL -> transactions/consistency.
        """
        entities_text = " ".join(eval_result.entities).lower()

        # Situational heuristic 1: Caching systems
        if ("redis" in entities_text or "cache" in entities_text or "memcached" in entities_text):
            if "failure" not in tested_dimensions:
                return "failure"
            if "tradeoff" not in tested_dimensions:
                return "tradeoff"

        # Situational heuristic 2: Streaming / Queues
        if ("kafka" in entities_text or "queue" in entities_text or "rabbitmq" in entities_text):
            if "scale" not in tested_dimensions:
                return "scale"
            if "concurrency" not in tested_dimensions:
                return "concurrency"

        # Situational heuristic 3: Databases / Consensus
        if ("postgres" in entities_text or "sql" in entities_text or "raft" in entities_text or "cassandra" in entities_text):
            if "consistency" not in tested_dimensions:
                return "consistency"
            if "concurrency" not in tested_dimensions:
                return "concurrency"

        return cls._pick_next_untried_dimension(
            tested_dimensions,
            preferred_first=["tradeoff", "failure", "scale", "concurrency", "consistency", "operations"]
        )

    @classmethod
    def _advance_agenda_or_phase(cls, state: InterviewState, reason: str = "") -> PlannerDecision:
        """
        Rules 19 & 20:
        Transitions through all Work Experience items, then all Projects,
        and starts Subject Knowledge ONLY after all experience items have finished.
        """
        curr_active_id = state.active_item_id
        if curr_active_id and curr_active_id in state.items:
            state.conclude_active_item(reason="COMPLETED")

        # Find next pending item in item_order
        pending_items = [
            state.items[iid] for iid in state.item_order
            if state.items[iid].status == "PENDING"
        ]

        # 1. Experience & Projects Phase
        exp_proj_pending = [
            item for item in pending_items
            if item.phase in ["EXPERIENCE_DEFENSE", "PROJECT_DEFENSE"]
        ]

        if exp_proj_pending:
            next_item = exp_proj_pending[0]
            state.start_item(next_item.item_id)
            return PlannerDecision(
                action=PlannerAction.START_NEXT_ITEM,
                focus_topic=next_item.title,
                focus_dimension="architecture",
                target_difficulty=0.50,
                target_depth=1,
                rationale=f"Advancing to next agenda item '{next_item.title}' in phase {next_item.phase}. ({reason})"
            )

        # 2. Subject Knowledge Phase (Begins only after all experience & projects finish)
        subject_pending = [
            item for item in pending_items
            if item.phase == "SUBJECT_KNOWLEDGE"
        ]

        if subject_pending:
            next_subj = subject_pending[0]
            was_prior_subject = (state.current_phase == "SUBJECT_KNOWLEDGE")
            state.start_item(next_subj.item_id)
            action = PlannerAction.START_NEXT_ITEM if was_prior_subject else PlannerAction.START_SUBJECT_STAGE
            return PlannerDecision(
                action=action,
                focus_topic=next_subj.title,
                focus_dimension="reasoning",
                target_difficulty=0.70,
                target_depth=1,
                rationale=f"All experience items defended. Initiating subject knowledge stage for '{next_subj.title}'."
            )

        # 3. All items complete -> End Interview
        state.current_phase = "COMPLETED"
        return PlannerDecision(
            action=PlannerAction.END_INTERVIEW,
            focus_topic="Conclusion",
            focus_dimension="summary",
            target_difficulty=0.20,
            target_depth=1,
            rationale="All work experience, projects, and subject knowledge stages successfully concluded."
        )
