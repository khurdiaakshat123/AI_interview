import unittest
from backend.app.engines.question_profile import QuestionProfile, QuestionKind


class TestQuestionProfileLayer(unittest.TestCase):

    def test_difficulty_and_depth_independence(self):
        """
        Verifies that difficulty and follow-up depth are strictly independent dimensions.
        Case A: Easy factual question with high follow-up depth (L5).
        Case B: Difficult independent question with low follow-up depth (L1).
        """
        # Case A: Easy factual question at deep follow-up level (Depth 5)
        easy_deep_profile = QuestionProfile(
            question_id="q_deep_easy",
            objective="Verify the exact cache TTL duration candidate configured in Redis.",
            evidence_units=["Candidate provides TTL numeric duration and unit"],
            phase="PROJECT_DEFENSE",
            item_id="proj_cache",
            item_type="PROJECT",
            topic="Distributed Caching",
            subtopic="TTL Configuration",
            difficulty=0.20,  # EASY
            follow_up_depth=5,  # HIGH DEPTH
            cognitive_complexity=0.15,
            technical_complexity=0.25,
            reasoning_requirement=0.10,
            specificity_requirement=0.80,
            question_kind=QuestionKind.SPECIFICATION_PROBE
        )
        self.assertEqual(easy_deep_profile.follow_up_depth, 5)
        self.assertEqual(easy_deep_profile.difficulty, 0.20)
        self.assertEqual(easy_deep_profile.difficulty_category(), "EASY")

        # Case B: Difficult architectural question at initial turn (Depth 1)
        hard_shallow_profile = QuestionProfile(
            question_id="q_init_hard",
            objective="Evaluate candidate's approach to distributed consensus split-brain resolution under asymmetric network partitions.",
            evidence_units=[
                "Candidate identifies quorum requirement (e.g. (N/2)+1)",
                "Candidate analyzes generation/epoch/term fencing tokens to prevent stale leader writes"
            ],
            phase="PROJECT_DEFENSE",
            item_id="proj_raft",
            item_type="PROJECT",
            topic="Distributed Consensus",
            subtopic="Split-Brain Prevention",
            difficulty=0.92,  # VERY HARD
            follow_up_depth=1,  # SHALLOW (Opening turn)
            cognitive_complexity=0.95,
            technical_complexity=0.90,
            reasoning_requirement=0.90,
            question_kind=QuestionKind.FAILURE_RECOVERY
        )
        self.assertEqual(hard_shallow_profile.follow_up_depth, 1)
        self.assertEqual(hard_shallow_profile.difficulty, 0.92)
        self.assertEqual(hard_shallow_profile.difficulty_category(), "HARD")

    def test_validation_bounds_normalized_zero_to_one(self):
        """Verifies that values outside [0, 1] raise ValueError."""
        # Value > 1.0
        with self.assertRaises(ValueError):
            QuestionProfile(
                question_id="q_invalid_high",
                objective="Test invalid upper bound",
                topic="Architecture",
                difficulty=1.25  # Exceeds 1.0
            )

        # Value < 0.0
        with self.assertRaises(ValueError):
            QuestionProfile(
                question_id="q_invalid_low",
                objective="Test invalid lower bound",
                topic="Architecture",
                reasoning_requirement=-0.10  # Negative
            )

        # Invalid follow-up depth < 1
        with self.assertRaises(ValueError):
            QuestionProfile(
                question_id="q_invalid_depth",
                objective="Test invalid depth",
                topic="Architecture",
                follow_up_depth=0
            )

    def test_serialization_and_deserialization(self):
        """Verifies to_dict and from_dict preserve all properties accurately."""
        profile = QuestionProfile(
            question_id="q_tradeoff_1",
            objective="Evaluate trade-off between relational PostgreSQL and document-based MongoDB for order processing.",
            evidence_units=[
                "Contrasts ACID multi-table transaction guarantees with schema flexibility",
                "Identifies indexing considerations and write amplification trade-offs"
            ],
            phase="EXPERIENCE_DEFENSE",
            item_id="exp_backend",
            item_type="WORK_EXPERIENCE",
            topic="Database Architecture",
            subtopic="Storage Engine Selection",
            difficulty=0.65,
            follow_up_depth=3,
            cognitive_complexity=0.75,
            technical_complexity=0.70,
            reasoning_requirement=0.80,
            specificity_requirement=0.60,
            breadth=0.50,
            role_relevance=0.95,
            objective_importance=0.90,
            question_kind=QuestionKind.TRADE_OFF_ANALYSIS,
            expected_answer_shape="Candidate explains why the specific database model fits their query patterns and acknowledges trade-offs.",
            valid_alternative_guidance="Accept either PostgreSQL, MySQL, CockroachDB, or MongoDB/DynamoDB if the relational or document choice is justified by operational requirements.",
            prohibited_assumptions=[
                "Do not assume candidate had an enterprise database budget",
                "Do not assume microservices were mandatory"
            ]
        )

        serialized = profile.to_dict()
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized["question_id"], "q_tradeoff_1")
        self.assertEqual(serialized["difficulty"], 0.65)
        self.assertEqual(serialized["follow_up_depth"], 3)
        self.assertEqual(serialized["question_kind"], "TRADE_OFF_ANALYSIS")
        self.assertEqual(len(serialized["prohibited_assumptions"]), 2)

        # Reconstitute from dict
        reconstituted = QuestionProfile.from_dict(serialized)
        self.assertEqual(reconstituted.question_id, profile.question_id)
        self.assertEqual(reconstituted.difficulty, profile.difficulty)
        self.assertEqual(reconstituted.follow_up_depth, profile.follow_up_depth)
        self.assertEqual(reconstituted.question_kind, QuestionKind.TRADE_OFF_ANALYSIS)
        self.assertEqual(reconstituted.valid_alternative_guidance, profile.valid_alternative_guidance)
        self.assertEqual(reconstituted.prohibited_assumptions, profile.prohibited_assumptions)

    def test_flexible_alternative_guidance_and_prohibited_assumptions(self):
        """Verifies profile defines evidence criteria and alternative patterns rather than rigid single answers."""
        profile = QuestionProfile(
            question_id="q_caching",
            objective="Understand the caching invalidation strategy implemented for catalog queries.",
            evidence_units=[
                "Candidate specifies invalidation trigger (e.g. TTL, event-driven, or write-through)",
                "Candidate explains how stale read window or cache stampede is managed"
            ],
            topic="Distributed Caching",
            expected_answer_shape="Strategy -> Invalidation Trigger -> Stale Data / Concurrency Mitigation",
            valid_alternative_guidance="Write-through, write-behind, or cache-aside are all acceptable. Redis, Memcached, or in-memory caches are all acceptable.",
            prohibited_assumptions=["Do not assume Redis was used", "Do not assume zero-stale consistency was strictly required"]
        )

        self.assertIn("write-through", profile.valid_alternative_guidance.lower())
        self.assertIn("Memcached", profile.valid_alternative_guidance)
        self.assertEqual(len(profile.prohibited_assumptions), 2)


if __name__ == "__main__":
    unittest.main()
