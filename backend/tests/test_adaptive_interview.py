import unittest
from unittest.mock import patch, MagicMock
from backend.app.engines.interview_state import InterviewState, ClaimSource, ClaimStatus
from backend.app.engines.question_profile import QuestionProfile, QuestionKind
from backend.app.engines.answer_evaluator import AnswerEvaluator, SemanticEvaluationResult, CandidateClaimExtraction
from backend.app.engines.consistency_engine import ConsistencyEngine, ConsistencyAnalysisResult
from backend.app.engines.scoring_policy import ScoringPolicy
from backend.app.engines.adaptive_planner import AdaptivePlanner, PlannerAction, PlannerDecision
from backend.app.agents.interview_agent import InterviewAgent
from backend.app.models.models import StructuredResume, RoleTopicProfile, InterviewSession, InterviewEvidence


class TestAdaptiveInterviewSystem(unittest.TestCase):
    """
    Comprehensive Behavioral and End-to-End Test Suite for the Refactored
    Adaptive Technical Interview Subsystem.
    """

    def test_agenda_work_experience_before_projects_and_relevance_sort(self):
        """
        Rule 19: All Work Experience items must appear before Projects.
        Projects must be strictly sorted by overall_relevance in descending order.
        Subject Knowledge topics must appear after experience items.
        """
        mock_resume = MagicMock(spec=StructuredResume)
        mock_resume.sections_json = {
            "work_experience": [
                {"id": "exp_1", "role": "Senior Engineer", "company": "Stripe", "overall_relevance": 0.95},
                {"id": "exp_2", "role": "Software Engineer", "company": "Uber", "overall_relevance": 0.70}
            ],
            "projects": [
                {"project_id": "p_low", "title": "Todo App", "overall_relevance": 0.30},
                {"project_id": "p_high", "title": "Distributed KV Store", "overall_relevance": 0.95},
                {"project_id": "p_mid", "title": "Image Resizer", "overall_relevance": 0.65}
            ]
        }

        agenda = InterviewAgent._build_interview_agenda(
            resume=mock_resume,
            role_profile=None,
            target_role="Backend Distributed Systems Engineer",
            target_company="Google"
        )

        phases = [item["phase"] for item in agenda]
        
        # 1. First two items are EXPERIENCE_DEFENSE
        self.assertEqual(phases[0], "EXPERIENCE_DEFENSE")
        self.assertEqual(phases[1], "EXPERIENCE_DEFENSE")
        self.assertEqual(agenda[0]["item_id"], "exp_1")
        self.assertEqual(agenda[1]["item_id"], "exp_2")

        # 2. Next items are PROJECT_DEFENSE, sorted by relevance descending
        self.assertEqual(phases[2], "PROJECT_DEFENSE")
        self.assertEqual(phases[3], "PROJECT_DEFENSE")
        self.assertEqual(phases[4], "PROJECT_DEFENSE")
        self.assertEqual(agenda[2]["item_id"], "p_high")  # 0.95
        self.assertEqual(agenda[3]["item_id"], "p_mid")   # 0.65
        self.assertEqual(agenda[4]["item_id"], "p_low")   # 0.30

        # 3. Final items are SUBJECT_KNOWLEDGE
        self.assertEqual(phases[5], "SUBJECT_KNOWLEDGE")
        self.assertEqual(phases[6], "SUBJECT_KNOWLEDGE")

    def test_state_distinguishes_resume_context_from_candidate_assertions(self):
        """
        Rule 7: Claim sources must remain distinguishable.
        A resume claim is contextual evidence (UNEXPLORED), NOT proof of candidate knowledge.
        A candidate claim is an assertion, NOT automatically verified.
        """
        state = InterviewState(session_id="claim_test")
        
        # Register resume claim
        res_claim = state.register_resume_claim(
            statement="Architected distributed Kafka cluster at Stripe",
            item_id="exp_stripe",
            entity="Kafka",
            attribute="clustering",
            topics=["Distributed Systems", "Kafka"]
        )
        self.assertEqual(res_claim.source, ClaimSource.RESUME)
        self.assertEqual(res_claim.status, ClaimStatus.UNEXPLORED)

        # Record candidate claim
        cand_claim = state.record_candidate_claim(
            statement="I used Kafka with 3-node replication and Raft metadata mode",
            item_id="exp_stripe",
            entity="Kafka",
            attribute="replication",
            topics=["Kafka"],
            verified=False
        )
        self.assertEqual(cand_claim.source, ClaimSource.CANDIDATE)
        self.assertEqual(cand_claim.status, ClaimStatus.MENTIONED)

        # Assert claims remain distinct in state
        self.assertNotEqual(res_claim.claim_id, cand_claim.claim_id)
        self.assertEqual(len(state.claims), 2)

    def test_question_profile_depth_and_difficulty_independence(self):
        """
        Rule 9: Question difficulty and follow-up depth are strictly independent dimensions.
        - Introductory question (depth 1) can be hard (difficulty 0.85).
        - Deep follow-up (depth 4) can be easy factual probe (difficulty 0.20).
        """
        hard_intro = QuestionProfile(
            question_id="q_intro_hard",
            objective="Explain consensus guarantees of Paxos under split-brain",
            phase="SUBJECT_KNOWLEDGE",
            topic="Distributed Systems",
            difficulty=0.85,
            follow_up_depth=1
        )
        self.assertEqual(hard_intro.follow_up_depth, 1)
        self.assertEqual(hard_intro.difficulty, 0.85)
        self.assertEqual(hard_intro.difficulty_category(), "HARD")

        easy_deep_followup = QuestionProfile(
            question_id="q_deep_easy",
            objective="Identify default port of Redis",
            phase="PROJECT_DEFENSE",
            topic="Redis",
            difficulty=0.20,
            follow_up_depth=4
        )
        self.assertEqual(easy_deep_followup.follow_up_depth, 4)
        self.assertEqual(easy_deep_followup.difficulty, 0.20)
        self.assertEqual(easy_deep_followup.difficulty_category(), "EASY")

    def test_semantic_evaluator_recognizes_factual_correctness_without_keyword_bias(self):
        """
        Rule 10 & 11: One-word factual answer to a factual question is valid and correct.
        Must not penalize due to word count or length heuristics.
        """
        profile = QuestionProfile(
            question_id="q_factual",
            objective="Identify primary relational database engine used",
            evidence_units=["Database engine named"],
            question_kind=QuestionKind.ARCHITECTURAL_CHOICE,
            topic="Database",
            difficulty=0.30,
            follow_up_depth=1,
            reasoning_requirement=0.10
        )

        eval_result = AnswerEvaluator.evaluate(
            question_profile=profile,
            candidate_answer="PostgreSQL",
            llm_client_instance=None  # Conservative fallback
        )

        self.assertFalse(eval_result.is_non_answer)
        self.assertGreaterEqual(eval_result.correctness, 0.90)
        self.assertIn("PostgreSQL", eval_result.entities)

    def test_semantic_evaluator_catches_semantic_evasion_non_answers(self):
        """
        Rule 4: Candidate evasion (e.g. 'I don't know', 'I am totally aware about this')
        must be flagged as non-answer with 0 evidence score.
        """
        profile = QuestionProfile(
            question_id="q_tradeoff",
            objective="Explain trade-offs between B-Tree and LSM-Tree",
            topic="Storage Engines",
            difficulty=0.75,
            follow_up_depth=2,
            reasoning_requirement=0.80
        )

        eval_evasion = AnswerEvaluator.evaluate(
            question_profile=profile,
            candidate_answer="I don't know about storage engines, never used them.",
            llm_client_instance=None
        )

        self.assertTrue(eval_evasion.is_non_answer)
        self.assertEqual(eval_evasion.correctness, 0.0)
        self.assertEqual(eval_evasion.objective_coverage, 0.0)

        # Deterministic scoring on non-answer yields 0 earned points
        earned, possible, severity = ScoringPolicy.calculate_turn_score(eval_evasion, profile)
        self.assertEqual(earned, 0.0)
        self.assertEqual(severity, "SEVERE")

    def test_consistency_engine_scoped_vs_unscoped_contradictions(self):
        """
        Rule 5 & 8: Contextual reconciliation.
        - Postgres for OLTP + Mongo for analytics in same project is COMPLEMENTARY (no contradiction).
        - Postgres for OLTP + Mongo for OLTP in same project service is a CONTRADICTION.
        """
        state = InterviewState(session_id="consistency_test")
        state.register_item("proj_1", "PROJECT", "PROJECT_DEFENSE", "E-Commerce Backend")
        state.start_item("proj_1")

        state.record_candidate_claim(
            statement="We used PostgreSQL for storing customer orders and transaction ledgers",
            item_id="proj_1",
            entity="PostgreSQL",
            attribute="transaction storage",
            topics=["Database", "PostgreSQL"],
            verified=True
        )

        # Scenario A: Candidate uses MongoDB for reporting/analytics -> Complementary
        eval_olap = SemanticEvaluationResult(
            answer_understanding="Candidate used MongoDB for analytics and reporting dashboards",
            reasoning_summary="Used MongoDB as specialized analytics store alongside relational OLTP",
            candidate_claims=[
                CandidateClaimExtraction(
                    statement="We pushed event logs to MongoDB for business analytics",
                    entity="MongoDB",
                    attribute_or_action="analytics",
                    causality_valid=True
                )
            ],
            entities=["MongoDB"],
            candidate_topics=["Analytics", "MongoDB"]
        )
        res_olap = ConsistencyEngine.analyze(eval_olap, state, current_item_id="proj_1")
        self.assertFalse(res_olap.has_discrepancies)

        # Scenario B: Candidate asserts MongoDB was used for the transaction ledger -> Contradiction
        eval_oltp_conflict = SemanticEvaluationResult(
            answer_understanding="Candidate stated MongoDB was used as the primary ACID transaction ledger",
            reasoning_summary="Contradicting statement claiming MongoDB held the relational transaction ledger",
            candidate_claims=[
                CandidateClaimExtraction(
                    statement="Our transaction ledger was stored in MongoDB with ACID guarantees",
                    entity="MongoDB",
                    attribute_or_action="transaction ledger",
                    causality_valid=True
                )
            ],
            entities=["MongoDB"],
            candidate_topics=["Database", "Transactions"]
        )
        res_oltp = ConsistencyEngine.analyze(eval_oltp_conflict, state, current_item_id="proj_1")
        self.assertTrue(res_oltp.has_discrepancies)
        self.assertEqual(len(res_oltp.discrepancies), 1)
        self.assertTrue(res_oltp.discrepancies[0].clarification_recommended)

    def test_scoring_policy_asymmetric_risk_reward(self):
        """
        Rule 12: Asymmetric formula A = D*Q + (1-D)*(1-Q).
        - Easy question (D=0.1) + poor answer (Q=0.0) -> A=0.9 -> High weight denominator (heavy penalty)
        - Easy question (D=0.1) + strong answer (Q=1.0) -> A=0.1 -> Low weight denominator (modest reward)
        - Hard question (D=0.9) + poor answer (Q=0.0) -> A=0.1 -> Low weight denominator (protected failure)
        - Hard question (D=0.9) + strong answer (Q=1.0) -> A=0.9 -> High weight denominator (high reward)
        """
        # Easy question
        a_easy_poor = ScoringPolicy.compute_asymmetry(difficulty=0.10, evidence_score=0.0)
        a_easy_strong = ScoringPolicy.compute_asymmetry(difficulty=0.10, evidence_score=1.0)
        self.assertGreater(a_easy_poor, a_easy_strong)
        self.assertAlmostEqual(a_easy_poor, 0.90, places=2)
        self.assertAlmostEqual(a_easy_strong, 0.10, places=2)

        # Hard question
        a_hard_poor = ScoringPolicy.compute_asymmetry(difficulty=0.90, evidence_score=0.0)
        a_hard_strong = ScoringPolicy.compute_asymmetry(difficulty=0.90, evidence_score=1.0)
        self.assertGreater(a_hard_strong, a_hard_poor)
        self.assertAlmostEqual(a_hard_strong, 0.90, places=2)
        self.assertAlmostEqual(a_hard_poor, 0.10, places=2)

    def test_scoring_policy_untested_item_receives_none(self):
        """
        Rule 15: An untested item receives None (never 0.0 or a fabricated score).
        Untested items are excluded from experience aggregation.
        """
        untested_score = ScoringPolicy.aggregate_item_score([])
        self.assertIsNone(untested_score)

        # Weighted experience score excludes None
        item_scores = [
            {"item_score": 90.0, "relevance_weight": 0.90},
            {"item_score": None, "relevance_weight": 0.50},  # Untested -> excluded
            {"item_score": 70.0, "relevance_weight": 0.60}
        ]
        agg_score = ScoringPolicy.aggregate_relevance_weighted_experience_score(item_scores)
        expected = ((90.0 * 0.90) + (70.0 * 0.60)) / (0.90 + 0.60)
        self.assertAlmostEqual(agg_score, round(expected, 1), places=1)

    def test_adaptive_planner_clarifies_contradiction_before_drilling(self):
        """
        Rule 5 & 8: Unresolved contradictions or clarification flags trigger
        CLARIFY_CONTRADICTION before further technical drilling.
        """
        state = InterviewState(session_id="contra_plan_test")
        state.register_item("exp_1", "WORK_EXPERIENCE", "EXPERIENCE_DEFENSE", "Senior Dev at Acme")
        state.start_item("exp_1")

        eval_clar = SemanticEvaluationResult(
            answer_understanding="Candidate gave ambiguous explanation of database transactions",
            reasoning_summary="Scope unclear",
            clarification_needed=True,
            clarification_reason="Clarify whether Mongo or Postgres held transaction records"
        )

        decision = AdaptivePlanner.plan_next_action(state, latest_eval=eval_clar)
        self.assertEqual(decision.action, PlannerAction.CLARIFY_CONTRADICTION)
        self.assertEqual(decision.focus_dimension, "consistency")

    def test_end_to_end_state_and_evidence_lifecycle(self):
        """
        Tests the full lifecycle of an interview session across turns:
        Turn 1: Work Experience opening -> candidate answer -> state update -> score.
        Turn 2: Follow-up question -> candidate strong answer -> deepening.
        Verify evidence records and dual headline scores.
        """
        state = InterviewState(session_id="lifecycle_test")
        state.register_item("exp_1", "WORK_EXPERIENCE", "EXPERIENCE_DEFENSE", "Lead Engineer at ScaleOps", relevance_weight=0.90)
        state.register_item("proj_1", "PROJECT", "PROJECT_DEFENSE", "Realtime Telemetry Pipeline", relevance_weight=0.85)
        state.register_item("subj_1", "SUBJECT_TOPIC", "SUBJECT_KNOWLEDGE", "Concurrency & Distributed Systems", relevance_weight=1.0)
        state.start_item("exp_1")

        # Turn 1
        q1_profile = QuestionProfile(
            question_id="q1",
            objective="Overview of architecture at ScaleOps",
            phase="EXPERIENCE_DEFENSE",
            item_id="exp_1",
            topic="ScaleOps Architecture",
            difficulty=0.50,
            follow_up_depth=1
        )
        eval1 = SemanticEvaluationResult(
            answer_understanding="Candidate designed an event ingestion pipeline processing 50k events/sec.",
            reasoning_summary="Sound event-driven streaming design and ingestion architecture",
            candidate_claims=[
                CandidateClaimExtraction(statement="Handled 50k events/sec with Kafka and Go workers", entity="Kafka", attribute_or_action="ingestion")
            ],
            entities=["Kafka", "Go"],
            candidate_topics=["Event Streaming", "Kafka"],
            correctness=0.90,
            objective_coverage=0.85,
            completeness=0.85,
            technical_validity=0.90,
            depth_demonstrated=0.80
        )
        earned1, poss1, sev1 = ScoringPolicy.calculate_turn_score(eval1, q1_profile)
        self.assertGreater(earned1, 0.0)
        self.assertEqual(sev1, "NONE")

        # Turn 2: Planner tests failure
        decision2 = AdaptivePlanner.plan_next_action(state, latest_eval=eval1)
        self.assertIn(decision2.action, [PlannerAction.TEST_FAILURE, PlannerAction.TEST_TRADEOFF, PlannerAction.DEEPEN_CURRENT_TOPIC, PlannerAction.TEST_SCALE])

        # Dual headline score aggregation verification
        mock_evidence = [
            {"earned_points": earned1, "possible_points": poss1}
        ]
        exp_score = ScoringPolicy.aggregate_item_score(mock_evidence)
        self.assertIsNotNone(exp_score)
        self.assertGreater(exp_score, 70.0)


if __name__ == "__main__":
    unittest.main()
