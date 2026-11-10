import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

def test_api_run(slug, code, lang):
    payload = json.dumps({"code": code, "language": lang}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/practice/lc/questions/{slug}/run",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode())
    return data

print("=" * 60)
print("TESTING LIVE HTTP API RUN ENDPOINTS ACROSS NEW HARNESSES")
print("=" * 60)

# 1. Invert Binary Tree
code_tree = """class Solution:
    def invertTree(self, root: Optional[TreeNode]) -> Optional[TreeNode]:
        if not root:
            return None
        root.left, root.right = self.invertTree(root.right), self.invertTree(root.left)
        return root"""
r_tree = test_api_run("invert-binary-tree", code_tree, "python")
print("1. Live Invert Binary Tree:", r_tree.get("status"), "Passed:", r_tree.get("test_cases_passed"), "/", r_tree.get("total_test_cases"))
assert r_tree.get("status") == "ACCEPTED"

# 2. Move Zeroes
code_zeroes = """class Solution:
    def moveZeroes(self, nums: List[int]) -> None:
        pos = 0
        for n in nums:
            if n != 0:
                nums[pos] = n
                pos += 1
        while pos < len(nums):
            nums[pos] = 0
            pos += 1"""
r_zeroes = test_api_run("move-zeroes", code_zeroes, "python")
print("2. Live Move Zeroes:", r_zeroes.get("status"), "Passed:", r_zeroes.get("test_cases_passed"), "/", r_zeroes.get("total_test_cases"))
assert r_zeroes.get("status") == "ACCEPTED"

# 3. LRU Cache
code_lru = """import collections
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
            self.cache.popitem(last=False)"""
r_lru = test_api_run("lru-cache", code_lru, "python")
print("3. Live LRU Cache:", r_lru.get("status"), "Passed:", r_lru.get("test_cases_passed"), "/", r_lru.get("total_test_cases"))
assert r_lru.get("status") == "ACCEPTED"

# 4. Combine Two Tables (SQL with ORDER BY firstName DESC)
sql_combine = "SELECT p.firstName, p.lastName, a.city, a.state FROM Person p LEFT JOIN Address a ON p.personId = a.personId ORDER BY p.firstName DESC"
r_sql = test_api_run("combine-two-tables", sql_combine, "sql")
print("4. Live Combine Two Tables SQL (DESC):", r_sql.get("status"), "Passed:", r_sql.get("test_cases_passed"), "/", r_sql.get("total_test_cases"))
assert r_sql.get("status") == "ACCEPTED"

# 5. Combine Two Tables in Python with Pandas
code_pandas = """import pandas as pd
def combine_two_tables(person: pd.DataFrame, address: pd.DataFrame) -> pd.DataFrame:
    merged = person.merge(address, on='personId', how='left')
    return merged[['firstName', 'lastName', 'city', 'state']]"""
r_pandas = test_api_run("combine-two-tables", code_pandas, "python")
print("5. Live Combine Two Tables Pandas:", r_pandas.get("status"), "Passed:", r_pandas.get("test_cases_passed"), "/", r_pandas.get("total_test_cases"))
assert r_pandas.get("status") == "ACCEPTED"

print("=" * 60)
print("ALL LIVE ENDPOINTS PASSED WITH 100% SUCCESS!")
print("=" * 60)
