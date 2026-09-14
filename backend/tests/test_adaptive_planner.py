import unittest
from backend.app.engines.interview_state import InterviewState, ClaimStatus
from backend.app.engines.answer_evaluator import SemanticEvaluationResult, CandidateClaimExtraction
from backend.app.engines.adaptive_planner import AdaptivePlanner, PlannerAction, PlannerDecision


class TestAdaptivePlanner(unittest.TestCase):

    def setUp(self):
        self.state = InterviewState(session_id="planner_test_session")
        self.state.register_item("exp_1", "WORK_EXPERIENCE", "EXPERIENCE_DEFENSE", "Staff Engineer at Datastream", relevance_weight=0.90)
        self.state.register_item("proj_1", "PROJECT", "PROJECT_DEFENSE", "High-Throughput Caching Layer", relevance_weight=0.85)
        self.state.register_item("proj_low", "PROJECT", "PROJECT_DEFENSE", "Small Side Script", relevance_weight=0.30)
        self.state.register_item("subj_1", "SUBJECT_TOPIC", "SUBJECT_KNOWLEDGE", "Operating Systems & Concurrency", relevance_weight=1.0)
        self.state.start_item("exp_1")

    def test_strong_answer_leads_to_deeper_action(self):
        """
        Rule 1: Strong evidence can justify deeper exploration.
        Candidate gives strong answer about Redis caching -> triggers situational failure testing.
        """
        eval_strong = SemanticEvaluationResult(
            answer_understanding="Candidate explained Redis cache-aside invalidation.",
            reasoning_summary="Sound cache invalidation logic",
            correctness=0.95,
            objective_coverage=0.95,
            completeness=0.90,
            technical_validity=0.95,
            depth_demonstrated=0.85,
            entities=["Redis"]
        )

        decision = AdaptivePlanner.plan_next_action(self.state, latest_eval=eval_strong)
        # Redis caching triggers situational failure testing (e.g. outage, cache stampede)
        self.assertEqual(decision.action, PlannerAction.TEST_FAILURE)
        self.assertEqual(decision.focus_dimension, "failure")
        self.assertGreater(decision.target_difficulty, 0.50)

    def test_weak_answer_leads_to_limited_probe_or_pivot(self):
        """
        Rule 2 & 3: Weak evidence receives at most one focused probe, then moves on.
        Turn 1 weak -> focused implementation check.
        Turn 2 weak -> moves on / advances agenda.
        """
        eval_weak = SemanticEvaluationResult(
            answer_understanding="Candidate gave vague answer lacking specifics.",
            reasoning_summary="Weak explanation",
            correctness=0.25,
            objective_coverage=0.20,
            completeness=0.20,
            technical_validity=0.30,
            depth_demonstrated=0.10
        )

        # Turn 1 weak: gives one repair probe
        d1 = AdaptivePlanner.plan_next_action(self.state, latest_eval=eval_weak)
        self.assertEqual(d1.action, PlannerAction.TEST_IMPLEMENTATION)
        self.assertLessEqual(d1.target_difficulty, 0.40)

        # Turn 2: candidate is weak again -> pivots / advances
        self.state.items["exp_1"].turns_spent = 2
        d2 = AdaptivePlanner.plan_next_action(self.state, latest_eval=eval_weak)
        self.assertEqual(d2.action, PlannerAction.START_NEXT_ITEM)

    def test_contradiction_triggers_clarification_before_penalty(self):
        """
        Rule 5: Contradictions must be clarified before penalty.
        """
        eval_contra = SemanticEvaluationResult(
            answer_understanding="Candidate mentions using MongoDB for transactions.",
            reasoning_summary="Potential contradiction with earlier PostgreSQL claim",
            clarification_needed=True,
            clarification_reason="Earlier stated PostgreSQL for transactions, now stated MongoDB."
        )

        decision = AdaptivePlanner.plan_next_action(self.state, latest_eval=eval_contra)
        self.assertEqual(decision.action, PlannerAction.CLARIFY_CONTRADICTION)
        self.assertIn("clarification", decision.rationale.lower())

    def test_candidate_created_topic_triggers_exploration(self):
        """
        Rule 7: Candidate-created high-value topics can become active threads.
        """
        self.state.add_candidate_topic("CQRS Pattern")
        eval_with_topic = SemanticEvaluationResult(
            answer_understanding="Candidate introduced CQRS pattern for read scaling.",
            reasoning_summary="Volunteered CQRS",
            correctness=0.85,
            objective_coverage=0.85,
            candidate_topics=["CQRS Pattern"],
            entities=["CQRS"]
        )

        decision = AdaptivePlanner.plan_next_action(self.state, latest_eval=eval_with_topic)
        self.assertEqual(decision.action, PlannerAction.EXPLORE_CANDIDATE_TOPIC)
        self.assertEqual(decision.focus_topic, "CQRS Pattern")

    def test_unexplored_resume_claim_triggers_exploration(self):
        """
        Rule 8: Resume topics remain available and can be explored.
        """
        # Register an unexplored resume claim on current item
        rc = self.state.register_resume_claim(
            statement="Tuned kernel TCP buffers for high-throughput streaming",
            item_id="exp_1",
            entity="TCP Buffers"
        )
        self.assertEqual(rc.status, ClaimStatus.UNEXPLORED)

        # Neutral baseline answer with no new claims
        eval_neutral = SemanticEvaluationResult(
            answer_understanding="Candidate provided normal overview.",
            reasoning_summary="Standard response",
            correctness=0.65,
            objective_coverage=0.60,
            completeness=0.60
        )

        decision = AdaptivePlanner.plan_next_action(self.state, latest_eval=eval_neutral)
        self.assertEqual(decision.action, PlannerAction.EXPLORE_RESUME_TOPIC)
        self.assertEqual(decision.focus_claim_id, rc.claim_id)

    def test_repeated_dimension_prevention_safety_guardrail(self):
        """
        Rule 17: Prevents repeatedly testing the same dimension on the same item.
        """
        eval_strong = SemanticEvaluationResult(
            answer_understanding="Detailed Redis caching and failover.",
            reasoning_summary="Strong answer",
            correctness=0.90,
            objective_coverage=0.90,
            entities=["Redis"]
        )

        # Record that 'failure' was already tested on this item
        self.state.record_planner_action(
            turn_index=1,
            action="TEST_FAILURE",
            focus_topic="Redis",
            rationale="Tested failure mode"
        )

        decision = AdaptivePlanner.plan_next_action(self.state, latest_eval=eval_strong)
        # Should NOT ask failure again; should choose tradeoff or another dimension!
        self.assertNotEqual(decision.focus_dimension, "failure")
        self.assertEqual(decision.action, PlannerAction.TEST_TRADEOFF)

    def test_high_relevance_vs_low_relevance_exploration_depth(self):
        """
        Rules 13 & 14: Higher-relevance items receive more exploration; lower-relevance items pivot sooner.
        """
        # Low relevance item (relevance = 0.30)
        self.state.start_item("proj_low")
        self.state.items["proj_low"].turns_spent = 2  # Already had 2 turns

        eval_ok = SemanticEvaluationResult(
            answer_understanding="Average script explanation",
            reasoning_summary="Average response",
            correctness=0.70,
            objective_coverage=0.70
        )

        decision = AdaptivePlanner.plan_next_action(self.state, latest_eval=eval_ok)
        # Low relevance item budget is exhausted at 2 turns -> must advance!
        self.assertEqual(decision.action, PlannerAction.START_NEXT_ITEM)

    def test_different_answers_produce_different_planner_actions(self):
        """
        Rule 21: Different candidate answers to the same starting item produce different planner actions.
        """
        # Answer A: Mentioned Redis -> tests failure
        ans_redis = SemanticEvaluationResult(
            answer_understanding="Used Redis",
            reasoning_summary="Redis cache",
            correctness=0.85,
            objective_coverage=0.85,
            entities=["Redis"]
        )
        dec_a = AdaptivePlanner.plan_next_action(self.state, latest_eval=ans_redis)
        self.assertEqual(dec_a.action, PlannerAction.TEST_FAILURE)

        # Answer B: Mentioned Kafka -> tests scale
        ans_kafka = SemanticEvaluationResult(
            answer_understanding="Used Kafka for message queues",
            reasoning_summary="Kafka event streaming",
            correctness=0.85,
            objective_coverage=0.85,
            entities=["Kafka"]
        )
        dec_b = AdaptivePlanner.plan_next_action(self.state, latest_eval=ans_kafka)
        self.assertEqual(dec_b.action, PlannerAction.TEST_SCALE)

        # Answer C: Contradiction -> clarify
        ans_contra = SemanticEvaluationResult(
            answer_understanding="Contradiction",
            reasoning_summary="Inconsistent",
            clarification_needed=True,
            clarification_reason="Scope conflict"
        )
        dec_c = AdaptivePlanner.plan_next_action(self.state, latest_eval=ans_contra)
        self.assertEqual(dec_c.action, PlannerAction.CLARIFY_CONTRADICTION)

        # Answer D: Non-answer -> does not drill
        ans_evasion = SemanticEvaluationResult(
            answer_understanding="Evasion",
            reasoning_summary="I don't know",
            is_non_answer=True
        )
        self.state.items["exp_1"].turns_spent = 1
        dec_d = AdaptivePlanner.plan_next_action(self.state, latest_eval=ans_evasion)
        self.assertIn(dec_d.action, [PlannerAction.START_NEXT_ITEM, PlannerAction.PIVOT_ITEM])

    def test_experience_and_projects_complete_before_subject_knowledge(self):
        """
        Rules 19 & 20:
        Pivots through all Work Experience & Projects before Subject Knowledge.
        Subject knowledge stage starts ONLY after all experience & projects have concluded.
        """
        # Advance through all experience items
        self.state.items["exp_1"].turns_spent = 5
        d1 = AdaptivePlanner.plan_next_action(self.state)
        self.assertEqual(d1.action, PlannerAction.START_NEXT_ITEM)
        self.assertEqual(self.state.active_item_id, "proj_1")

        self.state.items["proj_1"].turns_spent = 4
        d2 = AdaptivePlanner.plan_next_action(self.state)
        self.assertEqual(d2.action, PlannerAction.START_NEXT_ITEM)
        self.assertEqual(self.state.active_item_id, "proj_low")

        self.state.items["proj_low"].turns_spent = 2
        d3 = AdaptivePlanner.plan_next_action(self.state)

        # All experience and projects finished -> Now Subject Knowledge begins!
        self.assertEqual(d3.action, PlannerAction.START_SUBJECT_STAGE)
        self.assertEqual(self.state.current_phase, "SUBJECT_KNOWLEDGE")
        self.assertEqual(self.state.active_item_id, "subj_1")

        # When subject item concludes -> END_INTERVIEW
        self.state.items["subj_1"].turns_spent = 4
        d4 = AdaptivePlanner.plan_next_action(self.state)
        self.assertEqual(d4.action, PlannerAction.END_INTERVIEW)
        self.assertEqual(self.state.current_phase, "COMPLETED")


if __name__ == "__main__":
    unittest.main()
