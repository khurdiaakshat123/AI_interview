import requests
import json
import uuid

BASE_URL = "http://127.0.0.1:8000/api"

def test_account_isolation_and_persistence():
    print("=== Testing Account Isolation and Profile Persistence on Live Backend ===")
    
    # 1. Register User A
    rand_a = uuid.uuid4().hex[:6]
    user_a_email = f"alice_{rand_a}@example.com"
    user_a_pass = "Password123!"
    user_a_name = f"Alice Mercer {rand_a}"
    
    resp_a_reg = requests.post(f"{BASE_URL}/auth/signup", json={
        "name": user_a_name,
        "email": user_a_email,
        "password": user_a_pass
    })
    assert resp_a_reg.status_code == 200, f"Failed signup A: {resp_a_reg.text}"
    token_a = resp_a_reg.json()["access_token"]
    user_a_id = resp_a_reg.json()["user"]["id"]
    print(f"[PASS] Registered Account A: {user_a_email} (ID: {user_a_id})")

    # 2. Account A updates their Profile (Target Role, Company, Custom Resume, JD)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    profile_a_payload = {
        "name": "Alice M. Principal Architect",
        "company": "DeepMind Technologies",
        "role": "Principal Research Engineer",
        "experience": "5-8 years",
        "resume_text": "Experienced distributed systems and LLM researcher with 6 publications.",
        "jd_text": "Staff Research Engineer Job Description: Design next-generation inference architectures."
    }
    resp_a_update = requests.post(f"{BASE_URL}/candidate/profile", json=profile_a_payload, headers=headers_a)
    assert resp_a_update.status_code == 200, f"Failed updating profile A: {resp_a_update.text}"
    data_a = resp_a_update.json()
    assert data_a["role"] == "Principal Research Engineer"
    assert data_a["company"] == "DeepMind Technologies"
    assert "LLM researcher" in data_a["resume_text"]
    assert "inference architectures" in data_a["jd_text"]
    print("[PASS] Account A saved custom profile (Role, Resume, JD) successfully")

    # 3. Register User B
    rand_b = uuid.uuid4().hex[:6]
    user_b_email = f"bob_{rand_b}@example.com"
    user_b_pass = "Password456!"
    user_b_name = f"Bob Builder {rand_b}"

    resp_b_reg = requests.post(f"{BASE_URL}/auth/signup", json={
        "name": user_b_name,
        "email": user_b_email,
        "password": user_b_pass
    })
    assert resp_b_reg.status_code == 200, f"Failed signup B: {resp_b_reg.text}"
    token_b = resp_b_reg.json()["access_token"]
    user_b_id = resp_b_reg.json()["user"]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print(f"[PASS] Registered Account B: {user_b_email} (ID: {user_b_id})")

    # 4. Verify Account B gets a clean profile, ISOLATED from Account A
    resp_b_get = requests.get(f"{BASE_URL}/candidate/profile", headers=headers_b)
    assert resp_b_get.status_code == 200
    data_b = resp_b_get.json()
    assert data_b["role"] != "Principal Research Engineer", "Leak! Account B saw Account A's role"
    assert data_b["company"] != "DeepMind Technologies", "Leak! Account B saw Account A's company"
    assert "LLM researcher" not in (data_b["resume_text"] or ""), "Leak! Account B saw Account A's resume"
    assert "inference architectures" not in (data_b["jd_text"] or ""), "Leak! Account B saw Account A's JD"
    print("[PASS] Account Isolation Verified: Account B has zero trace of Account A's JD, Resume, or Role")

    # 5. Account B saves their own distinct Profile
    profile_b_payload = {
        "name": "Bob B. Frontend Specialist",
        "company": "Vercel",
        "role": "Lead Frontend Engineer",
        "experience": "3-5 years",
        "resume_text": "Expert in React 19, Next.js App Router, and browser performance optimization.",
        "jd_text": "Senior Web Platform Engineer: Build high-throughput frontend services."
    }
    resp_b_update = requests.post(f"{BASE_URL}/candidate/profile", json=profile_b_payload, headers=headers_b)
    assert resp_b_update.status_code == 200
    print("[PASS] Account B saved custom profile (Role, Resume, JD) successfully")

    # 6. Re-login as Account A (Simulate sign out and sign in back)
    resp_a_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": user_a_email,
        "password": user_a_pass
    })
    assert resp_a_login.status_code == 200
    fresh_token_a = resp_a_login.json()["access_token"]
    fresh_headers_a = {"Authorization": f"Bearer {fresh_token_a}"}

    resp_a_restored = requests.get(f"{BASE_URL}/candidate/profile", headers=fresh_headers_a)
    assert resp_a_restored.status_code == 200
    restored_a = resp_a_restored.json()
    assert restored_a["name"] == "Alice M. Principal Architect", f"Name not restored: {restored_a['name']}"
    assert restored_a["company"] == "DeepMind Technologies", f"Company not restored: {restored_a['company']}"
    assert restored_a["role"] == "Principal Research Engineer", f"Role not restored: {restored_a['role']}"
    assert "LLM researcher" in restored_a["resume_text"], f"Resume not restored: {restored_a['resume_text']}"
    assert "inference architectures" in restored_a["jd_text"], f"JD not restored: {restored_a['jd_text']}"
    print("[PASS] Saved Profile Persistence Verified: Account A logged out and back in, all profile fields 100% restored!")

    # 7. Re-login as Account B
    resp_b_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": user_b_email,
        "password": user_b_pass
    })
    assert resp_b_login.status_code == 200
    fresh_token_b = resp_b_login.json()["access_token"]
    fresh_headers_b = {"Authorization": f"Bearer {fresh_token_b}"}

    resp_b_restored = requests.get(f"{BASE_URL}/candidate/profile", headers=fresh_headers_b)
    assert resp_b_restored.status_code == 200
    restored_b = resp_b_restored.json()
    assert restored_b["name"] == "Bob B. Frontend Specialist"
    assert restored_b["company"] == "Vercel"
    assert restored_b["role"] == "Lead Frontend Engineer"
    assert "React 19" in restored_b["resume_text"]
    assert "Web Platform Engineer" in restored_b["jd_text"]
    print("[PASS] Saved Profile Persistence Verified: Account B logged out and back in, all profile fields 100% restored!")

    print("\nALL ACCOUNT ISOLATION AND PROFILE PERSISTENCE TESTS PASSED 100%!")

if __name__ == "__main__":
    test_account_isolation_and_persistence()
