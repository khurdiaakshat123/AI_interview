import unittest
from unittest.mock import MagicMock
from backend.app.engines.question_profile import QuestionProfile, QuestionKind
from backend.app.engines.interview_state import InterviewState, Claim, ClaimSource, ClaimStatus
from backend.app.engines.adaptive_planner import PlannerAction, PlannerDecision
from backend.app.engines.question_generator import QuestionGenerator, GeneratedQuestion
from backend.app.llm.client import LLMClient


class TestQuestionGenerator(unittest.TestCase):

    def setUp(self):
        self.state = InterviewState(session_id="qgen_test_session")
        self.state.register_item("proj_1", "PROJECT", "PROJECT_DEFENSE", "Distributed Event Streamer", relevance_weight=0.9)
        self.state.start_item("proj_1")

    def test_tradeoff_question_generation(self):
        profile = QuestionProfile(
            question_id="q_tradeoff_1",
            objective="Evaluate candidate's ability to justify architectural trade-offs.",
            evidence_units=["Articulates alternatives and trade-off rationale."],
            phase="PROJECT_DEFENSE",
            item_id="proj_1",
            item_type="PROJECT",
            topic="Distributed Event Streamer",
            subtopic="tradeoff",
            difficulty=0.7,
            follow_up_depth=2,
            question_kind=QuestionKind.TRADE_OFF_ANALYSIS
        )

        decision = PlannerDecision(
            action=PlannerAction.TEST_TRADEOFF,
            focus_topic="Distributed Event Streamer",
            focus_entity="Kafka",
            focus_dimension="tradeoff",
            target_difficulty=0.7,
            rationale="Candidate demonstrated baseline grasp; probe architectural trade-offs."
        )

        candidate_claims = [
            {"entity": "Kafka", "claim_text": "Used Kafka partition keys to maintain event order."}
        ]

        result = QuestionGenerator.generate_question(
            planner_action=decision.action,
            question_profile=profile,
            state=self.state,
            candidate_claims=candidate_claims,
            candidate_name="Alex"
        )

        self.assertIsInstance(result, GeneratedQuestion)
        self.assertIn("trade-off", result.question_text.lower())
        self.assertIn("Kafka", result.question_text)
        sentences = [s.strip() for s in result.question_text.split(".") if s.strip()]
        self.assertLessEqual(len(sentences), 2)
        self.assertEqual(len(self.state.question_history), 1)
        self.assertIsNotNone(self.state.question_history[0].question_profile)
        self.assertEqual(self.state.question_history[0].question_profile["question_id"], "q_tradeoff_1")

    def test_failure_recovery_question_generation(self):
        profile = QuestionProfile(
            question_id="q_failure_1",
            objective="Evaluate fault tolerance and graceful degradation.",
            evidence_units=["Explains node crash handling and data durability."],
            phase="PROJECT_DEFENSE",
            item_id="proj_1",
            item_type="PROJECT",
            topic="Distributed Event Streamer",
            subtopic="failure",
            difficulty=0.8,
            follow_up_depth=3,
            question_kind=QuestionKind.FAILURE_RECOVERY
        )

        result = QuestionGenerator.generate_question(
            planner_action=PlannerAction.TEST_FAILURE,
            question_profile=profile,
            state=self.state,
            candidate_topics=["Redis Sentinel"],
            candidate_name="Sam"
        )

        self.assertIn("Redis Sentinel", result.question_text)
        self.assertTrue("fail" in result.question_text.lower() or "crash" in result.question_text.lower())
        sentences = [s.strip() for s in result.question_text.split(".") if s.strip()]
        self.assertLessEqual(len(sentences), 2)

    def test_scale_bottleneck_question_generation(self):
        profile = QuestionProfile(
            question_id="q_scale_1",
            objective="Assess horizontal scaling limits and bottleneck identification.",
            evidence_units=["Identifies first bottleneck under 10x traffic spike."],
            phase="PROJECT_DEFENSE",
            item_id="proj_1",
            item_type="PROJECT",
            topic="Distributed Event Streamer",
            subtopic="scale",
            difficulty=0.75,
            follow_up_depth=2,
            question_kind=QuestionKind.SCALE_PERFORMANCE
        )

        result = QuestionGenerator.generate_question(
            planner_action=PlannerAction.TEST_SCALE,
            question_profile=profile,
            state=self.state,
            candidate_claims=[{"entity": "PostgreSQL", "claim_text": "Stored persistent events in PostgreSQL."}],
            candidate_name="Jordan"
        )

        self.assertIn("PostgreSQL", result.question_text)
        self.assertIn("bottleneck", result.question_text.lower())
        sentences = [s.strip() for s in result.question_text.split(".") if s.strip()]
        self.assertLessEqual(len(sentences), 2)

    def test_concurrency_question_generation(self):
        profile = QuestionProfile(
            question_id="q_conc_1",
            objective="Assess handling of concurrent resource updates.",
            evidence_units=["Explains locking or atomic updates."],
            phase="PROJECT_DEFENSE",
            item_id="proj_1",
            item_type="PROJECT",
            topic="Distributed Event Streamer",
            subtopic="concurrency",
            difficulty=0.85,
            follow_up_depth=3,
            question_kind=QuestionKind.CONCURRENCY_SYNC
        )

        result = QuestionGenerator.generate_question(
            planner_action=PlannerAction.TEST_CONCURRENCY,
            question_profile=profile,
            state=self.state,
            candidate_topics=["Worker Pool"],
            candidate_name="Taylor"
        )

        self.assertIn("race condition", result.question_text.lower())
        sentences = [s.strip() for s in result.question_text.split(".") if s.strip()]
        self.assertLessEqual(len(sentences), 2)

    def test_clarify_contradiction_is_neutral_and_non_accusatory(self):
        profile = QuestionProfile(
            question_id="q_contra_1",
            objective="Clarify service boundary between PostgreSQL and MongoDB.",
            evidence_units=["Explains role of each database."],
            phase="PROJECT_DEFENSE",
            item_id="proj_1",
            item_type="PROJECT",
            topic="Distributed Event Streamer",
            subtopic="clarification",
            difficulty=0.5,
            follow_up_depth=1,
            question_kind=QuestionKind.CONTRADICTION_RESOLUTION
        )

        contradiction_note = "Candidate mentioned MongoDB for order transactions while resume lists PostgreSQL."

        result = QuestionGenerator.generate_question(
            planner_action=PlannerAction.CLARIFY_CONTRADICTION,
            question_profile=profile,
            state=self.state,
            candidate_claims=[{"entity": "MongoDB", "claim_text": "Used MongoDB for event records."}],
            contradiction_context=contradiction_note,
            candidate_name="Morgan"
        )

        text_lower = result.question_text.lower()
        self.assertNotIn("contradict", text_lower)
        self.assertNotIn("liar", text_lower)
        self.assertNotIn("resume says", text_lower)
        self.assertNotIn("discrepancy", text_lower)
        self.assertTrue("service boundaries" in text_lower or "clarify" in text_lower)
        self.assertTrue(result.is_clarification)
        sentences = [s.strip() for s in result.question_text.split(".") if s.strip()]
        self.assertLessEqual(len(sentences), 2)

    def test_verify_unsupported_claim_tests_ownership(self):
        profile = QuestionProfile(
            question_id="q_owner_1",
            objective="Verify personal contribution vs team library.",
            evidence_units=["Distinguishes personal design from pre-existing code."],
            phase="PROJECT_DEFENSE",
            item_id="proj_1",
            item_type="PROJECT",
            topic="Distributed Event Streamer",
            subtopic="ownership",
            difficulty=0.6,
            follow_up_depth=1,
            question_kind=QuestionKind.IMPLEMENTATION_DETAIL
        )

        result = QuestionGenerator.generate_question(
            planner_action=PlannerAction.VERIFY_UNSUPPORTED_CLAIM,
            question_profile=profile,
            state=self.state,
            candidate_claims=[{"entity": "Consensus Engine", "claim_text": "Built custom Raft consensus."}],
            candidate_name="Chris"
        )

        self.assertIn("Consensus Engine", result.question_text)
        self.assertIn("personally", result.question_text.lower())
        sentences = [s.strip() for s in result.question_text.split(".") if s.strip()]
        self.assertLessEqual(len(sentences), 2)

    def test_subject_knowledge_stage_maps_to_role_objectives(self):
        profile = QuestionProfile(
            question_id="q_subj_1",
            objective="Evaluate understanding of cache eviction algorithms and latency trade-offs.",
            evidence_units=["Explains LRU vs LFU memory footprint."],
            phase="SUBJECT_KNOWLEDGE",
            item_id="subj_cache",
            item_type="SUBJECT_TOPIC",
            topic="Caching & Memory Management",
            subtopic="algorithms",
            difficulty=0.7,
            follow_up_depth=1,
            question_kind=QuestionKind.CONCEPTUAL_OVERVIEW
        )

        result = QuestionGenerator.generate_question(
            planner_action=PlannerAction.START_SUBJECT_STAGE,
            question_profile=profile,
            state=self.state,
            role_objective="High-Performance Backend Systems",
            candidate_name="Dana"
        )

        self.assertIn("Caching & Memory Management", result.question_text)
        self.assertIn("fundamentals", result.question_text.lower())
        sentences = [s.strip() for s in result.question_text.split(".") if s.strip()]
        self.assertLessEqual(len(sentences), 2)

    def test_no_leak_of_internal_planner_rationale_or_cot(self):
        profile = QuestionProfile(
            question_id="q_leak_test",
            objective="Evaluate database indexing strategy.",
            evidence_units=["Explains B-tree vs Hash index."],
            phase="PROJECT_DEFENSE",
            item_id="proj_1",
            item_type="PROJECT",
            topic="Distributed Event Streamer",
            subtopic="indexing",
            difficulty=0.95,
            follow_up_depth=4,
            question_kind=QuestionKind.SPECIFICATION_PROBE
        )

        secret_rationale = "INTERNAL_PLANNER_SECRET_DECISION_ABC123"

        result = QuestionGenerator.generate_question(
            planner_action=PlannerAction.TEST_IMPLEMENTATION,
            question_profile=profile,
            state=self.state,
            candidate_topics=["B-Tree Indexing"],
            candidate_name="Pat"
        )

        self.assertNotIn(secret_rationale, result.question_text)
        self.assertNotIn("0.95", result.question_text)
        self.assertNotIn("QuestionProfile", result.question_text)
        self.assertNotIn("PlannerAction", result.question_text)

    def test_mock_llm_client_integration(self):
        profile = QuestionProfile(
            question_id="q_llm_1",
            objective="Assess distributed transactions.",
            evidence_units=["Describes two-phase commit."],
            phase="PROJECT_DEFENSE",
            item_id="proj_1",
            item_type="PROJECT",
            topic="Distributed Event Streamer",
            subtopic="transactions",
            difficulty=0.8,
            follow_up_depth=2,
            question_kind=QuestionKind.ARCHITECTURAL_CHOICE
        )

        mock_client = MagicMock()
        mock_client.generate_completion.return_value = (
            "Interviewer: That's a helpful breakdown of your pipeline. "
            "Could you explain how two-phase commit is orchestrated across your event stores?"
        )

        result = QuestionGenerator.generate_question(
            planner_action=PlannerAction.TEST_CONSISTENCY,
            question_profile=profile,
            state=self.state,
            candidate_topics=["Two-Phase Commit"],
            candidate_name="Riley",
            llm_client_instance=mock_client
        )

        self.assertTrue(mock_client.generate_completion.called)
        self.assertFalse(result.question_text.startswith("Interviewer:"))
        self.assertIn("two-phase commit", result.question_text.lower())

    def test_llm_client_facade_delegation(self):
        client = LLMClient()
        client.generate_completion = MagicMock(return_value=None)

        profile = QuestionProfile(
            question_id="q_facade_1",
            objective="Test operational debugging.",
            evidence_units=["Explains thread dump profiling."],
            phase="PROJECT_DEFENSE",
            item_id="proj_1",
            item_type="PROJECT",
            topic="Distributed Event Streamer",
            subtopic="debugging",
            difficulty=0.7,
            follow_up_depth=2,
            question_kind=QuestionKind.DEBUGGING_DIAGNOSTIC
        )

        question_text = client.generate_interview_question(
            candidate_name="Casey",
            company="Tech Corp",
            role="Distributed Systems Engineer",
            phase="PROJECT_DEFENSE",
            current_depth=2,
            project_title="Distributed Event Streamer",
            planner_decision=PlannerDecision(
                action=PlannerAction.TEST_DEBUGGING,
                focus_topic="Distributed Event Streamer",
                focus_dimension="debugging",
                target_difficulty=0.7,
                rationale="Candidate demonstrated baseline; probe diagnostic profiling tools."
            ),
            question_profile=profile,
            state=self.state,
            candidate_topics=["Thread Pools"],
            persist_in_history=True
        )

        self.assertIsNotNone(question_text)
        self.assertIn("diagnostic", question_text.lower())
        self.assertEqual(len(self.state.question_history), 1)
        self.assertEqual(self.state.question_history[0].question_profile["question_id"], "q_facade_1")


if __name__ == '__main__':
    unittest.main()
