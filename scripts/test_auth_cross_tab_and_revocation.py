import sys
import uuid
import requests
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

BASE_URL = "http://127.0.0.1:8000/api"

def test_auth_and_revocation_lifecycle():
    print("=== Testing Auth Revocation and Cross-Tab Session Isolation ===")
    
    unique_suffix = uuid.uuid4().hex[:8]
    user_b_email = f"user_b_{unique_suffix}@intervyn.ai"
    user_a_email = f"user_a_{unique_suffix}@intervyn.ai"
    password = "TestPassword123!"

    # 1. Sign up User B
    print("\n[Step 1] Signing up User B...")
    res_b_signup = requests.post(f"{BASE_URL}/auth/signup", json={
        "name": "Candidate B",
        "email": user_b_email,
        "password": password
    })
    assert res_b_signup.status_code == 200, f"Signup failed: {res_b_signup.text}"
    data_b = res_b_signup.json()
    token_b = data_b["access_token"]
    user_b_id = data_b["user"]["id"]
    session_gen_b = data_b.get("session_generation") or data_b["user"].get("session_generation")
    print(f"User B signed up: ID={user_b_id}, SessionGen={session_gen_b[:8]}...")

    # Verify protected endpoints work with Token B
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Expected-User-Id": user_b_id,
        "X-Session-Generation": session_gen_b
    }
    me_res = requests.get(f"{BASE_URL}/auth/me", headers=headers_b)
    assert me_res.status_code == 200, f"/me failed: {me_res.text}"
    assert me_res.json()["email"] == user_b_email

    prof_res = requests.get(f"{BASE_URL}/candidate/profile", headers=headers_b)
    assert prof_res.status_code == 200, f"/candidate/profile failed: {prof_res.text}"

    # 2. Logout User B and verify credential revocation
    print("\n[Step 2] Logging out User B and verifying immediate token revocation...")
    logout_res = requests.post(f"{BASE_URL}/auth/logout", headers={"Authorization": f"Bearer {token_b}"})
    assert logout_res.status_code == 200, f"Logout failed: {logout_res.text}"
    print("Logout API returned 200 OK.")

    # Replay revoked Token B against /api/auth/me
    replay_me = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    print(f"Replay revoked token on /auth/me -> HTTP {replay_me.status_code} (detail: {replay_me.json().get('detail')})")
    assert replay_me.status_code == 401, f"Expected 401 Unauthorized for revoked token, got {replay_me.status_code}"

    # Replay revoked Token B against /api/candidate/profile (GET)
    replay_prof_get = requests.get(f"{BASE_URL}/candidate/profile", headers={"Authorization": f"Bearer {token_b}"})
    print(f"Replay revoked token on GET /candidate/profile -> HTTP {replay_prof_get.status_code} (detail: {replay_prof_get.json().get('detail')})")
    assert replay_prof_get.status_code == 401, f"Expected 401 Unauthorized for revoked token, got {replay_prof_get.status_code}"

    # Replay revoked Token B against /api/candidate/profile (POST)
    replay_prof_post = requests.post(f"{BASE_URL}/candidate/profile", headers={"Authorization": f"Bearer {token_b}"}, json={
        "name": "Hacked Name",
        "company": "Malicious Corp"
    })
    print(f"Replay revoked token on POST /candidate/profile -> HTTP {replay_prof_post.status_code} (detail: {replay_prof_post.json().get('detail')})")
    assert replay_prof_post.status_code == 401, f"Expected 401 Unauthorized for revoked token, got {replay_prof_post.status_code}"
    print("PASS: Revoked credentials strictly rejected across all protected endpoints with 401 Unauthorized.")

    # 3. Sign in as User A in "Tab 2"
    print("\n[Step 3] Signing up User A in simulated Tab 2...")
    res_a_signup = requests.post(f"{BASE_URL}/auth/signup", json={
        "name": "Candidate A",
        "email": user_a_email,
        "password": password
    })
    assert res_a_signup.status_code == 200, f"Signup User A failed: {res_a_signup.text}"
    data_a = res_a_signup.json()
    token_a = data_a["access_token"]
    user_a_id = data_a["user"]["id"]
    session_gen_a = data_a.get("session_generation") or data_a["user"].get("session_generation")
    print(f"User A signed up: ID={user_a_id}, SessionGen={session_gen_a[:8]}...")

    # 4. Cross-tab race condition: Tab 1 tries to submit User B form with User B expected identity
    print("\n[Step 4] Testing cross-tab account mismatch rejection...")
    stale_form_headers = {
        "Authorization": f"Bearer {token_a}",  # Token updated to User A in shared storage
        "X-Expected-User-Id": user_b_id,       # Form was opened under User B
        "X-Session-Generation": session_gen_b   # Belongs to User B's old session
    }
    mismatch_post = requests.post(
        f"{BASE_URL}/candidate/profile",
        headers=stale_form_headers,
        json={
            "name": "Candidate B Stale Overwrite",
            "email": "candidate_b_contact@intervyn.ai",
            "company": "User B Target Company",
            "role": "User B Target Role",
            "resume_text": "User B Stale Resume",
            "jd_text": "User B Stale JD"
        }
    )
    print(f"Stale form submission with expected User B -> HTTP {mismatch_post.status_code} (detail: {mismatch_post.json().get('detail')})")
    assert mismatch_post.status_code == 409, f"Expected 409 Conflict for account mismatch, got {mismatch_post.status_code}"
    print("PASS: Account context mismatch strictly caught and rejected with HTTP 409 Conflict.")

    # 5. Verify User A's profile remains untouched and uncorrupted
    print("\n[Step 5] Verifying User A's profile is intact and invariant login identity preserved...")
    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-Expected-User-Id": user_a_id,
        "X-Session-Generation": session_gen_a
    }
    prof_a_get = requests.get(f"{BASE_URL}/candidate/profile", headers=headers_a)
    assert prof_a_get.status_code == 200
    data_prof_a = prof_a_get.json()
    print("User A profile name:", data_prof_a.get("name"), "email:", data_prof_a.get("email"))
    assert data_prof_a.get("name") != "Candidate B Stale Overwrite", "User A profile was corrupted by User B form!"

    # 6. Test genuine User A profile update & login identity invariance
    print("\n[Step 6] Testing profile update without mutating User.email login identity...")
    update_res = requests.post(
        f"{BASE_URL}/candidate/profile",
        headers=headers_a,
        json={
            "name": "Alice Anderson",
            "email": "alice_personal_contact@domain.com",
            "company": "DeepMind",
            "role": "Research Scientist"
        }
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["name"] == "Alice Anderson"
    assert updated_data["email"] == "alice_personal_contact@domain.com"

    # Verify that the actual login identity user.email is unchanged
    me_check = requests.get(f"{BASE_URL}/auth/me", headers=headers_a)
    assert me_check.status_code == 200
    me_user = me_check.json()
    assert me_user["email"] == user_a_email, f"Login email was mutated! Expected {user_a_email}, got {me_user['email']}"
    print(f"Verified login identity is preserved: {me_user['email']} (did not mutate to contact email)")

    print("\nALL AUTH REVOCATION AND CROSS-TAB SESSION TESTS PASSED 100%!")

if __name__ == "__main__":
    test_auth_and_revocation_lifecycle()
