import unittest
from unittest.mock import MagicMock, patch
import uuid

from backend.app.models.models import (
    InterviewSession, InterviewEvidence, StructuredResume, RoleTopicProfile, utc_now
)
from backend.app.agents.interview_agent import InterviewAgent
from backend.app.engines.interview_state import InterviewState, ClaimSource, ClaimStatus
from backend.app.engines.question_profile import QuestionProfile
from backend.app.engines.adaptive_planner import PlannerAction, PlannerDecision


class TestLiveInterviewAgent(unittest.TestCase):
    """
    Integration tests for InterviewAgent live interview loop:
    start_session, process_answer, clarification prompts, and completion.
    """

    def setUp(self):
        self.db = MagicMock()
        self.user_id = "test_user_001"
        self.company = "Stripe"
        self.role = "Backend Distributed Systems Engineer"

        # Mock StructuredResume with 2 work experiences and 3 projects with distinct relevance
        self.resume = MagicMock(spec=StructuredResume)
        self.resume.id = "res_123"
        self.resume.candidate_name = "Alex Doe"
        self.resume.sections_json = {
            "work_experience": [
                {
                    "id": "exp_stripe",
                    "role": "Senior Infrastructure Engineer",
                    "company": "Stripe",
                    "summary": "Architected distributed transaction settlement engine handling 25k TPS.",
                    "key_skills": ["Kafka", "PostgreSQL", "Go", "Distributed Systems"],
                    "overall_relevance": 0.95
                },
                {
                    "id": "exp_uber",
                    "role": "Software Engineer",
                    "company": "Uber",
                    "summary": "Built internal dispatch routing microservices.",
                    "key_skills": ["gRPC", "Redis", "Python"],
                    "overall_relevance": 0.70
                }
            ],
            "projects": [
                {
                    "project_id": "p_low",
                    "title": "Recipe Finder App",
                    "description": "Simple CRUD app built with React and SQLite.",
                    "technologies": ["React", "SQLite"],
                    "overall_relevance": 0.30
                },
                {
                    "project_id": "p_high",
                    "title": "Distributed Raft Key-Value Store",
                    "description": "Implemented consensus protocol in Rust with snapshotting and log compaction.",
                    "technologies": ["Rust", "Raft", "Distributed Systems"],
                    "overall_relevance": 0.95
                },
                {
                    "project_id": "p_mid",
                    "title": "Log Streaming Service",
                    "description": "High-throughput log collector buffer using ZeroMQ.",
                    "technologies": ["ZeroMQ", "C++"],
                    "overall_relevance": 0.65
                }
            ]
        }

        # Mock RoleTopicProfile
        self.role_profile = MagicMock(spec=RoleTopicProfile)
        self.role_profile.id = "role_prof_456"
        self.role_profile.target_role = self.role
        self.role_profile.required_skills = ["Distributed Systems", "Kafka", "PostgreSQL", "Consensus"]

        # Setup db.query side_effects
        def query_side_effect(model):
            q_mock = MagicMock()
            if model == StructuredResume:
                filter_mock = MagicMock()
                filter_mock.first.return_value = self.resume
                q_mock.filter.return_value = filter_mock
            elif model == RoleTopicProfile:
                filter_mock = MagicMock()
                filter_mock.first.return_value = self.role_profile
                q_mock.filter.return_value = filter_mock
            elif model == InterviewEvidence:
                filter_mock = MagicMock()
                filter_mock.all.return_value = []
                q_mock.filter.return_value = filter_mock
            return q_mock

        self.db.query.side_effect = query_side_effect

    def test_start_session_creates_ordered_universe_and_first_question(self):
        """
        Verify start_session:
        - Work experience ordered first
        - Projects ordered descending by relevance (0.95 -> 0.65 -> 0.30)
        - Subject stage after experience items
        - First question starts with first work experience
        - Unified InterviewState initialized and persisted
        - Current QuestionProfile persisted in session metadata
        """
        session = InterviewAgent.start_session(
            db=self.db,
            user_id=self.user_id,
            company=self.company,
            role=self.role,
            resume=self.resume,
            role_profile=self.role_profile
        )

        self.assertIsNotNone(session)
        self.assertEqual(session.status, "IN_PROGRESS")
        self.assertEqual(session.current_phase, "EXPERIENCE_DEFENSE")
        self.assertEqual(session.current_depth, 1)

        # Check agenda ordering
        agenda = session.agent1_report_json["agenda"]
        self.assertGreaterEqual(len(agenda), 5)
        # Work experiences first
        self.assertEqual(agenda[0]["item_id"], "exp_stripe")
        self.assertEqual(agenda[0]["phase"], "EXPERIENCE_DEFENSE")
        self.assertEqual(agenda[1]["item_id"], "exp_uber")
        self.assertEqual(agenda[1]["phase"], "EXPERIENCE_DEFENSE")

        # Projects descending by relevance
        self.assertEqual(agenda[2]["item_id"], "p_high")
        self.assertEqual(agenda[2]["phase"], "PROJECT_DEFENSE")
        self.assertEqual(agenda[3]["item_id"], "p_mid")
        self.assertEqual(agenda[4]["item_id"], "p_low")

        # Subject stage at the end
        self.assertEqual(agenda[-1]["phase"], "SUBJECT_KNOWLEDGE")

        # Check unified state
        state_dict = session.agent1_report_json["unified_state"]
        self.assertIsNotNone(state_dict)
        self.assertEqual(state_dict["active_item_id"], "exp_stripe")

        # Check question profile
        q_profile = session.agent1_report_json["current_question_profile"]
        self.assertIsNotNone(q_profile)
        self.assertEqual(q_profile["phase"], "EXPERIENCE_DEFENSE")
        self.assertEqual(q_profile["item_id"], "exp_stripe")
        self.assertIn("difficulty", q_profile)
        self.assertEqual(q_profile["follow_up_depth"], 1)

        # Check initial interviewer turn in transcript
        self.assertEqual(len(session.transcript_json), 1)
        init_text = session.transcript_json[0]["text"]
        self.assertTrue(len(init_text) > 10)
        self.assertTrue(
            "Stripe" in init_text or "transaction" in init_text or "engine" in init_text or "Kafka" in init_text
        )

    def test_start_session_fallback_to_project_when_no_work_exp(self):
        """
        When resume has no work experience, the first item should be the highest-relevance project.
        """
        resume_no_work = MagicMock(spec=StructuredResume)
        resume_no_work.id = "res_no_work"
        resume_no_work.candidate_name = "Jane Dev"
        resume_no_work.sections_json = {
            "work_experience": [],
            "projects": [
                {"project_id": "p_low", "title": "Todo App", "overall_relevance": 0.40},
                {"project_id": "p_high", "title": "Distributed KV", "overall_relevance": 0.90}
            ]
        }

        session = InterviewAgent.start_session(
            db=self.db,
            user_id=self.user_id,
            company=self.company,
            role=self.role,
            resume=resume_no_work,
            role_profile=self.role_profile
        )

        self.assertEqual(session.current_phase, "PROJECT_DEFENSE")
        self.assertEqual(session.agent1_report_json["unified_state"]["active_item_id"], "p_high")

    def test_start_session_fallback_to_subject_when_no_resume(self):
        """
        When no resume is provided, interview starts directly with SUBJECT_KNOWLEDGE.
        """
        session = InterviewAgent.start_session(
            db=self.db,
            user_id=self.user_id,
            company=self.company,
            role=self.role,
            resume=None,
            role_profile=self.role_profile
        )

        self.assertEqual(session.current_phase, "SUBJECT_KNOWLEDGE")
        self.assertTrue(session.agent1_report_json["unified_state"]["active_item_id"].startswith("subj_"))

    def test_process_answer_full_pipeline_turn(self):
        """
        Verify live process_answer turn:
        - Transcript normalized
        - QuestionProfile rehydrated
        - AnswerEvaluator evaluates answer
        - InterviewState updated with candidate claims and topics
        - ScoringPolicy computes deterministic points
        - InterviewEvidence persisted
        - AdaptivePlanner chooses next step
        - Next QuestionProfile generated and stored in agent1_report_json
        - Returns next question response payload
        """
        session = InterviewAgent.start_session(
            db=self.db,
            user_id=self.user_id,
            company=self.company,
            role=self.role,
            resume=self.resume,
            role_profile=self.role_profile
        )

        candidate_answer = (
            "At Stripe, I designed our transaction settlement engine using Apache Kafka for event-driven "
            "ingestion and PostgreSQL for ACID transactions. We partitioned Kafka topics by merchant ID "
            "to guarantee strict in-order processing and scaled to 25,000 transactions per second."
        )

        turn_result = InterviewAgent.process_answer(
            db=self.db,
            session=session,
            user_answer=candidate_answer
        )

        self.assertIsNotNone(turn_result)
        self.assertIn("next_question", turn_result)
        self.assertFalse(turn_result["is_completed"])
        self.assertIn("eval_previous", turn_result)

        eval_prev = turn_result["eval_previous"]
        self.assertTrue(eval_prev["is_scored"])
        self.assertIn(eval_prev["quality_band"], ["Average", "Good", "Excellent"])
        self.assertNotEqual(eval_prev["quality_band"], "Weak")

        # Check evidence was persisted to DB
        evidence_saved = [arg[0][0] for arg in self.db.add.call_args_list if isinstance(arg[0][0], InterviewEvidence)]
        self.assertTrue(len(evidence_saved) >= 1)
        ev = evidence_saved[-1]
        self.assertEqual(ev.session_id, session.id)
        self.assertGreater(ev.earned_points, 0.0)
        self.assertIsNotNone(ev.evaluator_reason)

        # Check transcript updated: should have INTERVIEWER (turn 1), CANDIDATE (turn 2), INTERVIEWER (turn 3)
        self.assertEqual(len(session.transcript_json), 3)
        self.assertEqual(session.transcript_json[1]["sender"], "CANDIDATE")
        self.assertEqual(session.transcript_json[2]["sender"], "INTERVIEWER")

        # Check state has candidate claims and topics
        state_dict = session.agent1_report_json["unified_state"]
        candidate_claims = [c for c in state_dict["claims"].values() if c["source"] == "candidate"]
        self.assertGreaterEqual(len(candidate_claims), 1)
        self.assertGreaterEqual(len(state_dict["candidate_created_topics"]), 1)
        self.assertTrue(all(isinstance(t, str) and len(t) > 0 for t in state_dict["candidate_created_topics"]))

        # Check next question profile was created
        next_q_profile = session.agent1_report_json["current_question_profile"]
        self.assertIsNotNone(next_q_profile)
        self.assertIn("difficulty", next_q_profile)

    def test_process_answer_clarification_prompt_not_scored(self):
        """
        When a clarification prompt is answered:
        - Must NOT be counted as a normal scored question.
        - is_scored = False with 0.0 earned and 0.0 possible points.
        """
        session = InterviewAgent.start_session(
            db=self.db,
            user_id=self.user_id,
            company=self.company,
            role=self.role,
            resume=self.resume,
            role_profile=self.role_profile
        )

        # Set flag indicating that the question being answered was a clarification prompt
        meta = session.agent1_report_json
        meta["is_clarification_prompt"] = True
        session.agent1_report_json = meta

        turn_result = InterviewAgent.process_answer(
            db=self.db,
            session=session,
            user_answer="To clarify, PostgreSQL was used for the payment transactions, whereas MongoDB was used for analytics logs."
        )

        eval_prev = turn_result["eval_previous"]
        self.assertFalse(eval_prev["is_scored"])
        self.assertEqual(eval_prev["earned_points"], 0.0)
        self.assertEqual(eval_prev["possible_points"], 0.0)
        self.assertEqual(eval_prev["severity"], "NEUTRAL")

    def test_process_answer_interview_completion(self):
        """
        When AdaptivePlanner signals END_INTERVIEW:
        - is_completed = True
        - session.status = 'COMPLETED'
        - Final report generated with dual headline scores
        """
        session = InterviewAgent.start_session(
            db=self.db,
            user_id=self.user_id,
            company=self.company,
            role=self.role,
            resume=self.resume,
            role_profile=self.role_profile
        )

        # Patch AdaptivePlanner.plan_next_action to return END_INTERVIEW
        with patch("backend.app.engines.adaptive_planner.AdaptivePlanner.plan_next_action") as mock_plan:
            mock_plan.return_value = PlannerDecision(
                action=PlannerAction.END_INTERVIEW,
                focus_topic="Interview Wrap-Up",
                focus_dimension="conclusion",
                target_difficulty=0.5,
                target_depth=1,
                rationale="All agenda items and subject stages completed."
            )

            turn_result = InterviewAgent.process_answer(
                db=self.db,
                session=session,
                user_answer="We utilized read-replicas and connection pooling with PgBouncer."
            )

            self.assertTrue(turn_result["is_completed"])
            self.assertEqual(session.status, "COMPLETED")
            self.assertIn("Thank you", turn_result["next_question"])
            self.assertIsNotNone(session.completed_at)
            self.assertIn("experience_score", session.final_report_json)
            self.assertIn("subject_knowledge_score", session.final_report_json)


if __name__ == "__main__":
    unittest.main()
