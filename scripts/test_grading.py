import sys
import requests
import json

BASE_URL = 'http://localhost:8000/api'

def run():
    print("Testing Custom Practice Session Grading Logic...")
    
    # 1. Create session with question 6.2-021
    payload = {
        "title": "Aptitude Specific Validation",
        "session_type": "mcq",
        "duration_minutes": 15,
        "marking_scheme": {"mcq_correct": 1.0, "mcq_negative": -0.25, "coding_weight": 10.0},
        "sections": [
            {
                "id": "sec_1",
                "name": "Higher Math",
                "section_type": "mcq",
                "specific_question_ids": ["6.2-021"]
            }
        ]
    }

    r = requests.post(f"{BASE_URL}/practice/custom-session/prepare", json=payload)
    assert r.status_code == 200, f"Prepare failed: {r.text}"
    data = r.json()
    sid = data.get("session_id") or data.get("id")
    print(f"Created session {sid}")

    # Case A: Candidate selects correct answer 'C'
    sub_payload_correct = {
        "candidate_name": "Correct Candidate",
        "time_spent_seconds": 30,
        "mcq_answers": {"6.2-021": "C"},
        "coding_submissions": {}
    }
    r = requests.post(f"{BASE_URL}/practice/custom-session/{sid}/submit", json=sub_payload_correct)
    assert r.status_code == 200, f"Submit failed: {r.text}"
    res = r.json()
    q = res["questions"][0]
    
    print("\n--- TEST CASE A: CORRECT ANSWER 'C' ---")
    print(f"Question Prompt: {q.get('question')[:40]}...")
    print(f"User Answer: {q.get('user_answer')}")
    print(f"Correct Answer: {q.get('correct_answer')}")
    print(f"Is Correct: {q.get('is_correct')}")
    print(f"Points Awarded: {q.get('points_awarded')}")
    print(f"Total Score: {res.get('total_score')}")
    
    assert q.get("is_correct") is True, f"Expected is_correct=True, got {q.get('is_correct')}"
    assert q.get("correct_answer") == "C", f"Expected correct_answer='C', got {q.get('correct_answer')}"
    assert q.get("points_awarded") == 1.0, f"Expected points=1.0, got {q.get('points_awarded')}"
    assert res.get("total_score") == 1.0, f"Expected total_score=1.0, got {res.get('total_score')}"
    print("PASS: Correct Answer 'C' scored +1.0 points successfully!")

    # Case B: Create another session and candidate selects incorrect answer 'A'
    r2 = requests.post(f"{BASE_URL}/practice/custom-session/prepare", json=payload)
    sid2 = r2.json().get("session_id") or r2.json().get("id")
    sub_payload_wrong = {
        "candidate_name": "Wrong Candidate",
        "time_spent_seconds": 30,
        "mcq_answers": {"6.2-021": "A"},
        "coding_submissions": {}
    }
    r2 = requests.post(f"{BASE_URL}/practice/custom-session/{sid2}/submit", json=sub_payload_wrong)
    assert r2.status_code == 200
    res2 = r2.json()
    q2 = res2["questions"][0]

    print("\n--- TEST CASE B: INCORRECT ANSWER 'A' ---")
    print(f"User Answer: {q2.get('user_answer')}")
    print(f"Correct Answer: {q2.get('correct_answer')}")
    print(f"Is Correct: {q2.get('is_correct')}")
    print(f"Points Awarded: {q2.get('points_awarded')}")
    print(f"Total Score: {res2.get('total_score')}")

    assert q2.get("is_correct") is False, f"Expected is_correct=False, got {q2.get('is_correct')}"
    assert q2.get("correct_answer") == "C", f"Expected correct_answer='C', got {q2.get('correct_answer')}"
    assert q2.get("points_awarded") == -0.25, f"Expected points=-0.25, got {q2.get('points_awarded')}"
    assert res2.get("total_score") == -0.25, f"Expected total_score=-0.25, got {res2.get('total_score')}"
    print("PASS: Incorrect Answer 'A' applied -0.25 penalty and revealed correct answer 'C'!")

    print("\nALL GRADING ACCURACY TESTS PASSED!")

if __name__ == "__main__":
    run()
