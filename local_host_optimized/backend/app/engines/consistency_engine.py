from __future__ import annotations
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from backend.app.engines.interview_state import InterviewState, Claim, ClaimStatus
from backend.app.engines.answer_evaluator import SemanticEvaluationResult, CandidateClaimExtraction


class DiscrepancyRecord(BaseModel):
    """
    Structured record representing an isolated technical discrepancy between claims.
    
    INVARIANTS:
    - Does NOT subtract score or declare the candidate wrong.
    - Captures context: component, item, role, time, scope.
    - Generates neutral clarification inquiries.
    """
    discrepancy_id: str
    claim_references: List[str] = Field(default_factory=list)
    source_references: List[str] = Field(default_factory=list)  # e.g., ["resume", "candidate"]
    affected_item: Optional[str] = None
    component_service: Optional[str] = None
    role_context: Optional[str] = None
    time_context: Optional[str] = None
    scope: Optional[str] = None
    discrepancy_description: str
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    clarification_recommended: bool = True
    neutral_clarification_prompt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ConsistencyAnalysisResult(BaseModel):
    has_discrepancies: bool = False
    discrepancies: List[DiscrepancyRecord] = Field(default_factory=list)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ConsistencyEngine:
    """
    Context-Aware Discrepancy & Consistency Engine.
    
    Cross-references current statements against historical candidate and resume claims across 6 contextual dimensions:
    1. Project/Item context
    2. Component/Service context
    3. Role context
    4. Time/Migration context
    5. Architectural scope (e.g. read replica vs primary, cache vs persistent store)
    6. Specificity & certainty
    """

    # Functional component keywords used to distinguish service boundaries
    OLTP_KEYWORDS = {"transaction", "transactions", "oltp", "acid", "payment", "checkout", "order", "ledger", "relational"}
    OLAP_KEYWORDS = {"analytics", "olap", "reporting", "warehouse", "dashboard", "aggregations", "bi", "data lake", "spark"}
    CACHE_KEYWORDS = {"cache", "caching", "invalidation", "redis", "memcached", "hot partition", "buffer", "ttl"}
    STORAGE_KEYWORDS = {"database", "persistence", "postgres", "postgresql", "mysql", "mongodb", "cassandra", "dynamodb"}

    # Temporal / Migration indicators
    MIGRATION_KEYWORDS = {
        "migrated", "migration", "re-architected", "rewrote", "v1", "v2", "legacy", "initially",
        "phased out", "replaced with", "subsequently", "later on", "transitioned to"
    }

    @classmethod
    def analyze(
        cls,
        eval_result: SemanticEvaluationResult,
        state: InterviewState,
        current_item_id: Optional[str] = None,
        current_item_title: Optional[str] = None,
        role_context: Optional[str] = None,
        current_turn: int = 1,
        llm_client: Optional[Any] = None
    ) -> ConsistencyAnalysisResult:
        """
        Analyzes the candidate's latest answer and claims against established state.
        Returns a list of structured DiscrepancyRecords. Does not penalize or modify scores.
        """
        discrepancies: List[DiscrepancyRecord] = []
        target_item = current_item_id or state.active_item_id

        # 1. Attempt LLM-assisted contextual analysis if available
        if llm_client is not None and state.claims:
            llm_discrepancies = cls._analyze_via_llm(
                eval_result=eval_result,
                state=state,
                target_item=target_item,
                item_title=current_item_title,
                role_context=role_context,
                current_turn=current_turn,
                llm_client=llm_client
            )
            if llm_discrepancies is not None:
                return ConsistencyAnalysisResult(
                    has_discrepancies=len(llm_discrepancies) > 0,
                    discrepancies=llm_discrepancies,
                    notes="Evaluated via contextual LLM consistency analysis."
                )

        # 2. Deterministic Contextual Rule-Based Engine
        deterministic_records = cls._analyze_deterministic(
            eval_result=eval_result,
            state=state,
            current_item_id=target_item,
            current_item_title=current_item_title,
            role_context=role_context,
            current_turn=current_turn
        )

        return ConsistencyAnalysisResult(
            has_discrepancies=len(deterministic_records) > 0,
            discrepancies=deterministic_records,
            notes="Evaluated via deterministic multi-context consistency rules."
        )

    @classmethod
    def _analyze_deterministic(
        cls,
        eval_result: SemanticEvaluationResult,
        state: InterviewState,
        current_item_id: Optional[str],
        current_item_title: Optional[str],
        role_context: Optional[str],
        current_turn: int
    ) -> List[DiscrepancyRecord]:
        discrepancies: List[DiscrepancyRecord] = []
        new_claims = eval_result.candidate_claims
        answer_text_lower = eval_result.answer_understanding.lower() + " " + " ".join([c.statement for c in new_claims]).lower()

        # Check if candidate explicitly indicates a time progression or migration
        is_migration_context = any(kw in answer_text_lower for kw in cls.MIGRATION_KEYWORDS)

        for new_c in new_claims:
            new_stmt_lower = new_c.statement.lower()
            new_entity_lower = (new_c.entity or "").lower()

            for past_id, past_claim in state.claims.items():
                past_stmt_lower = past_claim.statement.lower()
                past_entity_lower = (past_claim.entity or "").lower()

                # Dimension 1: Cross-Project Isolation
                # If claims belong to explicitly different projects, they are independent.
                if past_claim.item_id and current_item_id and past_claim.item_id != current_item_id:
                    continue  # Different projects -> NO contradiction

                # Dimension 2: Cross-Component Isolation (OLTP vs OLAP vs Caching)
                if cls._are_different_components(past_stmt_lower, new_stmt_lower):
                    continue  # Different components (e.g. Postgres for OLTP, MongoDB for OLAP) -> NO contradiction

                # Dimension 3: Temporal / Migration Progression
                if is_migration_context:
                    continue  # v1 vs v2 architecture evolution -> NO contradiction

                # Dimension 4: Complementary Scope (Cache vs Persistent Database)
                if cls._is_complementary_cache_pattern(past_stmt_lower, new_stmt_lower, past_entity_lower, new_entity_lower):
                    continue  # Redis cache in front of Postgres -> NO contradiction

                # Dimension 5: Uncertain Scope (Ambiguity in same project)
                # Example: Earlier mentioned PostgreSQL for user balances, now mentions Redis for user balances without specifying caching.
                if cls._is_uncertain_scope(past_stmt_lower, new_stmt_lower, past_entity_lower, new_entity_lower):
                    disc_id = f"disc_scope_{len(discrepancies) + 1}_t{current_turn}"
                    entity_a = past_claim.entity or "previously mentioned technology"
                    entity_b = new_c.entity or "newly mentioned technology"
                    item_label = current_item_title or current_item_id or "this project"

                    prompt = (
                        f"Earlier you mentioned using {entity_a} for data in {item_label}, while now you mentioned {entity_b}. "
                        f"Were these used for different components, or was {entity_b} used as a caching layer in front of {entity_a}?"
                    )
                    discrepancies.append(
                        DiscrepancyRecord(
                            discrepancy_id=disc_id,
                            claim_references=[past_claim.claim_id],
                            source_references=[past_claim.source.value, "candidate"],
                            affected_item=current_item_id,
                            component_service="Data Storage / Caching Layer",
                            role_context=role_context,
                            scope="Uncertain Cache vs Primary",
                            discrepancy_description=f"Potential scope overlap between {entity_a} and {entity_b}.",
                            confidence=0.65,
                            clarification_recommended=True,
                            neutral_clarification_prompt=prompt
                        )
                    )
                    continue

                # Dimension 6: True Scoped Contradiction
                # Same project, same service, incompatible assertions (e.g., PostgreSQL for transactions vs MongoDB for the same transaction service)
                if cls._is_direct_scoped_contradiction(past_stmt_lower, new_stmt_lower, past_entity_lower, new_entity_lower):
                    disc_id = f"disc_contra_{len(discrepancies) + 1}_t{current_turn}"
                    entity_a = past_claim.entity or past_claim.statement[:30]
                    entity_b = new_c.entity or new_c.statement[:30]
                    item_label = current_item_title or current_item_id or "this system"

                    prompt = (
                        f"Earlier you mentioned {entity_a} for the core transaction flow in {item_label}, while now you noted {entity_b}. "
                        f"Were these used for different parts or environments, or did the stack change over time?"
                    )
                    discrepancies.append(
                        DiscrepancyRecord(
                            discrepancy_id=disc_id,
                            claim_references=[past_claim.claim_id],
                            source_references=[past_claim.source.value, "candidate"],
                            affected_item=current_item_id,
                            component_service="Core Transaction Processing",
                            role_context=role_context,
                            scope="Incompatible Primary Stores in Same Subsystem",
                            discrepancy_description=f"Direct architectural divergence: '{past_claim.statement}' vs '{new_c.statement}'",
                            confidence=0.88,
                            clarification_recommended=True,
                            neutral_clarification_prompt=prompt
                        )
                    )

        return discrepancies

    @classmethod
    def _are_different_components(cls, stmt_a: str, stmt_b: str) -> bool:
        """
        Detects if two statements clearly address separate functional subsystems (e.g., OLTP transactions vs OLAP analytics).
        """
        has_oltp_a = any(w in stmt_a for w in cls.OLTP_KEYWORDS)
        has_olap_a = any(w in stmt_a for w in cls.OLAP_KEYWORDS)
        has_oltp_b = any(w in stmt_b for w in cls.OLTP_KEYWORDS)
        has_olap_b = any(w in stmt_b for w in cls.OLAP_KEYWORDS)

        # One statement is for transactions, the other is for analytics/reporting
        if (has_oltp_a and has_olap_b) or (has_olap_a and has_oltp_b):
            return True

        return False

    CACHE_PATTERN_KEYWORDS = {"cache", "caching", "invalidation", "invalidate", "ttl", "read cache", "cache-aside", "write-through", "buffer", "buffered"}

    @classmethod
    def _is_complementary_cache_pattern(cls, stmt_a: str, stmt_b: str, ent_a: str, ent_b: str) -> bool:
        """
        Detects complementary caching patterns when explicitly articulated as a cache, buffer, or TTL layer.
        """
        cache_names = {"redis", "memcached"}
        db_names = {"postgres", "postgresql", "mysql", "cockroachdb", "sqlite", "mongodb"}

        # One is an explicit cache tool, the other is an explicit persistent database
        if (ent_a in cache_names and ent_b in db_names) or (ent_b in cache_names and ent_a in db_names):
            # Must explicitly articulate caching or buffer behavior
            if any(w in stmt_a or w in stmt_b for w in cls.CACHE_PATTERN_KEYWORDS):
                return True
        return False

    @classmethod
    def _is_uncertain_scope(cls, stmt_a: str, stmt_b: str, ent_a: str, ent_b: str) -> bool:
        """
        Detects when two technologies touch similar data domains but the caching or service division is ambiguous.
        """
        if not ent_a or not ent_b or ent_a == ent_b:
            return False

        cache_names = {"redis", "memcached"}
        db_names = {"postgres", "postgresql", "mysql", "mongodb", "dynamodb"}

        # Redis mentioned alongside a DB for the same domain without explicit caching clarification
        if (ent_a in cache_names and ent_b in db_names) or (ent_b in cache_names and ent_a in db_names):
            common_domain = any(w in stmt_a and w in stmt_b for w in ["user", "balance", "session", "order", "data"])
            if common_domain:
                return True

        return False

    @classmethod
    def _is_direct_scoped_contradiction(cls, stmt_a: str, stmt_b: str, ent_a: str, ent_b: str) -> bool:
        """
        Detects direct mutual exclusions within the same service and project.
        Example: Using PostgreSQL for transactions vs using MongoDB for the same transaction service.
        """
        if not ent_a or not ent_b or ent_a == ent_b:
            return False

        # If both are persistent databases claiming the same transactional primary role
        primary_dbs = {"postgres", "postgresql", "mysql", "mongodb", "dynamodb", "cassandra"}
        if ent_a in primary_dbs and ent_b in primary_dbs:
            # Both claim the same transactional service
            if any(w in stmt_a for w in cls.OLTP_KEYWORDS) and any(w in stmt_b for w in cls.OLTP_KEYWORDS):
                return True

        # State management contradiction: stateless vs stateful
        if ("stateless" in stmt_a and "in-memory session state" in stmt_b) or ("in-memory session state" in stmt_a and "stateless" in stmt_b):
            return True

        return False

    @classmethod
    def _analyze_via_llm(
        cls,
        eval_result: SemanticEvaluationResult,
        state: InterviewState,
        target_item: Optional[str],
        item_title: Optional[str],
        role_context: Optional[str],
        current_turn: int,
        llm_client: Any
    ) -> Optional[List[DiscrepancyRecord]]:
        """
        LLM contextual reconciliation prompt for subtle or complex architectural discrepancies.
        """
        claims_list = [
            {"id": c.claim_id, "source": c.source.value, "item": c.item_id, "statement": c.statement}
            for c in state.claims.values()
        ]
        new_claims_list = [c.statement for c in eval_result.candidate_claims]
        if not claims_list or not new_claims_list:
            return None

        system_prompt = (
            "You are a Principal Engineering Consistency Evaluator. Compare new candidate assertions with previous claims.\n"
            "CRITICAL RULES:\n"
            "1. A contradiction must NOT automatically mean the candidate is wrong. Do NOT subtract marks.\n"
            "2. Evaluate in context: Technology + Project + Component/Service + Role + Time + Scope.\n"
            "3. DIFFERENT COMPONENTS ARE NOT CONTRADICTIONS (e.g. Postgres for transactions, Mongo for analytics).\n"
            "4. DIFFERENT PROJECTS ARE NOT CONTRADICTIONS (e.g. MySQL in Project A, DynamoDB in Project B).\n"
            "5. MIGRATIONS & TIME PERIODS ARE NOT CONTRADICTIONS (e.g. v1 in Django, v2 in Go).\n"
            "6. If scope is ambiguous, flag clarification_recommended = true with a polite, neutral prompt.\n"
            "Output valid JSON matching schema:\n"
            '{"discrepancies": [{"claim_id": "...", "description": "...", "scope": "...", "confidence": 0.8, "clarification_prompt": "..."}]}'
        )

        user_prompt = (
            f"Active Item: {item_title or target_item or 'General'}\n"
            f"Existing Claims in State:\n{json.dumps(claims_list[:8])}\n\n"
            f"New Candidate Assertions (Turn {current_turn}):\n{json.dumps(new_claims_list)}\n"
        )

        try:
            completion = llm_client.generate_completion(system_prompt, user_prompt, temperature=0.1)
            if not completion:
                return None
            clean = completion.strip()
            if clean.startswith("```json"): clean = clean[7:]
            if clean.startswith("```"): clean = clean[3:]
            if clean.endswith("```"): clean = clean[:-3]
            parsed = json.loads(clean.strip())

            records = []
            for idx, d in enumerate(parsed.get("discrepancies", [])):
                records.append(
                    DiscrepancyRecord(
                        discrepancy_id=f"disc_llm_{idx+1}_t{current_turn}",
                        claim_references=[d.get("claim_id", "")],
                        source_references=["candidate"],
                        affected_item=target_item,
                        component_service=d.get("scope", "System Component"),
                        discrepancy_description=d.get("description", "Architectural discrepancy"),
                        confidence=float(d.get("confidence", 0.75)),
                        clarification_recommended=True,
                        neutral_clarification_prompt=d.get("clarification_prompt")
                    )
                )
            return records
        except Exception:
            return None
