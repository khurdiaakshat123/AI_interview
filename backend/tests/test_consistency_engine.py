import unittest
from backend.app.engines.interview_state import InterviewState
from backend.app.engines.answer_evaluator import SemanticEvaluationResult, CandidateClaimExtraction
from backend.app.engines.consistency_engine import ConsistencyEngine, DiscrepancyRecord


class TestConsistencyEngineLayer(unittest.TestCase):

    def setUp(self):
        self.state = InterviewState(session_id="consistency_test_session")

    def test_different_components_not_a_contradiction(self):
        """
        Example from prompt:
        Resume/Prior: PostgreSQL used for transactions.
        Candidate: MongoDB used for analytics.
        Must NOT be treated as a contradiction because components/subsystems are different.
        """
        self.state.register_resume_claim(
            statement="PostgreSQL used for ACID transactions in checkout service",
            item_id="proj_ecommerce",
            entity="PostgreSQL"
        )

        eval_result = SemanticEvaluationResult(
            answer_understanding="Candidate explained that MongoDB is used for analytics and reporting dashboards.",
            candidate_claims=[
                CandidateClaimExtraction(
                    statement="MongoDB used for analytics and aggregated reporting pipelines",
                    entity="MongoDB",
                    causality_valid=True
                )
            ],
            entities=["MongoDB"],
            reasoning_summary="Candidate clearly partitioned OLTP transactions to PostgreSQL and OLAP analytics to MongoDB."
        )

        analysis = ConsistencyEngine.analyze(
            eval_result=eval_result,
            state=self.state,
            current_item_id="proj_ecommerce",
            current_turn=2
        )

        self.assertFalse(analysis.has_discrepancies)
        self.assertEqual(len(analysis.discrepancies), 0)

    def test_different_projects_not_a_contradiction(self):
        """
        Different projects must not conflict with each other.
        Project 1 uses MySQL; Project 2 uses DynamoDB.
        """
        self.state.register_resume_claim(
            statement="Engineered relational schema in MySQL",
            item_id="proj_1_legacy",
            entity="MySQL"
        )

        eval_result = SemanticEvaluationResult(
            answer_understanding="Candidate explained choosing DynamoDB for single-digit millisecond latency.",
            candidate_claims=[
                CandidateClaimExtraction(
                    statement="Used DynamoDB as our serverless key-value document store",
                    entity="DynamoDB",
                    causality_valid=True
                )
            ],
            entities=["DynamoDB"],
            reasoning_summary="DynamoDB chosen for horizontal serverless scaling."
        )

        analysis = ConsistencyEngine.analyze(
            eval_result=eval_result,
            state=self.state,
            current_item_id="proj_2_serverless",  # Explicitly different project
            current_turn=3
        )

        self.assertFalse(analysis.has_discrepancies)
        self.assertEqual(len(analysis.discrepancies), 0)

    def test_different_time_periods_migration_not_a_contradiction(self):
        """
        Architectural migrations over time (e.g. Django monolith in v1 migrated to Go in v2)
        must NOT be treated as a contradiction.
        """
        self.state.register_resume_claim(
            statement="Maintained monolithic web backend in Django",
            item_id="proj_web",
            entity="Django"
        )

        eval_result = SemanticEvaluationResult(
            answer_understanding="Candidate explained migrating the monolith to Go microservices in v2.",
            candidate_claims=[
                CandidateClaimExtraction(
                    statement="We subsequently migrated and rewrote the services in Go to reduce CPU overhead in v2",
                    entity="Go",
                    causality_valid=True
                )
            ],
            entities=["Go"],
            reasoning_summary="Candidate described phased migration from legacy Django to Go microservices."
        )

        analysis = ConsistencyEngine.analyze(
            eval_result=eval_result,
            state=self.state,
            current_item_id="proj_web",
            current_turn=2
        )

        self.assertFalse(analysis.has_discrepancies)
        self.assertEqual(len(analysis.discrepancies), 0)

    def test_true_scoped_contradiction_prompts_clarification(self):
        """
        Example from prompt:
        Resume/Prior: PostgreSQL used for transactions in Project X.
        Candidate: MongoDB used for the same transaction service in Project X.
        Same project + same component + mutually exclusive stores -> Scoped contradiction.
        Clarification prompt must be neutral. Does NOT subtract score.
        """
        self.state.register_resume_claim(
            statement="PostgreSQL used for transaction service in Project X",
            item_id="proj_x",
            entity="PostgreSQL"
        )

        eval_result = SemanticEvaluationResult(
            answer_understanding="Candidate states MongoDB is used for transactions in Project X.",
            candidate_claims=[
                CandidateClaimExtraction(
                    statement="We store all customer payments and orders in MongoDB for our transaction service",
                    entity="MongoDB",
                    causality_valid=True
                )
            ],
            entities=["MongoDB"],
            reasoning_summary="Candidate stated MongoDB was used for the transaction service in Project X."
        )

        analysis = ConsistencyEngine.analyze(
            eval_result=eval_result,
            state=self.state,
            current_item_id="proj_x",
            current_item_title="Project X",
            current_turn=2
        )

        self.assertTrue(analysis.has_discrepancies)
        self.assertEqual(len(analysis.discrepancies), 1)

        record: DiscrepancyRecord = analysis.discrepancies[0]
        self.assertTrue(record.clarification_recommended)
        self.assertIsNotNone(record.neutral_clarification_prompt)
        self.assertIn("Project X", record.neutral_clarification_prompt)
        self.assertIn("PostgreSQL", record.neutral_clarification_prompt)
        self.assertIn("MongoDB", record.neutral_clarification_prompt)
        self.assertIn("did the stack change over time", record.neutral_clarification_prompt)

    def test_uncertain_scope_prompts_clarification(self):
        """
        Uncertain scope:
        Earlier: PostgreSQL used for user balance data.
        Now: Redis used for user balance data without specifying cache vs primary.
        Should flag clarification_recommended=True with a neutral inquiry asking if Redis was a cache.
        """
        self.state.register_resume_claim(
            statement="PostgreSQL used for persistent user balance records",
            item_id="proj_fintech",
            entity="PostgreSQL"
        )

        eval_result = SemanticEvaluationResult(
            answer_understanding="Candidate mentions Redis for user balance data.",
            candidate_claims=[
                CandidateClaimExtraction(
                    statement="Redis holds user balance data",
                    entity="Redis",
                    causality_valid=True
                )
            ],
            entities=["Redis"],
            reasoning_summary="Candidate mentioned Redis for user balance data."
        )

        analysis = ConsistencyEngine.analyze(
            eval_result=eval_result,
            state=self.state,
            current_item_id="proj_fintech",
            current_item_title="Fintech Engine",
            current_turn=3
        )

        self.assertTrue(analysis.has_discrepancies)
        self.assertTrue(analysis.discrepancies[0].clarification_recommended)
        self.assertIn("caching layer", analysis.discrepancies[0].neutral_clarification_prompt.lower())

    def test_no_contradiction_consistent_statements(self):
        """
        Consistent complementary statements (e.g. Postgres DB + Redis cache explicitly declared)
        produce no discrepancies.
        """
        self.state.register_resume_claim(
            statement="PostgreSQL used as database for user accounts",
            item_id="proj_auth",
            entity="PostgreSQL"
        )

        eval_result = SemanticEvaluationResult(
            answer_understanding="Candidate explains using Redis as a cache in front of PostgreSQL.",
            candidate_claims=[
                CandidateClaimExtraction(
                    statement="We deployed Redis for caching user session tokens in front of PostgreSQL with a 15-minute TTL",
                    entity="Redis",
                    causality_valid=True
                )
            ],
            entities=["Redis"],
            reasoning_summary="Candidate detailed Redis caching pattern."
        )

        analysis = ConsistencyEngine.analyze(
            eval_result=eval_result,
            state=self.state,
            current_item_id="proj_auth",
            current_turn=2
        )

        self.assertFalse(analysis.has_discrepancies)
        self.assertEqual(len(analysis.discrepancies), 0)


if __name__ == "__main__":
    unittest.main()
