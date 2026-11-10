import sys, os
sys.path.insert(0, r'C:\Users\aksha\Desktop\AI_interview')
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

print("=== 1. Test Google Auth Bypass Rejection ===")
res1 = client.post("/api/auth/google", json={"credential": "google_simulated", "user_info": {"email": "victim@test.com"}})
print("Status:", res1.status_code, res1.json())
assert res1.status_code == 401, "Google simulated auth must be rejected with 401!"
res1_b = client.post("/api/auth/google", json={"credential": "demo_invalid_token", "user_info": {"email": "victim@test.com"}})
assert res1_b.status_code == 401, "Demo token must be rejected with 401!"
print("PASSED: Issue 1 (Google Auth Bypass rejected)")

print("\n=== 2. Test Resume Leak Prevention ===")
res2 = client.get("/api/interview/resumes/sample")
print("Status:", res2.status_code)
sample_data = res2.json()
print("Candidate Name:", sample_data.get("candidate_name"))
assert "Sample" in sample_data.get("candidate_name", ""), "Sample resume must be generic template!"
assert sample_data.get("candidate_email") == "sample.candidate@intervyn.ai", "Sample email must be sample.candidate@intervyn.ai!"
print("PASSED: Issue 2 (Sample resume anonymized, no user resume leak)")

print("\n=== 3. Test Admin Review Queue Authentication ===")
res3_unauth = client.get("/api/admin/review-queue")
print("Unauth status:", res3_unauth.status_code)
assert res3_unauth.status_code in [401, 403], "Unauthenticated admin request must be rejected!"
res3_approve = client.post("/api/admin/review-queue/test-id/approve")
assert res3_approve.status_code in [401, 403], "Unauthenticated approve must be rejected!"
print("PASSED: Issue 5 (Admin review queue protected)")

print("\n=== 4. Test Image Mount /lc_assets ===")
res4 = client.get("/lc_assets/add-two-numbers-1.jpg")
print("Image status:", res4.status_code, "Length:", len(res4.content))
assert res4.status_code == 200, "Image must return 200 OK!"
assert len(res4.content) > 1000, "Image content must be present!"
print("PASSED: Issue 14 (Image mount working)")

print("\n=== 5. Test Role Profile Evidence for Fictional Company ===")
from backend.app.agents.role_profile_agent import RoleProfileAgent
fake_profile = RoleProfileAgent.generate_profile(
    company="Fictional Mystery Startup 99",
    role="Backend Engineer",
    jd_text="Build scalable web services."
)
for ev in fake_profile.get("evidence", []):
    print("Evidence for fictional company:", ev.get("source"), "| Trust:", ev.get("trust_level"), "| Fact:", ev.get("fact")[:60])
    assert ev.get("trust_level") in ["LOW", "MEDIUM"], "Fictional company must NOT have HIGH trust hiring claims!"
    assert "Past Hiring Windows" not in ev.get("source", ""), "Fictional company must NOT claim past candidate hiring data!"
print("PASSED: Issue 10 (Role profile does not invent evidence for fictional companies)")

print("\n=== 6. Test LC Service Add Two Numbers Complexity ===")
from backend.app.engines.lc_service import LCQuestionService
from backend.app.database import SessionLocal
db = SessionLocal()
LCQuestionService._is_initialized = False
LCQuestionService.initialize()
q2 = LCQuestionService.get_question("2", db=db)
print("Question 2:", q2.get("title"), "| Subcategory:", q2.get("subcategory"), "| Time Comp:", q2.get("timeComplexity"))
assert q2.get("subcategory") == "linked-lists", "Add Two Numbers must be in linked-lists!"
assert q2.get("timeComplexity") == "O(max(m, n))", "Add Two Numbers must have linear O(max(m, n)) complexity!"
db.close()
print("PASSED: Issue 13 (Add Two Numbers complexity correct)")

print("\n=== ALL TESTED BACKEND FIXES VERIFIED 100% SUCCESSFULLY! ===")
