import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from backend.app.engines.lc_service import LCQuestionService, get_complexity_for_question

def test_complexity_bounds():
    print("=== Testing Question Bank Complexity Guidance ===")
    
    # 1. Median of Two Sorted Arrays
    t1, s1 = get_complexity_for_question("divide-and-conquer", "Hard", slug_or_id="median-of-two-sorted-arrays", category="dsa")
    print("Median of Two Sorted Arrays:", t1, "/", s1)
    assert t1 == "O(log(min(m, n)))", f"Expected O(log(min(m, n))), got {t1}"
    assert s1 == "O(1)", f"Expected O(1), got {s1}"

    # 2. Container With Most Water
    t2, s2 = get_complexity_for_question("greedy", "Medium", slug_or_id="container-with-most-water", category="dsa")
    print("Container With Most Water:", t2, "/", s2)
    assert t2 == "O(n)", f"Expected O(n), got {t2}"
    assert s2 == "O(1)", f"Expected O(1), got {s2}"

    # 3. Database: Combine Two Tables
    t3, s3 = get_complexity_for_question("joins", "Easy", slug_or_id="combine-two-tables", category="database")
    print("Combine Two Tables (Database):", t3, "/", s3)
    assert t3 is None and s3 is None, f"Database questions must not have Big-O complexity, got {t3}, {s3}"

    # 4. Database: Duplicate Emails
    t4, s4 = get_complexity_for_question("null-handling", "Easy", slug_or_id="duplicate-emails", category="database")
    print("Duplicate Emails (Database):", t4, "/", s4)
    assert t4 is None and s4 is None, f"Database questions must not have Big-O complexity, got {t4}, {s4}"

    # 5. Generic unverified problem
    t5, s5 = get_complexity_for_question("arrays", "Hard", slug_or_id="unknown-arbitrary-hard-problem", category="dsa")
    print("Unverified Problem:", t5, "/", s5)
    assert t5 == "Unverified" and s5 == "Unverified", f"Unverified problems must return Unverified, got {t5}, {s5}"

    # 6. Service get_question check
    LCQuestionService.initialize()
    detail_median = LCQuestionService.get_question("median-of-two-sorted-arrays", None)
    assert detail_median is not None
    print("Detail Median Time:", detail_median["timeComplexity"], "Space:", detail_median["spaceComplexity"])
    assert detail_median["timeComplexity"] == "O(log(min(m, n)))"
    assert detail_median["spaceComplexity"] == "O(1)"
    assert "binary search" in detail_median["approach"].lower()

    detail_db = LCQuestionService.get_question("combine-two-tables", None)
    assert detail_db is not None
    print("Detail DB Time:", detail_db["timeComplexity"], "Space:", detail_db["spaceComplexity"])
    assert detail_db["timeComplexity"] is None
    assert detail_db["spaceComplexity"] is None

    # 7. Audit full question catalog
    all_qs = LCQuestionService._questions_list
    total = len(all_qs)
    db_count = sum(1 for q in all_qs if q.get("category") == "database")
    verified_count = sum(1 for q in all_qs if q.get("timeComplexity") and q.get("timeComplexity") != "Unverified" and q.get("category") != "database")
    unverified_count = sum(1 for q in all_qs if q.get("timeComplexity") == "Unverified")

    print("\n=== Question Bank Audit Report ===")
    print(f"Total Questions: {total}")
    print(f"Database Questions (No Big-O): {db_count}")
    print(f"Verified Optimal Algorithmic Questions: {verified_count}")
    print(f"Explicitly Unverified Algorithmic Questions: {unverified_count}")
    assert db_count > 0
    assert verified_count >= 20
    print("ALL COMPLEXITY GUIDANCE AND QUESTION BANK AUDIT CHECKS PASSED 100%!")

if __name__ == "__main__":
    test_complexity_bounds()
