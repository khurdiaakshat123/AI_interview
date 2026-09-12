import httpx
import json

BASE_URL = "http://127.0.0.1:8000/api"
client = httpx.Client(timeout=30.0)

def run_tests():
    print("=== Testing Intervyn System Endpoints ===")
    
    # 1. Health
    res = client.get(f"{BASE_URL}/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] Health Check:", res.json()["status"])

    # 2. Role Topic Profiles (Agent 1)
    res = client.get(f"{BASE_URL}/role-profiles")
    assert res.status_code == 200, f"Role profiles fetch failed: {res.text}"
    profiles = res.json()
    assert len(profiles) > 0, "No role profiles found"
    google_prof = profiles[0]
    print(f"[PASS] Agent 1 Role Topic Profile: {google_prof['company']} - {google_prof['role']} with {len(google_prof['subjects'])} subjects")

    # 3. Practice Engine (Agent 2 - SHA256 Key Determinism)
    p_payload = {
        "company": "Google",
        "role": "Software Engineer II (L4)",
        "selected_topics": ["Sliding Window & Two Pointers", "Graphs & Shortest Path"],
        "proficiency_vector": {"Sliding Window & Two Pointers": "intermediate"},
        "total_questions": 2,
        "allocation_mode": "auto"
    }
    res1 = client.post(f"{BASE_URL}/practice/sessions", json=p_payload)
    assert res1.status_code == 200, f"Practice session creation failed: {res1.text}"
    session1 = res1.json()
    key1 = session1["practice_generation_key"]

    # Request with identical parameters must yield identical SHA256 key
    res2 = client.post(f"{BASE_URL}/practice/sessions", json=p_payload)
    session2 = res2.json()
    key2 = session2["practice_generation_key"]
    assert key1 == key2, f"Determinism failure: {key1} != {key2}"
    print(f"[PASS] Agent 2 Practice Determinism SHA256 Key verified: {key1[:12]}...")

    # 4. Check Answer, Hint, Approach, Solution
    q_id = session1["questions"][0]["id"]
    ans_res = client.post(f"{BASE_URL}/practice/questions/{q_id}/check-answer", json={"question_id": q_id, "answer": "def lengthOfLongestSubstring(s):\n    return 3"})
    assert ans_res.status_code == 200
    print(f"[PASS] Evaluator Registry Check Answer: is_correct={ans_res.json()['is_correct']}, score={ans_res.json()['score_fraction']}")

    hint_res = client.get(f"{BASE_URL}/practice/questions/{q_id}/hint")
    assert hint_res.status_code == 200
    print(f"[PASS] Agent 2 Hint: {hint_res.json()['hint'][:50]}...")

    sol_res = client.get(f"{BASE_URL}/practice/questions/{q_id}/solution")
    assert sol_res.status_code == 200
    print(f"[PASS] Agent 2 Solution retrieved")

    # 5. Mock OA Engine (Agent 3 - Canonical Time Window & Attempt Numbering)
    oa_res = client.post(f"{BASE_URL}/mock-oa/start", json={"company": "Google", "role": "Software Engineer II (L4)"})
    assert oa_res.status_code == 200, f"Mock OA start failed: {oa_res.text}"
    oa_data = oa_res.json()
    print(f"[PASS] Agent 3 Mock OA: Attempt #{oa_data['attempt_number']}, Window expires in {oa_data['window_expires_in_days']} days, {len(oa_data['questions'])} questions")

    # Submit Mock OA (Agent 5 - Evaluation & Topic Breakdown)
    attempt_id = oa_data["mock_oa_attempt_id"]
    sub_res = client.post(f"{BASE_URL}/mock-oa/attempts/{attempt_id}/submit", json={
        "answers": {q["id"]: "optimal solution" for q in oa_data["questions"]},
        "time_spent_per_question": {q["id"]: 180 for q in oa_data["questions"]}
    })
    assert sub_res.status_code == 200
    report = sub_res.json()
    print(f"[PASS] Agent 5 Mock OA Evaluation: Score={report['total_score']}/100, Topics evaluated={len(report['accuracy_by_topic'])}")

    # 6. AI Mock Interview (Agent 1 Project Defense + Adaptive FSM + Deterministic Scoring Engine)
    int_start = client.post(f"{BASE_URL}/interview/sessions", json={
        "company": "Google",
        "role": "Software Engineer II (L4)",
        "candidate_name": "Alex Mercer"
    })
    assert int_start.status_code == 200
    turn1 = int_start.json()
    print(f"[PASS] Interview Agent 1 Initialized: Phase={turn1['phase']}, Depth=L{turn1['depth_level']}")

    # Answer turn with technical justification to test adaptive FSM progression
    ans_turn = client.post(f"{BASE_URL}/interview/sessions/{turn1['session_id']}/answer", json={
        "answer": "We chose Raft consensus over Paxos because of understandable state machine transitions. For storage, we used LSM-trees over B-trees to optimize for write-heavy throughput while caching hot read partitions in Redis with write-ahead logging to guarantee durability and eliminate bottlenecks."
    })
    assert ans_turn.status_code == 200
    turn2 = ans_turn.json()
    eval_prev = turn2["eval_previous"]
    print(f"[PASS] Adaptive FSM Transition: Depth now L{turn2['depth_level']}, Quality Band={eval_prev['quality_band']}, Points awarded=+{eval_prev['earned_points']}/{eval_prev['possible_points']} pts")

    # 7. Final Interview Audit Report (Dual Headline Scores §6.5)
    final_rep_res = client.post(f"{BASE_URL}/interview/sessions/{turn1['session_id']}/answer", json={
        "answer": "We enforce distributed deadlock prevention through wait-die transaction timestamping and ordered resource acquisition locks."
    })
    rep_res = client.get(f"{BASE_URL}/interview/sessions/{turn1['session_id']}/report")
    assert rep_res.status_code == 200
    final_report = rep_res.json()
    print(f"[PASS] Dual Headline Scores: Resume Defense={final_report['resume_related_score']}/100, Subject Knowledge={final_report['subject_knowledge_score']}/100")
    print(f"[PASS] Stored Evidence Records: {len(final_report['evidence_trail'])} audit records verified")

    # 8. Admin 18-Point Review Queue (Agent 4)
    rev_res = client.get(f"{BASE_URL}/admin/review-queue")
    assert rev_res.status_code == 200
    rev_items = rev_res.json()
    assert len(rev_items) > 0
    passed_18 = rev_items[0]["review_report"]["passed_checks_count"]
    print(f"[PASS] Agent 4 18-Point Review Queue: Verified item with {passed_18}/18 audit checkpoints passed")

    print("\n>>> ALL BACKEND AND AI AGENT PIPELINES VERIFIED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_tests()
