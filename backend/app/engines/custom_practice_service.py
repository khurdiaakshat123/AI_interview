from __future__ import annotations
import os
import json
import uuid
import random
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.models import CustomPracticeSession, utc_now
from backend.app.engines.mcq_service import MCQQuestionService
from backend.app.engines.lc_service import LCQuestionService

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../backend/data/custom_sessions"))
os.makedirs(DATA_DIR, exist_ok=True)


class CustomPracticeService:
    @classmethod
    def _save_session_file(cls, session_data: Dict[str, Any]) -> None:
        try:
            sid = session_data["id"]
            path = os.path.join(DATA_DIR, f"{sid}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[CustomPracticeService] Failed to cache session file: {e}")

    @classmethod
    def _load_session_file(cls, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            path = os.path.join(DATA_DIR, f"{session_id}.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[CustomPracticeService] Failed to read session file: {e}")
        return None

    @classmethod
    def prepare_session(
        cls,
        payload: Dict[str, Any],
        db: Optional[Session] = None,
        creator_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compiles a custom practice session supporting MCQ, DSA, or Hybrid sections
        with custom topic/difficulty permutations and negative marking.
        """
        MCQQuestionService._ensure_loaded()
        LCQuestionService.initialize()

        session_id = f"ps_{uuid.uuid4().hex[:10]}"
        title = payload.get("title") or "Timed Practice Assessment"
        session_type = payload.get("session_type", "hybrid") # "mcq" | "dsa" | "hybrid"
        duration_minutes = int(payload.get("duration_minutes", 30))
        marking_scheme = payload.get("marking_scheme") or {
            "mcq_correct": 1.0,
            "mcq_negative": -0.25,
            "coding_weight": 10.0
        }

        raw_sections = payload.get("sections", [])
        if not raw_sections:
            # Default fallback section
            if session_type == "mcq":
                raw_sections = [{
                    "id": "sec_1",
                    "name": "General MCQ Practice",
                    "section_type": "mcq",
                    "topic": "all",
                    "difficulty": "all",
                    "count": 10
                }]
            elif session_type == "dsa":
                raw_sections = [{
                    "id": "sec_1",
                    "name": "DSA Problem Solving",
                    "section_type": "dsa",
                    "topic": "all",
                    "difficulty": "Medium",
                    "count": 2
                }]
            else:
                raw_sections = [
                    {
                        "id": "sec_1",
                        "name": "Core Technical MCQs",
                        "section_type": "mcq",
                        "topic": "all",
                        "difficulty": "all",
                        "count": 5
                    },
                    {
                        "id": "sec_2",
                        "name": "Algorithms & Coding",
                        "section_type": "dsa",
                        "topic": "all",
                        "difficulty": "Medium",
                        "count": 2
                    }
                ]

        compiled_questions: List[Dict[str, Any]] = []
        solutions_store: Dict[str, Any] = {}
        processed_sections: List[Dict[str, Any]] = []

        seen_mcq_ids = set()
        seen_dsa_ids = set()

        for s_idx, sec in enumerate(raw_sections):
            sec_id = sec.get("id") or f"sec_{s_idx + 1}"
            sec_type = sec.get("section_type", "mcq").lower()
            sec_name = sec.get("name") or (f"Section {s_idx + 1}: {sec_type.upper()}")
            topic = (sec.get("topic") or "all").lower().strip()
            diff = (sec.get("difficulty") or "all").strip()
            count = max(1, int(sec.get("count", 5)))
            specific_ids = sec.get("specific_question_ids") or []

            sec_questions_count = 0

            # ---------------------------
            # Process MCQ Section
            # ---------------------------
            if sec_type == "mcq":
                candidates = []
                if specific_ids:
                    for qid in specific_ids:
                        qid_str = str(qid).strip()
                        q = MCQQuestionService._questions_by_id.get(qid_str)
                        if q and q["id"] not in seen_mcq_ids:
                            candidates.append(q)
                            seen_mcq_ids.add(q["id"])
                else:
                    pool = list(MCQQuestionService._questions_list)
                    if topic != "all":
                        pool = [q for q in pool if q.get("broad_topic_id", "").lower() == topic or q.get("broad_topic_name", "").lower() == topic]
                    if diff != "all":
                        pool = [q for q in pool if q.get("difficulty", "").lower() == diff.lower()]

                    # Avoid duplicate questions across sections
                    available = [q for q in pool if q["id"] not in seen_mcq_ids]
                    random.shuffle(available)
                    candidates = available[:count]
                    for q in candidates:
                        seen_mcq_ids.add(q["id"])

                for q in candidates:
                    q_obj = {
                        "id": q["id"],
                        "type": "mcq",
                        "section_id": sec_id,
                        "section_name": sec_name,
                        "broad_topic_id": q.get("broad_topic_id"),
                        "broad_topic_name": q.get("broad_topic_name"),
                        "subpart_name": q.get("subpart_name"),
                        "difficulty": q.get("difficulty", "Medium"),
                        "question": q["question"],
                        "options": q["options"],
                        "has_code": q.get("has_code", False),
                        "code_snippet": q.get("code_snippet"),
                        "marking": {
                            "correct": float(marking_scheme.get("mcq_correct", 1.0)),
                            "negative": float(marking_scheme.get("mcq_negative", -0.25))
                        }
                    }
                    compiled_questions.append(q_obj)
                    actual_correct = q.get("correct_answer") or q.get("correct_option")
                    solutions_store[q["id"]] = {
                        "correct_answer": actual_correct,
                        "correct_option": actual_correct,
                        "explanation": q.get("explanation", "No detailed explanation provided.")
                    }
                    sec_questions_count += 1

            # ---------------------------
            # Process DSA Section
            # ---------------------------
            elif sec_type == "dsa":
                candidates = []
                if specific_ids:
                    for qid in specific_ids:
                        qid_str = str(qid).strip()
                        # Match by ID or by question number or by slug
                        found = None
                        if qid_str in LCQuestionService._by_id:
                            found = LCQuestionService._by_id[qid_str]
                        elif qid_str in LCQuestionService._by_slug:
                            found = LCQuestionService._by_slug[qid_str]
                        else:
                            for item in LCQuestionService._questions_list:
                                if str(item.get("num")) == qid_str:
                                    found = item
                                    break
                        if found and found["id"] not in seen_dsa_ids:
                            candidates.append(found)
                            seen_dsa_ids.add(found["id"])
                else:
                    pool = list(LCQuestionService._questions_list)
                    if topic != "all":
                        pool = [q for q in pool if q.get("subcategory", "").lower() == topic or q.get("category", "").lower() == topic]
                    if diff != "all":
                        pool = [q for q in pool if q.get("difficulty", "").lower() == diff.lower()]

                    available = [q for q in pool if q["id"] not in seen_dsa_ids]
                    random.shuffle(available)
                    candidates = available[:count]
                    for q in candidates:
                        seen_dsa_ids.add(q["id"])

                for q_meta in candidates:
                    # Load full detail including starter code, description, and test cases
                    full_detail = LCQuestionService.get_question(q_meta["id"], db=db) or {}
                    q_obj = {
                        "id": q_meta["id"],
                        "num": q_meta.get("num"),
                        "slug": q_meta.get("slug"),
                        "type": "dsa",
                        "section_id": sec_id,
                        "section_name": sec_name,
                        "title": q_meta.get("title"),
                        "category": q_meta.get("category", "dsa"),
                        "subcategory": q_meta.get("subcategory"),
                        "difficulty": q_meta.get("difficulty", "Medium"),
                        "timeComplexity": q_meta.get("timeComplexity"),
                        "spaceComplexity": q_meta.get("spaceComplexity"),
                        "contentHtml": full_detail.get("contentHtml", ""),
                        "contentMarkdown": full_detail.get("contentMarkdown", ""),
                        "starterCode": full_detail.get("starterCode", {}),
                        "sampleTestCases": full_detail.get("sampleTestCases", []),
                        "sqlSchema": full_detail.get("sqlSchema"),
                        "sqlSetup": full_detail.get("sqlSetup"),
                        "marking": {
                            "weight": float(marking_scheme.get("coding_weight", 10.0))
                        }
                    }
                    compiled_questions.append(q_obj)
                    solutions_store[q_meta["id"]] = {
                        "testCases": full_detail.get("testCases", []),
                        "officialSolution": full_detail.get("officialSolution")
                    }
                    sec_questions_count += 1

            processed_sections.append({
                "id": sec_id,
                "name": sec_name,
                "section_type": sec_type,
                "topic": topic,
                "difficulty": diff,
                "count": sec_questions_count
            })

        session_record = {
            "id": session_id,
            "creator_user_id": creator_user_id,
            "title": title,
            "session_type": session_type,
            "duration_minutes": duration_minutes,
            "marking_scheme": marking_scheme,
            "sections": processed_sections,
            "total_questions": len(compiled_questions),
            "questions": compiled_questions,
            "solutions": solutions_store,
            "created_at": utc_now().isoformat()
        }

        # Cache to local file
        cls._save_session_file(session_record)

        # Also store to database if session is present
        if db:
            try:
                db_item = CustomPracticeSession(
                    id=session_id,
                    creator_user_id=creator_user_id,
                    title=title,
                    session_type=session_type,
                    duration_minutes=duration_minutes,
                    marking_scheme_json=marking_scheme,
                    sections_json=processed_sections,
                    questions_json=compiled_questions,
                    solutions_json=solutions_store,
                    created_at=utc_now()
                )
                db.add(db_item)
                db.commit()
            except Exception as dbe:
                print(f"[CustomPracticeService] DB save note: {dbe}")
                try: db.rollback()
                except: pass

        # Return candidate-safe preview without solutions
        safe_response = dict(session_record)
        del safe_response["solutions"]
        safe_response["session_id"] = session_id
        safe_response["share_url"] = f"/practice/timed-session/{session_id}"
        return safe_response

    @classmethod
    def get_session(cls, session_id: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves a session for an examinee without exposing ground-truth answers.
        """
        data = cls._load_session_file(session_id)
        if not data and db:
            try:
                db_item = db.query(CustomPracticeSession).filter(CustomPracticeSession.id == session_id).first()
                if db_item:
                    data = {
                        "id": db_item.id,
                        "creator_user_id": db_item.creator_user_id,
                        "title": db_item.title,
                        "session_type": db_item.session_type,
                        "duration_minutes": db_item.duration_minutes,
                        "marking_scheme": db_item.marking_scheme_json,
                        "sections": db_item.sections_json,
                        "total_questions": len(db_item.questions_json or []),
                        "questions": db_item.questions_json,
                        "solutions": db_item.solutions_json,
                        "created_at": db_item.created_at.isoformat() if db_item.created_at else None
                    }
                    cls._save_session_file(data)
            except Exception as e:
                print(f"[CustomPracticeService] DB lookup error: {e}")

        if not data:
            return None

        safe = dict(data)
        if "solutions" in safe:
            del safe["solutions"]
        safe["share_url"] = f"/practice/timed-session/{session_id}"
        return safe

    @classmethod
    def submit_session(
        cls,
        session_id: str,
        submission_payload: Dict[str, Any],
        db: Optional[Session] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Grades an examinee's submitted practice session:
        - Exact MCQ scoring with positive (+1.0) and negative (-0.25) marking.
        - Coding testcase completion evaluation.
        - Comprehensive section-wise breakdown and unlocks full explanations.
        """
        full_data = cls._load_session_file(session_id)
        if not full_data and db:
            try:
                db_item = db.query(CustomPracticeSession).filter(CustomPracticeSession.id == session_id).first()
                if db_item:
                    full_data = {
                        "id": db_item.id,
                        "title": db_item.title,
                        "session_type": db_item.session_type,
                        "duration_minutes": db_item.duration_minutes,
                        "marking_scheme": db_item.marking_scheme_json,
                        "sections": db_item.sections_json,
                        "questions": db_item.questions_json,
                        "solutions": db_item.solutions_json,
                    }
            except Exception as e:
                print(f"[CustomPracticeService] DB lookup error: {e}")

        if not full_data:
            raise ValueError(f"Session with ID '{session_id}' not found.")

        marking_scheme = full_data.get("marking_scheme") or {}
        mcq_correct_val = float(marking_scheme.get("mcq_correct", 1.0))
        mcq_negative_val = float(marking_scheme.get("mcq_negative", -0.25)) # negative deduction, e.g. -0.25
        coding_weight_val = float(marking_scheme.get("coding_weight", 10.0))

        mcq_answers = submission_payload.get("mcq_answers", {}) # {qid: "A"|"B"|"C"|"D"|null}
        coding_submissions = submission_payload.get("coding_submissions", {}) # {qid: {code, language, passed, total, status}}
        time_spent_seconds = int(submission_payload.get("time_spent_seconds", 0))

        solutions = full_data.get("solutions", {})
        questions = full_data.get("questions", [])

        # Review report per question
        question_results: List[Dict[str, Any]] = []

        total_mcq_correct = 0
        total_mcq_incorrect = 0
        total_mcq_unanswered = 0
        total_mcq_score = 0.0
        max_mcq_score = 0.0

        total_coding_solved = 0
        total_coding_attempted = 0
        total_coding_score = 0.0
        max_coding_score = 0.0

        section_stats: Dict[str, Dict[str, Any]] = {}
        for sec in full_data.get("sections", []):
            section_stats[sec["id"]] = {
                "name": sec["name"],
                "section_type": sec["section_type"],
                "total": 0,
                "attempted": 0,
                "correct": 0,
                "incorrect": 0,
                "score": 0.0,
                "max_score": 0.0
            }

        for q in questions:
            qid = q["id"]
            q_type = q.get("type", "mcq")
            sec_id = q.get("section_id", "sec_1")
            sec_stat = section_stats.setdefault(sec_id, {
                "name": q.get("section_name", "Section"),
                "section_type": q_type,
                "total": 0,
                "attempted": 0,
                "correct": 0,
                "incorrect": 0,
                "score": 0.0,
                "max_score": 0.0
            })
            sec_stat["total"] += 1

            if q_type == "mcq":
                max_mcq_score += mcq_correct_val
                sec_stat["max_score"] += mcq_correct_val

                sol = solutions.get(qid, {})
                correct_opt = sol.get("correct_answer") or sol.get("correct_option")
                user_opt = mcq_answers.get(qid)
                explanation = sol.get("explanation", "")

                is_attempted = bool(user_opt and user_opt.strip())
                is_correct = False
                points = 0.0

                if is_attempted:
                    sec_stat["attempted"] += 1
                    if correct_opt and user_opt.strip().upper() == str(correct_opt).strip().upper():
                        is_correct = True
                        points = mcq_correct_val
                        total_mcq_correct += 1
                        sec_stat["correct"] += 1
                    else:
                        points = mcq_negative_val # e.g. -0.25
                        total_mcq_incorrect += 1
                        sec_stat["incorrect"] += 1
                else:
                    total_mcq_unanswered += 1

                total_mcq_score += points
                sec_stat["score"] += points

                question_results.append({
                    "id": qid,
                    "type": "mcq",
                    "section_id": sec_id,
                    "section_name": q.get("section_name"),
                    "question": q.get("question"),
                    "options": q.get("options", {}),
                    "code_snippet": q.get("code_snippet"),
                    "user_answer": user_opt,
                    "correct_answer": correct_opt,
                    "is_attempted": is_attempted,
                    "is_correct": is_correct,
                    "points_awarded": points,
                    "max_points": mcq_correct_val,
                    "explanation": explanation
                })

            elif q_type == "dsa":
                max_coding_score += coding_weight_val
                sec_stat["max_score"] += coding_weight_val

                sub = coding_submissions.get(qid, {})
                code = sub.get("code", "")
                lang = sub.get("language", "cpp")
                status = sub.get("status", "unattempted")
                passed = int(sub.get("passed_tests", 0))
                total_tests = max(1, int(sub.get("total_tests", 1)))

                is_attempted = bool(code and len(code.strip()) > 15)
                points = 0.0

                if is_attempted:
                    sec_stat["attempted"] += 1
                    total_coding_attempted += 1
                    if status.lower() == "accepted" or passed == total_tests:
                        points = coding_weight_val
                        total_coding_solved += 1
                        sec_stat["correct"] += 1
                    else:
                        # Partial credit based on passed test cases
                        points = round(coding_weight_val * (passed / total_tests), 2)
                        sec_stat["incorrect"] += 1

                total_coding_score += points
                sec_stat["score"] += points

                sol = solutions.get(qid, {})
                question_results.append({
                    "id": qid,
                    "type": "dsa",
                    "num": q.get("num"),
                    "title": q.get("title"),
                    "difficulty": q.get("difficulty"),
                    "section_id": sec_id,
                    "section_name": q.get("section_name"),
                    "user_code": code,
                    "language": lang,
                    "status": status,
                    "passed_tests": passed,
                    "total_tests": total_tests,
                    "is_attempted": is_attempted,
                    "points_awarded": points,
                    "max_points": coding_weight_val,
                    "official_solution": sol.get("officialSolution")
                })

        total_earned = round(total_mcq_score + total_coding_score, 2)
        total_possible = round(max_mcq_score + max_coding_score, 2)
        percentage = round((total_earned / total_possible * 100), 1) if total_possible > 0 else 0.0

        for s in section_stats.values():
            s["score"] = round(s["score"], 2)
            s["max_score"] = round(s["max_score"], 2)
            s["percentage"] = round((s["score"] / s["max_score"] * 100), 1) if s["max_score"] > 0 else 0.0

        result = {
            "session_id": session_id,
            "title": full_data.get("title"),
            "session_type": full_data.get("session_type"),
            "total_score": total_earned,
            "max_possible_score": total_possible,
            "percentage": percentage,
            "time_spent_seconds": time_spent_seconds,
            "duration_minutes": full_data.get("duration_minutes", 30),
            "mcq_summary": {
                "correct": total_mcq_correct,
                "incorrect": total_mcq_incorrect,
                "unanswered": total_mcq_unanswered,
                "score": round(total_mcq_score, 2),
                "max_score": round(max_mcq_score, 2),
                "negative_marking_penalty": round(total_mcq_incorrect * abs(mcq_negative_val), 2)
            },
            "coding_summary": {
                "solved": total_coding_solved,
                "attempted": total_coding_attempted,
                "total": len([q for q in questions if q.get("type") == "dsa"]),
                "score": round(total_coding_score, 2),
                "max_score": round(max_coding_score, 2)
            },
            "section_stats": list(section_stats.values()),
            "questions": question_results
        }

        return result

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """
        Returns all available topics, subtopics, and question lists for rich UI builders.
        """
        MCQQuestionService._ensure_loaded()
        LCQuestionService.initialize()

        mcq_topics = [
            {"id": t["id"], "name": t["name"], "count": t["total_questions"]}
            for t in MCQQuestionService._broad_topics
        ]

        # Extract distinct DSA subcategories
        dsa_subcats = set()
        for q in LCQuestionService._questions_list:
            if q.get("subcategory"):
                dsa_subcats.add(q["subcategory"])

        dsa_topics = [{"id": sub, "name": sub.replace("-", " ").title()} for sub in sorted(dsa_subcats)]

        sample_dsa = [
            {"id": q["id"], "num": q.get("num"), "title": q.get("title"), "difficulty": q.get("difficulty"), "subcategory": q.get("subcategory")}
            for q in LCQuestionService._questions_list[:100]
        ]

        sample_mcq = [
            {"id": q["id"], "topic": q.get("broad_topic_name"), "difficulty": q.get("difficulty"), "question": q["question"][:80] + "..."}
            for q in MCQQuestionService._questions_list[:100]
        ]

        return {
            "mcq_topics": mcq_topics,
            "dsa_topics": dsa_topics,
            "difficulties": ["Easy", "Medium", "Hard"],
            "sample_dsa": sample_dsa,
            "sample_mcq": sample_mcq
        }
