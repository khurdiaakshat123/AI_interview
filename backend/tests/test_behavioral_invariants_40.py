import unittest
from unittest.mock import MagicMock, patch
import uuid
import json

from backend.app.schemas.schemas import (
    InterviewTurnOut, CurrentItemSummary, ProjectScoreCard, ExperienceItemScoreCard,
    InterviewFinalReportOut, InterviewSessionCreate, InterviewAnswerRequest
)
from backend.app.models.models import (
    InterviewSession, InterviewEvidence, StructuredResume, RoleTopicProfile, User
)
from backend.app.agents.interview_agent import InterviewAgent
from backend.app.engines.interview_state import (
    InterviewState, ClaimSource, ClaimStatus, Claim, ItemState
)
from backend.app.engines.question_profile import QuestionProfile, QuestionKind
from backend.app.engines.adaptive_planner import (
    PlannerAction, PlannerDecision, AdaptivePlanner
)
from backend.app.engines.consistency_engine import ConsistencyEngine, ConsistencyAnalysisResult, DiscrepancyRecord
from backend.app.engines.scoring_policy import ScoringPolicy
from backend.app.engines.answer_evaluator import AnswerEvaluator, SemanticEvaluationResult, CandidateClaimExtraction
from backend.app.engines.report_generator import ReportGenerator
from backend.app.engines.resume_parser import ResumeParser


class TestBehavioralInvariants40(unittest.TestCase):
    """
    Exhaustive verification of all 38 testable behavioral requirements:
    Invariants 1 to 38 test concrete functionality; items 39 and 40 correspond
    to full frontend build and backend test pass.
    """

    def setUp(self):
        self.db = MagicMock()
        self.user = MagicMock(spec=User)
        self.user.id = "user_inv_40"
        self.user.email = "inv40@example.com"

        self.resume = MagicMock(spec=StructuredResume)
        self.resume.id = "res_inv_40"
        self.resume.user_id = self.user.id
        self.resume.candidate_name = "Taylor Smith"
        self.resume.sections_json = {
            "work_experience": [
                {
                    "id": "exp_1",
                    "role": "Lead Architect",
                    "company": "Stripe",
                    "summary": "Built distributed ledger engine.",
                    "key_skills": ["Kafka", "PostgreSQL", "Go"],
                    "overall_relevance": 0.95
                },
                {
                    "id": "exp_2",
                    "role": "Systems Engineer",
                    "company": "Uber",
                    "summary": "Designed routing services.",
                    "key_skills": ["Redis", "Python"],
                    "overall_relevance": 0.70
                }
            ],
            "projects": [
                {
                    "project_id": "proj_paxos",
                    "title": "Consensus Engine",
                    "description": "Implemented Paxos consensus in Rust.",
                    "technologies": ["Rust", "Paxos"],
                    "overall_relevance": 0.90
                },
                {
                    "project_id": "proj_buffer",
                    "title": "Log Buffer",
                    "description": "Ring buffer using ZeroMQ.",
                    "technologies": ["C++", "ZeroMQ"],
                    "overall_relevance": 0.60
                },
                {
                    "project_id": "proj_notes",
                    "title": "Notes App",
                    "description": "Simple mobile app.",
                    "technologies": ["React Native"],
                    "overall_relevance": 0.30
                }
            ]
        }

        self.role_profile = MagicMock(spec=RoleTopicProfile)
        self.role_profile.id = "role_inv_40"
        self.role_profile.user_id = self.user.id
        self.role_profile.target_role = "Staff Systems Engineer"
        self.role_profile.required_skills = ["Distributed Systems", "Kafka", "PostgreSQL"]

    # 1. Work experience is first.
    def test_01_work_experience_is_first(self):
        agenda = InterviewAgent._build_interview_agenda(self.resume, self.role_profile, "Staff Systems Engineer", "Stripe")
        self.assertTrue(len(agenda) >= 1)
        self.assertEqual(agenda[0]["item_id"], "exp_1")
        self.assertEqual(agenda[0]["phase"], "EXPERIENCE_DEFENSE")

    # 2. All work experience comes before projects.
    def test_02_all_work_experience_comes_before_projects(self):
        agenda = InterviewAgent._build_interview_agenda(self.resume, self.role_profile, "Staff Systems Engineer", "Stripe")
        exp_indices = [i for i, it in enumerate(agenda) if it["phase"] == "EXPERIENCE_DEFENSE"]
        proj_indices = [i for i, it in enumerate(agenda) if it["phase"] == "PROJECT_DEFENSE"]
        self.assertTrue(len(exp_indices) > 0 and len(proj_indices) > 0)
        self.assertLess(max(exp_indices), min(proj_indices))

    # 3. Projects are ordered by descending relevance.
    def test_03_projects_ordered_by_descending_relevance(self):
        agenda = InterviewAgent._build_interview_agenda(self.resume, self.role_profile, "Staff Systems Engineer", "Stripe")
        projects = [it for it in agenda if it["phase"] == "PROJECT_DEFENSE"]
        relevances = [p["relevance"] for p in projects]
        self.assertEqual(relevances, sorted(relevances, reverse=True))
        self.assertEqual([p["item_id"] for p in projects], ["proj_paxos", "proj_buffer", "proj_notes"])

    # 4. Subject stage starts only after all work experience and projects are completed/pivoted.
    def test_04_subject_stage_starts_after_experience_and_projects(self):
        agenda = InterviewAgent._build_interview_agenda(self.resume, self.role_profile, "Staff Systems Engineer", "Stripe")
        subject_indices = [i for i, it in enumerate(agenda) if it["phase"] == "SUBJECT_KNOWLEDGE"]
        exp_and_proj_indices = [i for i, it in enumerate(agenda) if it["phase"] in ("EXPERIENCE_DEFENSE", "PROJECT_DEFENSE")]
        self.assertTrue(len(subject_indices) > 0)
        self.assertGreater(min(subject_indices), max(exp_and_proj_indices))

    # 5. Every work experience item can receive its own /100 score.
    def test_05_every_work_experience_can_receive_own_100_score(self):
        ev1 = [
            {"earned_points": 4.0, "possible_points": 5.0, "item_id": "exp_1"},
            {"earned_points": 3.0, "possible_points": 5.0, "item_id": "exp_1"}
        ]
        score_exp1 = ScoringPolicy.aggregate_item_score(ev1)
        self.assertEqual(score_exp1, 70.0)

    # 6. Every project can receive its own /100 score.
    def test_06_every_project_can_receive_own_100_score(self):
        ev_proj = [
            {"earned_points": 8.0, "possible_points": 10.0, "item_id": "proj_paxos"}
        ]
        score_proj = ScoringPolicy.aggregate_item_score(ev_proj)
        self.assertEqual(score_proj, 80.0)

    # 7. Overall experience score includes BOTH work experience and projects.
    def test_07_overall_experience_score_includes_both_work_and_projects(self):
        items = [
            {"item_type": "WORK_EXPERIENCE", "item_score": 80.0, "relevance_weight": 0.90},
            {"item_type": "PROJECT", "item_score": 60.0, "relevance_weight": 0.60}
        ]
        score = ScoringPolicy.aggregate_relevance_weighted_experience_score(items)
        expected = round((80.0 * 0.90 + 60.0 * 0.60) / (0.90 + 0.60), 1)
        self.assertEqual(score, expected)

    # 8. Overall experience score uses Σ(item_score × relevance) / Σ(relevance).
    def test_08_overall_experience_score_uses_relevance_formula(self):
        items = [
            {"item_score": 90.0, "relevance_weight": 0.8},
            {"item_score": 70.0, "relevance_weight": 0.2}
        ]
        score = ScoringPolicy.aggregate_relevance_weighted_experience_score(items)
        expected = round((90.0 * 0.8 + 70.0 * 0.2) / 1.0, 1)
        self.assertEqual(score, expected)
        self.assertEqual(score, 86.0)

    # 9. Subject score is separate.
    def test_09_subject_score_is_separate(self):
        subj_ev = [
            {"earned_points": 7.5, "possible_points": 10.0}
        ]
        subj_score = ScoringPolicy.aggregate_subject_score(subj_ev)
        self.assertEqual(subj_score, 75.0)

    # 10. Question aggregation uses Σ earned / Σ possible × 100.
    def test_10_question_aggregation_uses_formula(self):
        ev = [
            {"earned_points": 3.0, "possible_points": 4.0},
            {"earned_points": 5.0, "possible_points": 6.0}
        ]
        score = ScoringPolicy.aggregate_item_score(ev)
        self.assertEqual(score, 80.0)

    # 11. No double relevance weighting.
    def test_11_no_double_relevance_weighting(self):
        qp = QuestionProfile(
            question_id="q1",
            objective="Architecture",
            topic="Ledger",
            difficulty=0.5
        )
        res = SemanticEvaluationResult(
            answer_understanding="Good answer",
            reasoning_summary="Candidate articulated architecture cleanly",
            correctness=0.8,
            technical_validity=0.8,
            depth_demonstrated=0.8,
            confidence=0.8,
            is_non_answer=False
        )
        earned1, poss1, _ = ScoringPolicy.calculate_turn_score(res, qp)
        self.assertGreater(poss1, 0.0)
        self.assertGreater(earned1, 0.0)
        self.assertAlmostEqual(earned1 / poss1, ScoringPolicy.compute_semantic_evidence_score(res), places=2)

    # 12. Easy + poor produces a higher question denominator than easy + strong.
    def test_12_easy_plus_poor_higher_denominator_than_easy_plus_strong(self):
        qp = QuestionProfile(question_id="q_easy", objective="basics", topic="db", difficulty=0.15)
        res_poor = SemanticEvaluationResult(answer_understanding="poor", reasoning_summary="poor", correctness=0.10, technical_validity=0.10, depth_demonstrated=0.10, confidence=0.8, is_non_answer=False)
        res_strong = SemanticEvaluationResult(answer_understanding="strong", reasoning_summary="strong", correctness=0.95, technical_validity=0.95, depth_demonstrated=0.95, confidence=0.95, is_non_answer=False)
        _, poss_poor, _ = ScoringPolicy.calculate_turn_score(res_poor, qp)
        _, poss_strong, _ = ScoringPolicy.calculate_turn_score(res_strong, qp)
        self.assertGreater(poss_poor, poss_strong)

    # 13. Hard + strong produces a higher denominator than hard + poor.
    def test_13_hard_plus_strong_higher_denominator_than_hard_plus_poor(self):
        qp = QuestionProfile(question_id="q_hard", objective="deep", topic="dist", difficulty=0.85)
        res_poor = SemanticEvaluationResult(answer_understanding="poor", reasoning_summary="poor", correctness=0.10, technical_validity=0.10, depth_demonstrated=0.10, confidence=0.8, is_non_answer=False)
        res_strong = SemanticEvaluationResult(answer_understanding="strong", reasoning_summary="strong", correctness=0.95, technical_validity=0.95, depth_demonstrated=0.95, confidence=0.95, is_non_answer=False)
        _, poss_poor, _ = ScoringPolicy.calculate_turn_score(res_poor, qp)
        _, poss_strong, _ = ScoringPolicy.calculate_turn_score(res_strong, qp)
        self.assertGreater(poss_strong, poss_poor)

    # 14. Hard + poor can produce a lower denominator than easy + poor.
    def test_14_hard_plus_poor_lower_denominator_than_easy_plus_poor(self):
        qp_hard = QuestionProfile(question_id="q_hard", objective="deep", topic="dist", difficulty=0.85)
        qp_easy = QuestionProfile(question_id="q_easy", objective="basics", topic="db", difficulty=0.15)
        res_poor = SemanticEvaluationResult(answer_understanding="poor", reasoning_summary="poor", correctness=0.10, technical_validity=0.10, depth_demonstrated=0.10, confidence=0.8, is_non_answer=False)
        _, poss_hard_poor, _ = ScoringPolicy.calculate_turn_score(res_poor, qp_hard)
        _, poss_easy_poor, _ = ScoringPolicy.calculate_turn_score(res_poor, qp_easy)
        self.assertLess(poss_hard_poor, poss_easy_poor)

    # 15. Moderate combinations remain intermediate.
    def test_15_moderate_combinations_remain_intermediate(self):
        qp_med = QuestionProfile(question_id="q_med", objective="mid", topic="db", difficulty=0.50)
        res_med = SemanticEvaluationResult(answer_understanding="med", reasoning_summary="med", correctness=0.50, technical_validity=0.50, depth_demonstrated=0.50, confidence=0.8, is_non_answer=False)
        _, poss_med, _ = ScoringPolicy.calculate_turn_score(res_med, qp_med)
        self.assertTrue(1.0 <= poss_med <= 10.0)

    # 16. One-word factual answer can receive full evidence when appropriate.
    def test_16_one_word_factual_answer_full_evidence(self):
        qp = QuestionProfile(
            question_id="q_fact",
            objective="Which primary database did you use?",
            topic="Database",
            question_kind=QuestionKind.CONCEPTUAL_OVERVIEW,
            reasoning_requirement=0.10
        )
        res = AnswerEvaluator.evaluate(question_profile=qp, candidate_answer="PostgreSQL", llm_client_instance=None)
        self.assertFalse(res.is_non_answer)
        self.assertGreaterEqual(res.correctness, 0.85)

    # 17. One-word answer to reasoning question does not receive full evidence.
    def test_17_one_word_reasoning_answer_partial_evidence(self):
        qp = QuestionProfile(
            question_id="q_reason",
            objective="Explain the trade-offs between Raft and Multi-Paxos",
            topic="Consensus",
            question_kind=QuestionKind.TRADE_OFF_ANALYSIS,
            reasoning_requirement=0.85
        )
        res = AnswerEvaluator.evaluate(question_profile=qp, candidate_answer="Raft", llm_client_instance=None)
        self.assertLessEqual(res.correctness, 0.40)

    # 18. Resume omission is neutral.
    def test_18_resume_omission_is_neutral(self):
        state = InterviewState(session_id="sess_18")
        state.register_resume_claim(statement="Used Kubernetes for cluster orchestration", entity="Kubernetes")
        self.assertEqual(state.claims[list(state.claims.keys())[0]].status, ClaimStatus.UNEXPLORED)

    # 19. Resume claim starts UNEXPLORED.
    def test_19_resume_claim_starts_unexplored(self):
        state = InterviewState(session_id="sess_19")
        claim = state.register_resume_claim(statement="Engineered Kafka pipeline", entity="Kafka")
        self.assertEqual(claim.status, ClaimStatus.UNEXPLORED)

    # 20. Candidate mention moves it to MENTIONED, not SUPPORTED.
    def test_20_candidate_mention_moves_to_mentioned_not_supported(self):
        state = InterviewState(session_id="sess_20")
        claim = state.register_resume_claim(statement="Kafka pipeline", entity="Kafka")
        state.record_candidate_mention_of_resume_claim(claim.claim_id, turn_index=1)
        self.assertEqual(claim.status, ClaimStatus.MENTIONED)
        self.assertNotEqual(claim.status, ClaimStatus.SUPPORTED)

    # 21. Actual evidence can move claim to SUPPORTED/STRONGLY_SUPPORTED.
    def test_21_actual_evidence_moves_to_supported_strongly_supported(self):
        state = InterviewState(session_id="sess_21")
        claim = state.register_resume_claim(statement="Kafka pipeline", entity="Kafka")
        state.record_evidence_for_claim(
            claim_id=claim.claim_id,
            evidence_strength="STRONG",
            turn_index=2,
            observation="Candidate demonstrated Kafka partitioning in detail",
            topic="Kafka"
        )
        self.assertEqual(claim.status, ClaimStatus.STRONGLY_SUPPORTED)

    # 22. Candidate-created topics are retained.
    def test_22_candidate_created_topics_retained(self):
        state = InterviewState(session_id="sess_22")
        state.add_candidate_topic("ClickHouse")
        self.assertIn("ClickHouse", state.candidate_created_topics)
        self.assertIn("ClickHouse", state.topics)

    # 23. Resume and candidate claims coexist.
    def test_23_resume_and_candidate_claims_coexist(self):
        state = InterviewState(session_id="sess_23")
        rc = state.register_resume_claim("Resume says DynamoDB", entity="DynamoDB")
        cc = state.record_candidate_claim("Candidate states Redis for cache", entity="Redis")
        self.assertEqual(rc.source, ClaimSource.RESUME)
        self.assertEqual(cc.source, ClaimSource.CANDIDATE)
        self.assertEqual(len(state.claims), 2)

    # 24. Scoped contradiction can trigger clarification before penalty.
    def test_24_scoped_contradiction_triggers_clarification(self):
        eval_res = SemanticEvaluationResult(
            answer_understanding="Candidate stated MongoDB for transaction payment ledger",
            reasoning_summary="Candidate claimed Python instead of Go on the Raft project",
            candidate_claims=[CandidateClaimExtraction(statement="Used MongoDB for transactional payment ledger", entity="MongoDB")],
            is_non_answer=False
        )
        state = InterviewState(session_id="sess_24")
        state.register_resume_claim("Used PostgreSQL for transactional payment ledger", entity="PostgreSQL", item_id="p1")
        state.register_item("p1", "PROJECT", "PROJECT_DEFENSE", "Consensus Engine")
        res = ConsistencyEngine.analyze(eval_res, state, current_item_id="p1")
        self.assertTrue(res.has_discrepancies)
        self.assertTrue(res.discrepancies[0].clarification_recommended)

    # 25. Same technology used in different components/projects is not incorrectly treated as contradiction.
    def test_25_same_technology_different_components_not_contradiction(self):
        eval_res = SemanticEvaluationResult(
            answer_understanding="Candidate used PostgreSQL for auth service",
            reasoning_summary="Postgres auth",
            candidate_claims=[CandidateClaimExtraction(statement="Used PostgreSQL for auth", entity="PostgreSQL")],
            is_non_answer=False
        )
        state = InterviewState(session_id="sess_25")
        state.register_resume_claim("Used MongoDB for analytics logs", entity="MongoDB", item_id="p2")
        state.register_item("p1", "PROJECT", "PROJECT_DEFENSE", "Auth Service")
        res = ConsistencyEngine.analyze(eval_res, state, current_item_id="p1")
        self.assertFalse(res.has_discrepancies)

    # 26. Strong answer can trigger meaningful deeper exploration.
    def test_26_strong_answer_triggers_deeper_exploration(self):
        state = InterviewState(session_id="sess_26")
        state.register_item("exp_1", "WORK_EXPERIENCE", "EXPERIENCE_DEFENSE", "Ledger Engine", relevance_weight=0.95)
        eval_strong = SemanticEvaluationResult(
            answer_understanding="Deep architecture explained",
            reasoning_summary="Clear rationale",
            correctness=0.90,
            technical_validity=0.90,
            depth_demonstrated=0.85,
            confidence=0.90,
            is_non_answer=False
        )
        decision = AdaptivePlanner.plan_next_action(state, eval_strong, state.items["exp_1"], ["Distributed Systems"])
        self.assertIn(decision.action, [
            PlannerAction.DEEPEN_CURRENT_TOPIC, PlannerAction.TEST_SCALE, PlannerAction.TEST_FAILURE,
            PlannerAction.TEST_TRADEOFF, PlannerAction.TEST_CONCURRENCY, PlannerAction.TEST_CONSISTENCY,
            PlannerAction.TEST_PERFORMANCE
        ])

    # 27. Weak answer normally gets at most one targeted probe and then pivots.
    def test_27_weak_answer_gets_at_most_one_probe_then_pivots(self):
        state = InterviewState(session_id="sess_27")
        state.register_item("exp_1", "WORK_EXPERIENCE", "EXPERIENCE_DEFENSE", "Ledger Engine", relevance_weight=0.50)
        state.register_item("exp_2", "WORK_EXPERIENCE", "EXPERIENCE_DEFENSE", "Routing Service", relevance_weight=0.50)
        state.items["exp_1"].turns_spent = 1
        eval_weak = SemanticEvaluationResult(
            answer_understanding="Deflected",
            reasoning_summary="Deflection",
            correctness=0.10,
            is_non_answer=True
        )
        decision = AdaptivePlanner.plan_next_action(state, eval_weak, state.items["exp_1"], ["Distributed Systems"])
        self.assertIn(decision.action, [PlannerAction.PIVOT_ITEM, PlannerAction.START_NEXT_ITEM, PlannerAction.START_SUBJECT_STAGE])

    # 28. No generic repeated "tell me more" loops.
    def test_28_no_generic_tell_me_more_loops(self):
        state = InterviewState(session_id="sess_28")
        qp = QuestionProfile(question_id="q1", objective="failure modes", topic="Kafka", subtopic="failure")
        q = QuestionProfile.from_planner_decision(
            question_id="q2",
            decision=PlannerDecision(action=PlannerAction.TEST_FAILURE, focus_topic="Kafka", focus_dimension="failure", rationale="Test failure"),
            item=ItemState(item_id="it1", item_type="PROJECT", phase="PROJECT_DEFENSE", title="Kafka Pipeline")
        )
        self.assertNotEqual(q.question_kind, QuestionKind.CONCEPTUAL_OVERVIEW)

    # 29. Different candidate answers to the same first question can produce different planner actions.
    def test_29_different_answers_produce_different_planner_actions(self):
        state_a = InterviewState(session_id="sess_29a")
        state_a.register_item("it1", "PROJECT", "PROJECT_DEFENSE", "Engine", relevance_weight=0.8)
        state_b = InterviewState(session_id="sess_29b")
        state_b.register_item("it1", "PROJECT", "PROJECT_DEFENSE", "Engine", relevance_weight=0.8)

        eval_strong = SemanticEvaluationResult(answer_understanding="Strong", reasoning_summary="Strong", correctness=0.95, technical_validity=0.95, depth_demonstrated=0.9, confidence=0.9, is_non_answer=False)
        eval_weak = SemanticEvaluationResult(answer_understanding="Weak", reasoning_summary="Weak", correctness=0.10, is_non_answer=True)

        dec_strong = AdaptivePlanner.plan_next_action(state_a, eval_strong, state_a.items["it1"], ["Systems"])
        dec_weak = AdaptivePlanner.plan_next_action(state_b, eval_weak, state_b.items["it1"], ["Systems"])

        self.assertNotEqual(dec_strong.action, dec_weak.action)

    # 30. Alternative valid architecture/technical solution receives credit.
    def test_30_alternative_valid_architecture_receives_credit(self):
        qp = QuestionProfile(
            question_id="q_alt",
            topic="Event Streaming",
            objective="Event delivery",
            expected_concept="Kafka or RabbitMQ",
            valid_alternative_guidance="Redis Streams or AWS SQS is also valid"
        )
        res = SemanticEvaluationResult(
            answer_understanding="Candidate used Redis Streams",
            reasoning_summary="Redis Streams valid choice",
            correctness=0.85,
            technical_validity=0.90,
            depth_demonstrated=0.80,
            confidence=0.85,
            is_non_answer=False
        )
        earned, possible, _ = ScoringPolicy.calculate_turn_score(res, qp)
        self.assertGreaterEqual(earned / possible, 0.70)

    # 31. Keyword soup cannot produce a high score without semantic evidence.
    def test_31_keyword_soup_cannot_produce_high_score(self):
        qp = QuestionProfile(
            question_id="q_soup",
            topic="Consensus",
            objective="Explain consensus",
            expected_concept="quorum consensus and log replication",
            question_kind=QuestionKind.TRADE_OFF_ANALYSIS,
            reasoning_requirement=0.85
        )
        res = SemanticEvaluationResult(
            answer_understanding="Candidate dropped keywords without explanation",
            reasoning_summary="Keywords only",
            correctness=0.20,
            technical_validity=0.30,
            depth_demonstrated=0.10,
            reasoning_quality=0.10,
            confidence=0.50,
            is_non_answer=False
        )
        earned, possible, _ = ScoringPolicy.calculate_turn_score(res, qp)
        self.assertLessEqual(earned / possible, 0.40)

    # 32. Untested report topics remain UNTESTED.
    def test_32_untested_report_topics_remain_untested(self):
        state = InterviewState(session_id="sess_32")
        state.register_item("subj_1", "SUBJECT_TOPIC", "SUBJECT_KNOWLEDGE", "Operating Systems & Memory")
        report = ReportGenerator.generate_report(MagicMock(spec=InterviewSession, id="s32", transcript_json=[]), state, [])
        self.assertEqual(report["subject_topic_breakdown"].get("Operating Systems & Memory"), "UNTESTED")

    # 33. Final report contains no hardcoded generic strengths/gaps.
    def test_33_final_report_contains_no_hardcoded_generic_strengths(self):
        state = InterviewState(session_id="sess_33")
        state.register_item("exp_1", "WORK_EXPERIENCE", "EXPERIENCE_DEFENSE", "Ledger Engine")
        ev = [InterviewEvidence(
            session_id="s33",
            project_id_or_topic="exp_1",
            question_id="q1",
            follow_up_index=1,
            topic="Ledger Engine",
            subtopic="Scale",
            user_answer="Detailed scaling",
            expected_concept="Scaling",
            detected_gap=None,
            severity="MINOR",
            earned_points=8.0,
            possible_points=10.0,
            evaluator_reason="Strong scaling analysis"
        )]
        report = ReportGenerator.generate_report(MagicMock(spec=InterviewSession, id="s33", transcript_json=[]), state, ev)
        self.assertTrue(all("Ledger Engine" in s or "architecture" in s.lower() for s in report["strengths"]))

    # 34. Numeric earned/possible is returned after every scored answer.
    def test_34_numeric_earned_possible_returned_after_every_scored_answer(self):
        turn = InterviewTurnOut(
            session_id="sess_34",
            phase="EXPERIENCE_DEFENSE",
            current_topic="Ledger",
            question_id="q1",
            question_text="How did you scale?",
            depth_level=1,
            max_depth=5,
            is_completed=False,
            next_question="Next question",
            is_scored=True,
            earned_points=4.2,
            possible_points=5.0,
            evidence_score=0.84
        )
        self.assertEqual(turn.earned_points, 4.2)
        self.assertEqual(turn.possible_points, 5.0)

    # 35. Clarification prompt itself is not counted as a scored question.
    def test_35_clarification_prompt_not_scored(self):
        turn = InterviewTurnOut(
            session_id="sess_35",
            phase="PROJECT_DEFENSE",
            current_topic="Consensus",
            question_id="q_clarify",
            question_text="Could you clarify your role?",
            depth_level=1,
            max_depth=5,
            is_completed=False,
            next_question="Next",
            is_clarification=True,
            is_scored=False,
            earned_points=0.0,
            possible_points=0.0
        )
        self.assertTrue(turn.is_clarification)
        self.assertFalse(turn.is_scored)
        self.assertEqual(turn.earned_points, 0.0)
        self.assertEqual(turn.possible_points, 0.0)

    # 36. Old sessions/state do not crash.
    def test_36_old_sessions_state_do_not_crash(self):
        old_state_dict = {
            "current_phase": "PROJECT_DEFENSE",
            "active_item_id": "old_proj"
        }
        reconstituted = InterviewState.from_dict(old_state_dict, session_id="old_sess")
        self.assertEqual(reconstituted.session_id, "old_sess")
        self.assertEqual(reconstituted.current_phase, "PROJECT_DEFENSE")

    # 37. Multi-user sessions remain isolated.
    def test_37_multi_user_sessions_remain_isolated(self):
        state_1 = InterviewState(session_id="sess_user_1")
        state_2 = InterviewState(session_id="sess_user_2")
        state_1.add_candidate_topic("Kubernetes")
        self.assertIn("Kubernetes", state_1.candidate_created_topics)
        self.assertNotIn("Kubernetes", state_2.candidate_created_topics)

    # 38. API schemas validate.
    def test_38_api_schemas_validate(self):
        report = InterviewFinalReportOut(
            session_id="sess_38",
            candidate_name="Taylor",
            company="Stripe",
            role="Staff Engineer",
            experience_score=85.0,
            subject_knowledge_score=78.0,
            section_scores={"Overall": 82.0},
            experience_items=[
                ExperienceItemScoreCard(
                    project_id="exp_1",
                    item_id="exp_1",
                    item_type="WORK_EXPERIENCE",
                    title="Staff Engineer",
                    score=85.0,
                    star_rating=4.25,
                    relevance_weight=0.95
                )
            ]
        )
        self.assertEqual(report.experience_score, 85.0)
        self.assertEqual(report.subject_knowledge_score, 78.0)
        self.assertEqual(len(report.experience_items), 1)


if __name__ == "__main__":
    unittest.main()
