import unittest
from unittest.mock import MagicMock
import uuid

from backend.app.models.models import InterviewSession, InterviewEvidence, utc_now
from backend.app.engines.interview_state import InterviewState, ClaimStatus, ClaimSource
from backend.app.engines.report_generator import ReportGenerator


class TestEvidenceBackedReportGenerator(unittest.TestCase):
    """
    Test suite for 100% evidence-backed report generation:
    - Experience score weighting across both work experience and projects
    - Exclusion of untested items from experience score
    - Separate unblended subject knowledge score
    - Distinct claim status counts
    - Evidence-backed subject mastery breakdown (STRONG/PARTIAL/WEAK/UNTESTED)
    - Zero hardcoded generic strings in strengths, weaknesses, or recommendations
    """

    def setUp(self):
        self.session = MagicMock(spec=InterviewSession)
        self.session.id = "session_report_test"
        self.session.transcript_json = []

        self.state = InterviewState(session_id=self.session.id)

        # Register 1 Work Experience and 2 Projects (one tested, one untested)
        self.state.register_item(
            item_id="exp_stripe",
            item_type="WORK_EXPERIENCE",
            phase="EXPERIENCE_DEFENSE",
            title="Senior Infrastructure Engineer at Stripe",
            relevance_weight=0.90
        )
        self.state.register_item(
            item_id="proj_raft",
            item_type="PROJECT",
            phase="PROJECT_DEFENSE",
            title="Distributed Raft Key-Value Store",
            relevance_weight=0.60
        )
        self.state.register_item(
            item_id="proj_todo",
            item_type="PROJECT",
            phase="PROJECT_DEFENSE",
            title="Simple Todo App",
            relevance_weight=0.30
        )

        # Register Subject Knowledge topic
        self.state.register_item(
            item_id="subj_distributed",
            item_type="SUBJECT_TOPIC",
            phase="SUBJECT_KNOWLEDGE",
            title="Distributed Systems & Consensus",
            relevance_weight=1.0
        )
        self.state.register_item(
            item_id="subj_untested",
            item_type="SUBJECT_TOPIC",
            phase="SUBJECT_KNOWLEDGE",
            title="Operating Systems & Kernel Scheduling",
            relevance_weight=1.0
        )

    def test_experience_score_relevance_weighting_and_untested_exclusion(self):
        """
        Rule: Experience score is:
        Sigma(item_score * item_relevance) / Sigma(item_relevance)
        Untested items MUST have score = None and be excluded from the calculation.
        Work experience must be treated identically to projects for scoring.
        """
        # exp_stripe: earned 80 / possible 100 -> score 80.0
        ev1 = InterviewEvidence(
            id=str(uuid.uuid4()),
            session_id=self.session.id,
            project_id_or_topic="exp_stripe",
            question_id="q1",
            topic="Stripe Settlement Pipeline",
            earned_points=80.0,
            possible_points=100.0,
            evidence_ref="EV-EXP-1",
            evaluator_reason="Solid architectural breakdown of settlement pipeline",
            expected_concept="Kafka partition scaling",
            severity="NONE"
        )

        # proj_raft: earned 90 / possible 100 -> score 90.0
        ev2 = InterviewEvidence(
            id=str(uuid.uuid4()),
            session_id=self.session.id,
            project_id_or_topic="proj_raft",
            question_id="q2",
            topic="Raft Consensus Protocol",
            earned_points=90.0,
            possible_points=100.0,
            evidence_ref="EV-PRO-1",
            evaluator_reason="Clear understanding of leader election and log compaction",
            expected_concept="Consensus guarantees",
            severity="NONE"
        )

        # proj_todo is UNTESTED (0 evidence rows)

        report = ReportGenerator.generate_report(
            session=self.session,
            state=self.state,
            all_evidence=[ev1, ev2]
        )

        # Verify cards
        cards_by_id = {c["item_id"]: c for c in report["project_cards"]}
        self.assertIn("exp_stripe", cards_by_id)
        self.assertIn("proj_raft", cards_by_id)
        self.assertIn("proj_todo", cards_by_id)

        # Tested items
        self.assertEqual(cards_by_id["exp_stripe"]["score"], 80.0)
        self.assertEqual(cards_by_id["exp_stripe"]["star_rating"], 4.0)
        self.assertEqual(cards_by_id["exp_stripe"]["item_type"], "WORK_EXPERIENCE")

        self.assertEqual(cards_by_id["proj_raft"]["score"], 90.0)
        self.assertEqual(cards_by_id["proj_raft"]["star_rating"], 4.5)
        self.assertEqual(cards_by_id["proj_raft"]["item_type"], "PROJECT")

        # Untested item
        self.assertIsNone(cards_by_id["proj_todo"]["score"])
        self.assertIsNone(cards_by_id["proj_todo"]["star_rating"])

        # Expected Experience score: (80.0 * 0.90 + 90.0 * 0.60) / (0.90 + 0.60)
        # = (72.0 + 54.0) / 1.50 = 126.0 / 1.50 = 84.0
        self.assertEqual(report["experience_score"], 84.0)
        self.assertEqual(report["resume_related_score"], 84.0)

    def test_subject_knowledge_score_separate_without_blending(self):
        """
        Rule: Subject Knowledge score is separate:
        Sigma(subject earned) / Sigma(subject possible) * 100
        Must not invent a combined score.
        """
        ev_exp = InterviewEvidence(
            id=str(uuid.uuid4()),
            session_id=self.session.id,
            project_id_or_topic="exp_stripe",
            question_id="q1",
            topic="Stripe Pipeline",
            earned_points=50.0,
            possible_points=100.0,
            evidence_ref="EV-EXP-1",
            evaluator_reason="Basic overview",
            severity="NONE"
        )
        ev_subj = InterviewEvidence(
            id=str(uuid.uuid4()),
            session_id=self.session.id,
            project_id_or_topic="subj_distributed",
            question_id="q_sub_1",
            topic="Distributed Systems & Consensus",
            earned_points=95.0,
            possible_points=100.0,
            evidence_ref="EV-SUB-1",
            evaluator_reason="Exemplary Paxos vs Raft trade-off analysis",
            expected_concept="Consensus split brain",
            severity="NONE"
        )

        report = ReportGenerator.generate_report(
            session=self.session,
            state=self.state,
            all_evidence=[ev_exp, ev_subj]
        )

        self.assertEqual(report["experience_score"], 50.0)
        self.assertEqual(report["subject_knowledge_score"], 95.0)
        self.assertNotEqual(report["experience_score"], report["subject_knowledge_score"])

    def test_claim_status_summary_distinctions(self):
        """
        Rule: Claim status must strictly distinguish:
        - claimed on resume (UNEXPLORED)
        - mentioned by candidate
        - demonstrated
        - strongly demonstrated
        - partially supported
        - unverified
        - contradicted
        - clarification required
        - not explored.
        Do not treat 'present on resume' as 'demonstrated knowledge'.
        Do not penalize 'not explored'.
        """
        # Register various claims on exp_stripe
        c1 = self.state.register_resume_claim("Managed Kafka clusters", item_id="exp_stripe")
        # c1 is UNEXPLORED -> claimed_on_resume / not_explored

        c2 = self.state.register_resume_claim("Designed caching layer", item_id="exp_stripe")
        self.state.record_candidate_mention_of_resume_claim(c2.claim_id, 1)
        # c2 is MENTIONED

        c3 = self.state.record_candidate_claim("Scaled to 25k TPS", item_id="exp_stripe")
        self.state.record_evidence_for_claim(c3.claim_id, "MODERATE", 2, "Verified with metrics")
        # c3 is SUPPORTED -> demonstrated

        c4 = self.state.record_candidate_claim("Zero downtime migrations", item_id="exp_stripe")
        self.state.record_evidence_for_claim(c4.claim_id, "STRONG", 3, "Detailed schema migration strategy")
        # c4 is STRONGLY_SUPPORTED -> strongly_demonstrated

        c5 = self.state.record_contradiction(
            claim_id_a=c1.claim_id,
            description="Contradiction in storage engine",
            item_id="exp_stripe",
            is_uncertain=False
        )
        # c1 marked CONTRADICTED

        card = ReportGenerator._build_item_card("exp_stripe", self.state.items["exp_stripe"], self.state, [])
        summary = card["claim_status_summary"]

        self.assertGreaterEqual(summary["mentioned_by_candidate"], 1)
        self.assertGreaterEqual(summary["demonstrated"], 1)
        self.assertGreaterEqual(summary["strongly_demonstrated"], 1)
        self.assertGreaterEqual(summary["contradicted"], 1)

    def test_subject_topic_breakdown_evidence_backed(self):
        """
        Rule: Subject topics must be evidence-backed (STRONG/PARTIAL/WEAK/UNTESTED).
        No hardcoded role-keyword guessing.
        """
        # Test subj_distributed with strong evidence (90%)
        ev_strong = InterviewEvidence(
            id=str(uuid.uuid4()),
            session_id=self.session.id,
            project_id_or_topic="subj_distributed",
            question_id="q_sub",
            topic="Distributed Systems & Consensus",
            earned_points=90.0,
            possible_points=100.0,
            evidence_ref="EV-SUB-1",
            evaluator_reason="Strong Paxos explanation",
            severity="NONE"
        )

        report = ReportGenerator.generate_report(
            session=self.session,
            state=self.state,
            all_evidence=[ev_strong]
        )

        breakdown = report["subject_topic_breakdown"]
        self.assertEqual(breakdown.get("Distributed Systems & Consensus"), "STRONG")
        self.assertEqual(breakdown.get("Operating Systems & Kernel Scheduling"), "UNTESTED")

    def test_zero_hardcoded_generic_strings(self):
        """
        Rule: The final report must NOT contain hardcoded generic strengths, weaknesses,
        or recommendations. Every insight must trace to evidence or detected gaps.
        """
        ev_gap = InterviewEvidence(
            id=str(uuid.uuid4()),
            session_id=self.session.id,
            project_id_or_topic="exp_stripe",
            question_id="q_gap",
            topic="Database Sharding",
            earned_points=20.0,
            possible_points=100.0,
            evidence_ref="EV-EXP-2",
            detected_gap="Failed to explain shard key distribution and hot-spotting mitigation",
            evaluator_reason="Unclear partitioning strategy",
            severity="MODERATE"
        )

        report = ReportGenerator.generate_report(
            session=self.session,
            state=self.state,
            all_evidence=[ev_gap]
        )

        # Must not contain old hardcoded phrases
        old_phrases = [
            "Articulates design trade-offs with practical engineering rationale.",
            "Demonstrates solid fundamental and architectural intuition.",
            "Deeper knowledge of partition-tolerance failure edge cases",
            "Review distributed state synchronization and split-brain handling."
        ]
        for phrase in old_phrases:
            self.assertNotIn(phrase, report["strengths"])
            self.assertNotIn(phrase, report["weaknesses"])
            self.assertNotIn(phrase, report["improvement_recommendations"])

        # Must contain evidence-traceable weaknesses regarding the detected gap
        self.assertTrue(
            any("hot-spotting" in w or "Database Sharding" in w or "partitioning" in w for w in report["weaknesses"])
        )
        # Recommendation must directly relate to the gap
        self.assertTrue(
            any("hot-spotting" in r or "Database Sharding" in r or "partitioning" in r for r in report["improvement_recommendations"])
        )


if __name__ == "__main__":
    unittest.main()
