# -*- coding: utf-8 -*-
import sys
import os

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.engines.sandbox_runner import SandboxRunner

print("Testing Java runners...")

# 1. Invert Tree in Java
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
tcs_tree = [
    {"input": "[4,2,7,1,3,6,9]", "expected_output": "[4,7,2,9,6,3,1]"},
    {"input": "[2,1,3]", "expected_output": "[2,3,1]"},
    {"input": "[]", "expected_output": "[]"}
]
res_tree = SandboxRunner.evaluate_code(java_tree_code, "java", tcs_tree)
print("Java Invert Tree:", res_tree["status"], f"{res_tree.get('test_cases_passed')}/{res_tree.get('total_test_cases')}")
assert res_tree["status"] == "ACCEPTED", f"Tree failed: {res_tree}"

# 2. Move Zeroes in Java
java_zeroes_code = """
class Solution {
    public void moveZeroes(int[] nums) {
        int pos = 0;
        for (int x : nums) {
            if (x != 0) nums[pos++] = x;
        }
        while (pos < nums.length) nums[pos++] = 0;
    }
}
"""
tcs_zeroes = [
    {"input": "[0,1,0,3,12]", "expected_output": "[1,3,12,0,0]"},
    {"input": "[0]", "expected_output": "[0]"},
    {"input": "[1,2,3]", "expected_output": "[1,2,3]"}
]
res_zeroes = SandboxRunner.evaluate_code(java_zeroes_code, "java", tcs_zeroes)
print("Java Move Zeroes:", res_zeroes["status"], f"{res_zeroes.get('test_cases_passed')}/{res_zeroes.get('total_test_cases')}")
assert res_zeroes["status"] == "ACCEPTED", f"Zeroes failed: {res_zeroes}"

# 3. LRU Cache in Java
java_lru_code = """
import java.util.*;

class LRUCache {
    private final int capacity;
    private final Map<Integer, Integer> map;

    public LRUCache(int capacity) {
        this.capacity = capacity;
        this.map = new LinkedHashMap<>(capacity, 0.75f, true) {
            protected boolean removeEldestEntry(Map.Entry eldest) {
                return size() > LRUCache.this.capacity;
            }
        };
    }

    public int get(int key) {
        return map.getOrDefault(key, -1);
    }

    public void put(int key, int value) {
        map.put(key, value);
    }
}
"""
tcs_lru = [
    {
        "input": "[\"LRUCache\",\"put\",\"put\",\"get\",\"put\",\"get\",\"put\",\"get\",\"get\",\"get\"]\n[[2],[1,1],[2,2],[1],[3,3],[2],[4,4],[1],[3],[4]]",
        "expected_output": "[null,null,null,1,null,-1,null,-1,3,4]"
    }
]
res_lru = SandboxRunner.evaluate_code(java_lru_code, "java", tcs_lru)
print("Java LRU Cache:", res_lru["status"], f"{res_lru.get('test_cases_passed')}/{res_lru.get('total_test_cases')}")
assert res_lru["status"] == "ACCEPTED", f"LRU failed: {res_lru}"

print("ALL JAVA TESTS PASSED 100%!")
