from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class QuestionKind(str, Enum):
    CONCEPTUAL_OVERVIEW = "CONCEPTUAL_OVERVIEW"
    ARCHITECTURAL_CHOICE = "ARCHITECTURAL_CHOICE"
    TRADE_OFF_ANALYSIS = "TRADE_OFF_ANALYSIS"
    FAILURE_RECOVERY = "FAILURE_RECOVERY"
    SCALE_PERFORMANCE = "SCALE_PERFORMANCE"
    IMPLEMENTATION_DETAIL = "IMPLEMENTATION_DETAIL"
    CONCURRENCY_SYNC = "CONCURRENCY_SYNC"
    DEBUGGING_DIAGNOSTIC = "DEBUGGING_DIAGNOSTIC"
    SPECIFICATION_PROBE = "SPECIFICATION_PROBE"
    CONTRADICTION_RESOLUTION = "CONTRADICTION_RESOLUTION"


class QuestionProfile(BaseModel):
    """
    Multidimensional representation of what an interview question is testing.
    
    CRITICAL INVARIANT:
    Difficulty and follow-up depth are strictly independent dimensions.
    - An introductory question can be difficult (e.g., depth=1, difficulty=0.85)
    - A follow-up question can be easy/factual (e.g., depth=4, difficulty=0.20)
    
    The profile defines objective targets, evidence units, and alternative guidance
    rather than a rigid single expected answer.
    """
    question_id: str
    objective: str
    evidence_units: List[str] = Field(
        default_factory=list,
        description="Specific observable pieces of evidence that satisfy the objective"
    )
    phase: str = "PROJECT_DEFENSE"
    item_id: Optional[str] = None
    item_type: str = "PROJECT"  # WORK_EXPERIENCE | PROJECT | SUBJECT_TOPIC
    topic: str
    subtopic: Optional[str] = None

    # Continuous multidimensional attributes normalized to [0, 1]
    difficulty: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Intrinsic difficulty of the question concept [0, 1]"
    )
    follow_up_depth: int = Field(
        default=1,
        ge=1,
        description="Turn depth level within the current item thread (decoupled from difficulty)"
    )
    cognitive_complexity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Recall (0.0) vs synthesis/design/evaluation (1.0)"
    )
    technical_complexity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="High-level architecture (0.2) vs low-level kernel/internals/protocol (1.0)"
    )
    reasoning_requirement: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Simple statement (0.0) vs formal trade-off justification and proof (1.0)"
    )
    specificity_requirement: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="High-level directional answer (0.2) vs exact parameters/metrics/APIs (1.0)"
    )
    breadth: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Narrow focused question (0.1) vs broad cross-system impact (1.0)"
    )
    role_relevance: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Direct alignment with the target role and seniority [0, 1]"
    )
    objective_importance: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Weight multiplier for question objective priority [0, 1]"
    )

    # Question Semantics & Flexibility Criteria
    question_kind: QuestionKind = QuestionKind.ARCHITECTURAL_CHOICE
    expected_answer_shape: str = Field(
        default="Candidate articulates the chosen design or mechanism and explains the engineering rationale.",
        description="Structural shape expected, NOT a single required answer."
    )
    valid_alternative_guidance: str = Field(
        default="Accept any technically sound alternative architecture or pattern that achieves the objective with valid causality.",
        description="Instructions on valid alternative technologies and trade-offs."
    )
    prohibited_assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions the question or evaluator must NOT make about candidate's environment."
    )

    @field_validator(
        "difficulty",
        "cognitive_complexity",
        "technical_complexity",
        "reasoning_requirement",
        "specificity_requirement",
        "breadth",
        "role_relevance",
        "objective_importance",
        mode="before"
    )
    @classmethod
    def clamp_or_validate_range(cls, v: Any) -> float:
        try:
            val = float(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Value must be a valid float, got {v}") from e
        if val < 0.0 or val > 1.0:
            raise ValueError(f"Value must be within normalized range [0.0, 1.0], got {val}")
        return round(val, 4)

    @field_validator("follow_up_depth", mode="before")
    @classmethod
    def validate_depth(cls, v: Any) -> int:
        try:
            val = int(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Depth must be an integer, got {v}") from e
        if val < 1:
            raise ValueError(f"Follow-up depth must be >= 1, got {val}")
        return val

    def difficulty_category(self) -> str:
        """
        Categorical difficulty helper for downstream displays or reporting.
        """
        if self.difficulty < 0.35:
            return "EASY"
        elif self.difficulty <= 0.70:
            return "MEDIUM"
        else:
            return "HARD"

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes profile to a JSON-compatible dictionary.
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuestionProfile":
        """
        Deserializes profile from a dictionary with strict validation.
        """
        return cls.model_validate(data)

    @classmethod
    def from_planner_decision(
        cls,
        question_id: str,
        decision: Any,
        item: Optional[Any] = None,
        phase: str = "PROJECT_DEFENSE",
        role: str = "Software Engineer"
    ) -> "QuestionProfile":
        """
        Constructs a QuestionProfile from a PlannerDecision and item context.
        """
        focus_topic = getattr(decision, "focus_topic", "Technical Architecture") or "Technical Architecture"
        focus_dim = getattr(decision, "focus_dimension", "architecture") or "architecture"
        difficulty = float(getattr(decision, "target_difficulty", 0.50))
        depth = int(getattr(decision, "target_depth", 1))
        action_val = decision.action.value if hasattr(decision.action, "value") else str(decision.action)

        item_id = getattr(item, "item_id", None) if item else None
        item_type = getattr(item, "item_type", "PROJECT") if item else ("WORK_EXPERIENCE" if "EXPERIENCE" in phase else "PROJECT")

        # Map focus dimension and action to QuestionKind & expectations
        if action_val == "CLARIFY_CONTRADICTION":
            kind = QuestionKind.CONTRADICTION_RESOLUTION
            objective = f"Clarify apparent technical inconsistency regarding {focus_topic} in {focus_dim}."
            cog_comp = 0.50
            tech_comp = 0.50
            reas_req = 0.40
            spec_req = 0.60
            evidence_units = [f"Clarification of {focus_dim} in {focus_topic}", "Resolution of component or context ambiguity"]
        elif focus_dim == "tradeoff":
            kind = QuestionKind.TRADE_OFF_ANALYSIS
            objective = f"Articulate engineering trade-offs and rationale behind technology choices in {focus_topic}."
            cog_comp = max(0.60, difficulty)
            tech_comp = 0.60
            reas_req = 0.80
            spec_req = 0.60
            evidence_units = [f"Trade-off analysis of {focus_topic}", "Alternative architectures evaluated", "Performance vs complexity trade-offs"]
        elif focus_dim == "failure":
            kind = QuestionKind.FAILURE_RECOVERY
            objective = f"Explain fault tolerance, circuit breaking, fallback, or recovery mechanisms for {focus_topic}."
            cog_comp = max(0.65, difficulty)
            tech_comp = 0.70
            reas_req = 0.75
            spec_req = 0.65
            evidence_units = [f"Failure mode identification in {focus_topic}", "Graceful degradation strategy", "Data consistency preservation under failure"]
        elif focus_dim in ["scale", "performance"]:
            kind = QuestionKind.SCALE_PERFORMANCE
            objective = f"Identify bottlenecks, latency optimizations, and horizontal scaling strategies for {focus_topic}."
            cog_comp = max(0.60, difficulty)
            tech_comp = 0.75
            reas_req = 0.70
            spec_req = 0.70
            evidence_units = [f"Scaling bottleneck identification in {focus_topic}", "Caching/partitioning optimization", "Latency and throughput trade-offs"]
        elif focus_dim == "concurrency":
            kind = QuestionKind.CONCURRENCY_SYNC
            objective = f"Explain race condition prevention, locking, transaction isolation, or distributed state management in {focus_topic}."
            cog_comp = max(0.70, difficulty)
            tech_comp = 0.85
            reas_req = 0.80
            spec_req = 0.75
            evidence_units = [f"Thread safety or distributed locking in {focus_topic}", "Transaction isolation semantics", "Deadlock avoidance"]
        elif focus_dim == "debugging":
            kind = QuestionKind.DEBUGGING_DIAGNOSTIC
            objective = f"Diagnose root causes using telemetry, distributed tracing, profiling, or logs for {focus_topic}."
            cog_comp = max(0.60, difficulty)
            tech_comp = 0.80
            reas_req = 0.70
            spec_req = 0.70
            evidence_units = [f"Profiling/monitoring metrics for {focus_topic}", "Root cause isolation method", "Telemetry indicators"]
        elif focus_dim == "specification":
            kind = QuestionKind.SPECIFICATION_PROBE
            objective = f"Provide concrete technical specifications, parameters, schemas, or metrics for {focus_topic}."
            cog_comp = 0.40
            tech_comp = 0.65
            reas_req = 0.30
            spec_req = 0.85
            evidence_units = [f"Concrete technical specifications for {focus_topic}", "Chosen database/protocol configuration", "Exact parameters or schemas"]
        else:
            if depth == 1:
                kind = QuestionKind.CONCEPTUAL_OVERVIEW
                objective = f"Provide high-level architecture overview and core engineering challenges of {focus_topic}."
                cog_comp = 0.40
                tech_comp = 0.40
                reas_req = 0.30
                spec_req = 0.40
                evidence_units = [f"Overview of {focus_topic}", "Primary problem solved", "High-level technology stack"]
            else:
                kind = QuestionKind.ARCHITECTURAL_CHOICE
                objective = f"Explain architectural structure, component communication, and data flow of {focus_topic}."
                cog_comp = max(0.50, difficulty)
                tech_comp = 0.60
                reas_req = 0.50
                spec_req = 0.60
                evidence_units = [f"Component architecture of {focus_topic}", "Data flow and service boundaries", "Key implementation choices"]

        return cls(
            question_id=question_id,
            objective=objective,
            evidence_units=evidence_units,
            phase=phase,
            item_id=item_id,
            item_type=item_type,
            topic=focus_topic,
            subtopic=focus_dim.capitalize(),
            difficulty=difficulty,
            follow_up_depth=depth,
            cognitive_complexity=cog_comp,
            technical_complexity=tech_comp,
            reasoning_requirement=reas_req,
            specificity_requirement=spec_req,
            breadth=0.5,
            role_relevance=1.0,
            objective_importance=1.0,
            question_kind=kind,
            expected_answer_shape="Candidate articulates engineering rationale and concrete implementation details.",
            valid_alternative_guidance="Accept any technically sound alternative architecture or pattern that achieves the objective.",
            prohibited_assumptions=[
                "Candidate must use a specific cloud provider or vendor tool.",
                "Candidate's architecture must strictly match a standard textbook design."
            ]
        )
