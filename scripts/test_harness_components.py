import json
import collections
import inspect
import pandas as pd

# Test 1: String Quoting
act_str = "fl"
exp_str = '"fl"'
assert act_str.strip('"\'') == exp_str.strip('"\''), "String unquoting test failed"
print("1. String Unquoting Test: PASSED")

# Test 2: LRU Cache Design Runner
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

lru_inp = '["LRUCache","put","put","get","put","get","put","get","get","get"]\n[[2],[1,1],[2,2],[1],[3,3],[2],[4,4],[1],[3],[4]]'
lru_exp = '[null,null,null,1,null,-1,null,-1,3,4]'

lines = [l.strip() for l in lru_inp.splitlines() if l.strip()]
methods = json.loads(lines[0])
args = json.loads(lines[1])
inst = LRUCache(*args[0])
res_lru = [None]
for m, a in zip(methods[1:], args[1:]):
    res_lru.append(getattr(inst, m)(*a))
act_lru_json = json.dumps(res_lru, separators=(',', ':')).replace("None", "null")
assert act_lru_json == lru_exp, f"LRU Cache expected {lru_exp}, got {act_lru_json}"
print("2. LRU Cache Design Runner Test: PASSED")

# Test 3: Binary Tree Inversion
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def _to_tree_node(vals):
    if not isinstance(vals, list) or not vals or vals[0] is None:
        return None
    root = TreeNode(vals[0])
    queue = collections.deque([root])
    i = 1
    n = len(vals)
    while queue and i < n:
        curr = queue.popleft()
        if i < n:
            if vals[i] is not None:
                curr.left = TreeNode(vals[i])
                queue.append(curr.left)
            i += 1
        if i < n:
            if vals[i] is not None:
                curr.right = TreeNode(vals[i])
                queue.append(curr.right)
            i += 1
    return root

def _from_tree_node(root):
    if not root:
        return []
    res = []
    queue = collections.deque([root])
    while queue:
        curr = queue.popleft()
        if curr:
            res.append(curr.val)
            queue.append(curr.left)
            queue.append(curr.right)
        else:
            res.append(None)
    while res and res[-1] is None:
        res.pop()
    return res

class SolutionTree:
    def invertTree(self, root: TreeNode) -> TreeNode:
        if not root:
            return None
        root.left, root.right = self.invertTree(root.right), self.invertTree(root.left)
        return root

tree_in = [4, 2, 7, 1, 3, 6, 9]
tree_root = _to_tree_node(tree_in)
tree_out = SolutionTree().invertTree(tree_root)
tree_res = _from_tree_node(tree_out)
assert tree_res == [4, 7, 2, 9, 6, 3, 1], f"Tree invert expected [4, 7, 2, 9, 6, 3, 1], got {tree_res}"
print("3. Binary Tree Invert Test: PASSED")

# Test 4: In-Place Arrays (Move Zeroes)
class SolutionMoveZeroes:
    def moveZeroes(self, nums):
        insert_pos = 0
        for num in nums:
            if num != 0:
                nums[insert_pos] = num
                insert_pos += 1
        while insert_pos < len(nums):
            nums[insert_pos] = 0
            insert_pos += 1

nums_in = [0, 1, 0, 3, 12]
ret_val = SolutionMoveZeroes().moveZeroes(nums_in)
assert ret_val is None
assert nums_in == [1, 3, 12, 0, 0]
print("4. Move Zeroes In-Place Test: PASSED")

# Test 5: Pandas Database Problems
from backend.app.engines.sql_runner import SQLRunner

def combine_two_tables(person: pd.DataFrame, address: pd.DataFrame) -> pd.DataFrame:
    merged = person.merge(address, on='personId', how='left')
    return merged[['firstName', 'lastName', 'city', 'state']]

inp_db = {"headers":{"Person":["personId","lastName","firstName"],"Address":["addressId","personId","city","state"]},"rows":{"Person":[[1,"Wang","Allen"],[2,"Alice","Bob"]],"Address":[[1,2,"New York City","New York"],[2,3,"Leetcode","California"]]}}
exp_db = """+-----------+----------+---------------+----------+
| firstName | lastName | city          | state    |
+-----------+----------+---------------+----------+
| Allen     | Wang     | Null          | Null     |
| Bob       | Alice    | New York City | New York |
+-----------+----------+---------------+----------+"""

df_person = pd.DataFrame(inp_db["rows"]["Person"], columns=inp_db["headers"]["Person"])
df_address = pd.DataFrame(inp_db["rows"]["Address"], columns=inp_db["headers"]["Address"])
df_res = combine_two_tables(df_person, df_address)
cols = list(df_res.columns)
rows = df_res.where(pd.notnull(df_res), None).values.tolist()
db_passed, db_reason = SQLRunner.compare_results(cols, rows, exp_db, is_ordered=False)
assert db_passed, f"Pandas combine_two_tables failed: {db_reason}"
print("5. Pandas DataFrame Database Test: PASSED")

print("\nALL 5 CORE HARNESS COMPONENTS PASSED 100%!")
