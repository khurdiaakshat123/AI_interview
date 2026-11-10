# -*- coding: utf-8 -*-
"""
Master Regression Test Suite for Bugs 5 through 9:
- Bug 5: LRU Cache in Java & JavaScript (Stateful design problems, constructor-and-operations, isolated state, broken rejected)
- Bug 6: Tree inputs/outputs in Java & JavaScript (TreeNode deserialization, serialization, [], [0], asymmetric trees)
- Bug 7: In-place array problems in Java & JavaScript (Move Zeroes, Rotate Image, void return, no undefined)
- Bug 8: Debugger unsupported language contract (NOT_SUPPORTED status, explanation message, Python tracing)
- Bug 9: Algorithmic complexity guidance (Rotate Image O(n²)/O(1), approach text, single source of truth)
"""

import sys
import os
import json

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.engines.sandbox_runner import SandboxRunner
from backend.app.engines.debug_tracer import DebugTracer
from backend.app.engines.lc_service import LCQuestionService

print("=" * 70)
print("RUNNING MASTER REGRESSION TESTS FOR BUGS 5 THROUGH 9")
print("=" * 70)

# ==============================================================================
# BUG 5: LRU Cache in Java and JavaScript
# ==============================================================================
print("\n[BUG 5] Testing LRU Cache (Java & JavaScript)...")

java_lru_code = """
import java.util.*;

class LRUCache {
    class Node {
        int key, val;
        Node prev, next;
        Node(int k, int v) { key = k; val = v; }
    }
    
    private final int capacity;
    private final Map<Integer, Node> map = new HashMap<>();
    private final Node head = new Node(0, 0);
    private final Node tail = new Node(0, 0);

    public LRUCache(int capacity) {
        this.capacity = capacity;
        head.next = tail;
        tail.prev = head;
    }

    private void remove(Node node) {
        node.prev.next = node.next;
        node.next.prev = node.prev;
    }

    private void insert(Node node) {
        node.next = head.next;
        node.next.prev = node;
        head.next = node;
        node.prev = head;
    }

    public int get(int key) {
        if (!map.containsKey(key)) return -1;
        Node node = map.get(key);
        remove(node);
        insert(node);
        return node.val;
    }

    public void put(int key, int value) {
        if (map.containsKey(key)) {
            remove(map.get(key));
        }
        if (map.size() == capacity) {
            map.remove(tail.prev.key);
            remove(tail.prev);
        }
        Node node = new Node(key, value);
        insert(node);
        map.put(key, node);
    }
}
"""

tc_lru_canonical = {
    "input": '["LRUCache","put","put","get","put","get","put","get","get","get"]\n[[2],[1,1],[2,2],[1],[3,3],[2],[4,4],[1],[3],[4]]',
    "expected_output": "[null,null,null,1,null,-1,null,-1,3,4]",
    "execution_mode": "stateful_class"
}

tc_lru_cap1 = {
    "input": '["LRUCache","put","get","put","get"]\n[[1],[10,100],[10],[20,200],[10]]',
    "expected_output": "[null,null,100,null,-1]",
    "execution_mode": "stateful_class"
}

tc_lru_update = {
    "input": '["LRUCache","put","put","get"]\n[[2],[1,10],[1,20],[1]]',
    "expected_output": "[null,null,null,20]",
    "execution_mode": "stateful_class"
}

# 1. Java LRU Cache
res_java_lru = SandboxRunner.evaluate_code(java_lru_code, "java", [tc_lru_canonical, tc_lru_cap1, tc_lru_update])
print(f"Java LRU Cache: {res_java_lru.get('status')} ({res_java_lru.get('test_cases_passed')}/{res_java_lru.get('total_test_cases')})")
assert res_java_lru.get("status") == "ACCEPTED", f"Java LRU Cache failed: {res_java_lru}"

# 2. Broken Java LRU Cache (must be rejected)
java_broken_lru = """
class LRUCache {
    public LRUCache(int capacity) {}
    public int get(int key) { return -1; }
    public void put(int key, int value) {}
}
"""
res_java_broken = SandboxRunner.evaluate_code(java_broken_lru, "java", [tc_lru_canonical])
print(f"Java Broken LRU Cache Rejected: {res_java_broken.get('status') == 'WRONG_ANSWER'}")
assert res_java_broken.get("status") == "WRONG_ANSWER", f"Broken Java LRU must be WRONG_ANSWER, got: {res_java_broken}"

# 3. JS LRU Cache (Prototype style)
js_lru_prototype = """
/**
 * @param {number} capacity
 */
var LRUCache = function(capacity) {
    this.capacity = capacity;
    this.cache = new Map();
};

LRUCache.prototype.get = function(key) {
    if (!this.cache.has(key)) return -1;
    const val = this.cache.get(key);
    this.cache.delete(key);
    this.cache.set(key, val);
    return val;
};

LRUCache.prototype.put = function(key, value) {
    if (this.cache.has(key)) {
        this.cache.delete(key);
    } else if (this.cache.size >= this.capacity) {
        const oldestKey = this.cache.keys().next().value;
        this.cache.delete(oldestKey);
    }
    this.cache.set(key, value);
};
"""
res_js_lru = SandboxRunner.evaluate_code(js_lru_prototype, "javascript", [tc_lru_canonical, tc_lru_cap1, tc_lru_update])
print(f"JS LRU Cache (Prototype): {res_js_lru.get('status')} ({res_js_lru.get('test_cases_passed')}/{res_js_lru.get('total_test_cases')})")
assert res_js_lru.get("status") == "ACCEPTED", f"JS LRU Cache (Prototype) failed: {res_js_lru}"

# 4. JS LRU Cache (ES6 Class style)
js_lru_class = """
class LRUCache {
    constructor(capacity) {
        this.capacity = capacity;
        this.cache = new Map();
    }
    get(key) {
        if (!this.cache.has(key)) return -1;
        const val = this.cache.get(key);
        this.cache.delete(key);
        this.cache.set(key, val);
        return val;
    }
    put(key, value) {
        if (this.cache.has(key)) {
            this.cache.delete(key);
        } else if (this.cache.size >= this.capacity) {
            const oldest = this.cache.keys().next().value;
            this.cache.delete(oldest);
        }
        this.cache.set(key, value);
    }
}
"""
res_js_class = SandboxRunner.evaluate_code(js_lru_class, "javascript", [tc_lru_canonical, tc_lru_cap1, tc_lru_update])
print(f"JS LRU Cache (ES6 Class): {res_js_class.get('status')} ({res_js_class.get('test_cases_passed')}/{res_js_class.get('total_test_cases')})")
assert res_js_class.get("status") == "ACCEPTED", f"JS LRU Cache (Class) failed: {res_js_class}"

# 5. Broken JS LRU Cache (must be rejected)
js_broken_lru = """
var LRUCache = function(capacity) {};
LRUCache.prototype.get = function(key) { return -1; };
LRUCache.prototype.put = function(key, value) {};
"""
res_js_broken = SandboxRunner.evaluate_code(js_broken_lru, "javascript", [tc_lru_canonical])
print(f"JS Broken LRU Cache Rejected: {res_js_broken.get('status') == 'WRONG_ANSWER'}")
assert res_js_broken.get("status") == "WRONG_ANSWER", f"Broken JS LRU must be WRONG_ANSWER, got: {res_js_broken}"

# ==============================================================================
# BUG 6: Tree inputs/outputs in Java and JavaScript
# ==============================================================================
print("\n[BUG 6] Testing Tree Inputs & Outputs (Java & JavaScript)...")

tcs_tree = [
    {"input": "[4,2,7,1,3,6,9]", "expected_output": "[4,7,2,9,6,3,1]"},
    {"input": "[2,1,3]", "expected_output": "[2,3,1]"},
    {"input": "[]", "expected_output": "[]"},
    {"input": "[0]", "expected_output": "[0]"},
    {"input": "[1,2,null]", "expected_output": "[1,null,2]"}
]

# 1. Java Invert Binary Tree
java_tree_code = """
class Solution {
    public TreeNode invertTree(TreeNode root) {
        if (root == null) return null;
        TreeNode tmp = root.left;
        root.left = invertTree(root.right);
        root.right = invertTree(tmp);
        return root;
    }
}
"""
res_java_tree = SandboxRunner.evaluate_code(java_tree_code, "java", tcs_tree)
print(f"Java Tree: {res_java_tree.get('status')} ({res_java_tree.get('test_cases_passed')}/{res_java_tree.get('total_test_cases')})")
assert res_java_tree.get("status") == "ACCEPTED", f"Java Tree failed: {res_java_tree}"

# 2. JavaScript Invert Binary Tree
js_tree_code = """
/**
 * @param {TreeNode} root
 * @return {TreeNode}
 */
var invertTree = function(root) {
    if (!root) return null;
    var tmp = root.left;
    root.left = invertTree(root.right);
    root.right = invertTree(tmp);
    return root;
};
"""
res_js_tree = SandboxRunner.evaluate_code(js_tree_code, "javascript", tcs_tree)
print(f"JS Tree: {res_js_tree.get('status')} ({res_js_tree.get('test_cases_passed')}/{res_js_tree.get('total_test_cases')})")
assert res_js_tree.get("status") == "ACCEPTED", f"JS Tree failed: {res_js_tree}"

# 3. Python Invert Binary Tree (remains working)
py_tree_code = """
class Solution:
    def invertTree(self, root):
        if not root:
            return None
        root.left, root.right = self.invertTree(root.right), self.invertTree(root.left)
        return root
"""
res_py_tree = SandboxRunner.evaluate_code(py_tree_code, "python", tcs_tree, timeout_seconds=8.0)
print(f"Python Tree: {res_py_tree.get('status')} ({res_py_tree.get('test_cases_passed')}/{res_py_tree.get('total_test_cases')})")
assert res_py_tree.get("status") == "ACCEPTED", f"Python Tree failed: {res_py_tree}"

# ==============================================================================
# BUG 7: In-place Array Mutations in Java and JavaScript
# ==============================================================================
print("\n[BUG 7] Testing In-place Array Mutations (Move Zeroes, Rotate Image)...")

tcs_zeroes = [
    {"input": "[0,1,0,3,12]", "expected_output": "[1,3,12,0,0]", "output_source": "mutated_arg_0"},
    {"input": "[0]", "expected_output": "[0]", "output_source": "mutated_arg_0"},
    {"input": "[1,2,3]", "expected_output": "[1,2,3]", "output_source": "mutated_arg_0"}
]

# 1. Java Move Zeroes (void return, in-place mutated nums)
java_zeroes_code = """
class Solution {
    public void moveZeroes(int[] nums) {
        int pos = 0;
        for (int i = 0; i < nums.length; i++) {
            if (nums[i] != 0) {
                nums[pos++] = nums[i];
            }
        }
        while (pos < nums.length) {
            nums[pos++] = 0;
        }
    }
}
"""
res_java_zeroes = SandboxRunner.evaluate_code(java_zeroes_code, "java", tcs_zeroes)
print(f"Java Move Zeroes: {res_java_zeroes.get('status')} ({res_java_zeroes.get('test_cases_passed')}/{res_java_zeroes.get('total_test_cases')})")
assert res_java_zeroes.get("status") == "ACCEPTED", f"Java Move Zeroes failed: {res_java_zeroes}"

# 2. JS Move Zeroes (void return, in-place mutated nums)
js_zeroes_code = """
/**
 * @param {number[]} nums
 * @return {void} Do not return anything, modify nums in-place instead.
 */
var moveZeroes = function(nums) {
    let pos = 0;
    for (let i = 0; i < nums.length; i++) {
        if (nums[i] !== 0) {
            nums[pos++] = nums[i];
        }
    }
    while (pos < nums.length) {
        nums[pos++] = 0;
    }
};
"""
res_js_zeroes = SandboxRunner.evaluate_code(js_zeroes_code, "javascript", tcs_zeroes)
print(f"JS Move Zeroes: {res_js_zeroes.get('status')} ({res_js_zeroes.get('test_cases_passed')}/{res_js_zeroes.get('total_test_cases')})")
assert res_js_zeroes.get("status") == "ACCEPTED", f"JS Move Zeroes failed: {res_js_zeroes}"

# 3. JS Rotate Image (2D in-place mutation)
js_rotate_code = """
/**
 * @param {number[][]} matrix
 * @return {void} Do not return anything, modify matrix in-place instead.
 */
var rotate = function(matrix) {
    const n = matrix.length;
    // Transpose
    for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
            const tmp = matrix[i][j];
            matrix[i][j] = matrix[j][i];
            matrix[j][i] = tmp;
        }
    }
    // Reverse each row
    for (let i = 0; i < n; i++) {
        matrix[i].reverse();
    }
};
"""
tcs_rotate = [
    {"input": "[[1,2,3],[4,5,6],[7,8,9]]", "expected_output": "[[7,4,1],[8,5,2],[9,6,3]]", "output_source": "mutated_arg_0"}
]
res_js_rotate = SandboxRunner.evaluate_code(js_rotate_code, "javascript", tcs_rotate)
print(f"JS Rotate Image: {res_js_rotate.get('status')} ({res_js_rotate.get('test_cases_passed')}/{res_js_rotate.get('total_test_cases')})")
assert res_js_rotate.get("status") == "ACCEPTED", f"JS Rotate Image failed: {res_js_rotate}"

# ==============================================================================
# BUG 8: Debugger Contract and Unsupported Languages
# ==============================================================================
print("\n[BUG 8] Testing Debugger Contract...")

# 1. Non-Python language tracing returns NOT_SUPPORTED
res_dbg_js = DebugTracer.trace("var x = 1;", "javascript", "1")
print(f"Debugger JS trace status: {res_dbg_js.get('status')}")
assert res_dbg_js.get("status") == "NOT_SUPPORTED", f"Expected NOT_SUPPORTED, got: {res_dbg_js}"
assert "Python" in res_dbg_js.get("error", ""), f"Expected informative explanation, got: {res_dbg_js.get('error')}"
assert res_dbg_js.get("return_value") is None, f"Expected None return_value, got: {res_dbg_js.get('return_value')}"

res_dbg_java = DebugTracer.trace("int x = 1;", "java", "1")
print(f"Debugger Java trace status: {res_dbg_java.get('status')}")
assert res_dbg_java.get("status") == "NOT_SUPPORTED", f"Expected NOT_SUPPORTED, got: {res_dbg_java}"

# Also test through LCQuestionService.debug_code
res_lc_dbg = LCQuestionService.debug_code("two-sum", "class Solution {}", "java", "[2,7,11,15]")
print(f"LCQuestionService Java debug status: {res_lc_dbg.get('status')}")
assert res_lc_dbg.get("status") == "NOT_SUPPORTED", f"Expected NOT_SUPPORTED, got: {res_lc_dbg}"

# 2. Python tracing works and returns valid execution steps
py_trace_code = """
def twoSum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        diff = target - n
        if diff in seen:
            return [seen[diff], i]
        seen[n] = i
    return []
"""
res_dbg_py = DebugTracer.trace(py_trace_code, "python", "nums = [2, 7, 11, 15], target = 9")
print(f"Debugger Python trace status: {res_dbg_py.get('status')} (steps: {res_dbg_py.get('total_steps')})")
assert res_dbg_py.get("status") == "SUCCESS", f"Expected SUCCESS, got: {res_dbg_py}"
assert res_dbg_py.get("total_steps") > 0, "Expected positive step count"

# ==============================================================================
# BUG 9: Complexity Guidance & Rotate Image
# ==============================================================================
print("\n[BUG 9] Testing Complexity Guidance & Rotate Image...")

LCQuestionService._is_initialized = False
LCQuestionService.initialize()

rotate_img = LCQuestionService.get_question("rotate-image", db=None)
print(f"Rotate Image Time: {rotate_img.get('timeComplexity')}, Space: {rotate_img.get('spaceComplexity')}")
print(f"Rotate Image Approach: {rotate_img.get('approach')}")
assert rotate_img.get("timeComplexity") in ["O(n²)", "O(n^2)"], f"Expected O(n²), got {rotate_img.get('timeComplexity')}"
assert rotate_img.get("spaceComplexity") == "O(1)", f"Expected O(1), got {rotate_img.get('spaceComplexity')}"
assert "transpos" in (rotate_img.get("approach") or "").lower(), f"Approach missing transposing: {rotate_img.get('approach')}"

# Problem list index shares same verified complexity
all_qs = LCQuestionService.list_questions(db=None).get("questions", [])
idx_rotate = [q for q in all_qs if q.get("slug") == "rotate-image"][0]
print(f"Index Rotate Image Time: {idx_rotate.get('timeComplexity')}, Space: {idx_rotate.get('spaceComplexity')}")
assert idx_rotate.get("timeComplexity") in ["O(n²)", "O(n^2)"]
assert idx_rotate.get("spaceComplexity") == "O(1)"

# Check other verified bounds
idx_twosum = [q for q in all_qs if q.get("slug") == "two-sum"][0]
print(f"Index Two Sum Time: {idx_twosum.get('timeComplexity')}, Space: {idx_twosum.get('spaceComplexity')}")
assert idx_twosum.get("timeComplexity") == "O(n)"
assert idx_twosum.get("spaceComplexity") == "O(n)"

print("\n" + "=" * 70)
print("ALL TESTS FOR BUGS 5 THROUGH 9 PASSED 100%!")
print("=" * 70)
