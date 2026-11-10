import json
import os
import sys

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath("."))

from backend.app.engines.sandbox_runner import SandboxRunner
from backend.app.engines.sql_runner import SQLRunner

passed_all = True

print("=" * 60)
print("RUNNING MASTER VERIFICATION FOR ALL 7 REPORTED ISSUES")
print("=" * 60)

# -------------------------------------------------------------
# ISSUE 1: String Quoting (To Lower Case / Longest Common Prefix)
# -------------------------------------------------------------
print("\n[Issue 1] Verifying String Quoting (fl vs \"fl\")...")
code_prefix = """
class Solution:
    def longestCommonPrefix(self, strs: list[str]) -> str:
        if not strs:
            return ""
        prefix = strs[0]
        for s in strs[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        return prefix
"""
tcs_prefix = [
    {"input": '["flower","flow","flight"]', "expected_output": '"fl"'},
    {"input": '["dog","racecar","car"]', "expected_output": '""'}
]
res_prefix = SandboxRunner.evaluate_code(code_prefix, "python", tcs_prefix)
assert res_prefix["status"] == "ACCEPTED", f"Issue 1 failed: {res_prefix}"
print(f"  -> PASSED: Status = {res_prefix['status']} ({res_prefix['test_cases_passed']}/{res_prefix['total_test_cases']})")

# -------------------------------------------------------------
# ISSUE 4: LRU Cache (Design Problem)
# -------------------------------------------------------------
print("\n[Issue 4] Verifying LRU Cache Design Runner...")
with open("lc_qbank/questions/dsa/linked-lists/lru-cache.json", "r", encoding="utf-8") as f:
    lru_data = json.load(f)
lru_tcs = lru_data.get("testCases", [])

code_lru = """
import collections
class LRUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.cache = collections.OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.cap:
            self.cache.popitem(last=False)
"""
res_lru = SandboxRunner.evaluate_code(code_lru, "python", lru_tcs)
assert res_lru["status"] == "ACCEPTED", f"Issue 4 failed: {res_lru}"
print(f"  -> PASSED: Status = {res_lru['status']} ({res_lru['test_cases_passed']}/{res_lru['total_test_cases']} test cases passed!)")

# -------------------------------------------------------------
# ISSUE 5: Binary Trees (Invert Binary Tree)
# -------------------------------------------------------------
print("\n[Issue 5] Verifying Binary Tree Inversion (TreeNode)...")
with open("lc_qbank/questions/dsa/graphs/invert-binary-tree.json", "r", encoding="utf-8") as f:
    tree_data = json.load(f)
tree_tcs = tree_data.get("testCases", [])

code_tree = """
class Solution:
    def invertTree(self, root: Optional[TreeNode]) -> Optional[TreeNode]:
        if not root:
            return None
        root.left, root.right = self.invertTree(root.right), self.invertTree(root.left)
        return root
"""
res_tree = SandboxRunner.evaluate_code(code_tree, "python", tree_tcs)
assert res_tree["status"] == "ACCEPTED", f"Issue 5 failed: {res_tree}"
print(f"  -> PASSED: Status = {res_tree['status']} ({res_tree['test_cases_passed']}/{res_tree['total_test_cases']} test cases passed!)")

# -------------------------------------------------------------
# ISSUE 6: In-place Arrays (Move Zeroes)
# -------------------------------------------------------------
print("\n[Issue 6] Verifying In-Place Array Mutation (Move Zeroes)...")
with open("lc_qbank/questions/dsa/two-pointers/move-zeroes.json", "r", encoding="utf-8") as f:
    zeroes_data = json.load(f)
zeroes_tcs = zeroes_data.get("testCases", [])

code_zeroes = """
class Solution:
    def moveZeroes(self, nums: List[int]) -> None:
        insert_pos = 0
        for num in nums:
            if num != 0:
                nums[insert_pos] = num
                insert_pos += 1
        while insert_pos < len(nums):
            nums[insert_pos] = 0
            insert_pos += 1
"""
res_zeroes = SandboxRunner.evaluate_code(code_zeroes, "python", zeroes_tcs)
assert res_zeroes["status"] == "ACCEPTED", f"Issue 6 failed: {res_zeroes}"
print(f"  -> PASSED: Status = {res_zeroes['status']} ({res_zeroes['test_cases_passed']}/{res_zeroes['total_test_cases']} test cases passed!)")

# -------------------------------------------------------------
# ISSUE 7: C++ and Java Reversed Indices (Two Sum)
# -------------------------------------------------------------
print("\n[Issue 7] Verifying C++ and Java Reversed Two Sum Indices...")
two_sum_tcs = [
    {"input": "[2, 7, 11, 15], 9", "expected_output": "[0, 1]"},
    {"input": "[3, 2, 4], 6", "expected_output": "[1, 2]"},
    {"input": "[3, 3], 6", "expected_output": "[0, 1]"}
]

code_cpp_reversed = """
#include <vector>
using namespace std;
class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        for (int i = 0; i < (int)nums.size(); i++) {
            for (int j = i + 1; j < (int)nums.size(); j++) {
                if (nums[i] + nums[j] == target) {
                    return {j, i}; // Intentionally reversed order!
                }
            }
        }
        return {};
    }
};
"""
res_cpp = SandboxRunner.evaluate_code(code_cpp_reversed, "cpp", two_sum_tcs)
assert res_cpp["status"] == "ACCEPTED", f"Issue 7 (C++) failed: {res_cpp}"
print(f"  -> C++ PASSED: Status = {res_cpp['status']} ({res_cpp['test_cases_passed']}/{res_cpp['total_test_cases']})")

code_java_reversed = """
class Solution {
    public int[] twoSum(int[] nums, int target) {
        for (int i = 0; i < nums.length; i++) {
            for (int j = i + 1; j < nums.length; j++) {
                if (nums[i] + nums[j] == target) {
                    return new int[]{j, i}; // Intentionally reversed order!
                }
            }
        }
        return new int[]{};
    }
}
"""
res_java = SandboxRunner.evaluate_code(code_java_reversed, "java", two_sum_tcs)
assert res_java["status"] == "ACCEPTED", f"Issue 7 (Java) failed: {res_java}"
print(f"  -> Java PASSED: Status = {res_java['status']} ({res_java['test_cases_passed']}/{res_java['total_test_cases']})")

# -------------------------------------------------------------
# ISSUE 8: SQL Ordering (Combine Two Tables)
# -------------------------------------------------------------
print("\n[Issue 8] Verifying SQL Ordering (Combine Two Tables & Rank Scores)...")
tcs_combine = [{
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
sql_combine = "SELECT p.firstName, p.lastName, a.city, a.state FROM Person p LEFT JOIN Address a ON p.personId = a.personId ORDER BY p.firstName DESC"
res_sql_combine = SQLRunner.evaluate(user_code=sql_combine, test_cases=tcs_combine)
assert res_sql_combine["status"] == "ACCEPTED", f"Issue 8 (Combine) failed: {res_sql_combine}"
print(f"  -> Combine Two Tables (ORDER BY DESC on any-order problem): ACCEPTED!")

tcs_rank = [{
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
res_rank_wrong = SQLRunner.evaluate(user_code=sql_rank_wrong, test_cases=tcs_rank)
assert res_rank_wrong["status"] == "WRONG_ANSWER", "Issue 8 (Rank Scores wrong order should fail)"
print(f"  -> Rank Scores (ASC wrong order correctly rejected): WRONG_ANSWER!")

# -------------------------------------------------------------
# ISSUE 9: Pandas Database Problems
# -------------------------------------------------------------
print("\n[Issue 9] Verifying Pandas Database Harness...")
code_pandas = """
import pandas as pd
def combine_two_tables(person: pd.DataFrame, address: pd.DataFrame) -> pd.DataFrame:
    merged = person.merge(address, on='personId', how='left')
    return merged[['firstName', 'lastName', 'city', 'state']]
"""
res_pandas = SandboxRunner.evaluate_code(code_pandas, "python", tcs_combine)
assert res_pandas["status"] == "ACCEPTED", f"Issue 9 failed: {res_pandas}"
print(f"  -> Pandas combine_two_tables: ACCEPTED ({res_pandas['test_cases_passed']}/{res_pandas['total_test_cases']})")

print("\n" + "=" * 60)
print("ALL 7 REPORTED ISSUES VERIFIED AND PASSING 100%!")
print("=" * 60)
