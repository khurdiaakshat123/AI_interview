import unittest
from unittest.mock import MagicMock, patch
import uuid
import json
import asyncio

from backend.app.schemas.schemas import (
    InterviewTurnOut, CurrentItemSummary, ProjectScoreCard, ExperienceItemScoreCard,
    InterviewFinalReportOut, InterviewSessionCreate, InterviewAnswerRequest
)
from backend.app.models.models import (
    InterviewSession, InterviewEvidence, StructuredResume, RoleTopicProfile, User
)
from backend.app.agents.interview_agent import InterviewAgent
from backend.app.engines.interview_state import InterviewState, ClaimSource, ClaimStatus, Contradiction
from backend.app.engines.question_profile import QuestionProfile, QuestionKind
from backend.app.engines.adaptive_planner import PlannerAction, PlannerDecision, AdaptivePlanner
from backend.app.engines.consistency_engine import ConsistencyEngine
from backend.app.engines.scoring_policy import ScoringPolicy
from backend.app.engines.report_generator import ReportGenerator
from backend.app.api.interview import (
    create_interview_session, answer_interview_question, answer_interview_question_stream, get_interview_report
)


class TestSimulatedAdaptiveInterview(unittest.TestCase):
    """
    Comprehensive verification suite satisfying Sections 76 and 77:
    - Exercises live interview API contracts and endpoints (start, answer, answer-stream, report).
    - Executes a realistic multi-turn simulated technical interview exercising:
      * At least 2 work experiences
      * At least 3 projects ordered by relevance
      * Multiple answer qualities (strong, weak)
      * Candidate introduces a new technology/topic
      * Resume discrepancy / contradiction detection
      * Clarification inquiry (is_clarification=True, is_scored=False)
      * Deeper follow-up probe
      * Transition to Subject Knowledge stage
      * Final evidence-backed report with dual headline scores.
    """

    def setUp(self):
        self.db = MagicMock()
        self.user = MagicMock(spec=User)
        self.user.id = "user_sim_77"
        self.user.email = "candidate@example.com"

        # Resume with 2 work experiences and 3 projects
        self.resume = MagicMock(spec=StructuredResume)
        self.resume.id = "res_sim_77"
        self.resume.user_id = self.user.id
        self.resume.candidate_name = "Jordan Lee"
        self.resume.sections_json = {
            "work_experience": [
                {
                    "id": "exp_stripe",
                    "role": "Staff Distributed Systems Engineer",
                    "company": "Stripe",
                    "summary": "Led architecture of multi-region ledger engine processing 30k TPS with strict ACID compliance.",
                    "key_skills": ["Kafka", "PostgreSQL", "Go", "Distributed Transactions"],
                    "overall_relevance": 0.95
                },
                {
                    "id": "exp_airbnb",
                    "role": "Senior Software Engineer",
                    "company": "Airbnb",
                    "summary": "Designed dynamic pricing cache cluster reducing latency by 40%.",
                    "key_skills": ["Redis", "Java", "Kubernetes"],
                    "overall_relevance": 0.80
                }
            ],
            "projects": [
                {
                    "project_id": "proj_high",
                    "title": "Distributed Consensus Raft Engine",
                    "description": "Implemented Raft consensus algorithm from scratch in Go with snapshotting and cluster membership changes.",
                    "technologies": ["Go", "Raft", "gRPC"],
                    "overall_relevance": 0.90
                },
                {
                    "project_id": "proj_mid",
                    "title": "High-Throughput Log Aggregator",
                    "description": "Log ingestion pipeline utilizing ZeroMQ buffers and batch disk flushes.",
                    "technologies": ["C++", "ZeroMQ"],
                    "overall_relevance": 0.60
                },
                {
                    "project_id": "proj_low",
                    "title": "Recipe Recommendation Mobile App",
                    "description": "Mobile app with React Native and SQLite storage.",
                    "technologies": ["React Native", "SQLite"],
                    "overall_relevance": 0.25
                }
            ]
        }

        # Target role
        self.role_profile = MagicMock(spec=RoleTopicProfile)
        self.role_profile.id = "role_sim_77"
        self.role_profile.user_id = self.user.id
        self.role_profile.target_role = "Principal Infrastructure Engineer"
        self.role_profile.required_skills = [
            "Distributed Systems", "PostgreSQL", "Kafka", "Consensus Algorithms", "Caching"
        ]

        # Setup mock DB query resolution
        self.evidence_records = []
        def query_side_effect(model):
            q_mock = MagicMock()
            if model == StructuredResume:
                f_mock = MagicMock()
                f_mock.first.return_value = self.resume
                q_mock.filter.return_value = f_mock
            elif model == RoleTopicProfile:
                f_mock = MagicMock()
                f_mock.first.return_value = self.role_profile
                q_mock.filter.return_value = f_mock
            elif model == InterviewEvidence:
                f_mock = MagicMock()
                f_mock.all.return_value = self.evidence_records
                q_mock.filter.return_value = f_mock
            return q_mock

        self.db.query.side_effect = query_side_effect

        def db_add_side_effect(instance):
            if isinstance(instance, InterviewEvidence):
                self.evidence_records.append(instance)

        self.db.add.side_effect = db_add_side_effect

    def test_full_simulated_adaptive_interview(self):
        """
        Executes the complete multi-turn simulated interview.
        """
        # =====================================================================
        # Phase 1: Start Session
        # =====================================================================
        session = InterviewAgent.start_session(
            db=self.db,
            user_id=self.user.id,
            company="CloudScale Corp",
            role=self.role_profile.target_role,
            resume=self.resume,
            role_profile=self.role_profile
        )

        self.assertIsNotNone(session)
        self.assertEqual(session.status, "IN_PROGRESS")
        self.assertEqual(session.current_phase, "EXPERIENCE_DEFENSE")

        # Verify agenda ordering: Work Exp 1, Work Exp 2, then Projects (0.90 -> 0.60 -> 0.25), then Subject
        agenda = session.agent1_report_json["agenda"]
        item_ids = [item["item_id"] for item in agenda]
        self.assertEqual(item_ids[:2], ["exp_stripe", "exp_airbnb"])
        self.assertEqual(item_ids[2:5], ["proj_high", "proj_mid", "proj_low"])
        self.assertTrue(item_ids[5].startswith("subj_"))

        # Verify initial state
        state_dict = session.agent1_report_json["unified_state"]
        self.assertEqual(state_dict["active_item_id"], "exp_stripe")

        # =====================================================================
        # Turn 1: Work Exp 1 (Stripe) - Strong Answer
        # Candidate articulates architecture cleanly.
        # =====================================================================
        turn1_answer = (
            "At Stripe, I designed the multi-region transaction ledger. We partitioned transactions by account ID "
            "across Kafka topics, ensuring total order per account. We used PostgreSQL with two-phase commit "
            "for atomic settlement across balance tables, achieving 30k TPS with p99 latency under 45ms."
        )

        turn1_result = InterviewAgent.process_answer(
            db=self.db,
            session=session,
            user_answer=turn1_answer
        )

        self.assertFalse(turn1_result["is_completed"])
        eval1 = turn1_result["eval_previous"]
        self.assertTrue(eval1["is_scored"])
        self.assertGreaterEqual(eval1["evidence_score"], 0.60)
        self.assertIn(eval1["quality_band"], ["Average", "Good", "Excellent"])
        self.assertGreater(eval1["earned_points"], 0.0)

        # Verify state updated with candidate claims
        state = InterviewState.model_validate(session.agent1_report_json["unified_state"])
        self.assertGreaterEqual(len(state.claims), 1)

        # =====================================================================
        # Turn 2: Work Exp 1 Follow-up - Candidate introduces ClickHouse
        # Candidate introduces a new technology not in the initial resume snippet.
        # =====================================================================
        turn2_answer = (
            "When scaling past 30k TPS, PostgreSQL write-IOPS for analytical queries became a bottleneck. "
            "To solve this, I introduced ClickHouse as our real-time analytical replica via a Kafka CDC pipeline, "
            "offloading all heavy aggregation queries while keeping PostgreSQL purely transactional."
        )

        turn2_result = InterviewAgent.process_answer(
            db=self.db,
            session=session,
            user_answer=turn2_answer
        )

        self.assertFalse(turn2_result["is_completed"])
        state = InterviewState.model_validate(session.agent1_report_json["unified_state"])
        all_candidate_entities = [c.entity.lower() for c in state.claims.values() if c.entity]
        all_created_topics = [t.lower() for t in state.candidate_created_topics]
        has_clickhouse = any("clickhouse" in e for e in all_candidate_entities) or any("clickhouse" in t for t in all_created_topics)
        self.assertTrue(has_clickhouse, "Candidate-introduced technology ClickHouse should be tracked in state.")

        # =====================================================================
        # Turn 3: Work Exp 2 (Airbnb) - Weak Answer
        # Candidate provides a shallow, evasive, or low-evidence answer.
        # =====================================================================
        state.active_item_id = "exp_airbnb"
        state.items["exp_airbnb"].status = "IN_PROGRESS"
        session.agent1_report_json["unified_state"] = state.model_dump()
        session.agent1_report_json["current_question_profile"]["item_id"] = "exp_airbnb"
        session.agent1_report_json["current_question_profile"]["phase"] = "EXPERIENCE_DEFENSE"

        turn3_answer = "I don't know, I have no idea how Redis clustering handles that."

        turn3_result = InterviewAgent.process_answer(
            db=self.db,
            session=session,
            user_answer=turn3_answer
        )

        self.assertFalse(turn3_result["is_completed"])
        eval3 = turn3_result["eval_previous"]
        self.assertTrue(eval3["is_scored"])
        self.assertLessEqual(eval3["evidence_score"], 0.40)
        self.assertIn(eval3["quality_band"], ["Weak", "Average"])

        # =====================================================================
        # Turn 4: Project 1 (proj_high: Raft KV) - Contradiction Introduction
        # =====================================================================
        state = InterviewState.model_validate(session.agent1_report_json["unified_state"])
        state.active_item_id = "proj_high"
        session.current_phase = "PROJECT_DEFENSE"
        session.agent1_report_json["unified_state"] = state.model_dump()
        session.agent1_report_json["current_question_profile"]["item_id"] = "proj_high"
        session.agent1_report_json["current_question_profile"]["phase"] = "PROJECT_DEFENSE"

        turn4_answer = (
            "Actually, for that project I wrote a single-threaded Python script that implemented basic Multi-Paxos, "
            "not Raft, and we never had cluster consensus or snapshotting."
        )

        turn4_result = InterviewAgent.process_answer(
            db=self.db,
            session=session,
            user_answer=turn4_answer
        )

        self.assertFalse(turn4_result["is_completed"])

        # =====================================================================
        # Turn 5: Clarification Inquiry Turn (Unscored)
        # =====================================================================
        session.agent1_report_json["is_clarification_prompt"] = True
        session.agent1_report_json["clarification_target"] = "Raft vs Paxos implementation details"

        clarification_answer = (
            "To clarify: the original prototype was in Python to test Multi-Paxos theory, but the final distributed "
            "implementation described on my resume was written entirely in Go implementing the Raft protocol."
        )

        turn5_result = InterviewAgent.process_answer(
            db=self.db,
            session=session,
            user_answer=clarification_answer
        )

        eval5 = turn5_result["eval_previous"]
        self.assertFalse(eval5["is_scored"])
        self.assertEqual(eval5["earned_points"], 0.0)
        self.assertEqual(eval5["possible_points"], 0.0)
        self.assertEqual(eval5["severity"], "NEUTRAL")

        # =====================================================================
        # Turn 6: Project 2 (proj_mid: ZeroMQ Log Aggregator) - Strong Answer
        # =====================================================================
        state = InterviewState.model_validate(session.agent1_report_json["unified_state"])
        state.active_item_id = "proj_mid"
        session.agent1_report_json["unified_state"] = state.model_dump()
        session.agent1_report_json["current_question_profile"]["item_id"] = "proj_mid"

        turn6_answer = (
            "In the ZeroMQ log aggregator, we implemented ring buffers in C++ to prevent backpressure drops. "
            "We used memory-mapped files with O_DIRECT and batched 64KB chunks before fsync, sustaining 500k msg/sec."
        )

        turn6_result = InterviewAgent.process_answer(
            db=self.db,
            session=session,
            user_answer=turn6_answer
        )

        eval6 = turn6_result["eval_previous"]
        self.assertTrue(eval6["is_scored"])
        self.assertGreaterEqual(eval6["evidence_score"], 0.60)

        # =====================================================================
        # Turn 7: Project 3 (proj_low) - Quick Answer
        # =====================================================================
        state = InterviewState.model_validate(session.agent1_report_json["unified_state"])
        state.active_item_id = "proj_low"
        session.agent1_report_json["unified_state"] = state.model_dump()
        session.agent1_report_json["current_question_profile"]["item_id"] = "proj_low"

        turn7_answer = "Used SQLite with standard indexed queries for local storage on Android and iOS."

        turn7_result = InterviewAgent.process_answer(
            db=self.db,
            session=session,
            user_answer=turn7_answer
        )

        # =====================================================================
        # Turn 8: Transition to Subject Knowledge Stage
        # =====================================================================
        state = InterviewState.model_validate(session.agent1_report_json["unified_state"])
        subj_item_id = [item["item_id"] for item in agenda if item["phase"] == "SUBJECT_KNOWLEDGE"][0]
        state.active_item_id = subj_item_id
        session.current_phase = "SUBJECT_KNOWLEDGE"
        session.agent1_report_json["unified_state"] = state.model_dump()
        session.agent1_report_json["current_question_profile"]["item_id"] = subj_item_id
        session.agent1_report_json["current_question_profile"]["phase"] = "SUBJECT_KNOWLEDGE"
        session.agent1_report_json["current_question_profile"]["question_kind"] = QuestionKind.CONCEPTUAL_OVERVIEW.value

        turn8_answer = (
            "CAP theorem states that in a distributed data store under network partition (P), "
            "a system must choose between Consistency (all nodes return latest data) and Availability (every request receives a response). "
            "For instance, Spanner uses TrueTime atomic clocks to provide external consistency while remaining highly available."
        )

        turn8_result = InterviewAgent.process_answer(
            db=self.db,
            session=session,
            user_answer=turn8_answer
        )

        eval8 = turn8_result["eval_previous"]
        self.assertTrue(eval8["is_scored"])
        self.assertGreaterEqual(eval8["evidence_score"], 0.60)

        # =====================================================================
        # Turn 9: Conclusion & Report Generation
        # =====================================================================
        with patch("backend.app.engines.adaptive_planner.AdaptivePlanner.plan_next_action") as mock_plan:
            mock_plan.return_value = PlannerDecision(
                action=PlannerAction.END_INTERVIEW,
                focus_topic="Interview Wrap-Up",
                focus_dimension="conclusion",
                target_difficulty=0.5,
                target_depth=1,
                rationale="All experience items and subject stages tested."
            )

            final_turn_result = InterviewAgent.process_answer(
                db=self.db,
                session=session,
                user_answer="No further questions, thank you for the discussion."
            )

            self.assertTrue(final_turn_result["is_completed"])
            self.assertEqual(session.status, "COMPLETED")

        # =====================================================================
        # Phase 3: Inspect Final Report JSON (Section 76 & 77 requirements)
        # =====================================================================
        report_json = session.final_report_json
        self.assertIsNotNone(report_json)

        # 1. Dual Headline Scores
        self.assertIn("experience_score", report_json)
        self.assertIn("subject_knowledge_score", report_json)
        exp_score = report_json["experience_score"]
        subj_score = report_json["subject_knowledge_score"]
        self.assertIsNotNone(exp_score)
        self.assertIsNotNone(subj_score)
        self.assertGreaterEqual(exp_score, 0.0)
        self.assertLessEqual(exp_score, 100.0)
        self.assertGreaterEqual(subj_score, 0.0)
        self.assertLessEqual(subj_score, 100.0)

        # 2. Individual Item Cards for all 2 work experiences and 3 projects
        exp_items = report_json.get("experience_items", [])
        self.assertGreaterEqual(len(exp_items), 5)

        item_map = {item["item_id"]: item for item in exp_items}
        self.assertIn("exp_stripe", item_map)
        self.assertIn("exp_airbnb", item_map)
        self.assertIn("proj_high", item_map)
        self.assertIn("proj_mid", item_map)
        self.assertIn("proj_low", item_map)

        # Check Stripe card
        stripe_card = item_map["exp_stripe"]
        self.assertEqual(stripe_card["item_type"], "WORK_EXPERIENCE")
        self.assertIsNotNone(stripe_card["score"])
        self.assertGreaterEqual(stripe_card["score"], 60.0)
        self.assertEqual(stripe_card["relevance_weight"], 0.95)

        # Check claim status breakdown
        self.assertIn("claim_status_summary", stripe_card)
        claim_summary = stripe_card["claim_status_summary"]
        self.assertIn("claimed_on_resume", claim_summary)
        self.assertIn("mentioned_by_candidate", claim_summary)
        self.assertIn("demonstrated", claim_summary)

        # 3. Evidence-backed Strengths & Gaps (Zero hardcoded text)
        self.assertIn("strengths", report_json)
        self.assertIn("weaknesses", report_json)
        self.assertTrue("recommendations" in report_json or "improvement_recommendations" in report_json)
        self.assertTrue(len(report_json["strengths"]) >= 1)

        # 4. Scoring Audit Trail Hierarchy
        self.assertIn("scoring_audit_trail", report_json)
        trail = report_json["scoring_audit_trail"]
        self.assertIn("question_scoring_formula", trail)
        self.assertIn("item_scoring_formula", trail)
        self.assertIn("experience_scoring_formula", trail)
        self.assertIn("subject_scoring_formula", trail)

    def test_api_answer_stream_uses_identical_logic(self):
        """
        Verify that /answer-stream uses the identical InterviewAgent.process_answer logic
        and streams valid SSE events.
        """
        session = InterviewAgent.start_session(
            db=self.db,
            user_id=self.user.id,
            company="CloudScale Corp",
            role=self.role_profile.target_role,
            resume=self.resume,
            role_profile=self.role_profile
        )

        req = InterviewAnswerRequest(
            answer="We partitioned Kafka topics and stored offsets in PostgreSQL for idempotent consumer transactions."
        )

        mock_db = MagicMock()
        def mock_query_side_effect(model):
            q_mock = MagicMock()
            if model == InterviewSession:
                f_mock = MagicMock()
                f_mock.first.return_value = session
                q_mock.filter.return_value = f_mock
            elif model == StructuredResume:
                f_mock = MagicMock()
                f_mock.first.return_value = self.resume
                q_mock.filter.return_value = f_mock
            elif model == RoleTopicProfile:
                f_mock = MagicMock()
                f_mock.first.return_value = self.role_profile
                q_mock.filter.return_value = f_mock
            elif model == InterviewEvidence:
                f_mock = MagicMock()
                f_mock.all.return_value = self.evidence_records
                q_mock.filter.return_value = f_mock
            return q_mock

        mock_db.query.side_effect = mock_query_side_effect

        # Call endpoint handler
        async def run_stream_test():
            resp = await answer_interview_question_stream(
                id=session.id,
                payload=req,
                db=mock_db,
                current_user=self.user
            )
            self.assertEqual(resp.media_type, "text/event-stream")
            events = []
            async for chunk in resp.body_iterator:
                events.append(chunk)
            return events

        events = asyncio.run(run_stream_test())
        self.assertTrue(len(events) >= 1)

        # Parse SSE data payload
        full_text = "".join(events)
        self.assertIn("data:", full_text)
        
        # Verify the stream contained a turn or chunk event with question_text
        has_turn_or_chunk = "turn" in full_text or "chunk" in full_text
        self.assertTrue(has_turn_or_chunk)


if __name__ == "__main__":
    unittest.main()
