import json
from backend.app.engines.sql_runner import SQLRunner

test_cases_combine = [{
    "input": json.dumps({
        "headers": {"Person": ["personId", "lastName", "firstName"], "Address": ["addressId", "personId", "city", "state"]},
        "rows": {"Person": [[1, "Wang", "Allen"], [2, "Alice", "Bob"]], "Address": [[1, 2, "New York City", "New York"], [2, 3, "Leetcode", "California"]]}
    }),
    "expected_output": """+-----------+----------+---------------+----------+
| firstName | lastName | city          | state    |
+-----------+----------+---------------+----------+
| Allen     | Wang     | Null          | Null     |
| Bob       | Alice    | New York City | New York |
+-----------+----------+---------------+----------+""",
    "is_ordered": False
}]

sql_combine = """
SELECT p.firstName, p.lastName, a.city, a.state
FROM Person p
LEFT JOIN Address a ON p.personId = a.personId
ORDER BY p.firstName DESC
"""

res = SQLRunner.evaluate(user_code=sql_combine, test_cases=test_cases_combine)
print("Combine Two Tables DESC status:", res["status"])
assert res["status"] == "ACCEPTED", f"Expected ACCEPTED, got {res}"

test_cases_rank = [{
    "input": json.dumps({
        "headers": {"Scores": ["id", "score"]},
        "rows": {"Scores": [[1, 3.50], [2, 3.65], [3, 4.00], [4, 3.85], [5, 4.00], [6, 3.65]]}
    }),
    "expected_output": """+-------+------+
| score | rank |
+-------+------+
| 4.00  | 1    |
| 4.00  | 1    |
| 3.85  | 2    |
| 3.65  | 3    |
| 3.65  | 3    |
| 3.50  | 4    |
+-------+------+""",
    "is_ordered": True
}]

sql_rank_wrong = "SELECT score, DENSE_RANK() OVER (ORDER BY score ASC) as rank FROM Scores ORDER BY score ASC"
res_rank_wrong = SQLRunner.evaluate(user_code=sql_rank_wrong, test_cases=test_cases_rank)
print("Rank Scores ASC (wrong) status:", res_rank_wrong["status"])
assert res_rank_wrong["status"] == "WRONG_ANSWER"

sql_rank_right = "SELECT score, DENSE_RANK() OVER (ORDER BY score DESC) as rank FROM Scores ORDER BY score DESC"
res_rank_right = SQLRunner.evaluate(user_code=sql_rank_right, test_cases=test_cases_rank)
print("Rank Scores DESC (correct) status:", res_rank_right["status"])
assert res_rank_right["status"] == "ACCEPTED"

print("BOTH COMBINE TWO TABLES AND RANK SCORES PASSED WITH 100% PRECISION!")
