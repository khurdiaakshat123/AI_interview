import requests
import json
import sys

BASE_URL = "http://localhost:8000/api"

def run_tests():
    print("=================================================================")
    print("STARTING AUTHENTICATION & SECURITY AUDIT TEST SUITE")
    print("=================================================================\n")
    
    passed = 0
    failed = 0

    test_email = "security_test_candidate@intervyn.ai"
    test_password = "SecurePassword123!"
    wrong_password = "TotallyWrongPassword999!"

    # 1. Sign up test user
    try:
        signup_res = requests.post(
            f"{BASE_URL}/auth/signup",
            json={"name": "Security Test User", "email": test_email, "password": test_password}
        )
        if signup_res.status_code == 200:
            print("INFO: Test account created successfully")
        elif signup_res.status_code == 400 and "already registered" in signup_res.text:
            print("INFO: Test account already exists, proceeding with existing account")
        else:
            print(f"WARN: Signup returned {signup_res.status_code}: {signup_res.text}")
    except Exception as e:
        print(f"WARN: Signup request exception: {e}")

    # TEST 1: Intentionally wrong password MUST be rejected with HTTP 401
    try:
        r = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": test_email, "password": wrong_password}
        )
        assert r.status_code == 401, f"Expected 401 for wrong password, got {r.status_code}: {r.text}"
        data = r.json()
        assert "Invalid" in data.get("detail", ""), f"Expected invalid credentials detail, got {data}"
        print("PASS [Security Bug 1]: Wrong password correctly rejected with HTTP 401 Unauthorized")
        passed += 1
    except Exception as e:
        print(f"FAIL [Security Bug 1]: {e}")
        failed += 1

    # TEST 2: Correct password MUST succeed with HTTP 200
    valid_token = None
    user_id = None
    try:
        r = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": test_email, "password": test_password}
        )
        assert r.status_code == 200, f"Expected 200 for correct password, got {r.status_code}: {r.text}"
        data = r.json()
        valid_token = data["access_token"]
        user_id = data["user"]["id"]
        assert valid_token and user_id, "Missing token or user_id in login response"
        print("PASS: Correct password successfully logged in with HTTP 200")
        passed += 1
    except Exception as e:
        print(f"FAIL: Login with correct password failed: {e}")
        failed += 1

    # TEST 3: Login with non-existent email MUST return HTTP 401 (NO auto-creation)
    try:
        r = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": "completely_nonexistent_user_9999@intervyn.ai", "password": "AnyPassword123"}
        )
        assert r.status_code == 401, f"Expected 401 for non-existent user, got {r.status_code}: {r.text}"
        print("PASS: Non-existent user login rejected with HTTP 401 (no auto-creation)")
        passed += 1
    except Exception as e:
        print(f"FAIL: Non-existent user auto-created or allowed: {e}")
        failed += 1

    # TEST 4: Sending email address as Bearer token MUST be rejected with HTTP 401
    try:
        r = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {test_email}"}
        )
        assert r.status_code == 401, f"CRITICAL: Expected 401 when sending email as Bearer token, got {r.status_code}: {r.text}"
        print("PASS [Security Bug 2]: Sending email as Bearer token correctly rejected with HTTP 401")
        passed += 1
    except Exception as e:
        print(f"FAIL [Security Bug 2]: {e}")
        failed += 1

    # TEST 5: Sending invalid arbitrary Bearer token MUST be rejected with HTTP 401
    try:
        r = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": "Bearer totally_invalid_token_xyz"}
        )
        assert r.status_code == 401, f"Expected 401 for invalid token, got {r.status_code}: {r.text}"
        print("PASS: Arbitrary invalid Bearer token correctly rejected with HTTP 401")
        passed += 1
    except Exception as e:
        print(f"FAIL: Invalid Bearer token allowed: {e}")
        failed += 1

    # TEST 6: Sending valid authentic Bearer token MUST succeed and return profile
    if valid_token:
        try:
            r = requests.get(
                f"{BASE_URL}/auth/me",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            assert r.status_code == 200, f"Expected 200 for valid token, got {r.status_code}: {r.text}"
            profile = r.json()
            assert profile["email"] == test_email, f"Expected email {test_email}, got {profile.get('email')}"
            assert profile["id"] == user_id, f"Expected user_id {user_id}, got {profile.get('id')}"
            print(f"PASS: Authentic Bearer token returned user profile ({profile['email']})")
            passed += 1
        except Exception as e:
            print(f"FAIL: Valid Bearer token failed: {e}")
            failed += 1

    print("\n=================================================================")
    print(f"SECURITY AUDIT SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=================================================================")

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
