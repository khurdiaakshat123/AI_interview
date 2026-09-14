import unittest
from unittest.mock import MagicMock, patch
import uuid

from backend.app.schemas.schemas import (
    InterviewTurnOut, CurrentItemSummary, ProjectScoreCard, ExperienceItemScoreCard,
    InterviewFinalReportOut, InterviewEvidenceRecord, CandidateSetupResponse,
    InterviewSessionCreate, InterviewAnswerRequest, UserOut, RoleTopicProfileOut,
    StructuredResumeOut
)
from backend.app.models.models import InterviewSession, InterviewEvidence, StructuredResume, RoleTopicProfile
from backend.app.agents.interview_agent import InterviewAgent
from backend.app.engines.adaptive_planner import PlannerAction, PlannerDecision
from backend.app.api.interview import (
    create_interview_session, answer_interview_question, get_interview_report
)


class TestInterviewApiContracts(unittest.TestCase):
    """
    Test suite verifying that all API and schema contracts conform to requirements:
    - InterviewTurnOut contains all required frontend fields.
    - Clarification prompts flag is_clarification=True and is_scored=False.
    - No chain-of-thought or planner rationale is exposed.
    - Report schemas support dual headline scores and individual item cards.
    - Endpoints serialize properly without breaking CandidateSetup or existing paths.
    """

    def test_interview_turn_out_schema_complete(self):
        """Verify InterviewTurnOut schema accepts and serializes all new contract fields."""
        turn = InterviewTurnOut(
            session_id="sess_123",
            phase="EXPERIENCE_DEFENSE",
            current_topic="Distributed Consensus",
            question_id="q_456",
            question_text="How did you handle network partitions?",
            depth_level=2,
            max_depth=5,
            is_completed=False,
            next_question="How did you handle network partitions?",
            current_item_id="exp_1",
            current_item_type="WORK_EXPERIENCE",
            current_item_title="Senior Backend Engineer at Stripe",
            current_item=CurrentItemSummary(
                item_id="exp_1",
                item_type="WORK_EXPERIENCE",
                title="Senior Backend Engineer at Stripe"
            ),
            current_dimension="reliability",
            depth_dimension="reliability",
            target_difficulty=0.75,
            question_difficulty=0.75,
            is_clarification=False,
            is_scored=True,
            earned_points=3.8,
            possible_points=4.5,
            evidence_score=0.84,
            concise_evaluation_summary="Candidate demonstrated clear understanding of leader election trade-offs.",
            eval_previous={
                "quality_band": "Good",
                "earned_points": 3.8,
                "possible_points": 4.5,
                "severity": "LOW",
                "feedback": "Clear explanation of leader election.",
                "detected_gap": None,
                "is_scored": True
            }
        )

        data = turn.model_dump()
        self.assertEqual(data["session_id"], "sess_123")
        self.assertEqual(data["current_item_id"], "exp_1")
        self.assertEqual(data["current_item_type"], "WORK_EXPERIENCE")
        self.assertEqual(data["current_item"]["title"], "Senior Backend Engineer at Stripe")
        self.assertEqual(data["current_dimension"], "reliability")
        self.assertEqual(data["depth_dimension"], "reliability")
        self.assertEqual(data["target_difficulty"], 0.75)
        self.assertFalse(data["is_clarification"])
        self.assertTrue(data["is_scored"])
        self.assertEqual(data["earned_points"], 3.8)
        self.assertEqual(data["possible_points"], 4.5)
        self.assertEqual(data["evidence_score"], 0.84)
        self.assertIn("leader election", data["concise_evaluation_summary"])

        # Invariant: No chain-of-thought or planner rationale
        self.assertNotIn("chain_of_thought", data)
        self.assertNotIn("rationale", data)
        self.assertNotIn("planner_rationale", data)

    def test_clarification_prompt_turn_contract(self):
        """Clarification turns must explicitly set is_clarification=True, is_scored=False."""
        turn = InterviewTurnOut(
            session_id="sess_789",
            phase="EXPERIENCE_DEFENSE",
            current_topic="Database Choice",
            question_id="q_clarify_01",
            question_text="Earlier you mentioned PostgreSQL for payments, but later referred to MongoDB. Could you clarify which handled the ACID ledger?",
            depth_level=2,
            max_depth=5,
            is_completed=False,
            is_clarification=True,
            is_scored=False,
            earned_points=0.0,
            possible_points=0.0
        )

        data = turn.model_dump()
        self.assertTrue(data["is_clarification"])
        self.assertFalse(data["is_scored"])
        self.assertEqual(data["earned_points"], 0.0)
        self.assertEqual(data["possible_points"], 0.0)

    def test_project_scorecard_and_untested_item(self):
        """Verify ProjectScoreCard / ExperienceItemScoreCard allows untested items with score=None."""
        tested_card = ProjectScoreCard(
            project_id="proj_raft",
            item_id="proj_raft",
            item_type="PROJECT",
            title="Raft KV Store",
            score=88.5,
            star_rating=4.42,
            relevance_weight=0.9,
            coverage=0.80,
            topics_covered=["Consensus", "Log Compaction"],
            demonstrated_strengths=["Explained term election and heartbeat timers"],
            strengths=["Explained term election and heartbeat timers"],
            identified_gaps=[],
            claim_status_summary={"demonstrated": 4, "unexplored": 1}
        )
        self.assertEqual(tested_card.score, 88.5)
        self.assertEqual(tested_card.star_rating, 4.42)

        untested_card = ExperienceItemScoreCard(
            project_id="proj_recipe",
            item_id="proj_recipe",
            item_type="PROJECT",
            title="Recipe App",
            score=None,
            star_rating=None,
            relevance_weight=0.3,
            coverage=0.0,
            topics_covered=["Recipe App"],
            demonstrated_strengths=[],
            strengths=[],
            identified_gaps=[],
            claim_status_summary={"unexplored": 2}
        )
        self.assertIsNone(untested_card.score)
        self.assertIsNone(untested_card.star_rating)

    def test_interview_final_report_out_schema(self):
        """Verify InterviewFinalReportOut serialization with dual scores and item cards."""
        card = ProjectScoreCard(
            project_id="item_stripe",
            item_id="item_stripe",
            item_type="WORK_EXPERIENCE",
            title="Stripe Infrastructure",
            score=92.0,
            star_rating=4.6,
            relevance_weight=1.0,
            coverage=0.85,
            topics_covered=["Transactions", "Kafka"],
            demonstrated_strengths=["Deep understanding of idempotency"],
            strengths=["Deep understanding of idempotency"],
            identified_gaps=[],
            claim_status_summary={"demonstrated": 5}
        )

        ev_record = InterviewEvidenceRecord(
            id="ev_001",
            project_id_or_topic="item_stripe",
            question_id="q_001",
            follow_up_index=1,
            topic="Transactions",
            subtopic="Idempotency",
            user_answer="We used idempotent keys stored in Redis with atomic SETNX.",
            expected_concept="Idempotent consumer pattern",
            detected_gap=None,
            severity="LOW",
            earned_points=4.8,
            possible_points=5.0,
            evaluator_reason="Solid explanation of atomic key deduplication.",
            evidence_ref="EV-EXP-1"
        )

        report = InterviewFinalReportOut(
            session_id="sess_001",
            company="Stripe",
            role="Backend Engineer",
            candidate_name="Alex",
            resume_related_score=92.0,
            experience_score=92.0,
            subject_knowledge_score=85.0,
            section_scores={
                "Work Experience & Projects": 92.0,
                "Technical Fundamentals": 85.0
            },
            experience_items=[card],
            project_cards=[card],
            experience_cards=[card],
            subject_topics={"Distributed Systems": "STRONG", "Databases": "PARTIAL"},
            subject_topic_breakdown={"Distributed Systems": "STRONG", "Databases": "PARTIAL"},
            evidence_trail=[ev_record],
            strengths=["Strong grasp of distributed transactions and idempotency."],
            weaknesses=[],
            improvement_recommendations=[]
        )

        dumped = report.model_dump()
        self.assertEqual(dumped["experience_score"], 92.0)
        self.assertEqual(dumped["subject_knowledge_score"], 85.0)
        self.assertEqual(len(dumped["experience_items"]), 1)
        self.assertEqual(dumped["experience_items"][0]["item_type"], "WORK_EXPERIENCE")
        self.assertEqual(dumped["subject_topics"]["Distributed Systems"], "STRONG")

    def test_sessions_endpoint_returns_turn_contract(self):
        """Test create_interview_session returns full InterviewTurnOut."""
        db = MagicMock()
        current_user = MagicMock()
        current_user.id = "user_123"

        mock_session = MagicMock()
        mock_session.id = "sess_created"
        mock_session.current_phase = "EXPERIENCE_DEFENSE"
        mock_session.current_question_id = "q_init_1"
        mock_session.current_depth = 1
        mock_session.current_thread_id = "exp_mock"
        mock_session.transcript_json = [
            {"turn_index": 1, "sender": "INTERVIEWER", "topic": "Stripe Payments", "text": "Can you describe your role at Stripe?"}
        ]
        mock_session.agent1_report_json = {
            "current_question_profile": {"difficulty": 0.55, "follow_up_dimension": "responsibilities"},
            "unified_state": {
                "items": {
                    "exp_mock": {
                        "item_id": "exp_mock",
                        "item_type": "WORK_EXPERIENCE",
                        "title": "Stripe Payments Engine"
                    }
                }
            }
        }

        with patch("backend.app.agents.interview_agent.InterviewAgent.start_session", return_value=mock_session):
            payload = InterviewSessionCreate(
                company="Stripe",
                role="Backend Engineer",
                candidate_name="Alex Candidate"
            )
            turn_out = create_interview_session(payload=payload, db=db, current_user=current_user)

            self.assertIsInstance(turn_out, InterviewTurnOut)
            self.assertEqual(turn_out.session_id, "sess_created")
            self.assertEqual(turn_out.current_item_id, "exp_mock")
            self.assertEqual(turn_out.current_item_type, "WORK_EXPERIENCE")
            self.assertEqual(turn_out.current_item_title, "Stripe Payments Engine")
            self.assertEqual(turn_out.current_dimension, "responsibilities")
            self.assertEqual(turn_out.target_difficulty, 0.55)
            self.assertFalse(turn_out.is_clarification)
            self.assertTrue(turn_out.is_scored)

    def test_answer_endpoint_returns_turn_contract(self):
        """Test answer_interview_question returns enriched InterviewTurnOut."""
        db = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "sess_ans"
        mock_session.status = "IN_PROGRESS"
        db.query.return_value.filter.return_value.first.return_value = mock_session

        process_result = {
            "session_id": "sess_ans",
            "phase": "PROJECT_DEFENSE",
            "current_topic": "Raft Consensus",
            "question_id": "q_next_2",
            "question_text": "How do you avoid split-brain during election?",
            "next_question": "How do you avoid split-brain during election?",
            "depth_level": 2,
            "max_depth": 5,
            "is_completed": False,
            "current_item_id": "proj_raft",
            "current_item_type": "PROJECT",
            "current_item_title": "Raft KV Store",
            "current_item": {"item_id": "proj_raft", "item_type": "PROJECT", "title": "Raft KV Store"},
            "current_dimension": "reliability",
            "depth_dimension": "reliability",
            "target_difficulty": 0.65,
            "question_difficulty": 0.65,
            "is_clarification": False,
            "is_scored": True,
            "earned_points": 4.1,
            "possible_points": 4.8,
            "evidence_score": 0.85,
            "concise_evaluation_summary": "Solid explanation of quorum requirements.",
            "eval_previous": {
                "quality_band": "Good",
                "earned_points": 4.1,
                "possible_points": 4.8,
                "severity": "LOW",
                "feedback": "Solid explanation of quorum requirements.",
                "detected_gap": None,
                "is_scored": True,
                "evidence_score": 0.85,
                "concise_evaluation_summary": "Solid explanation of quorum requirements."
            }
        }

        with patch("backend.app.agents.interview_agent.InterviewAgent.process_answer", return_value=process_result):
            payload = InterviewAnswerRequest(answer="A leader must receive votes from a strict majority (N/2 + 1) nodes.")
            turn_out = answer_interview_question(id="sess_ans", payload=payload, db=db)

            self.assertIsInstance(turn_out, InterviewTurnOut)
            self.assertEqual(turn_out.current_item_id, "proj_raft")
            self.assertEqual(turn_out.current_dimension, "reliability")
            self.assertEqual(turn_out.earned_points, 4.1)
            self.assertEqual(turn_out.possible_points, 4.8)
            self.assertEqual(turn_out.evidence_score, 0.85)

    def test_report_endpoint_returns_final_report_contract(self):
        """Test get_interview_report returns InterviewFinalReportOut."""
        db = MagicMock()
        mock_session = MagicMock()
        mock_session.id = "sess_rep"
        mock_session.company = "Stripe"
        mock_session.role = "Backend Engineer"
        mock_session.resume_id = "res_1"
        mock_session.completed_at = None
        mock_session.created_at = None
        mock_session.final_report_json = {
            "session_id": "sess_rep",
            "resume_related_score": 90.0,
            "experience_score": 90.0,
            "subject_knowledge_score": 88.0,
            "section_scores": {"Work Experience & Projects": 90.0, "Technical Fundamentals": 88.0},
            "experience_items": [
                {
                    "project_id": "exp_stripe",
                    "item_id": "exp_stripe",
                    "item_type": "WORK_EXPERIENCE",
                    "title": "Stripe Infrastructure",
                    "score": 90.0,
                    "star_rating": 4.5,
                    "relevance_weight": 1.0,
                    "coverage": 0.9,
                    "topics_covered": ["Kafka"],
                    "demonstrated_strengths": ["Demonstrated mastery"],
                    "strengths": ["Demonstrated mastery"],
                    "identified_gaps": [],
                    "claim_status_summary": {"demonstrated": 4}
                }
            ],
            "subject_topics": {"Databases": "STRONG"},
            "evidence_trail": [],
            "strengths": ["Excellent architecture"],
            "weaknesses": [],
            "improvement_recommendations": []
        }

        mock_resume = MagicMock()
        mock_resume.candidate_name = "Alex Candidate"

        def mock_query(model):
            q = MagicMock()
            if model == InterviewSession:
                q.filter.return_value.first.return_value = mock_session
            elif model == StructuredResume:
                q.filter.return_value.first.return_value = mock_resume
            else:
                q.filter.return_value.all.return_value = []
            return q

        db.query.side_effect = mock_query

        report_out = get_interview_report(id="sess_rep", db=db)
        self.assertIsInstance(report_out, InterviewFinalReportOut)
        self.assertEqual(report_out.experience_score, 90.0)
        self.assertEqual(report_out.subject_knowledge_score, 88.0)
        self.assertEqual(len(report_out.experience_items), 1)
        self.assertEqual(report_out.experience_items[0].item_type, "WORK_EXPERIENCE")


if __name__ == "__main__":
    unittest.main()
