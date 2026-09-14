from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    UNEXPLORED = "UNEXPLORED"
    MENTIONED = "MENTIONED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    SUPPORTED = "SUPPORTED"
    STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"


class ClaimSource(str, Enum):
    RESUME = "resume"
    CANDIDATE = "candidate"


class Claim(BaseModel):
    claim_id: str
    source: ClaimSource  # "resume" | "candidate"
    item_id: Optional[str] = None  # e.g., work exp ID or project ID
    statement: str
    entity: Optional[str] = None
    status: ClaimStatus = ClaimStatus.UNEXPLORED
    turn_first_seen: int = 0
    turn_last_updated: int = 0
    supporting_turns: List[int] = Field(default_factory=list)
    contradicting_turns: List[int] = Field(default_factory=list)
    confidence: float = 1.0
    notes: Optional[str] = None


class SemanticEvidence(BaseModel):
    evidence_id: str
    turn_index: int
    item_id: Optional[str] = None
    claim_ids: List[str] = Field(default_factory=list)
    topic: str
    subtopic: Optional[str] = None
    observation: str
    evidence_strength: str = "MODERATE"  # "WEAK" | "MODERATE" | "STRONG"
    is_falsifying: bool = False
    invalidated_assumption_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Contradiction(BaseModel):
    contradiction_id: str
    turn_detected: int
    item_id: Optional[str] = None
    claim_id_a: str
    claim_id_b: Optional[str] = None
    description: str
    severity: str = "MODERATE"  # "MINOR" | "MODERATE" | "SEVERE"
    status: str = "UNRESOLVED"  # "UNRESOLVED" | "CLARIFICATION_REQUIRED" | "RESOLVED" | "DISMISSED"
    clarification_prompt: Optional[str] = None
    resolution_notes: Optional[str] = None
    turn_resolved: Optional[int] = None


class UnresolvedIssue(BaseModel):
    issue_id: str
    turn_detected: int
    issue_type: str  # "CONTRADICTION" | "AMBIGUITY" | "UNSUPPORTED_SPEC" | "UNVERIFIED_ASSERTION"
    target_claim_id: Optional[str] = None
    description: str
    status: str = "OPEN"  # "OPEN" | "IN_PROGRESS" | "RESOLVED"


class Objective(BaseModel):
    objective_id: str
    title: str
    description: str
    phase: str
    item_id: Optional[str] = None
    is_satisfied: bool = False
    evidence_ids: List[str] = Field(default_factory=list)


class QuestionHistoryEntry(BaseModel):
    question_id: str
    turn_index: int
    phase: str
    item_id: Optional[str] = None
    topic: str
    subtopic: Optional[str] = None
    question_text: str
    planner_action: Optional[str] = None
    target_difficulty: Optional[str] = None
    question_profile: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ItemState(BaseModel):
    item_id: str
    item_type: str  # "WORK_EXPERIENCE" | "PROJECT" | "SUBJECT_TOPIC"
    phase: str      # "EXPERIENCE_DEFENSE" | "PROJECT_DEFENSE" | "SUBJECT_KNOWLEDGE"
    title: str
    details: str = ""
    relevance_weight: float = 1.0
    status: str = "PENDING"  # "PENDING" | "IN_PROGRESS" | "COMPLETED" | "PIVOTED"
    turns_spent: int = 0
    claims_established: List[str] = Field(default_factory=list)
    claims_verified: List[str] = Field(default_factory=list)
    topics_covered: List[str] = Field(default_factory=list)
    completion_reason: Optional[str] = None


class SubjectCoverageItem(BaseModel):
    topic: str
    subtopics: List[str] = Field(default_factory=list)
    status: str = "UNTESTED"  # "UNTESTED" | "EXPLORING" | "STRONG" | "PARTIAL" | "WEAK"
    turns_tested: int = 0
    evidence_ids: List[str] = Field(default_factory=list)


class PlannerHistoryEntry(BaseModel):
    turn_index: int
    action: str
    focus_topic: str
    focus_claim_id: Optional[str] = None
    target_difficulty: Optional[str] = None
    rationale: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExplorationGuardrails(BaseModel):
    total_turns: int = 0
    turns_on_current_item: int = 0
    clarification_attempts_current_item: int = 0
    max_turns_per_item: int = 6
    max_clarification_attempts_per_item: int = 2
    max_total_turns: int = 30
    min_turns_per_item: int = 1


class InterviewerAssumption(BaseModel):
    assumption_id: str
    statement: str
    item_id: Optional[str] = None
    turn_recorded: int = 0
    is_invalidated: bool = False
    invalidating_evidence_id: Optional[str] = None
    invalidation_notes: Optional[str] = None


# Known distinct technologies that share prefix or substring similarities
# but MUST NOT be merged or treated as interchangeable
DISTINCT_TECH_PAIRS = [
    ({"postgres", "postgresql"}, {"postgis"}),
    ({"redis"}, {"redshift"}),
    ({"java"}, {"javascript"}),
    ({"c"}, {"c++", "c#"}),
    ({"react"}, {"react native"}),
    ({"kafka"}, {"kafka connect"}),
    ({"docker"}, {"docker swarm"}),
    ({"mysql"}, {"mssql"}),
]


def are_distinct_technologies(entity_a: Optional[str], entity_b: Optional[str]) -> bool:
    """
    Returns True if entity_a and entity_b are known distinct technologies
    that must not be merged even if one name is a substring or prefix of another.
    """
    if not entity_a or not entity_b:
        return False
    ea = entity_a.strip().lower()
    eb = entity_b.strip().lower()
    if ea == eb:
        return False

    for group_1, group_2 in DISTINCT_TECH_PAIRS:
        if (ea in group_1 and eb in group_2) or (ea in group_2 and eb in group_1):
            return True
    return False


class InterviewState(BaseModel):
    """
    Unified Interview State Layer.
    Persisted deterministically inside InterviewSession.agent1_report_json['unified_state'].
    """
    state_version: str = "1.0.0"
    session_id: str
    current_phase: str = "EXPERIENCE_DEFENSE"
    active_item_id: Optional[str] = None

    # Claims: Dual-layer store separating contextual resume claims from candidate assertions
    claims: Dict[str, Claim] = Field(default_factory=dict)

    # Topics: Persistent, non-destructive topic retention
    topics: List[str] = Field(default_factory=list)
    candidate_created_topics: List[str] = Field(default_factory=list)
    topics_covered: List[str] = Field(default_factory=list)

    # Agenda Items
    items: Dict[str, ItemState] = Field(default_factory=dict)
    item_order: List[str] = Field(default_factory=list)
    completed_item_ids: List[str] = Field(default_factory=list)
    pivoted_item_ids: List[str] = Field(default_factory=list)

    # Objectives & Evidence
    objectives: Dict[str, Objective] = Field(default_factory=dict)
    evidence: List[SemanticEvidence] = Field(default_factory=list)

    # Question & Issue Tracking
    question_history: List[QuestionHistoryEntry] = Field(default_factory=list)
    unresolved_issues: List[UnresolvedIssue] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)

    # Subject Coverage
    subject_coverage: Dict[str, SubjectCoverageItem] = Field(default_factory=dict)

    # Planner History & Guardrails
    planner_history: List[PlannerHistoryEntry] = Field(default_factory=list)
    guardrails: ExplorationGuardrails = Field(default_factory=ExplorationGuardrails)

    # Interviewer Assumptions (Subject to candidate refutation)
    interviewer_assumptions: Dict[str, InterviewerAssumption] = Field(default_factory=dict)

    # --------------------------------------------------------------------------
    # Deterministic State Update / Merge Helpers
    # --------------------------------------------------------------------------

    def register_resume_claim(
        self,
        statement: str,
        item_id: Optional[str] = None,
        entity: Optional[str] = None,
        claim_id: Optional[str] = None,
        attribute: Optional[str] = None,
        topics: Optional[List[str]] = None,
        **kwargs
    ) -> Claim:
        """
        Rule 1: Resume claim starts strictly as UNEXPLORED.
        Resume claims are contextual evidence, NOT proof of candidate knowledge.
        """
        cid = claim_id or f"rc_{len(self.claims) + 1}_{entity or 'gen'}"
        claim = Claim(
            claim_id=cid,
            source=ClaimSource.RESUME,
            item_id=item_id,
            statement=statement.strip(),
            entity=entity.strip() if entity else None,
            status=ClaimStatus.UNEXPLORED,
            turn_first_seen=0,
            turn_last_updated=0
        )
        self.claims[cid] = claim
        if item_id and item_id in self.items:
            if cid not in self.items[item_id].claims_established:
                self.items[item_id].claims_established.append(cid)
        return claim

    def record_candidate_claim(
        self,
        statement: str,
        item_id: Optional[str] = None,
        entity: Optional[str] = None,
        turn_index: int = 1,
        initial_status: ClaimStatus = ClaimStatus.MENTIONED,
        claim_id: Optional[str] = None,
        attribute: Optional[str] = None,
        topics: Optional[List[str]] = None,
        verified: bool = False,
        **kwargs
    ) -> Claim:
        """
        Rule 5: Candidate-created claims start strictly as MENTIONED or UNVERIFIED.
        A candidate claim is an assertion, NOT automatically proven knowledge.
        """
        if verified:
            initial_status = ClaimStatus.SUPPORTED
        elif initial_status not in [ClaimStatus.MENTIONED, ClaimStatus.UNVERIFIED]:
            initial_status = ClaimStatus.MENTIONED
            initial_status = ClaimStatus.MENTIONED

        cid = claim_id or f"cc_{len(self.claims) + 1}_{entity or 'gen'}"
        claim = Claim(
            claim_id=cid,
            source=ClaimSource.CANDIDATE,
            item_id=item_id or self.active_item_id,
            statement=statement.strip(),
            entity=entity.strip() if entity else None,
            status=initial_status,
            turn_first_seen=turn_index,
            turn_last_updated=turn_index,
            supporting_turns=[turn_index]
        )
        self.claims[cid] = claim

        act_id = item_id or self.active_item_id
        if act_id and act_id in self.items:
            if cid not in self.items[act_id].claims_established:
                self.items[act_id].claims_established.append(cid)
        return claim

    def record_candidate_mention_of_resume_claim(
        self,
        claim_id: str,
        turn_index: int
    ) -> Optional[Claim]:
        """
        Rule 2: Candidate mentioning a resume claim changes it to MENTIONED, NOT SUPPORTED.
        """
        claim = self.claims.get(claim_id)
        if not claim:
            return None

        # Only transition from UNEXPLORED to MENTIONED upon verbal mention
        if claim.status == ClaimStatus.UNEXPLORED:
            claim.status = ClaimStatus.MENTIONED

        claim.turn_last_updated = turn_index
        if turn_index not in claim.supporting_turns:
            claim.supporting_turns.append(turn_index)
        return claim

    def record_evidence_for_claim(
        self,
        claim_id: str,
        evidence_strength: str,
        turn_index: int,
        observation: str,
        topic: str = "System Architecture",
        subtopic: Optional[str] = None,
        item_id: Optional[str] = None
    ) -> Tuple[Optional[Claim], SemanticEvidence]:
        """
        Rule 3: Actual evidence moves claim toward PARTIALLY_SUPPORTED, SUPPORTED, STRONGLY_SUPPORTED.
        """
        claim = self.claims.get(claim_id)
        current_item = item_id or self.active_item_id

        # Determine progression
        strength = evidence_strength.upper().strip()
        if claim:
            if strength == "WEAK":
                if claim.status in [ClaimStatus.UNEXPLORED, ClaimStatus.MENTIONED]:
                    claim.status = ClaimStatus.PARTIALLY_SUPPORTED
            elif strength == "MODERATE":
                if claim.status in [ClaimStatus.UNEXPLORED, ClaimStatus.MENTIONED, ClaimStatus.PARTIALLY_SUPPORTED]:
                    claim.status = ClaimStatus.SUPPORTED
            elif strength == "STRONG":
                claim.status = ClaimStatus.STRONGLY_SUPPORTED

            claim.turn_last_updated = turn_index
            if turn_index not in claim.supporting_turns:
                claim.supporting_turns.append(turn_index)

            if current_item and current_item in self.items:
                if claim.status in [ClaimStatus.SUPPORTED, ClaimStatus.STRONGLY_SUPPORTED]:
                    if claim_id not in self.items[current_item].claims_verified:
                        self.items[current_item].claims_verified.append(claim_id)

        ev_id = f"ev_{len(self.evidence) + 1}_t{turn_index}"
        ev = SemanticEvidence(
            evidence_id=ev_id,
            turn_index=turn_index,
            item_id=current_item,
            claim_ids=[claim_id] if claim else [],
            topic=topic,
            subtopic=subtopic,
            observation=observation,
            evidence_strength=strength
        )
        self.evidence.append(ev)
        return claim, ev

    def add_candidate_topic(self, topic: str) -> bool:
        """
        Rule 4: Candidate-created topics must be retained.
        Rule 7: Never delete old topics or claims.
        """
        clean_topic = topic.strip()
        if not clean_topic:
            return False

        if clean_topic not in self.candidate_created_topics:
            self.candidate_created_topics.append(clean_topic)

        if clean_topic not in self.topics:
            self.topics.append(clean_topic)
            return True
        return False

    def add_topic(self, topic: str) -> bool:
        """
        Rule 7: Never delete old topics. Adds standard topic if not present.
        """
        clean = topic.strip()
        if clean and clean not in self.topics:
            self.topics.append(clean)
            return True
        return False

    def can_merge_claims(self, claim_a: Claim, claim_b: Claim) -> bool:
        """
        Rule 8: Do not incorrectly merge distinct technologies/components
        just because their names are similar.
        """
        if claim_a.claim_id == claim_b.claim_id:
            return False

        # If entities are recognized as distinct technologies, never merge
        if are_distinct_technologies(claim_a.entity, claim_b.entity):
            return False

        # Same entity and exact statement matching
        if claim_a.entity and claim_b.entity and claim_a.entity.lower() == claim_b.entity.lower():
            if claim_a.statement.lower() == claim_b.statement.lower():
                return True

        return False

    def record_interviewer_assumption(
        self,
        assumption_id: str,
        statement: str,
        item_id: Optional[str] = None,
        turn_index: int = 0
    ) -> InterviewerAssumption:
        """
        Registers an interviewer's assumption for tracking.
        """
        assump = InterviewerAssumption(
            assumption_id=assumption_id,
            statement=statement.strip(),
            item_id=item_id or self.active_item_id,
            turn_recorded=turn_index,
            is_invalidated=False
        )
        self.interviewer_assumptions[assumption_id] = assump
        return assump

    def invalidate_interviewer_assumption(
        self,
        assumption_id: str,
        candidate_evidence_text: str,
        turn_index: int
    ) -> Optional[InterviewerAssumption]:
        """
        Rule 9: Candidate evidence can invalidate assumptions made by the interviewer.
        """
        assump = self.interviewer_assumptions.get(assumption_id)
        if not assump:
            return None

        assump.is_invalidated = True
        assump.invalidation_notes = candidate_evidence_text.strip()

        # Record a falsifying semantic evidence entry
        ev_id = f"ev_falsify_{len(self.evidence) + 1}_t{turn_index}"
        falsifying_ev = SemanticEvidence(
            evidence_id=ev_id,
            turn_index=turn_index,
            item_id=assump.item_id,
            topic="Assumption Invalidation",
            observation=f"Candidate evidence refuted interviewer assumption: '{assump.statement}'. Evidence: {candidate_evidence_text}",
            evidence_strength="STRONG",
            is_falsifying=True,
            invalidated_assumption_id=assumption_id
        )
        self.evidence.append(falsifying_ev)
        assump.invalidating_evidence_id = ev_id
        return assump

    def record_contradiction(
        self,
        claim_id_a: str,
        description: str = "",
        claim_id_b: Optional[str] = None,
        turn_index: int = 0,
        severity: str = "MODERATE",
        is_uncertain: bool = True,
        item_id: Optional[str] = None,
        **kwargs
    ) -> Contradiction:
        """
        Rule 10: Contradictions must be stored as unresolved/clarification-required
        when context is uncertain.
        """
        cid = f"contra_{len(self.contradictions) + 1}_t{turn_index}"
        contra = Contradiction(
            contradiction_id=cid,
            turn_detected=turn_index,
            item_id=item_id or self.active_item_id,
            claim_id_a=claim_id_a,
            claim_id_b=claim_id_b,
            description=description.strip(),
            severity=severity,
            status="CLARIFICATION_REQUIRED" if is_uncertain else "UNRESOLVED"
        )
        self.contradictions.append(contra)

        # Update affected claims
        claim_a = self.claims.get(claim_id_a)
        if claim_a:
            claim_a.status = ClaimStatus.CLARIFICATION_REQUIRED if is_uncertain else ClaimStatus.CONTRADICTED
            if turn_index not in claim_a.contradicting_turns:
                claim_a.contradicting_turns.append(turn_index)

        if claim_id_b:
            claim_b = self.claims.get(claim_id_b)
            if claim_b:
                claim_b.status = ClaimStatus.CLARIFICATION_REQUIRED if is_uncertain else ClaimStatus.CONTRADICTED
                if turn_index not in claim_b.contradicting_turns:
                    claim_b.contradicting_turns.append(turn_index)

        # Register an open unresolved issue
        issue_id = f"issue_{len(self.unresolved_issues) + 1}"
        self.unresolved_issues.append(
            UnresolvedIssue(
                issue_id=issue_id,
                turn_detected=turn_index,
                issue_type="CONTRADICTION",
                target_claim_id=claim_id_a,
                description=description.strip(),
                status="OPEN"
            )
        )
        return contra

    def resolve_contradiction(
        self,
        contradiction_id: str,
        resolution_notes: str,
        turn_index: int,
        resolved_status_for_claim_a: ClaimStatus = ClaimStatus.SUPPORTED
    ) -> bool:
        """
        Resolves an existing contradiction when the candidate provides clarification.
        """
        contra = next((c for c in self.contradictions if c.contradiction_id == contradiction_id), None)
        if not contra:
            return False

        contra.status = "RESOLVED"
        contra.resolution_notes = resolution_notes.strip()
        contra.turn_resolved = turn_index

        claim_a = self.claims.get(contra.claim_id_a)
        if claim_a:
            claim_a.status = resolved_status_for_claim_a
            claim_a.turn_last_updated = turn_index

        # Close corresponding unresolved issue
        for issue in self.unresolved_issues:
            if issue.target_claim_id == contra.claim_id_a and issue.status == "OPEN":
                issue.status = "RESOLVED"
        return True

    def register_item(
        self,
        item_id: str,
        item_type: str,
        phase: str,
        title: str,
        details: str = "",
        relevance_weight: float = 1.0
    ) -> ItemState:
        """
        Registers an agenda item (Work Experience, Project, or Subject Topic).
        """
        item = ItemState(
            item_id=item_id,
            item_type=item_type,
            phase=phase,
            title=title.strip(),
            details=details.strip(),
            relevance_weight=relevance_weight,
            status="PENDING"
        )
        self.items[item_id] = item
        if item_id not in self.item_order:
            self.item_order.append(item_id)
        if not self.active_item_id:
            self.active_item_id = item_id
            item.status = "IN_PROGRESS"
        return item

    def start_item(self, item_id: str) -> bool:
        """
        Transitions active focus to a new agenda item.
        """
        if item_id not in self.items:
            return False
        self.active_item_id = item_id
        item = self.items[item_id]
        item.status = "IN_PROGRESS"
        self.current_phase = item.phase
        self.guardrails.turns_on_current_item = 0
        self.guardrails.clarification_attempts_current_item = 0
        return True

    def conclude_active_item(self, reason: str = "COMPLETED") -> Optional[str]:
        """
        Concludes or pivots away from the active item.
        """
        if not self.active_item_id or self.active_item_id not in self.items:
            return None

        curr_id = self.active_item_id
        item = self.items[curr_id]
        item.completion_reason = reason
        if reason == "PIVOTED":
            item.status = "PIVOTED"
            if curr_id not in self.pivoted_item_ids:
                self.pivoted_item_ids.append(curr_id)
        else:
            item.status = "COMPLETED"
            if curr_id not in self.completed_item_ids:
                self.completed_item_ids.append(curr_id)

        return curr_id

    def record_turn(
        self,
        question_id: str,
        turn_index: int,
        topic: str,
        question_text: str,
        subtopic: Optional[str] = None,
        planner_action: Optional[str] = None,
        target_difficulty: Optional[str] = None,
        question_profile: Optional[Any] = None,
        **kwargs
    ) -> QuestionHistoryEntry:
        """
        Updates question history and exploration guardrail counters.
        Persists associated QuestionProfile with the question history entry.
        """
        qp_dict = None
        if question_profile is not None:
            if hasattr(question_profile, "to_dict"):
                qp_dict = question_profile.to_dict()
            elif hasattr(question_profile, "model_dump"):
                qp_dict = question_profile.model_dump()
            elif isinstance(question_profile, dict):
                qp_dict = question_profile

        entry = QuestionHistoryEntry(
            question_id=question_id,
            turn_index=turn_index,
            phase=self.current_phase,
            item_id=self.active_item_id,
            topic=topic,
            subtopic=subtopic,
            question_text=question_text,
            planner_action=planner_action,
            target_difficulty=target_difficulty,
            question_profile=qp_dict
        )
        self.question_history.append(entry)
        self.guardrails.total_turns += 1
        self.guardrails.turns_on_current_item += 1

        if self.active_item_id and self.active_item_id in self.items:
            self.items[self.active_item_id].turns_spent += 1

        self.add_topic(topic)
        return entry

    def record_planner_action(
        self,
        turn_index: int = 0,
        action: str = "",
        focus_topic: str = "",
        focus_claim_id: Optional[str] = None,
        target_difficulty: Optional[str] = None,
        rationale: str = "",
        **kwargs
    ) -> None:
        """
        Records internal planner telemetry without exposing chain-of-thought to candidate.
        """
        entry = PlannerHistoryEntry(
            turn_index=turn_index,
            action=action,
            focus_topic=focus_topic,
            focus_claim_id=focus_claim_id,
            target_difficulty=target_difficulty,
            rationale=rationale
        )
        self.planner_history.append(entry)

    # --------------------------------------------------------------------------
    # Serialization & Deserialization Helpers (Safe JSON Storage)
    # --------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes unified state to a JSON-compatible dictionary.
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]], session_id: str = "") -> "InterviewState":
        """
        Deterministically loads state from JSON storage. Handles state_version safety.
        """
        if not data:
            return cls(session_id=session_id)

        try:
            return cls.model_validate(data)
        except Exception:
            # Fallback for backward compatibility with partial or pre-refactor dicts
            return cls(
                state_version=data.get("state_version", "1.0.0"),
                session_id=data.get("session_id", session_id),
                current_phase=data.get("current_phase", "EXPERIENCE_DEFENSE"),
                active_item_id=data.get("active_item_id"),
                topics=data.get("topics", []),
                candidate_created_topics=data.get("candidate_created_topics", [])
            )
