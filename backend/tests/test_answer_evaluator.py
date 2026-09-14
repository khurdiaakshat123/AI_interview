import unittest
from unittest.mock import MagicMock
from backend.app.engines.question_profile import QuestionProfile, QuestionKind
from backend.app.engines.interview_state import InterviewState
from backend.app.engines.answer_evaluator import AnswerEvaluator, SemanticEvaluationResult


class TestAnswerEvaluatorLayer(unittest.TestCase):

    def setUp(self):
        self.state = InterviewState(session_id="eval_test_session")

    def test_rule_10_one_word_factual_answer_is_fully_correct(self):
        """
        Rule 10: A one-word factual answer can be fully correct when the question asks for a fact/name.
        Question: 'Which database did you use?' -> Answer: 'PostgreSQL'
        Must NOT be classified as a non-answer. High coverage, high correctness.
        """
        factual_profile = QuestionProfile(
            question_id="q_fact_1",
            objective="Identify the primary relational database utilized for user data.",
            evidence_units=["Candidate names the primary relational database"],
            topic="Database Architecture",
            difficulty=0.20,
            follow_up_depth=1,
            reasoning_requirement=0.10,  # Low reasoning, direct fact
            question_kind=QuestionKind.ARCHITECTURAL_CHOICE
        )

        result = AnswerEvaluator.evaluate(
            question_profile=factual_profile,
            candidate_answer="PostgreSQL",
            state=self.state,
            llm_client_instance=None  # Tests deterministic fallback rule
        )

        self.assertFalse(result.is_non_answer)
        self.assertGreaterEqual(result.correctness, 0.85)
        self.assertGreaterEqual(result.objective_coverage, 0.85)
        self.assertIn("PostgreSQL", result.entities)
        self.assertEqual(result.directness, 1.0)

    def test_rule_10_one_word_answer_to_reasoning_question_has_low_coverage(self):
        """
        Rule 10 second part:
        Question: 'Why did you choose PostgreSQL over a document store?' -> Answer: 'PostgreSQL'
        Must receive low objective coverage because reasoning objective was not answered.
        """
        reasoning_profile = QuestionProfile(
            question_id="q_why_pg",
            objective="Explain the technical trade-offs that motivated choosing PostgreSQL over MongoDB.",
            evidence_units=["Candidate compares ACID transactional integrity against document flexibility"],
            topic="Database Architecture",
            difficulty=0.70,
            follow_up_depth=2,
            reasoning_requirement=0.85,  # High reasoning requirement!
            question_kind=QuestionKind.TRADE_OFF_ANALYSIS
        )

        result = AnswerEvaluator.evaluate(
            question_profile=reasoning_profile,
            candidate_answer="PostgreSQL",
            state=self.state,
            llm_client_instance=None
        )

        self.assertFalse(result.is_non_answer)  # Not an explicit evasion, but deficient in reasoning
        self.assertLessEqual(result.objective_coverage, 0.25)
        self.assertTrue(len(result.missing_evidence) > 0)
        self.assertIn("reasoning", result.missing_evidence[0].lower())

    def test_explicit_evasion_non_answer_detection(self):
        """
        Verifies genuine deflections/evasions are identified without using length heuristics.
        """
        profile = QuestionProfile(
            question_id="q_evasion_test",
            objective="Explain consensus election timeouts.",
            topic="Distributed Systems"
        )

        for evasion_text in ["I don't know", "No idea", "i am totally aware about this", "pass"]:
            res = AnswerEvaluator.evaluate(
                question_profile=profile,
                candidate_answer=evasion_text,
                state=self.state
            )
            self.assertTrue(res.is_non_answer)
            self.assertEqual(res.correctness, 0.0)
            self.assertEqual(res.objective_coverage, 0.0)

    def test_mocked_llm_evaluator_valid_alternative_architecture(self):
        """
        Rule 7: Alternative technically valid architectures must receive credit.
        Mocks LLM output showing RabbitMQ chosen instead of Kafka for transactional task queues.
        """
        profile = QuestionProfile(
            question_id="q_messaging",
            objective="Evaluate message broker choice for asynchronous background jobs.",
            evidence_units=["Broker selection justified by message routing and retry requirements"],
            topic="Event-Driven Architecture",
            question_kind=QuestionKind.ARCHITECTURAL_CHOICE,
            valid_alternative_guidance="RabbitMQ with AMQP exchange routing is completely valid for worker task queues."
        )

        mock_llm = MagicMock()
        mock_llm.generate_completion.return_value = """
        {
            "answer_understanding": "Candidate chose RabbitMQ with dead-letter exchanges instead of Kafka.",
            "candidate_claims": [
                {
                    "statement": "RabbitMQ chosen because task queues required granular per-message ACKs and dead-lettering rather than append-only stream replays",
                    "entity": "RabbitMQ",
                    "attribute_or_action": "Dead-letter exchange routing",
                    "causality_valid": true,
                    "is_alternative_pattern": true
                }
            ],
            "entities": ["RabbitMQ", "AMQP"],
            "candidate_topics": ["Dead Letter Queues", "Task Queues"],
            "relationships": ["RabbitMQ routes failed jobs to dead letter queue"],
            "reasoning_summary": "Candidate clearly justified RabbitMQ over Kafka based on per-message acknowledgment needs.",
            "objective_evidence": ["Sound architectural justification of AMQP queueing."],
            "missing_evidence": [],
            "correctness": 0.95,
            "objective_coverage": 0.95,
            "completeness": 0.90,
            "technical_validity": 0.95,
            "depth_demonstrated": 0.85,
            "reasoning_quality": 0.90,
            "specificity": 0.85,
            "ownership": 1.0,
            "directness": 1.0,
            "confidence": 0.95,
            "contradictions_with_previous_answers": [],
            "resume_discrepancies": [],
            "technically_valid_alternative": true,
            "clarification_needed": false,
            "clarification_reason": null,
            "uncertainty_notes": null,
            "is_non_answer": false
        }
        """

        result = AnswerEvaluator.evaluate(
            question_profile=profile,
            candidate_answer="We chose RabbitMQ over Kafka because our task queue needed per-message acknowledgments and fine-grained dead-letter exchanges.",
            state=self.state,
            llm_client_instance=mock_llm
        )

        self.assertTrue(result.technically_valid_alternative)
        self.assertGreaterEqual(result.objective_coverage, 0.90)
        self.assertEqual(result.entities, ["RabbitMQ", "AMQP"])
        self.assertIn("RabbitMQ", result.candidate_claims[0].statement)

    def test_mocked_llm_evaluator_scoped_contradiction_prompts_clarification(self):
        """
        Rule 8 & 9: Contradictions must be evaluated in context.
        If context/scope is uncertain, request clarification instead of declaring candidate wrong.
        """
        profile = QuestionProfile(
            question_id="q_consistency_test",
            objective="Explain database isolation used during high-frequency balance checks.",
            topic="Database Transactions",
            question_kind=QuestionKind.CONCURRENCY_SYNC
        )

        mock_llm = MagicMock()
        mock_llm.generate_completion.return_value = """
        {
            "answer_understanding": "Candidate mentions using Read Committed, whereas earlier turn stated Serializable.",
            "candidate_claims": [
                {
                    "statement": "Balance read checks run at Read Committed",
                    "entity": "PostgreSQL",
                    "attribute_or_action": "Read Committed isolation",
                    "causality_valid": true,
                    "is_alternative_pattern": false
                }
            ],
            "entities": ["PostgreSQL"],
            "candidate_topics": ["Transaction Isolation"],
            "relationships": [],
            "reasoning_summary": "Potential scope difference: candidate may separate read paths from write transactions.",
            "objective_evidence": ["Identified Read Committed isolation level."],
            "missing_evidence": [],
            "correctness": 0.70,
            "objective_coverage": 0.70,
            "completeness": 0.70,
            "technical_validity": 0.80,
            "depth_demonstrated": 0.60,
            "reasoning_quality": 0.65,
            "specificity": 0.70,
            "ownership": 0.80,
            "directness": 0.90,
            "confidence": 0.75,
            "contradictions_with_previous_answers": ["Turn 1 stated Serializable for all queries, but now stated Read Committed."],
            "resume_discrepancies": [],
            "technically_valid_alternative": false,
            "clarification_needed": true,
            "clarification_reason": "Clarify whether Read Committed applies to read replicas or primary financial ledger writes.",
            "uncertainty_notes": "Scope distinction between read and write paths is ambiguous.",
            "is_non_answer": false
        }
        """

        result = AnswerEvaluator.evaluate(
            question_profile=profile,
            candidate_answer="We check balances using Read Committed.",
            state=self.state,
            llm_client_instance=mock_llm
        )

        self.assertTrue(result.clarification_needed)
        self.assertIsNotNone(result.clarification_reason)
        self.assertIn("Read Committed", result.clarification_reason)
        self.assertEqual(len(result.contradictions_with_previous_answers), 1)

    def test_conservative_fallback_without_llm(self):
        """
        Rule 11: Does NOT pretend keyword counting understands semantics when LLM is unavailable.
        Returns conservative evidence with uncertainty notes.
        """
        profile = QuestionProfile(
            question_id="q_general_arch",
            objective="Describe system architecture and load balancing.",
            topic="System Architecture",
            difficulty=0.50,
            follow_up_depth=2,
            reasoning_requirement=0.50
        )

        result = AnswerEvaluator.evaluate(
            question_profile=profile,
            candidate_answer="We deployed Nginx as reverse proxy and load balanced across multiple FastAPI worker containers.",
            state=self.state,
            llm_client_instance=None
        )

        self.assertFalse(result.is_non_answer)
        self.assertIsNotNone(result.uncertainty_notes)
        self.assertIn("conservative fallback", result.uncertainty_notes.lower())
        self.assertIn("Nginx", result.entities)

    def test_serialization_of_semantic_evaluation_result(self):
        """Verifies to_dict and from_dict roundtrip."""
        res = SemanticEvaluationResult(
            answer_understanding="Candidate explained Kafka partition keys.",
            reasoning_summary="Partitioning on user_id ensures strict chronological ordering per customer.",
            correctness=0.92,
            objective_coverage=0.88,
            completeness=0.85,
            technical_validity=0.95,
            depth_demonstrated=0.80,
            reasoning_quality=0.90,
            specificity=0.85,
            ownership=1.0,
            directness=1.0,
            confidence=0.90,
            entities=["Kafka", "Partition Key"]
        )

        dumped = res.to_dict()
        self.assertIsInstance(dumped, dict)
        self.assertEqual(dumped["correctness"], 0.92)

        reconstituted = SemanticEvaluationResult.from_dict(dumped)
        self.assertEqual(reconstituted.answer_understanding, res.answer_understanding)
        self.assertEqual(reconstituted.correctness, 0.92)
        self.assertEqual(reconstituted.entities, ["Kafka", "Partition Key"])


if __name__ == "__main__":
    unittest.main()
