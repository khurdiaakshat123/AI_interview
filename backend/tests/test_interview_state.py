import unittest
from backend.app.engines.interview_state import (
    InterviewState,
    ClaimStatus,
    ClaimSource,
    are_distinct_technologies,
)


class TestInterviewStateLayer(unittest.TestCase):

    def setUp(self):
        self.state = InterviewState(session_id="test_session_123")

    def test_rule_1_resume_claim_starts_as_unexplored(self):
        """Rule 1: Resume claim starts as UNEXPLORED."""
        claim = self.state.register_resume_claim(
            statement="Architected distributed cache using Redis",
            item_id="proj_1",
            entity="Redis"
        )
        self.assertEqual(claim.source, ClaimSource.RESUME)
        self.assertEqual(claim.status, ClaimStatus.UNEXPLORED)
        self.assertIn(claim.claim_id, self.state.claims)

    def test_rule_2_candidate_mentioning_resume_claim_moves_to_mentioned(self):
        """Rule 2: Candidate mentioning a resume claim changes it to MENTIONED, not SUPPORTED."""
        claim = self.state.register_resume_claim(
            statement="Built microservices in Go",
            item_id="proj_1",
            entity="Go"
        )
        self.assertEqual(claim.status, ClaimStatus.UNEXPLORED)

        updated_claim = self.state.record_candidate_mention_of_resume_claim(claim.claim_id, turn_index=1)
        self.assertIsNotNone(updated_claim)
        self.assertEqual(updated_claim.status, ClaimStatus.MENTIONED)
        self.assertNotEqual(updated_claim.status, ClaimStatus.SUPPORTED)
        self.assertIn(1, updated_claim.supporting_turns)

    def test_rule_3_evidence_moves_claim_to_supported_levels(self):
        """Rule 3: Actual evidence can move claim toward PARTIALLY_SUPPORTED, SUPPORTED, STRONGLY_SUPPORTED."""
        claim = self.state.register_resume_claim(
            statement="Implemented Raft consensus log replication",
            item_id="proj_1",
            entity="Raft"
        )
        self.state.record_candidate_mention_of_resume_claim(claim.claim_id, turn_index=1)
        self.assertEqual(self.state.claims[claim.claim_id].status, ClaimStatus.MENTIONED)

        # 1. Weak evidence -> PARTIALLY_SUPPORTED
        c1, ev1 = self.state.record_evidence_for_claim(
            claim_id=claim.claim_id,
            evidence_strength="WEAK",
            turn_index=2,
            observation="Candidate gave high-level overview of leader election."
        )
        self.assertEqual(c1.status, ClaimStatus.PARTIALLY_SUPPORTED)

        # 2. Moderate evidence -> SUPPORTED
        c2, ev2 = self.state.record_evidence_for_claim(
            claim_id=claim.claim_id,
            evidence_strength="MODERATE",
            turn_index=3,
            observation="Candidate correctly detailed term changes and heartbeat RPC timeouts."
        )
        self.assertEqual(c2.status, ClaimStatus.SUPPORTED)

        # 3. Strong evidence -> STRONGLY_SUPPORTED
        c3, ev3 = self.state.record_evidence_for_claim(
            claim_id=claim.claim_id,
            evidence_strength="STRONG",
            turn_index=4,
            observation="Candidate proved split-brain mitigation and log compaction via snapshots."
        )
        self.assertEqual(c3.status, ClaimStatus.STRONGLY_SUPPORTED)

    def test_rule_4_and_7_candidate_created_topics_retained(self):
        """Rule 4 & 7: Candidate-created topics must be retained, and never deleted."""
        self.state.add_topic("Distributed Systems")
        self.state.add_candidate_topic("Event Sourcing")
        self.state.add_candidate_topic("CQRS Architecture")

        self.assertIn("Event Sourcing", self.state.candidate_created_topics)
        self.assertIn("CQRS Architecture", self.state.candidate_created_topics)
        self.assertIn("Event Sourcing", self.state.topics)
        self.assertIn("Distributed Systems", self.state.topics)

        # Adding existing topic does not erase or duplicate
        self.state.add_candidate_topic("Event Sourcing")
        self.assertEqual(self.state.candidate_created_topics.count("Event Sourcing"), 1)

    def test_rule_5_candidate_claims_start_as_mentioned_or_unverified(self):
        """Rule 5: Candidate-created claims start as MENTIONED or UNVERIFIED."""
        c1 = self.state.record_candidate_claim(
            statement="We chose Cassandra for multi-region writes with tunable consistency",
            entity="Cassandra",
            turn_index=1,
            initial_status=ClaimStatus.MENTIONED
        )
        self.assertEqual(c1.source, ClaimSource.CANDIDATE)
        self.assertEqual(c1.status, ClaimStatus.MENTIONED)

        c2 = self.state.record_candidate_claim(
            statement="Our service handled 500,000 requests per second under peak load",
            entity="Cassandra",
            turn_index=2,
            initial_status=ClaimStatus.UNVERIFIED
        )
        self.assertEqual(c2.source, ClaimSource.CANDIDATE)
        self.assertEqual(c2.status, ClaimStatus.UNVERIFIED)

    def test_rule_6_omitted_resume_claims_remain_unexplored(self):
        """Rule 6: Omitted resume claims remain UNEXPLORED."""
        claim_a = self.state.register_resume_claim(
            statement="Used Kubernetes for autoscaling pods",
            entity="Kubernetes"
        )
        claim_b = self.state.register_resume_claim(
            statement="Designed database schemas in PostgreSQL",
            entity="PostgreSQL"
        )

        # Candidate only discusses PostgreSQL
        self.state.record_candidate_mention_of_resume_claim(claim_b.claim_id, turn_index=1)
        self.state.record_evidence_for_claim(claim_b.claim_id, "MODERATE", turn_index=2, observation="Good normalization explanation.")

        # Kubernetes was never touched -> remains strictly UNEXPLORED
        self.assertEqual(self.state.claims[claim_a.claim_id].status, ClaimStatus.UNEXPLORED)
        self.assertEqual(self.state.claims[claim_b.claim_id].status, ClaimStatus.SUPPORTED)

    def test_rule_8_distinct_technologies_disambiguation(self):
        """Rule 8: Do not incorrectly merge distinct technologies just because their names are similar."""
        self.assertTrue(are_distinct_technologies("Postgres", "PostGIS"))
        self.assertTrue(are_distinct_technologies("PostgreSQL", "PostGIS"))
        self.assertTrue(are_distinct_technologies("Redis", "Redshift"))
        self.assertTrue(are_distinct_technologies("Java", "JavaScript"))
        self.assertTrue(are_distinct_technologies("React", "React Native"))
        self.assertTrue(are_distinct_technologies("Kafka", "Kafka Connect"))

        # Same tech variations should not be considered distinct
        self.assertFalse(are_distinct_technologies("Postgres", "PostgreSQL"))

        claim_pg = self.state.register_resume_claim("Stored geographic data in PostGIS", entity="PostGIS")
        claim_sql = self.state.register_resume_claim("Managed transactions in PostgreSQL", entity="PostgreSQL")

        # Must not merge
        self.assertFalse(self.state.can_merge_claims(claim_pg, claim_sql))

    def test_rule_9_candidate_evidence_invalidates_interviewer_assumptions(self):
        """Rule 9: Candidate evidence can invalidate assumptions made by the interviewer."""
        assump = self.state.record_interviewer_assumption(
            assumption_id="assump_single_dc",
            statement="System is hosted in a single AWS availability zone.",
            item_id="proj_1",
            turn_index=1
        )
        self.assertFalse(assump.is_invalidated)

        # Candidate demonstrates active multi-region CockroachDB replication
        invalidated = self.state.invalidate_interviewer_assumption(
            assumption_id="assump_single_dc",
            candidate_evidence_text="Candidate explained active-active 3-region CockroachDB deployment with Raft consensus ranges.",
            turn_index=2
        )
        self.assertIsNotNone(invalidated)
        self.assertTrue(invalidated.is_invalidated)
        self.assertIn("CockroachDB", invalidated.invalidation_notes or invalidated.invalidating_evidence_id)
        # Verify a falsifying evidence record was created
        falsifying_records = [e for e in self.state.evidence if e.is_falsifying]
        self.assertEqual(len(falsifying_records), 1)
        self.assertEqual(falsifying_records[0].invalidated_assumption_id, "assump_single_dc")

    def test_rule_10_contradictions_stored_as_clarification_required(self):
        """Rule 10: Contradictions must be stored as unresolved/clarification-required when context is uncertain."""
        c1 = self.state.record_candidate_claim(
            statement="All database transactions strictly use Serializable isolation",
            entity="PostgreSQL",
            turn_index=1
        )
        c2 = self.state.record_candidate_claim(
            statement="We allow dirty reads without locks to maximize throughput",
            entity="PostgreSQL",
            turn_index=3
        )

        contra = self.state.record_contradiction(
            claim_id_a=c1.claim_id,
            claim_id_b=c2.claim_id,
            description="Claimed Serializable isolation in Turn 1, but claimed dirty reads without locks in Turn 3.",
            turn_index=3,
            is_uncertain=True
        )

        self.assertEqual(contra.status, "CLARIFICATION_REQUIRED")
        self.assertEqual(self.state.claims[c1.claim_id].status, ClaimStatus.CLARIFICATION_REQUIRED)
        self.assertEqual(self.state.claims[c2.claim_id].status, ClaimStatus.CLARIFICATION_REQUIRED)
        self.assertEqual(len(self.state.unresolved_issues), 1)
        self.assertEqual(self.state.unresolved_issues[0].status, "OPEN")

        # Resolving the contradiction
        success = self.state.resolve_contradiction(
            contradiction_id=contra.contradiction_id,
            resolution_notes="Candidate clarified that analytics queries run Read Uncommitted on replicas, while payments run Serializable on primary.",
            turn_index=4,
            resolved_status_for_claim_a=ClaimStatus.SUPPORTED
        )
        self.assertTrue(success)
        self.assertEqual(self.state.contradictions[0].status, "RESOLVED")
        self.assertEqual(self.state.claims[c1.claim_id].status, ClaimStatus.SUPPORTED)
        self.assertEqual(self.state.unresolved_issues[0].status, "RESOLVED")

    def test_guardrails_and_agenda_tracking(self):
        """Verifies turn counters, guardrails, and item status transitions."""
        self.state.register_item("exp_1", "WORK_EXPERIENCE", "EXPERIENCE_DEFENSE", "Software Engineer at Google")
        self.state.register_item("proj_1", "PROJECT", "PROJECT_DEFENSE", "Distributed KV Store")

        self.assertEqual(self.state.active_item_id, "exp_1")
        self.assertEqual(self.state.guardrails.turns_on_current_item, 0)

        # Turn 1
        self.state.record_turn(
            question_id="q_1",
            turn_index=1,
            topic="Experience: Google",
            question_text="Walk me through your responsibilities at Google.",
            planner_action="START_NEXT_ITEM"
        )
        self.assertEqual(self.state.guardrails.total_turns, 1)
        self.assertEqual(self.state.guardrails.turns_on_current_item, 1)
        self.assertEqual(self.state.items["exp_1"].turns_spent, 1)

        # Conclude item and transition to next
        self.state.conclude_active_item("COMPLETED")
        self.assertIn("exp_1", self.state.completed_item_ids)

        self.state.start_item("proj_1")
        self.assertEqual(self.state.active_item_id, "proj_1")
        self.assertEqual(self.state.guardrails.turns_on_current_item, 0)
        self.assertEqual(self.state.current_phase, "PROJECT_DEFENSE")

    def test_deterministic_serialization_and_version_safety(self):
        """Verifies that to_dict and from_dict preserve all state structures deterministically."""
        self.state.register_resume_claim("Kafka partition buffering", item_id="proj_1", entity="Kafka")
        self.state.add_candidate_topic("Kafka Streams")
        self.state.record_turn("q_100", 1, "Kafka", "How do you handle consumer lag?")

        raw_dict = self.state.to_dict()
        self.assertIsInstance(raw_dict, dict)
        self.assertEqual(raw_dict["state_version"], "1.0.0")
        self.assertEqual(raw_dict["session_id"], "test_session_123")

        # Reload state from dict
        rehydrated = InterviewState.from_dict(raw_dict)
        self.assertEqual(rehydrated.state_version, "1.0.0")
        self.assertEqual(rehydrated.session_id, "test_session_123")
        self.assertEqual(len(rehydrated.claims), 1)
        self.assertIn("Kafka Streams", rehydrated.candidate_created_topics)
        self.assertEqual(len(rehydrated.question_history), 1)


if __name__ == "__main__":
    unittest.main()
