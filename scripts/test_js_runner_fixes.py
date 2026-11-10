# -*- coding: utf-8 -*-
import sys
import os

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.engines.sandbox_runner import SandboxRunner

print("Testing JavaScript runners...")

# 1. Invert Tree in JavaScript (function style)
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
tcs_tree = [
    {"input": "[4,2,7,1,3,6,9]", "expected_output": "[4,7,2,9,6,3,1]"},
    {"input": "[2,1,3]", "expected_output": "[2,3,1]"},
    {"input": "[]", "expected_output": "[]"}
]
res_tree = SandboxRunner.evaluate_code(js_tree_code, "javascript", tcs_tree)
print("JS Invert Tree:", res_tree["status"], f"{res_tree.get('test_cases_passed')}/{res_tree.get('total_test_cases')}")
assert res_tree["status"] == "ACCEPTED", f"Tree failed: {res_tree}"

# 2. Move Zeroes in JavaScript
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
tcs_zeroes = [
    {"input": "[0,1,0,3,12]", "expected_output": "[1,3,12,0,0]"},
    {"input": "[0]", "expected_output": "[0]"},
    {"input": "[1,2,3]", "expected_output": "[1,2,3]"}
]
res_zeroes = SandboxRunner.evaluate_code(js_zeroes_code, "javascript", tcs_zeroes)
print("JS Move Zeroes:", res_zeroes["status"], f"{res_zeroes.get('test_cases_passed')}/{res_zeroes.get('total_test_cases')}")
assert res_zeroes["status"] == "ACCEPTED", f"Zeroes failed: {res_zeroes}"

# 3. LRU Cache in JavaScript (function prototype style)
js_lru_code = """
/**
 * @param {number} capacity
 */
var LRUCache = function(capacity) {
    this.capacity = capacity;
    this.map = new Map();
};

/** 
 * @param {number} key
 * @return {number}
 */
LRUCache.prototype.get = function(key) {
    if (!this.map.has(key)) return -1;
    const val = this.map.get(key);
    this.map.delete(key);
    this.map.set(key, val);
    return val;
};

/** 
 * @param {number} key 
 * @param {number} value
 * @return {void}
 */
LRUCache.prototype.put = function(key, value) {
    if (this.map.has(key)) {
        this.map.delete(key);
    }
    this.map.set(key, value);
    if (this.map.size > this.capacity) {
        const firstKey = this.map.keys().next().value;
        this.map.delete(firstKey);
    }
};
"""
tcs_lru = [
    {
        "input": "[\"LRUCache\",\"put\",\"put\",\"get\",\"put\",\"get\",\"put\",\"get\",\"get\",\"get\"]\n[[2],[1,1],[2,2],[1],[3,3],[2],[4,4],[1],[3],[4]]",
        "expected_output": "[null,null,null,1,null,-1,null,-1,3,4]"
    }
]
res_lru = SandboxRunner.evaluate_code(js_lru_code, "javascript", tcs_lru)
print("JS LRU Cache:", res_lru["status"], f"{res_lru.get('test_cases_passed')}/{res_lru.get('total_test_cases')}")
assert res_lru["status"] == "ACCEPTED", f"LRU failed: {res_lru}"

# 4. LRU Cache in JavaScript (ES6 class style)
js_lru_class_code = """
class LRUCache {
    constructor(capacity) {
        this.capacity = capacity;
        this.map = new Map();
    }
    get(key) {
        if (!this.map.has(key)) return -1;
        const val = this.map.get(key);
        this.map.delete(key);
        this.map.set(key, val);
        return val;
    }
    put(key, value) {
        if (this.map.has(key)) {
            this.map.delete(key);
        }
        this.map.set(key, value);
        if (this.map.size > this.capacity) {
            const firstKey = this.map.keys().next().value;
            this.map.delete(firstKey);
        }
    }
}
"""
res_lru_class = SandboxRunner.evaluate_code(js_lru_class_code, "javascript", tcs_lru)
print("JS LRU Cache (ES6 Class):", res_lru_class["status"], f"{res_lru_class.get('test_cases_passed')}/{res_lru_class.get('total_test_cases')}")
assert res_lru_class["status"] == "ACCEPTED", f"LRU Class failed: {res_lru_class}"

print("ALL JAVASCRIPT TESTS PASSED 100%!")
