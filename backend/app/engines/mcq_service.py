import os
import json
import random
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.models import MCQUserProgress, utc_now
from backend.app.engines.mcq_topics import get_broad_topics, get_subpart_to_topic_lookup, get_subparts_for_broad_topic

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../mcq_qbank"))
MANIFEST_PATH = os.path.join(BASE_DIR, "manifests", "mcq-index.json")

class MCQQuestionService:
    _index_cache: Optional[Dict[str, Any]] = None
    _questions_list: List[Dict[str, Any]] = []
    _questions_by_id: Dict[str, Dict[str, Any]] = {}
    _broad_topics: List[Dict[str, Any]] = []

    @classmethod
    def _ensure_loaded(cls):
        if cls._index_cache is not None:
            return

        if not os.path.exists(MANIFEST_PATH):
            raise FileNotFoundError(f"MCQ Index Manifest not found at {MANIFEST_PATH}")

        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            cls._index_cache = json.load(f)

        cls._questions_list = cls._index_cache.get("questions", [])
        cls._questions_by_id = {q["id"]: q for q in cls._questions_list}
        cls._broad_topics = cls._index_cache.get("broad_topics", [])

    @classmethod
    def get_topics(cls, db: Optional[Session] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns the 9 broad topics with aggregated question counts,
        difficulty counts, and candidate progress.
        """
        cls._ensure_loaded()
        topics = [dict(t) for t in cls._broad_topics]

        # If user is authenticated, query their progress across broad topics
        user_progress_by_topic: Dict[str, Dict[str, int]] = {
            t["id"]: {"solved": 0, "attempted": 0, "starred": 0} for t in topics
        }

        if db and user_id:
            subpart_lookup = get_subpart_to_topic_lookup()
            records = db.query(MCQUserProgress).filter(MCQUserProgress.user_id == user_id).all()
            for r in records:
                q = cls._questions_by_id.get(r.question_id)
                if not q:
                    continue
                topic_id = q.get("broad_topic_id")
                if topic_id in user_progress_by_topic:
                    if r.status == "solved" or r.is_correct:
                        user_progress_by_topic[topic_id]["solved"] += 1
                    elif r.status == "attempted":
                        user_progress_by_topic[topic_id]["attempted"] += 1
                    if r.is_starred:
                        user_progress_by_topic[topic_id]["starred"] += 1

        for t in topics:
            tid = t["id"]
            u_stat = user_progress_by_topic.get(tid, {"solved": 0, "attempted": 0, "starred": 0})
            t["solved_count"] = u_stat["solved"]
            t["attempted_count"] = u_stat["attempted"]
            t["starred_count"] = u_stat["starred"]
            t["progress_pct"] = round((u_stat["solved"] / t["total_questions"] * 100), 1) if t["total_questions"] > 0 else 0.0

        return topics

    @classmethod
    def list_questions(
        cls,
        db: Optional[Session] = None,
        user_id: Optional[str] = None,
        topic: str = "all",
        topics: Optional[str] = None,
        difficulty: str = "all",
        status: str = "all",
        search: Optional[str] = None,
        has_code: Optional[bool] = None,
        starred_only: bool = False,
        page: int = 1,
        limit: int = 50,
        sort_by: str = "id",
        order: str = "asc"
    ) -> Dict[str, Any]:
        """
        Lists questions with full support for broad-topic selection, multi-topic filter,
        difficulty, status, search, and bookmarks.
        """
        cls._ensure_loaded()

        # Load user progress lookup if logged in
        user_records: Dict[str, MCQUserProgress] = {}
        if db and user_id:
            rows = db.query(MCQUserProgress).filter(MCQUserProgress.user_id == user_id).all()
            user_records = {r.question_id: r for r in rows}

        # Determine target broad topics
        selected_topics: Optional[set] = None
        if topics and topics.strip():
            selected_topics = {t.strip() for t in topics.split(",") if t.strip() and t.strip() != "all"}
        elif topic and topic != "all":
            selected_topics = {topic}

        filtered = []
        for q in cls._questions_list:
            # 1. Topic filter (broad topic match)
            if selected_topics and q["broad_topic_id"] not in selected_topics:
                continue

            # 2. Difficulty filter
            if difficulty != "all" and q["difficulty"].lower() != difficulty.lower():
                continue

            # 3. Code presence filter
            if has_code is not None and q["has_code"] != has_code:
                continue

            # 4. User progress filter (status / starred)
            prog = user_records.get(q["id"])
            q_status = "todo"
            is_starred = False
            user_answer = None
            is_correct = False
            if prog:
                q_status = prog.status
                is_starred = prog.is_starred
                user_answer = prog.selected_option
                is_correct = prog.is_correct

            if starred_only and not is_starred:
                continue

            if status != "all":
                if status == "solved" and q_status != "solved":
                    continue
                if status == "attempted" and q_status != "attempted":
                    continue
                if status == "todo" and q_status != "todo":
                    continue

            # 5. Search query
            if search and search.strip():
                query = search.strip().lower()
                id_match = query in q["id"].lower()
                q_match = query in q["question"].lower()
                code_match = query in (q["code_snippet"] or "").lower()
                subpart_match = query in q.get("subpart_name", "").lower()
                topic_match = query in q.get("broad_topic_name", "").lower()
                options_match = any(query in opt.lower() for opt in q["options"].values())

                if not (id_match or q_match or code_match or subpart_match or topic_match or options_match):
                    continue

            # Append summary item with candidate status
            filtered.append({
                "id": q["id"],
                "broad_topic_id": q["broad_topic_id"],
                "broad_topic_name": q["broad_topic_name"],
                "subpart_id": q["subpart_id"],
                "subpart_name": q["subpart_name"],
                "difficulty": q["difficulty"],
                "question": q["question"],
                "has_code": q["has_code"],
                "code_snippet": q["code_snippet"],
                "options": q["options"],
                "status": q_status,
                "is_starred": is_starred,
                "user_answer": user_answer,
                "is_correct": is_correct
            })

        total = len(filtered)

        # Sorting
        if sort_by == "random":
            random.seed(42)
            random.shuffle(filtered)
        elif sort_by == "difficulty":
            diff_weights = {"easy": 1, "medium": 2, "hard": 3}
            filtered.sort(key=lambda x: diff_weights.get(x["difficulty"].lower(), 2), reverse=(order == "desc"))
        else:
            # Default sort by id
            filtered.sort(key=lambda x: x["id"], reverse=(order == "desc"))

        # Pagination
        start = (page - 1) * limit
        end = start + limit
        paginated = filtered[start:end]

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit),
            "questions": paginated
        }

    @classmethod
    def get_question(cls, question_id: str, db: Optional[Session] = None, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves full question details with explanation, options, and candidate state.
        """
        cls._ensure_loaded()
        q = cls._questions_by_id.get(question_id)
        if not q:
            return None

        result = dict(q)

        # Attach candidate state if logged in
        result["status"] = "todo"
        result["is_starred"] = False
        result["user_answer"] = None
        result["is_correct"] = False
        result["notes"] = ""
        result["attempts_count"] = 0

        if db and user_id:
            prog = db.query(MCQUserProgress).filter(
                MCQUserProgress.user_id == user_id,
                MCQUserProgress.question_id == question_id
            ).first()
            if prog:
                result["status"] = prog.status
                result["is_starred"] = prog.is_starred
                result["user_answer"] = prog.selected_option
                result["is_correct"] = prog.is_correct
                result["notes"] = prog.notes or ""
                result["attempts_count"] = prog.attempts_count

        return result

    @classmethod
    def submit_answer(cls, question_id: str, selected_option: str, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Validates the candidate's answer and persists progress in the database.
        """
        cls._ensure_loaded()
        q = cls._questions_by_id.get(question_id)
        if not q:
            raise ValueError(f"Question with ID {question_id} not found.")

        selected_option = selected_option.strip().upper()
        if selected_option not in ("A", "B", "C", "D"):
            raise ValueError(f"Invalid option '{selected_option}'. Must be one of A, B, C, D.")

        correct_answer = q["correct_answer"].strip().upper()
        is_correct = (selected_option == correct_answer)

        # Update or create progress in DB
        prog = db.query(MCQUserProgress).filter(
            MCQUserProgress.user_id == user_id,
            MCQUserProgress.question_id == question_id
        ).first()

        new_status = "solved" if is_correct else "attempted"

        if not prog:
            prog = MCQUserProgress(
                user_id=user_id,
                question_id=question_id,
                selected_option=selected_option,
                is_correct=is_correct,
                status=new_status,
                attempts_count=1,
                updated_at=utc_now()
            )
            db.add(prog)
        else:
            prog.selected_option = selected_option
            prog.is_correct = is_correct
            # If already solved, stay solved; otherwise update to solved or attempted
            if prog.status != "solved" or is_correct:
                prog.status = new_status
            prog.attempts_count = (prog.attempts_count or 0) + 1
            prog.updated_at = utc_now()

        db.commit()

        return {
            "question_id": question_id,
            "selected_option": selected_option,
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": q.get("explanation", ""),
            "status": prog.status,
            "attempts_count": prog.attempts_count
        }

    @classmethod
    def toggle_star(cls, question_id: str, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Toggles star / bookmark status for a question.
        """
        cls._ensure_loaded()
        if question_id not in cls._questions_by_id:
            raise ValueError(f"Question with ID {question_id} not found.")

        prog = db.query(MCQUserProgress).filter(
            MCQUserProgress.user_id == user_id,
            MCQUserProgress.question_id == question_id
        ).first()

        if not prog:
            prog = MCQUserProgress(
                user_id=user_id,
                question_id=question_id,
                is_starred=True,
                status="todo",
                updated_at=utc_now()
            )
            db.add(prog)
            is_starred = True
        else:
            prog.is_starred = not prog.is_starred
            prog.updated_at = utc_now()
            is_starred = prog.is_starred

        db.commit()
        return {
            "question_id": question_id,
            "is_starred": is_starred
        }

    @classmethod
    def save_notes(cls, question_id: str, notes: str, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Saves candidate notes for a question.
        """
        cls._ensure_loaded()
        if question_id not in cls._questions_by_id:
            raise ValueError(f"Question with ID {question_id} not found.")

        prog = db.query(MCQUserProgress).filter(
            MCQUserProgress.user_id == user_id,
            MCQUserProgress.question_id == question_id
        ).first()

        if not prog:
            prog = MCQUserProgress(
                user_id=user_id,
                question_id=question_id,
                notes=notes,
                status="todo",
                updated_at=utc_now()
            )
            db.add(prog)
        else:
            prog.notes = notes
            prog.updated_at = utc_now()

        db.commit()
        return {
            "question_id": question_id,
            "notes": notes
        }

    @classmethod
    def generate_quiz(
        cls,
        topics: Optional[List[str]] = None,
        difficulties: Optional[List[str]] = None,
        count: int = 10,
        mode: str = "random",
        db: Optional[Session] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a custom quiz session from selected broad topics, difficulty mix, and count.
        """
        cls._ensure_loaded()
        candidate_pool = []

        target_topics = set(topics) if topics else None
        target_diffs = {d.lower() for d in difficulties} if difficulties else None

        for q in cls._questions_list:
            if target_topics and q["broad_topic_id"] not in target_topics and "all" not in target_topics:
                continue
            if target_diffs and q["difficulty"].lower() not in target_diffs:
                continue
            candidate_pool.append(q)

        if not candidate_pool:
            candidate_pool = list(cls._questions_list)

        sample_size = min(count, len(candidate_pool))
        selected = random.sample(candidate_pool, sample_size)

        quiz_questions = []
        for q in selected:
            quiz_questions.append({
                "id": q["id"],
                "broad_topic_id": q["broad_topic_id"],
                "broad_topic_name": q["broad_topic_name"],
                "subpart_id": q["subpart_id"],
                "subpart_name": q["subpart_name"],
                "difficulty": q["difficulty"],
                "question": q["question"],
                "has_code": q["has_code"],
                "code_snippet": q["code_snippet"],
                "options": q["options"]
            })

        return {
            "quiz_id": f"quiz_{random.randint(100000, 999999)}",
            "mode": mode,
            "total_questions": len(quiz_questions),
            "questions": quiz_questions
        }

    @classmethod
    def get_analytics(cls, db: Optional[Session] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Computes overall accuracy, topic breakdown, and difficulty mastery.
        """
        cls._ensure_loaded()
        total_q = len(cls._questions_list)

        solved_count = 0
        attempted_count = 0
        correct_count = 0
        topic_stats = {
            t["id"]: {
                "id": t["id"],
                "name": t["name"],
                "short_name": t["short_name"],
                "icon": t["icon"],
                "color": t["color"],
                "total": t["total_questions"],
                "solved": 0,
                "attempted": 0
            }
            for t in cls._broad_topics
        }
        diff_stats = {
            "Easy": {"total": 0, "solved": 0},
            "Medium": {"total": 0, "solved": 0},
            "Hard": {"total": 0, "solved": 0}
        }

        for q in cls._questions_list:
            d = q.get("difficulty", "Medium")
            if d in diff_stats:
                diff_stats[d]["total"] += 1

        if db and user_id:
            rows = db.query(MCQUserProgress).filter(MCQUserProgress.user_id == user_id).all()
            for r in rows:
                q = cls._questions_by_id.get(r.question_id)
                if not q:
                    continue
                tid = q["broad_topic_id"]
                diff = q.get("difficulty", "Medium")

                if r.status == "solved" or r.is_correct:
                    solved_count += 1
                    correct_count += 1
                    if tid in topic_stats:
                        topic_stats[tid]["solved"] += 1
                    if diff in diff_stats:
                        diff_stats[diff]["solved"] += 1
                elif r.status == "attempted":
                    attempted_count += 1
                    if tid in topic_stats:
                        topic_stats[tid]["attempted"] += 1

        accuracy = round((correct_count / (solved_count + attempted_count) * 100), 1) if (solved_count + attempted_count) > 0 else 0.0

        return {
            "total_questions": total_q,
            "solved_count": solved_count,
            "attempted_count": attempted_count,
            "todo_count": max(0, total_q - solved_count - attempted_count),
            "accuracy": accuracy,
            "broad_topics": list(topic_stats.values()),
            "difficulty_breakdown": diff_stats
        }

    @classmethod
    def submit_quiz(
        cls,
        answers: Dict[str, Optional[str]],
        question_ids: List[str],
        time_spent_seconds: int = 0,
        db: Optional[Session] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a completed quiz session, computes full scores,
        persists progress, and returns detailed question-by-question review with explanations.
        """
        cls._ensure_loaded()
        total_q = len(question_ids)
        correct_count = 0
        incorrect_count = 0
        skipped_count = 0

        detailed_results = []
        topic_stats: Dict[str, Dict[str, int]] = {}
        diff_stats: Dict[str, Dict[str, int]] = {
            "Easy": {"total": 0, "correct": 0},
            "Medium": {"total": 0, "correct": 0},
            "Hard": {"total": 0, "correct": 0}
        }

        # Query existing user progress records if authenticated
        existing_records = {}
        if db and user_id:
            rows = db.query(MCQUserProgress).filter(
                MCQUserProgress.user_id == user_id,
                MCQUserProgress.question_id.in_(question_ids)
            ).all()
            existing_records = {r.question_id: r for r in rows}

        for qid in question_ids:
            q = cls._questions_by_id.get(qid)
            if not q:
                continue

            user_ans = answers.get(qid)
            if user_ans:
                user_ans = user_ans.strip().upper()
                if user_ans not in ("A", "B", "C", "D"):
                    user_ans = None

            correct_ans = q["correct_answer"].strip().upper()
            t_name = q.get("broad_topic_name", "General")
            diff = q.get("difficulty", "Medium")

            if t_name not in topic_stats:
                topic_stats[t_name] = {"total": 0, "correct": 0}
            topic_stats[t_name]["total"] += 1
            if diff in diff_stats:
                diff_stats[diff]["total"] += 1

            if not user_ans:
                status = "skipped"
                is_correct = False
                skipped_count += 1
            elif user_ans == correct_ans:
                status = "correct"
                is_correct = True
                correct_count += 1
                topic_stats[t_name]["correct"] += 1
                if diff in diff_stats:
                    diff_stats[diff]["correct"] += 1
            else:
                status = "incorrect"
                is_correct = False
                incorrect_count += 1

            # Update DB progress if authenticated and user attempted the question
            if db and user_id and user_ans:
                prog = existing_records.get(qid)
                db_status = "solved" if is_correct else "attempted"
                if not prog:
                    prog = MCQUserProgress(
                        user_id=user_id,
                        question_id=qid,
                        selected_option=user_ans,
                        is_correct=is_correct,
                        status=db_status,
                        attempts_count=1,
                        updated_at=utc_now()
                    )
                    db.add(prog)
                else:
                    prog.selected_option = user_ans
                    prog.is_correct = is_correct
                    if prog.status != "solved" or is_correct:
                        prog.status = db_status
                    prog.attempts_count = (prog.attempts_count or 0) + 1
                    prog.updated_at = utc_now()

            detailed_results.append({
                "id": q["id"],
                "broad_topic_id": q["broad_topic_id"],
                "broad_topic_name": q["broad_topic_name"],
                "subpart_id": q["subpart_id"],
                "subpart_name": q["subpart_name"],
                "difficulty": q["difficulty"],
                "question": q["question"],
                "has_code": q["has_code"],
                "code_snippet": q["code_snippet"],
                "options": q["options"],
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "status": status,
                "explanation": q.get("explanation", "")
            })

        if db and user_id:
            db.commit()

        score_pct = round((correct_count / total_q * 100), 1) if total_q > 0 else 0.0

        return {
            "total_questions": total_q,
            "answered_count": correct_count + incorrect_count,
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "skipped_count": skipped_count,
            "score_pct": score_pct,
            "time_spent_seconds": time_spent_seconds,
            "topic_breakdown": topic_stats,
            "difficulty_breakdown": diff_stats,
            "detailed_results": detailed_results
        }
