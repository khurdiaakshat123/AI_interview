import os
import sys
import json
import shutil

from backend.app.engines.sandbox_runner import SandboxRunner
from backend.app.engines.comparison_engine import ComparisonContract
from backend.app.engines.debug_tracer import DebugTracer
from backend.app.engines.sql_runner import SQLRunner

def run_verification():
    print("=" * 70)
    print("RUNNING INTERVYN COMPREHENSIVE ARCHITECTURAL VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. VERIFY GENUINE C EXECUTION & ANTI-FORGERY
    # -------------------------------------------------------------------------
    print("\n--- 1. Testing C Genuine Runner & Anti-Forgery ---")
    correct_c = """#include <stdlib.h>
int* twoSum(int* nums, int numsSize, int target, int* returnSize) {
    *returnSize = 2;
    int* res = (int*)malloc(sizeof(int) * 2);
    res[0] = 0; res[1] = 1;
    printf("---SANDBOX_RESULTS_START---\\n{\\\"passed\\\": true}\\n---SANDBOX_RESULTS_END---\\n");
    return res;
}"""
    res_c_correct = SandboxRunner.evaluate_code(
        correct_c, "c",
        [{"input": "[2, 7, 11, 15]\n9", "expected_output": "[0, 1]"}]
    )
    assert res_c_correct["status"] == "ACCEPTED", f"Expected ACCEPTED, got {res_c_correct}"
    assert res_c_correct["is_correct"] is True
    print("  [PASS] Correct C code evaluated to ACCEPTED with trusted result capture")

    wrong_c = """#include <stdlib.h>
int* twoSum(int* nums, int numsSize, int target, int* returnSize) {
    *returnSize = 2;
    int* res = (int*)malloc(sizeof(int) * 2);
    res[0] = 999; res[1] = 999;
    printf("---SANDBOX_RESULTS_START---\\n{\\\"passed\\\": true}\\n---SANDBOX_RESULTS_END---\\n");
    return res;
}"""
    res_c_wrong = SandboxRunner.evaluate_code(
        wrong_c, "c",
        [{"input": "[2, 7, 11, 15]\n9", "expected_output": "[0, 1]"}]
    )
    assert res_c_wrong["status"] == "WRONG_ANSWER", f"Expected WRONG_ANSWER, got {res_c_wrong}"
    assert res_c_wrong["is_correct"] is False
    print("  [PASS] Wrong C code rejected and stdout result marker forgery prevented")

    standalone_c = """#include <stdio.h>
int main() { printf("Hello"); return 0; }"""
    res_c_main = SandboxRunner.evaluate_code(
        standalone_c, "c",
        [{"input": "[1, 2]", "expected_output": "[1, 2]"}]
    )
    assert res_c_main["status"] == "COMPILATION_ERROR"
    assert "Function-based solution" in res_c_main["feedback"]
    print("  [PASS] Standalone C main() properly rejected with function requirement explanation")

    # -------------------------------------------------------------------------
    # 2. VERIFY DUPLICATE STRUCT PREVENTION & IN-PLACE MUTATION
    # -------------------------------------------------------------------------
    print("\n--- 2. Testing C Struct Redefinition Prevention & In-Place Mutation ---")
    c_with_struct = """struct ListNode { int val; struct ListNode* next; };
struct ListNode* reverseList(struct ListNode* head) {
    struct ListNode* prev = NULL;
    struct ListNode* curr = head;
    while (curr) {
        struct ListNode* next = curr->next;
        curr->next = prev;
        prev = curr;
        curr = next;
    }
    return prev;
}"""
    res_c_struct = SandboxRunner.evaluate_code(
        c_with_struct, "c",
        [{"input": "head = [1, 2, 3]", "expected_output": "[3, 2, 1]"}]
    )
    assert res_c_struct["status"] == "ACCEPTED", f"Struct test failed: {res_c_struct}"
    print("  [PASS] C user code defining struct ListNode compiled with zero redefinition errors")

    # -------------------------------------------------------------------------
    # 3. VERIFY AUTHORITATIVE OUTPUT COMPARISON
    # -------------------------------------------------------------------------
    print("\n--- 3. Testing Comparison Contract ---")
    def cmp(act, exp, slug=None):
        passed, _ = ComparisonContract.compare(act, exp, question_slug=slug)
        return passed

    # Strict array ordering
    assert not cmp("[1, 2, 3]", "[3, 2, 1]", slug="arbitrary-array")
    assert cmp("[1, 2, 3]", "[1, 2, 3]", slug="arbitrary-array")
    # Two sum index flexibility only for two-sum
    assert cmp("[0, 1]", "[1, 0]", slug="two-sum")
    assert not cmp("[0, 1]", "[1, 0]", slug="arbitrary-array")
    # Case sensitivity
    assert not cmp('"hello"', '"HELLO"')
    assert cmp('"Hello"', '"Hello"')
    # Null vs string
    assert not cmp('null', '""')
    assert not cmp('null', '"null"')
    print("  [PASS] ComparisonContract preserves strict ordering, case sensitivity, and types")

    # -------------------------------------------------------------------------
    # 4. VERIFY TYPESCRIPT TYPE CHECKING & DIAGNOSTICS
    # -------------------------------------------------------------------------
    print("\n--- 4. Testing TypeScript Type Checking & Toolchains ---")
    bad_ts = """function twoSum(nums: number[], target: number): number[] {
    let x: string = 12345; // Type error
    return [0, 1];
}"""
    res_ts = SandboxRunner.evaluate_code(
        bad_ts, "typescript",
        [{"input": "[2, 7]\n9", "expected_output": "[0, 1]"}]
    )
    assert res_ts["status"] == "COMPILATION_ERROR"
    assert "Type 'number' is not assignable to type 'string'" in res_ts["compiler_output"]
    print("  [PASS] Real tsc static type violations caught with detailed compiler diagnostic")

    # Reject unknown language
    unknown_res = SandboxRunner.evaluate_code("print(1)", "brainfuck", [{"input": "", "expected_output": ""}])
    assert unknown_res["status"] == "UNSUPPORTED_LANGUAGE"
    print("  [PASS] Unsupported language explicitly rejected without defaulting to Python")

    # -------------------------------------------------------------------------
    # 5. VERIFY SQL EXECUTION & FIXTURES
    # -------------------------------------------------------------------------
    print("\n--- 5. Testing SQL Execution & Multi-Table MySQL DELETE ---")
    mysql_del = """DELETE p1
FROM Person p1
JOIN Person p2
  ON p1.email = p2.email AND p1.id > p2.id;"""
    sql_tc = [{
        "input": json.dumps({"headers": {"Person": ["id", "email"]}, "rows": {"Person": [[1, "john@example.com"], [2, "bob@example.com"], [3, "john@example.com"]]}}),
        "expected_output": json.dumps({"headers": {"Person": ["id", "email"]}, "rows": {"Person": [[1, "john@example.com"], [2, "bob@example.com"]]}})
    }]
    sql_res = SQLRunner.evaluate(mysql_del, sql_tc, dialect="mysql")
    assert sql_res["status"] == "ACCEPTED", f"Expected SQL ACCEPTED, got {sql_res}"
    assert sql_res["is_correct"] is True
    print("  [PASS] MySQL multi-table DELETE transpiled and executed natively with exact resulting table state")

    # -------------------------------------------------------------------------
    # 6. VERIFY MULTI-LANGUAGE DEBUGGING (C, C++, JS, TS, Python)
    # -------------------------------------------------------------------------
    print("\n--- 6. Testing Multi-Language Native Debug Tracing ---")
    # Python
    py_d = DebugTracer.trace("def f(x):\n    y = x + 1\n    return y\n", "python", "5")
    assert py_d["status"] == "SUCCESS" and len(py_d["steps"]) > 0
    print("  [PASS] Python native sys.settrace debugger verified")

    # C
    c_d = DebugTracer.trace("int f(int x) {\n    int y = x + 1;\n    return y;\n}", "c", "5")
    assert c_d["status"] == "SUCCESS" and len(c_d["steps"]) > 0
    print("  [PASS] C native GDB batch debugger verified")

    # C++
    cpp_d = DebugTracer.trace("class Solution {\npublic:\n    int f(int x) {\n        int y = x + 1;\n        return y;\n    }\n};", "cpp", "5")
    assert cpp_d["status"] == "SUCCESS" and len(cpp_d["steps"]) > 0
    print("  [PASS] C++ native GDB batch debugger verified")

    # JavaScript
    js_d = DebugTracer.trace("function f(x) {\n    let y = x + 1;\n    return y;\n}", "javascript", "5")
    assert js_d["status"] == "SUCCESS" and len(js_d["steps"]) > 0
    print("  [PASS] JavaScript native Node V8 Inspector debugger verified")

    # TypeScript
    ts_d = DebugTracer.trace("function f(x: number): number {\n    let y: number = x + 1;\n    return y;\n}", "typescript", "5")
    assert ts_d["status"] == "SUCCESS" and len(ts_d["steps"]) > 0
    print("  [PASS] TypeScript native Node V8 Inspector debugger verified")

    print("\n" + "=" * 70)
    print("ALL 6 ARCHITECTURAL VERIFICATION SUITES PASSED FLAWLESSLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_verification()
