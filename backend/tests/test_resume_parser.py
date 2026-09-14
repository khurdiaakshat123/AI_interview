import unittest
from backend.app.engines.resume_parser import ResumeParser, generate_stable_id
from backend.app.engines.interview_state import InterviewState, ClaimSource, ClaimStatus
from backend.app.agents.interview_agent import InterviewAgent


class TestResumeParser(unittest.TestCase):

    def setUp(self):
        self.state = InterviewState(session_id="test_parser_session")

    def test_no_fake_fallback_candidate_data(self):
        """
        Requirement: Do NOT inject fake certifications, achievements, extracurriculars,
        projects, technologies, or metrics.
        If extraction fails or text is minimal, return neutral empty context.
        """
        sparse_text = "Jane Doe\njane.doe@example.com\nSoftware Engineer"
        parsed = ResumeParser.parse_resume(sparse_text, target_company="Tech Corp", target_role="Software Engineer")

        sections = parsed["sections"]
        # Certifications must be empty, not fake AWS/CKAD
        self.assertEqual(sections["certifications"], [])
        # Achievements must be empty, not fake Hackathon/publications
        self.assertEqual(sections["achievements"], [])
        # Extracurricular must be empty, not fake open source contributor
        self.assertEqual(sections["extracurricular"], [])
        # Projects must be empty, not fake Distributed Key-Value Store / Whiteboard
        self.assertEqual(sections["projects"], [])
        # Work experience must be empty, not fake Datastream / CloudScale
        self.assertEqual(sections["work_experience"], [])

        # Check candidate details
        self.assertEqual(parsed["candidate_email"], "jane.doe@example.com")
        self.assertIn("Jane", parsed["candidate_name"])

    def test_resume_claims_start_unexplored(self):
        """
        Requirement:
        1. Explicit resume claims must be stored separately from candidate assertions.
        2. Resume claims start UNEXPLORED.
        3. Do NOT mark resume claims as demonstrated.
        """
        resume_sections = {
            "work_experience": [
                {
                    "company": "Apex Cloud",
                    "role": "Lead Systems Engineer",
                    "summary": "Architected multi-region Kubernetes clusters handling 50k RPS.",
                    "responsibilities": ["Lead zero-downtime database migrations"],
                    "technologies": ["Go", "Kubernetes", "PostgreSQL"],
                    "components_services": ["Ingress Gateway", "PostgreSQL Cluster"],
                    "architecture_claims": ["Multi-region active-passive failover"],
                    "metrics": ["50k RPS", "99.99% availability"],
                    "ownership_claims": ["Spearheaded core cloud migration"],
                    "overall_relevance": 0.90
                }
            ],
            "projects": [
                {
                    "title": "Distributed Ledger",
                    "description": "Implemented Paxos consensus engine with RocksDB persistence.",
                    "technologies": ["Rust", "RocksDB"],
                    "components_services": ["Storage Engine"],
                    "architecture_claims": ["Quorum consensus"],
                    "metrics": ["sub-10ms commit latency"],
                    "responsibilities": ["Implemented WAL recovery log"],
                    "overall_relevance": 0.85
                }
            ]
        }

        ResumeParser.populate_interview_state(self.state, resume_sections)

        self.assertGreater(len(self.state.claims), 0)
        for cid, claim in self.state.claims.items():
            # Must be RESUME source
            self.assertEqual(claim.source, ClaimSource.RESUME)
            # Must start strictly as UNEXPLORED
            self.assertEqual(claim.status, ClaimStatus.UNEXPLORED)
            # Must not be demonstrated
            self.assertNotEqual(claim.status, ClaimStatus.SUPPORTED)
            self.assertNotEqual(claim.status, ClaimStatus.STRONGLY_SUPPORTED)

    def test_work_experience_ordering(self):
        """
        Requirement:
        - Ask ALL work experience first.
        - Preserve resume order/chronology.
        """
        resume_text = """
John Smith
john@smith.io

Experience:
Senior Software Engineer at Alpha Systems (2022 - Present)
- Designed real-time event pipeline using Apache Kafka and Redis.
- Maintained 99.9% uptime across 10 microservices.

Software Developer at Beta Technologies (2020 - 2022)
- Built internal REST APIs in Python FastAPI and PostgreSQL.
- Optimized database queries reducing latency by 40%.

Projects:
Project: Distributed Cache
- Built distributed cache in Go.
"""
        parsed = ResumeParser.parse_resume(resume_text, target_company="Alpha", target_role="Backend Engineer")
        work_exps = parsed["sections"]["work_experience"]

        # Ensure order is preserved: Alpha Systems first, Beta Technologies second
        self.assertGreaterEqual(len(work_exps), 2)
        self.assertIn("Alpha", work_exps[0]["company"])
        self.assertIn("Beta", work_exps[1]["company"])

        # Test agenda building in InterviewAgent
        class MockResume:
            candidate_name = "John Smith"
            sections_json = parsed["sections"]

        agenda = InterviewAgent._build_interview_agenda(
            MockResume(),
            role_profile=None,
            target_role="Backend Engineer",
            target_company="Alpha"
        )

        # Work experience items must appear first before projects
        exp_indices = [i for i, item in enumerate(agenda) if item["item_type"] == "WORK_EXPERIENCE"]
        proj_indices = [i for i, item in enumerate(agenda) if item["item_type"] == "PROJECT"]

        self.assertGreater(len(exp_indices), 0)
        self.assertGreater(len(proj_indices), 0)
        self.assertLess(max(exp_indices), min(proj_indices))

    def test_project_relevance_ordering(self):
        """
        Requirement:
        - Sort projects descending by overall_relevance.
        - Do NOT fabricate descending relevance values merely because extraction is missing.
        """
        resume_sections = {
            "projects": [
                {
                    "title": "Low Relevance Script",
                    "description": "Simple Python script to convert CSV to JSON.",
                    "technologies": ["Python"],
                    "overall_relevance": 0.45
                },
                {
                    "title": "High Relevance Distributed System",
                    "description": "High-throughput Kafka streaming pipeline with zero-data-loss guarantees.",
                    "technologies": ["Kafka", "Go", "PostgreSQL"],
                    "overall_relevance": 0.94
                },
                {
                    "title": "Medium Relevance Web App",
                    "description": "Full stack dashboard with React and Express.",
                    "technologies": ["React", "Node.js"],
                    "overall_relevance": 0.75
                }
            ]
        }

        # Build parsed dict
        parsed = {"sections": resume_sections}
        state = InterviewState(session_id="proj_order_session")
        ResumeParser.populate_interview_state(state, parsed["sections"])

        # Check order in InterviewState.item_order
        proj_items = [state.items[item_id] for item_id in state.item_order if state.items[item_id].item_type == "PROJECT"]
        relevances = [p.relevance_weight for p in proj_items]

        # Verify sorted descending
        self.assertEqual(relevances, sorted(relevances, reverse=True))
        self.assertEqual(proj_items[0].title, "High Relevance Distributed System")
        self.assertEqual(proj_items[1].title, "Medium Relevance Web App")
        self.assertEqual(proj_items[2].title, "Low Relevance Script")

    def test_stable_item_ids(self):
        """
        Requirement:
        - Create stable item IDs.
        - Prevent UUID churn across repeated parses of the same data.
        """
        id1 = generate_stable_id("exp", "Datastream Corp", 0)
        id2 = generate_stable_id("exp", "Datastream Corp", 0)
        self.assertEqual(id1, id2)
        self.assertEqual(id1, "exp_1_datastream_corp")

        proj_id1 = generate_stable_id("proj", "Real-Time Payment Pipeline", 1)
        proj_id2 = generate_stable_id("proj", "Real-Time Payment Pipeline", 1)
        self.assertEqual(proj_id1, proj_id2)
        self.assertEqual(proj_id1, "proj_2_real_time_payment_pipeli")

        # Parsing identical text produces identical IDs
        text = """
Experience:
Senior Engineer at TechStack Inc (2021 - Present)
- Developed APIs.
Projects:
Project: Analytics Hub
- Processed data.
"""
        p1 = ResumeParser.parse_resume(text)
        p2 = ResumeParser.parse_resume(text)

        self.assertEqual(
            p1["sections"]["work_experience"][0]["id"],
            p2["sections"]["work_experience"][0]["id"]
        )
        self.assertEqual(
            p1["sections"]["projects"][0]["project_id"],
            p2["sections"]["projects"][0]["project_id"]
        )

    def test_rich_claim_extraction(self):
        """
        Requirement: Extract components/services, responsibilities, architecture claims,
        metrics, achievements, and technologies into InterviewState.
        """
        sections = {
            "work_experience": [
                {
                    "company": "Nexus Streaming",
                    "role": "Principal Architect",
                    "responsibilities": ["Directed architecture of real-time ingestion layer"],
                    "technologies": ["Go", "Kafka", "Redis"],
                    "components_services": ["Kafka Cluster", "Ingestion Gateway"],
                    "architecture_claims": ["Event-driven pipeline with exactly-once semantics"],
                    "metrics": ["250k events/sec", "sub-15ms latency"],
                    "ownership_claims": ["Owned core infrastructure and SLA"],
                    "achievements": ["Reduced cloud footprint costs by 35%"],
                    "overall_relevance": 0.95
                }
            ]
        }

        ResumeParser.populate_interview_state(self.state, sections)

        statements = [c.statement.lower() for c in self.state.claims.values()]

        # Check that metrics were extracted
        self.assertTrue(any("250k events/sec" in s for s in statements))
        self.assertTrue(any("sub-15ms" in s for s in statements))
        # Check architecture claims
        self.assertTrue(any("exactly-once" in s for s in statements))
        # Check components
        self.assertTrue(any("kafka cluster" in s for s in statements))
        # Check ownership
        self.assertTrue(any("owned core infrastructure" in s for s in statements))
        # Check achievements
        self.assertTrue(any("35%" in s for s in statements))


if __name__ == "__main__":
    unittest.main()
