import unittest
from unittest.mock import MagicMock
from backend.app.engines.resume_parser import ResumeParser
from backend.app.agents.interview_agent import InterviewAgent

AKSHAT_RESUME = """
AKSHAT KHURDIA
Software Engineer | Backend & Full-Stack Development
Hyderabad, India  |  +91 77423 27831  |  akshatkhurdia@gmail.com

SUMMARY
Computer Science undergraduate (CGPA 8.93/10, BITS Pilani) building backend services, REST APIs, and full-stack systems end-to-end.

EDUCATION
B.E. Computer Science Engineering (2028)
BITS Pilani, Hyderabad Campus
CGPA 8.93
Ongoing

TECHNICAL SKILLS
Languages: Python, C++, C, Java, SQL
Backend & Systems: FastAPI, REST APIs, PostgreSQL, Docker, Git/GitHub, System Design, Distributed Data Pipelines
Frontend: React, Tailwind CSS

EXPERIENCE
Software Engineering Intern  —  KVGAI
May 2026 – Jul 2026
●
Architected a Python web scraping pipeline (requests, BeautifulSoup) that reliably extracted and verified data for 1,300+ civic officials from official government portals.
●
Implemented AI-agent integrations with LLM APIs using a heuristic ≥30-point confidence threshold to autonomously scan portals.

Crisis & Emergency Response Management System  —  DBMS Project
Jan 2026 – Mar 2026
●
Engineered a relational database in PostgreSQL with 11 interconnected entities to manage real-time disaster metrics.

Quantum Networks and Topology  —  Computer & Quantum Networks Research
Jan 2026 – Present
●
Designing an optimized routing algorithm to compute minimum-cost paths across quantum network topologies.

Domain-Specific RAG Chatbot  —  NLP Project
May 2026 – Jun 2026
●
Constructed a retrieval-augmented QA system for Quantum Networks literature (LangChain, Streamlit, Pinecone VectorDB) across 11+ research papers.

CERTIFICATIONS & AWARDS
● Supervised Machine Learning — Coursera
"""

class TestResumeParserRobustness(unittest.TestCase):
    def test_fallback_extract_work_experience_with_em_dash_and_nextline_date(self):
        work_exps = ResumeParser._extract_work_experience(AKSHAT_RESUME, target_role="Software Engineer")
        self.assertGreaterEqual(len(work_exps), 1)
        kvgai_entry = next((e for e in work_exps if "kvgai" in e["company"].lower()), None)
        self.assertIsNotNone(kvgai_entry, "KVGAI work experience should be detected")
        self.assertIn("Intern", kvgai_entry["role"])
        self.assertIn("2026", kvgai_entry["duration"])

    def test_fallback_extract_projects_under_experience_header(self):
        projects = ResumeParser._extract_projects(AKSHAT_RESUME, target_role="Software Engineer")
        self.assertGreaterEqual(len(projects), 3)
        titles = [p["title"].lower() for p in projects]
        self.assertTrue(any("crisis" in t or "emergency" in t for t in titles))
        self.assertTrue(any("quantum" in t for t in titles))
        self.assertTrue(any("rag" in t or "chatbot" in t for t in titles))

    def test_interview_agenda_places_work_experience_first(self):
        work_exps = ResumeParser._extract_work_experience(AKSHAT_RESUME, target_role="Software Engineer")
        projects = ResumeParser._extract_projects(AKSHAT_RESUME, target_role="Software Engineer")
        
        mock_resume = MagicMock()
        mock_resume.sections_json = {
            "work_experience": work_exps,
            "projects": projects
        }
        mock_resume.candidate_name = "AKSHAT KHURDIA"

        agenda = InterviewAgent._build_interview_agenda(mock_resume, None, "Software Engineer", "Teradata")
        self.assertGreater(len(agenda), 0)
        
        # Invariant: Item 0 is ALWAYS work experience when present
        item0 = agenda[0]
        self.assertEqual(item0["phase"], "EXPERIENCE_DEFENSE")
        self.assertEqual(item0["item_type"], "WORK_EXPERIENCE")
        self.assertIn("KVGAI", item0["title"])

        # All work experiences come before projects
        first_proj_idx = next((i for i, it in enumerate(agenda) if it["item_type"] == "PROJECT"), None)
        last_exp_idx = max(i for i, it in enumerate(agenda) if it["item_type"] == "WORK_EXPERIENCE")
        if first_proj_idx is not None:
            self.assertLess(last_exp_idx, first_proj_idx)

    def test_safety_guard_when_resume_empty(self):
        mock_resume = MagicMock()
        mock_resume.sections_json = {
            "work_experience": [],
            "projects": []
        }
        agenda = InterviewAgent._build_interview_agenda(mock_resume, None, "Software Engineer", "Teradata")
        self.assertGreater(len(agenda), 0)
        # Safety guard must ensure item 0 is EXPERIENCE_DEFENSE
        self.assertEqual(agenda[0]["phase"], "EXPERIENCE_DEFENSE")
        self.assertEqual(agenda[0]["item_type"], "WORK_EXPERIENCE")

if __name__ == "__main__":
    unittest.main()
