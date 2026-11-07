import requests
import json
import sys

BASE_URL = "http://localhost:8000/api"

def run_tests():
    print("=================================================================")
    print("STARTING FULL RUNTIME API PIPELINE VERIFICATION")
    print("=================================================================\n")
    
    passed = 0
    failed = 0

    # Test 1: MCQ Topics
    try:
        r = requests.get(f"{BASE_URL}/practice/mcq/topics")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        topics = r.json()
        assert len(topics) == 9, f"Expected 9 topics, got {len(topics)}"
        print(f"PASS: MCQ Topics (9 broad topics returned)")
        passed += 1
    except Exception as e:
        print(f"FAIL: MCQ Topics - {e}")
        failed += 1

    # Test 2: MCQ Questions for Computer Networks with limit=300
    try:
        r = requests.get(f"{BASE_URL}/practice/mcq/questions?topic=computer-networks&limit=300&page=1")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        questions = data.get("questions", [])
        total = data.get("total", 0)
        assert total == 100, f"Expected 100 questions, got {total}"
        assert len(questions) == 100, f"Expected 100 questions in page, got {len(questions)}"
        print(f"PASS: MCQ Questions for Computer Networks (total: {total}, returned: {len(questions)})")
        passed += 1
    except Exception as e:
        print(f"FAIL: MCQ Questions Computer Networks - {e}")
        failed += 1

    # Test 3: MCQ Questions for Operating Systems with limit=300
    try:
        r = requests.get(f"{BASE_URL}/practice/mcq/questions?topic=os&limit=300&page=1")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        questions = data.get("questions", [])
        total = data.get("total", 0)
        assert total == 110, f"Expected 110 questions, got {total}"
        assert len(questions) == 110, f"Expected 110 questions in page, got {len(questions)}"
        print(f"PASS: MCQ Questions for OS (total: {total}, returned: {len(questions)})")
        passed += 1
    except Exception as e:
        print(f"FAIL: MCQ Questions OS - {e}")
        failed += 1

    # Test 4: Single MCQ Question detail
    sample_q_id = None
    try:
        r = requests.get(f"{BASE_URL}/practice/mcq/questions?topic=computer-networks&limit=10&page=1")
        questions = r.json().get("questions", [])
        sample_q_id = questions[0]["id"]
        
        detail_r = requests.get(f"{BASE_URL}/practice/mcq/questions/{sample_q_id}")
        assert detail_r.status_code == 200, f"Expected 200, got {detail_r.status_code}"
        detail = detail_r.json()
        assert "options" in detail and len(detail["options"]) == 4, "Options missing or incomplete"
        assert "question" in detail and len(detail["question"]) > 0, "Question prompt missing"
        print(f"PASS: Single MCQ Question detail for '{sample_q_id}'")
        passed += 1
    except Exception as e:
        print(f"FAIL: Single MCQ Question detail - {e}")
        failed += 1

    # Test 5: Submit MCQ Answer
    if sample_q_id:
        try:
            submit_r = requests.post(
                f"{BASE_URL}/practice/mcq/questions/{sample_q_id}/submit",
                json={"selected_option": "A"}
            )
            assert submit_r.status_code == 200, f"Expected 200, got {submit_r.status_code}: {submit_r.text}"
            res = submit_r.json()
            assert "is_correct" in res and "correct_answer" in res and "explanation" in res
            print(f"PASS: Submit MCQ Answer (is_correct={res['is_correct']}, correct={res['correct_answer']})")
            passed += 1
        except Exception as e:
            print(f"FAIL: Submit MCQ Answer - {e}")
            failed += 1

    # Test 6: Custom Practice Session - Metadata
    try:
        r = requests.get(f"{BASE_URL}/practice/custom-session/metadata")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        meta = r.json()
        assert "mcq_topics" in meta and len(meta["mcq_topics"]) == 9
        assert "dsa_topics" in meta and len(meta["dsa_topics"]) > 10
        print(f"PASS: Custom Practice Metadata (MCQ topics: {len(meta['mcq_topics'])}, DSA topics: {len(meta['dsa_topics'])})")
        passed += 1
    except Exception as e:
        print(f"FAIL: Custom Practice Metadata - {e}")
        failed += 1

    # Test 7: Prepare Custom Practice Session (Both MCQ & DSA)
    session_id = None
    try:
        payload = {
            "title": "Runtime Test Assessment",
            "session_type": "hybrid",
            "duration_minutes": 30,
            "marking_scheme": {
                "mcq_correct": 1.0,
                "mcq_negative": -0.25,
                "coding_weight": 10.0
            },
            "sections": [
                {
                    "id": "sec_1",
                    "name": "OS MCQ Section",
                    "section_type": "mcq",
                    "topic": "os",
                    "difficulty": "Easy",
                    "count": 3
                },
                {
                    "id": "sec_2",
                    "name": "DSA Coding Section",
                    "section_type": "dsa",
                    "topic": "all",
                    "difficulty": "Easy",
                    "count": 1
                }
            ]
        }
        r = requests.post(f"{BASE_URL}/practice/custom-session/prepare", json=payload)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        session_id = data["session_id"]
        assert session_id.startswith("ps_"), f"Unexpected session_id {session_id}"
        assert data["total_questions"] == 4, f"Expected 4 questions, got {data['total_questions']}"
        print(f"PASS: Prepare Custom Session (Session ID: {session_id}, Questions: {data['total_questions']})")
        passed += 1
    except Exception as e:
        print(f"FAIL: Prepare Custom Session - {e}")
        failed += 1

    # Test 8: Get Prepared Session by ID
    if session_id:
        try:
            r = requests.get(f"{BASE_URL}/practice/custom-session/{session_id}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            data = r.json()
            assert len(data["questions"]) == 4, f"Expected 4 questions, got {len(data['questions'])}"
            # Verify solutions are not leaked
            for q in data["questions"]:
                assert "correct_answer" not in q or q.get("correct_answer") is None, "Security leak: correct_answer exposed"
                assert "solution" not in q or q.get("solution") is None, "Security leak: solution exposed"
            print(f"PASS: Get Custom Session by ID (Candidate safe, 0 solution leaks)")
            passed += 1
        except Exception as e:
            print(f"FAIL: Get Custom Session - {e}")
            failed += 1

    # Test 9: Submit Custom Session (Grading & Explanations with Rigorous Answer Validation)
    if session_id:
        try:
            # Fetch the question IDs from the prepared session
            sess_r = requests.get(f"{BASE_URL}/practice/custom-session/{session_id}")
            sess_questions = sess_r.json().get("questions", [])
            first_mcq = next((q for q in sess_questions if q.get("type") == "mcq"), None)
            
            submit_payload = {
                "candidate_name": "Test Candidate",
                "time_spent_seconds": 120,
                "mcq_answers": {first_mcq["id"]: "A"} if first_mcq else {},
                "coding_submissions": {}
            }
            r = requests.post(f"{BASE_URL}/practice/custom-session/{session_id}/submit", json=submit_payload)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            res = r.json()
            assert "total_score" in res, "Missing total_score"
            assert "percentage" in res, "Missing percentage"
            assert "questions" in res and len(res["questions"]) == 4, "Missing evaluated questions"
            
            evaluated_first = next((q for q in res["questions"] if q.get("type") == "mcq"), None)
            assert evaluated_first is not None, "Missing evaluated MCQ question"
            assert evaluated_first.get("correct_answer") is not None, "correct_answer must NOT be null in evaluated results"
            assert evaluated_first.get("explanation") is not None, "explanation must NOT be null"
            
            print(f"PASS: Submit Custom Session (Score: {res['total_score']}, Unlocked: {len(res['questions'])}, Validated correct_answer: '{evaluated_first.get('correct_answer')}')")
            passed += 1
        except Exception as e:
            print(f"FAIL: Submit Custom Session - {e}")
            failed += 1

    # Test 10: Coding Questions (LeetCode API)
    try:
        r = requests.get(f"{BASE_URL}/practice/lc/questions?category=all&page=1&limit=10")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert data.get("total", 0) > 3000, f"Expected >3000 questions, got {data.get('total')}"
        print(f"PASS: Coding Questions list (Total: {data.get('total')})")
        passed += 1
    except Exception as e:
        print(f"FAIL: Coding Questions list - {e}")
        failed += 1

    # Test 11: Single Coding Question
    try:
        r = requests.get(f"{BASE_URL}/practice/lc/questions/1")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        q = r.json()
        assert q["id"] == "1"
        assert "starter_code" in q or "starterCode" in q
        print(f"PASS: Single Coding Question #1 ({q['title']})")
        passed += 1
    except Exception as e:
        print(f"FAIL: Single Coding Question - {e}")
        failed += 1

    # Test 12: Run Code against sample test cases
    try:
        run_payload = {
            "code": "class Solution:\n    def twoSum(self, nums: list[int], target: int) -> list[int]:\n        seen = {}\n        for i, n in enumerate(nums):\n            diff = target - n\n            if diff in seen:\n                return [seen[diff], i]\n            seen[n] = i\n        return []",
            "language": "python3"
        }
        r = requests.post(f"{BASE_URL}/practice/lc/questions/1/run", json=run_payload)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        run_res = r.json()
        assert run_res["status"].upper() == "ACCEPTED", f"Expected Accepted, got {run_res['status']}"
        print(f"PASS: Run Code for Question #1 (Status: {run_res['status']}, Passed: {run_res.get('passed_test_cases')}/{run_res.get('total_test_cases')})")
        passed += 1
    except Exception as e:
        print(f"FAIL: Run Code - {e}")
        failed += 1

    print("\n=================================================================")
    print(f"VERIFICATION SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=================================================================")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
