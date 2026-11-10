import sys
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from backend.app.engines.sandbox_runner import SandboxRunner

def test_combine_two_tables():
    print("=== Testing Combine Two Tables SQL Submission Isolation ===")
    p = Path("lc_qbank/questions/database/joins/combine-two-tables.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    test_cases = data["testCases"]
    
    # 1. Negative control: hardcoded answer matching only the public example
    hardcoded_sql = """
    SELECT 'Allen' AS firstName, 'Wang' AS lastName, NULL AS city, NULL AS state
    UNION ALL
    SELECT 'Bob', 'Alice', 'New York City', 'New York'
    """
    res_fake = SandboxRunner.evaluate_code_against_tests(
        user_code=hardcoded_sql,
        test_cases=test_cases,
        approach="",
        timeout_seconds=5.0,
        language="mysql"
    )
    print("Fake Hardcoded Query Status:", res_fake["status"], f"Passed {res_fake.get('test_cases_passed')}/{res_fake.get('total_test_cases')}")
    assert res_fake["status"] == "WRONG_ANSWER", f"Hardcoded query must fail submission tests, got: {res_fake['status']}"
    assert res_fake.get("test_cases_passed") == 1, f"Expected exactly 1 test case passed (the public example), got: {res_fake.get('test_cases_passed')}"
    print("PASS: Hardcoded query rejected by hidden test cases.")

    # 2. Positive control: genuine relational LEFT JOIN solution
    real_sql = """
    SELECT Person.firstName, Person.lastName, Address.city, Address.state
    FROM Person
    LEFT JOIN Address ON Person.personId = Address.personId;
    """
    res_real = SandboxRunner.evaluate_code_against_tests(
        user_code=real_sql,
        test_cases=test_cases,
        approach="",
        timeout_seconds=5.0,
        language="mysql"
    )
    print("Genuine Query Status:", res_real["status"], f"Passed {res_real.get('test_cases_passed')}/{res_real.get('total_test_cases')}")
    assert res_real["status"] == "ACCEPTED", f"Genuine query must pass all test cases, got: {res_real['status']}"
    assert res_real.get("test_cases_passed") == len(test_cases)
    print("PASS: Genuine LEFT JOIN query accepted across all public and hidden test cases.")

def test_duplicate_emails():
    print("\n=== Testing Duplicate Emails SQL Submission Isolation ===")
    p = Path("lc_qbank/questions/database/null-handling/duplicate-emails.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    test_cases = data["testCases"]

    # 1. Negative control: hardcoded answer matching only the public example
    hardcoded_sql = "SELECT 'a@b.com' AS Email;"
    res_fake = SandboxRunner.evaluate_code_against_tests(
        user_code=hardcoded_sql,
        test_cases=test_cases,
        approach="",
        timeout_seconds=5.0,
        language="mysql"
    )
    print("Fake Hardcoded Query Status:", res_fake["status"], f"Passed {res_fake.get('test_cases_passed')}/{res_fake.get('total_test_cases')}")
    assert res_fake["status"] == "WRONG_ANSWER", f"Hardcoded query must fail submission tests, got: {res_fake['status']}"
    assert res_fake.get("test_cases_passed") == 1
    print("PASS: Hardcoded query rejected by hidden test cases.")

    # 2. Positive control: genuine aggregation solution
    real_sql = """
    SELECT email AS Email
    FROM Person
    GROUP BY email
    HAVING COUNT(email) > 1;
    """
    res_real = SandboxRunner.evaluate_code_against_tests(
        user_code=real_sql,
        test_cases=test_cases,
        approach="",
        timeout_seconds=5.0,
        language="mysql"
    )
    print("Genuine Query Status:", res_real["status"], f"Passed {res_real.get('test_cases_passed')}/{res_real.get('total_test_cases')}")
    assert res_real["status"] == "ACCEPTED", f"Genuine query must pass all test cases, got: {res_real['status']}"
    assert res_real.get("test_cases_passed") == len(test_cases)
    print("PASS: Genuine GROUP BY query accepted across all public and hidden test cases.")

if __name__ == "__main__":
    test_combine_two_tables()
    test_duplicate_emails()
    print("\nALL SQL SUBMISSION AND HARDCODING ISOLATION TESTS PASSED 100%!")
