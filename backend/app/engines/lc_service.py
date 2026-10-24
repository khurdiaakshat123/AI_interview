import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.models import LCUserProgress, LCSubmission, utc_now
from backend.app.engines.sandbox_runner import SandboxRunner

# Path to the cloned lc_qbank repository
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../lc_qbank"))
MANIFEST_PATH = os.path.join(BASE_DIR, "manifests", "questions-index.json")

# Algorithmic Complexity Mapping based on subcategory & difficulty
COMPLEXITY_RULES = {
    "binary-search": ("O(log n)", "O(1)"),
    "two-pointers": ("O(n)", "O(1)"),
    "sliding-window": ("O(n)", "O(1)"),
    "hashing": ("O(n)", "O(n)"),
    "arrays": {
        "Easy": ("O(n)", "O(1)"),
        "Medium": ("O(n)", "O(n)"),
        "Hard": ("O(n log n)", "O(n)")
    },
    "strings": {
        "Easy": ("O(n)", "O(1)"),
        "Medium": ("O(n)", "O(n)"),
        "Hard": ("O(n)", "O(n)")
    },
    "linked-lists": {
        "Easy": ("O(n)", "O(1)"),
        "Medium": ("O(n)", "O(1)"),
        "Hard": ("O(n log k)", "O(1)")
    },
    "stacks-queues": ("O(n)", "O(n)"),
    "trees": {
        "Easy": ("O(n)", "O(h)"),
        "Medium": ("O(n)", "O(h)"),
        "Hard": ("O(n)", "O(n)")
    },
    "heaps": ("O(n log k)", "O(k)"),
    "graphs": {
        "Easy": ("O(V + E)", "O(V)"),
        "Medium": ("O(V + E)", "O(V)"),
        "Hard": ("O(E log V)", "O(V)")
    },
    "dynamic-programming": {
        "Easy": ("O(n)", "O(1)"),
        "Medium": ("O(m * n)", "O(n)"),
        "Hard": ("O(n * k)", "O(n * k)")
    },
    "greedy": {
        "Easy": ("O(n)", "O(1)"),
        "Medium": ("O(n log n)", "O(1)"),
        "Hard": ("O(n log n)", "O(n)")
    },
    "recursion-backtracking": {
        "Medium": ("O(2^n)", "O(n)"),
        "Hard": ("O(n!)", "O(n)")
    },
    "tries": ("O(L)", "O(N * L)"),
    "bit-manipulation": ("O(1)", "O(1)"),
    "mathematics": ("O(log n)", "O(1)"),
    "divide-and-conquer": ("O(n log n)", "O(log n)"),
    "sorting": ("O(n log n)", "O(1)"),
    "prefix-sum": ("O(n)", "O(n)"),
    "design": ("O(1)", "O(n)"),
    "advanced-data-structures": ("O(log n)", "O(n)"),
    "miscellaneous": ("O(n)", "O(n)"),
    # Database
    "select-filtering": ("O(n)", "O(1)"),
    "joins": ("O(m + n)", "O(min(m, n))"),
    "aggregation": ("O(n)", "O(groups)"),
    "window-functions": ("O(n log n)", "O(n)"),
    "null-handling": ("O(n)", "O(1)"),
    "string-functions": ("O(n)", "O(1)"),
    "date-time": ("O(n)", "O(1)"),
    "set-operations": ("O(m + n)", "O(m + n)")
}

def get_complexity_for_question(subcategory: str, difficulty: str) -> Tuple[str, str]:
    sub = subcategory.lower().strip()
    rule = COMPLEXITY_RULES.get(sub)
    if not rule:
        return ("O(n)", "O(n)") if difficulty == "Hard" else ("O(n)", "O(1)")
    if isinstance(rule, tuple):
        return rule
    if isinstance(rule, dict):
        return rule.get(difficulty, rule.get("Medium", ("O(n)", "O(1)")))
    return ("O(n)", "O(1)")

class LCQuestionService:
    _instance = None
    _questions_list: List[Dict[str, Any]] = []
    _by_id: Dict[str, Dict[str, Any]] = {}
    _by_slug: Dict[str, Dict[str, Any]] = {}
    _is_initialized: bool = False

    @classmethod
    def initialize(cls):
        if cls._is_initialized and cls._questions_list:
            return

        if not os.path.exists(MANIFEST_PATH):
            print(f"[LCQuestionService] Manifest not found at {MANIFEST_PATH}")
            return

        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_qs = data.get("questions", [])

            processed = []
            for item in raw_qs:
                q_id = str(item.get("id"))
                q_num = int(q_id) if q_id.isdigit() else 999999
                cat = item.get("category", "dsa")
                subcat = item.get("subcategory", "")
                diff = item.get("difficulty", "Medium")
                t_comp, s_comp = get_complexity_for_question(subcat, diff)

                entry = {
                    "id": q_id,
                    "num": q_num,
                    "slug": item.get("slug", ""),
                    "title": item.get("title", ""),
                    "category": cat,
                    "subcategory": subcat,
                    "difficulty": diff,
                    "path": item.get("path", ""),
                    "timeComplexity": t_comp,
                    "spaceComplexity": s_comp
                }
                processed.append(entry)

            # Sort strictly by numeric question number
            processed.sort(key=lambda x: x["num"])

            cls._questions_list = processed
            cls._by_id = {q["id"]: q for q in processed}
            cls._by_slug = {q["slug"]: q for q in processed}
            cls._is_initialized = True
            print(f"[LCQuestionService] Successfully indexed {len(processed)} LeetCode questions.")
        except Exception as e:
            print(f"[LCQuestionService] Failed to load manifest: {e}")

    @classmethod
    def list_questions(
        cls,
        db: Session,
        user_id: Optional[str] = None,
        category: str = "all",
        subcategory: Optional[str] = None,
        difficulty: str = "all",
        status: str = "all",
        search: Optional[str] = None,
        my_list_only: bool = False,
        page: int = 1,
        limit: int = 50,
        sort_by: str = "id",
        order: str = "asc"
    ) -> Dict[str, Any]:
        cls.initialize()

        # Fetch user progress map
        progress_map = {}
        starred_set = set()
        if user_id:
            user_records = db.query(LCUserProgress).filter(LCUserProgress.user_id == user_id).all()
            for rec in user_records:
                progress_map[rec.question_id] = rec.status
                if rec.is_starred:
                    starred_set.add(rec.question_id)

        # Apply filtering
        filtered = []
        search_lower = search.lower().strip() if search else None

        for q in cls._questions_list:
            q_id = q["id"]
            q_status = progress_map.get(q_id, "todo")
            is_starred = q_id in starred_set

            # Category filter ('dsa' | 'database')
            if category != "all" and q["category"] != category:
                continue

            # Subcategory filter
            if subcategory and subcategory != "all":
                if q["subcategory"].lower() != subcategory.lower():
                    continue

            # Difficulty filter
            if difficulty != "all" and q["difficulty"].lower() != difficulty.lower():
                continue

            # Status filter ('solved', 'attempted', 'todo')
            if status != "all" and q_status.lower() != status.lower():
                continue

            # My List filter
            if my_list_only and not is_starred:
                continue

            # Search filter (matches number, title, slug, or subcategory)
            if search_lower:
                match_id = q_id == search_lower or search_lower in q_id
                match_title = search_lower in q["title"].lower()
                match_slug = search_lower in q["slug"].lower()
                match_sub = search_lower in q["subcategory"].lower()
                if not (match_id or match_title or match_slug or match_sub):
                    continue

            filtered.append({
                **q,
                "status": q_status,
                "isStarred": is_starred
            })

        # Sorting
        reverse = (order == "desc")
        if sort_by == "title":
            filtered.sort(key=lambda x: x["title"].lower(), reverse=reverse)
        elif sort_by == "difficulty":
            diff_rank = {"Easy": 1, "Medium": 2, "Hard": 3}
            filtered.sort(key=lambda x: diff_rank.get(x["difficulty"], 2), reverse=reverse)
        else: # sort by id/num
            filtered.sort(key=lambda x: x["num"], reverse=reverse)

        total = len(filtered)
        limit = max(1, min(limit, 100))
        total_pages = max(1, (total + limit - 1) // limit)
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_items = filtered[start_idx:end_idx]

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": total_pages,
            "questions": paginated_items
        }

    @classmethod
    def get_question(cls, id_or_slug: str, db: Session, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        cls.initialize()
        q_ref = cls._by_id.get(str(id_or_slug)) or cls._by_slug.get(str(id_or_slug).lower())
        if not q_ref:
            return None

        file_path = os.path.join(BASE_DIR, q_ref["path"])
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                full_data = json.load(f)

            # Normalize image links: replace ./assets/ with /lc_assets/
            statement = full_data.get("statement", "")
            if statement:
                # Replace markdown image links ./assets/ and assets/
                statement = re.sub(r'!\[(.*?)\]\(\./assets/(.*?)\)', r'![\1](/lc_assets/\2)', statement)
                statement = re.sub(r'!\[(.*?)\]\(assets/(.*?)\)', r'![\1](/lc_assets/\2)', statement)
                statement = re.sub(r'src=[\'"]\./assets/(.*?)[\'"]', r'src="/lc_assets/\1"', statement)
                statement = re.sub(r'src=[\'"]assets/(.*?)[\'"]', r'src="/lc_assets/\1"', statement)

            q_id = q_ref["id"]
            is_starred = False
            status = "todo"
            if user_id:
                prog = db.query(LCUserProgress).filter(
                    LCUserProgress.user_id == user_id,
                    LCUserProgress.question_id == q_id
                ).first()
                if prog:
                    is_starred = prog.is_starred
                    status = prog.status

            # Get previous submissions
            prev_submissions = []
            if user_id:
                subs = db.query(LCSubmission).filter(
                    LCSubmission.user_id == user_id,
                    LCSubmission.question_id == q_id
                ).order_by(LCSubmission.submitted_at.desc()).limit(20).all()
                for s in subs:
                    prev_submissions.append({
                        "id": s.id,
                        "language": s.language,
                        "code": s.code,
                        "status": s.status,
                        "runtime_ms": s.runtime_ms,
                        "memory_mb": s.memory_mb,
                        "test_cases_passed": s.test_cases_passed,
                        "total_test_cases": s.total_test_cases,
                        "error_message": s.error_message,
                        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else ""
                    })

            t_comp, s_comp = get_complexity_for_question(q_ref["subcategory"], full_data.get("difficulty", "Medium"))

            # Extract sample test cases from examples or publicTests
            raw_examples = full_data.get("examples", [])
            raw_tests = full_data.get("publicTests") or full_data.get("testCases") or []
            sample_cases = []
            if raw_examples:
                for idx, ex in enumerate(raw_examples):
                    sample_cases.append({
                        "case_number": idx + 1,
                        "input": ex.get("input", ""),
                        "expected": ex.get("output", ""),
                        "explanation": ex.get("explanation", "")
                    })
            elif raw_tests:
                for idx, t in enumerate(raw_tests[:3]):
                    sample_cases.append({
                        "case_number": idx + 1,
                        "input": t.get("input", ""),
                        "expected": t.get("expectedOutput", "") or t.get("expected_output", ""),
                        "explanation": ""
                    })

            return {
                "id": q_id,
                "num": q_ref["num"],
                "slug": q_ref["slug"],
                "title": full_data.get("title", q_ref["title"]),
                "category": full_data.get("category", q_ref["category"]),
                "subcategory": full_data.get("subcategory", q_ref["subcategory"]),
                "difficulty": full_data.get("difficulty", q_ref["difficulty"]),
                "tags": full_data.get("tags", []),
                "timeComplexity": t_comp,
                "spaceComplexity": s_comp,
                "statement": statement,
                "constraints": full_data.get("constraints", []),
                "examples": full_data.get("examples", []),
                "sampleCases": sample_cases,
                "starterCode": full_data.get("starterCode") or {},
                "hints": full_data.get("hints", []),
                "sqlSchema": full_data.get("sqlSchema"),
                "sqlSetup": full_data.get("sqlSetup"),
                "isStarred": is_starred,
                "status": status,
                "prevSubmissions": prev_submissions
            }
        except Exception as e:
            print(f"[LCQuestionService] Error reading {file_path}: {e}")
            return None

    @classmethod
    def get_analytics(cls, db: Session, user_id: Optional[str] = None) -> Dict[str, Any]:
        cls.initialize()

        total = len(cls._questions_list)
        dsa_total = sum(1 for q in cls._questions_list if q["category"] == "dsa")
        db_total = sum(1 for q in cls._questions_list if q["category"] == "database")

        easy_total = sum(1 for q in cls._questions_list if q["difficulty"] == "Easy")
        med_total = sum(1 for q in cls._questions_list if q["difficulty"] == "Medium")
        hard_total = sum(1 for q in cls._questions_list if q["difficulty"] == "Hard")

        solved_ids = set()
        attempted_ids = set()
        starred_count = 0

        if user_id:
            user_records = db.query(LCUserProgress).filter(LCUserProgress.user_id == user_id).all()
            for r in user_records:
                if r.status == "solved":
                    solved_ids.add(r.question_id)
                elif r.status == "attempted":
                    attempted_ids.add(r.question_id)
                if r.is_starred:
                    starred_count += 1

        easy_solved = sum(1 for q in cls._questions_list if q["id"] in solved_ids and q["difficulty"] == "Easy")
        med_solved = sum(1 for q in cls._questions_list if q["id"] in solved_ids and q["difficulty"] == "Medium")
        hard_solved = sum(1 for q in cls._questions_list if q["id"] in solved_ids and q["difficulty"] == "Hard")

        dsa_solved = sum(1 for q in cls._questions_list if q["id"] in solved_ids and q["category"] == "dsa")
        db_solved = sum(1 for q in cls._questions_list if q["id"] in solved_ids and q["category"] == "database")

        # Topic counts
        topic_stats = {}
        for q in cls._questions_list:
            sub = q["subcategory"]
            if sub not in topic_stats:
                topic_stats[sub] = {"total": 0, "solved": 0}
            topic_stats[sub]["total"] += 1
            if q["id"] in solved_ids:
                topic_stats[sub]["solved"] += 1

        return {
            "totalQuestions": total,
            "solvedCount": len(solved_ids),
            "attemptedCount": len(attempted_ids),
            "starredCount": starred_count,
            "dsa": {
                "total": dsa_total,
                "solved": dsa_solved,
                "percentage": round((dsa_solved / dsa_total * 100), 1) if dsa_total else 0
            },
            "database": {
                "total": db_total,
                "solved": db_solved,
                "percentage": round((db_solved / db_total * 100), 1) if db_total else 0
            },
            "difficulty": {
                "easy": {"total": easy_total, "solved": easy_solved},
                "medium": {"total": med_total, "solved": med_solved},
                "hard": {"total": hard_total, "solved": hard_solved}
            },
            "topicStats": topic_stats
        }

    @classmethod
    def toggle_star(cls, db: Session, user_id: str, question_id: str) -> bool:
        prog = db.query(LCUserProgress).filter(
            LCUserProgress.user_id == user_id,
            LCUserProgress.question_id == str(question_id)
        ).first()

        if not prog:
            prog = LCUserProgress(
                user_id=user_id,
                question_id=str(question_id),
                status="todo",
                is_starred=True,
                updated_at=utc_now()
            )
            db.add(prog)
            db.commit()
            return True
        else:
            prog.is_starred = not prog.is_starred
            prog.updated_at = utc_now()
            db.commit()
            return prog.is_starred

    @classmethod
    def run_code(cls, question_id: str, code: str, language: str) -> Dict[str, Any]:
        cls.initialize()
        q_ref = cls._by_id.get(str(question_id)) or cls._by_slug.get(str(question_id).lower())
        if not q_ref:
            return {"status": "Error", "message": "Question not found"}

        file_path = os.path.join(BASE_DIR, q_ref["path"])
        test_cases = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Use public tests or examples
            tests = data.get("publicTests") or data.get("testCases") or []
            if tests:
                test_cases = [
                    {"input": t.get("input", ""), "expected_output": t.get("expectedOutput") or t.get("expected_output", "")}
                    for t in tests[:3]
                ]
            elif data.get("examples"):
                test_cases = [
                    {"input": ex.get("input", ""), "expected_output": ex.get("output", "")}
                    for ex in data.get("examples", [])[:3]
                ]

        if not test_cases:
            test_cases = [{"input": "Sample", "expected_output": "Sample"}]

        res = SandboxRunner.evaluate_code(
            user_code=code,
            language=language,
            test_cases=test_cases,
            timeout_seconds=4.0
        )
        return res

    @classmethod
    def submit_code(cls, db: Session, user_id: str, question_id: str, code: str, language: str) -> Dict[str, Any]:
        cls.initialize()
        q_ref = cls._by_id.get(str(question_id)) or cls._by_slug.get(str(question_id).lower())
        if not q_ref:
            return {"status": "Error", "message": "Question not found"}

        file_path = os.path.join(BASE_DIR, q_ref["path"])
        test_cases = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tests = data.get("testCases") or data.get("publicTests") or []
            if tests:
                test_cases = [
                    {"input": t.get("input", ""), "expected_output": t.get("expectedOutput") or t.get("expected_output", "")}
                    for t in tests
                ]
            elif data.get("examples"):
                test_cases = [
                    {"input": ex.get("input", ""), "expected_output": ex.get("output", "")}
                    for ex in data.get("examples", [])
                ]

        if not test_cases:
            test_cases = [{"input": "Sample", "expected_output": "Sample"}]

        # Execute
        eval_result = SandboxRunner.evaluate_code(
            user_code=code,
            language=language,
            test_cases=test_cases,
            timeout_seconds=4.0
        )

        is_correct = eval_result.get("is_correct", False)
        raw_status = eval_result.get("status", "")
        if raw_status in ["COMPILATION_ERROR", "Compile Error"]:
            status_label = "Compile Error"
        elif raw_status in ["RUNTIME_ERROR", "Runtime Error"]:
            status_label = "Runtime Error"
        elif raw_status in ["TLE", "Time Limit Exceeded"]:
            status_label = "Time Limit Exceeded"
        elif is_correct:
            status_label = "Accepted"
        else:
            status_label = "Wrong Answer"

        runtime_ms = eval_result.get("runtime_ms")
        memory_mb = eval_result.get("memory_mb")
        tc_results = eval_result.get("test_case_results", [])
        passed = sum(1 for t in tc_results if t.get("passed")) if tc_results else (len(test_cases) if is_correct else 0)
        total_tc = len(tc_results) if tc_results else len(test_cases)

        err_msg = eval_result.get("error")
        if not err_msg and not is_correct and eval_result.get("compiler_output"):
            err_msg = eval_result.get("compiler_output")

        # Create submission record
        sub = LCSubmission(
            user_id=user_id,
            question_id=str(question_id),
            language=language,
            code=code,
            status=status_label,
            runtime_ms=runtime_ms or 0.0,
            memory_mb=memory_mb or 0.0,
            test_cases_passed=passed,
            total_test_cases=total_tc,
            error_message=err_msg,
            submitted_at=utc_now()
        )
        db.add(sub)

        # Update user question progress
        prog = db.query(LCUserProgress).filter(
            LCUserProgress.user_id == user_id,
            LCUserProgress.question_id == str(question_id)
        ).first()

        new_status = "solved" if is_correct else "attempted"
        if not prog:
            prog = LCUserProgress(
                user_id=user_id,
                question_id=str(question_id),
                status=new_status,
                last_language=language,
                updated_at=utc_now()
            )
            db.add(prog)
        else:
            if prog.status != "solved":
                prog.status = new_status
            prog.last_language = language
            prog.updated_at = utc_now()

        db.commit()

        return {
            "submission_id": sub.id,
            "status": status_label,
            "is_correct": is_correct,
            "runtime_ms": runtime_ms,
            "memory_mb": memory_mb,
            "passed_test_cases": passed,
            "total_test_cases": total_tc,
            "test_case_results": eval_result.get("test_case_results", []),
            "error": err_msg,
            "error_message": err_msg,
            "submitted_at": sub.submitted_at.isoformat()
        }
