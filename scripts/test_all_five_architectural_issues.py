import sys
import uuid
import json
import requests
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from backend.app.engines.sandbox_runner import SandboxRunner
from backend.app.engines.lc_service import LCQuestionService, get_complexity_for_question

BASE_URL = "http://127.0.0.1:8000/api"

def run_suite():
    print("=" * 70)
    print("MASTER REGRESSION SUITE: 5 ARCHITECTURAL ISSUES")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # ISSUE 1: Cross-Tab Account Switching Overwriting Profiles
    # -------------------------------------------------------------------------
    print("\n[ISSUE 1] Verifying Cross-Tab Account Switching Overwrite Prevention...")
    uniq = uuid.uuid4().hex[:8]
    user_b_email = f"user_b_{uniq}@intervyn.ai"
    user_a_email = f"user_a_{uniq}@intervyn.ai"
    password = "SuperSecurePassword123!"

    # Sign up B
    res_b = requests.post(f"{BASE_URL}/auth/signup", json={"name": "User B", "email": user_b_email, "password": password})
    assert res_b.status_code == 200, f"B signup failed: {res_b.text}"
    user_b = res_b.json()
    token_b = user_b["access_token"]
    user_b_id = user_b["user"]["id"]
    sess_b = user_b.get("session_generation") or user_b["user"].get("session_generation")

    # Sign up A in Tab 2
    res_a = requests.post(f"{BASE_URL}/auth/signup", json={"name": "User A", "email": user_a_email, "password": password})
    assert res_a.status_code == 200, f"A signup failed: {res_a.text}"
    user_a = res_a.json()
    token_a = user_a["access_token"]
    user_a_id = user_a["user"]["id"]
    sess_a = user_a.get("session_generation") or user_a["user"].get("session_generation")

    # Stale form from Tab 1 (User B data + User B expected headers) sent with Tab 2 token (Token A)
    stale_headers = {
        "Authorization": f"Bearer {token_a}",
        "X-Expected-User-Id": user_b_id,
        "X-Session-Generation": sess_b
    }
    stale_payload = {
        "name": "User B Form Stale",
        "email": "user_b_contact@intervyn.ai",
        "company": "Company B",
        "role": "Role B",
        "resume_text": "Resume B Stale",
        "jd_text": "JD B Stale"
    }
    mismatch_res = requests.post(f"{BASE_URL}/candidate/profile", headers=stale_headers, json=stale_payload)
    print(f"  - Stale submission with account mismatch -> HTTP {mismatch_res.status_code} ({mismatch_res.json().get('detail')})")
    assert mismatch_res.status_code == 409, f"Expected 409 Conflict, got {mismatch_res.status_code}"

    # Verify User A's profile remains pristine and uncorrupted
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Expected-User-Id": user_a_id, "X-Session-Generation": sess_a}
    prof_a = requests.get(f"{BASE_URL}/candidate/profile", headers=headers_a).json()
    assert prof_a.get("name") != "User B Form Stale", "User A profile was corrupted by User B form!"

    # Verify updating candidate contact email does NOT mutate verified login identity User.email
    update_prof_a = requests.post(f"{BASE_URL}/candidate/profile", headers=headers_a, json={
        "name": "User A Updated",
        "email": "contact_only_email@different.com"
    })
    assert update_prof_a.status_code == 200
    me_a = requests.get(f"{BASE_URL}/auth/me", headers=headers_a).json()
    assert me_a["email"] == user_a_email, f"Login email was mutated! Expected {user_a_email}, got {me_a['email']}"
    print("  [PASS] Issue 1 verified: Account mismatch rejected with 409, profile uncorrupted, login identity preserved.")

    # -------------------------------------------------------------------------
    # ISSUE 2: Logout Credential Revocation
    # -------------------------------------------------------------------------
    print("\n[ISSUE 2] Verifying User Logout & Immediate Credential Revocation...")
    # Log out User B
    logout_b = requests.post(f"{BASE_URL}/auth/logout", headers={"Authorization": f"Bearer {token_b}"})
    assert logout_b.status_code == 200

    # Replay revoked token against protected endpoints
    rep_me = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    rep_prof_get = requests.get(f"{BASE_URL}/candidate/profile", headers={"Authorization": f"Bearer {token_b}"})
    rep_prof_post = requests.post(f"{BASE_URL}/candidate/profile", headers={"Authorization": f"Bearer {token_b}"}, json={"name": "Hacked"})

    print(f"  - Replayed revoked token on /auth/me -> HTTP {rep_me.status_code}")
    print(f"  - Replayed revoked token on GET /candidate/profile -> HTTP {rep_prof_get.status_code}")
    print(f"  - Replayed revoked token on POST /candidate/profile -> HTTP {rep_prof_post.status_code}")

    assert rep_me.status_code == 401, f"Expected 401 on /auth/me, got {rep_me.status_code}"
    assert rep_prof_get.status_code == 401, f"Expected 401 on GET /candidate/profile, got {rep_prof_get.status_code}"
    assert rep_prof_post.status_code == 401, f"Expected 401 on POST /candidate/profile, got {rep_prof_post.status_code}"
    print("  [PASS] Issue 2 verified: Credential immediately revoked and rejected with 401 across all protected endpoints.")

    # -------------------------------------------------------------------------
    # ISSUE 3: Java LRU Cache Test Code Generation ('constant string too long')
    # -------------------------------------------------------------------------
    print("\n[ISSUE 3] Verifying Java LRU Cache with Large Fixture (>90,000 bytes)...")
    ops = ["LRUCache"]
    args = [[100]]
    expected = ["null"]
    for i in range(1, 5000):
        if i % 2 == 1:
            ops.append("put")
            args.append([i, i * 10])
            expected.append("null")
        else:
            ops.append("get")
            args.append([i - 1])
            expected.append(str((i - 1) * 10))

    fixture_input = f"{json.dumps(ops)}\n{json.dumps(args)}"
    exp_output = "[" + ",".join(expected) + "]"
    fixture_bytes = len(fixture_input.encode("utf-8"))
    print(f"  - Fixture size: {fixture_bytes:,} bytes (exceeds JVM 65,535 constant pool limit)")
    assert fixture_bytes > 65535

    java_lru_code = """
import java.util.*;

class LRUCache {
    private int capacity;
    private LinkedHashMap<Integer, Integer> map;

    public LRUCache(int capacity) {
        this.capacity = capacity;
        this.map = new LinkedHashMap<Integer, Integer>(capacity, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<Integer, Integer> eldest) {
                return size() > LRUCache.this.capacity;
            }
        };
    }
    
    public int get(int key) {
        return map.getOrDefault(key, -1);
    }
    
    public void put(int key, int value) {
        map.put(key, value);
    }
}
"""
    res_large_lru = SandboxRunner.evaluate_code_against_tests(
        user_code=java_lru_code,
        language="java",
        test_cases=[{"input": fixture_input, "expected_output": exp_output, "is_hidden": False, "is_custom": False}],
        approach="",
        timeout_seconds=10.0
    )
    print(f"  - Java Large LRU Cache Execution Status: {res_large_lru.get('status')} (Compiler exit: {res_large_lru.get('compiler_output')})")
    assert res_large_lru.get("status") == "ACCEPTED", f"Expected ACCEPTED, got {res_large_lru}"
    assert res_large_lru.get("is_correct") is True
    print("  [PASS] Issue 3 verified: Java compiled and passed >90KB fixture without string literal overflow.")

    # -------------------------------------------------------------------------
    # ISSUE 4: SQL Submission Tests Accepting Hardcoded Answers
    # -------------------------------------------------------------------------
    print("\n[ISSUE 4] Verifying SQL Submission Tests & Hardcoded Answer Rejection...")
    p_combine = Path("lc_qbank/questions/database/joins/combine-two-tables.json")
    tcs_combine = json.loads(p_combine.read_text(encoding="utf-8"))["testCases"]

    # Negative control: hardcoded answer matching only the public example
    fake_sql = "SELECT 'Allen' AS firstName, 'Wang' AS lastName, NULL AS city, NULL AS state UNION ALL SELECT 'Bob', 'Alice', 'New York City', 'New York'"
    res_fake_sql = SandboxRunner.evaluate_code_against_tests(user_code=fake_sql, test_cases=tcs_combine, language="mysql")
    print(f"  - Hardcoded Combine Two Tables Query: {res_fake_sql.get('status')} (Passed: {res_fake_sql.get('test_cases_passed')}/{res_fake_sql.get('total_test_cases')})")
    assert res_fake_sql.get("status") == "WRONG_ANSWER", "Hardcoded query should fail submission test cases!"
    assert res_fake_sql.get("test_cases_passed") == 1, "Only public example case should pass for hardcoded query"

    # Positive control: genuine relational LEFT JOIN
    real_sql = "SELECT Person.firstName, Person.lastName, Address.city, Address.state FROM Person LEFT JOIN Address ON Person.personId = Address.personId;"
    res_real_sql = SandboxRunner.evaluate_code_against_tests(user_code=real_sql, test_cases=tcs_combine, language="mysql")
    print(f"  - Genuine Combine Two Tables Query: {res_real_sql.get('status')} (Passed: {res_real_sql.get('test_cases_passed')}/{res_real_sql.get('total_test_cases')})")
    assert res_real_sql.get("status") == "ACCEPTED", "Genuine query should pass all test cases!"
    assert res_real_sql.get("test_cases_passed") == len(tcs_combine)
    print("  [PASS] Issue 4 verified: Hardcoded answer rejected by hidden testcases, genuine query accepted.")

    # -------------------------------------------------------------------------
    # ISSUE 5: Incorrect Complexity Guidance Across Question Bank
    # -------------------------------------------------------------------------
    print("\n[ISSUE 5] Verifying Authoritative Complexity Guidance & Question Bank Audit...")
    LCQuestionService.initialize()

    # Median of Two Sorted Arrays
    t_median, s_median = get_complexity_for_question("divide-and-conquer", "Hard", slug_or_id="median-of-two-sorted-arrays", category="dsa")
    print(f"  - Median of Two Sorted Arrays: Time={t_median}, Space={s_median}")
    assert t_median == "O(log(min(m, n)))", f"Expected O(log(min(m, n))), got {t_median}"
    assert s_median == "O(1)", f"Expected O(1), got {s_median}"

    # Container With Most Water
    t_water, s_water = get_complexity_for_question("greedy", "Medium", slug_or_id="container-with-most-water", category="dsa")
    print(f"  - Container With Most Water: Time={t_water}, Space={s_water}")
    assert t_water == "O(n)", f"Expected O(n), got {t_water}"
    assert s_water == "O(1)", f"Expected O(1), got {s_water}"

    # Database questions: NO algorithmic Big-O
    t_db, s_db = get_complexity_for_question("joins", "Easy", slug_or_id="combine-two-tables", category="database")
    print(f"  - Combine Two Tables (Database): Time={t_db}, Space={s_db}")
    assert t_db is None and s_db is None, f"Database questions must not have Big-O complexity, got {t_db}, {s_db}"

    # Unverified problem: explicitly "Unverified"
    t_unv, s_unv = get_complexity_for_question("arrays", "Hard", slug_or_id="unknown-problem-12345", category="dsa")
    print(f"  - Unverified Algorithmic Problem: Time={t_unv}, Space={s_unv}")
    assert t_unv == "Unverified" and s_unv == "Unverified"

    # Full Question Bank Catalog Audit
    all_qs = LCQuestionService._questions_list
    total_q = len(all_qs)
    db_q = sum(1 for q in all_qs if q.get("category") == "database")
    verified_dsa = sum(1 for q in all_qs if q.get("timeComplexity") and q.get("timeComplexity") != "Unverified" and q.get("category") != "database")
    unverified_dsa = sum(1 for q in all_qs if q.get("timeComplexity") == "Unverified")

    print(f"\n  --- Full Question Bank Catalog Audit ({total_q} questions) ---")
    print(f"  - Total Indexed Questions: {total_q}")
    print(f"  - Database Questions (Big-O omitted): {db_q}")
    print(f"  - Verified Optimal Algorithmic Questions: {verified_dsa}")
    print(f"  - Explicitly Unverified Algorithmic Questions: {unverified_dsa}")
    assert total_q == 3269
    assert db_q == 105
    assert verified_dsa >= 20
    print("  [PASS] Issue 5 verified: Optimal bounds verified, database Big-O omitted, unverified state explicit.")

    print("\n" + "=" * 70)
    print("ALL FIVE ARCHITECTURAL ISSUES RESOLVED AND VERIFIED 100%!")
    print("=" * 70)

if __name__ == "__main__":
    run_suite()
