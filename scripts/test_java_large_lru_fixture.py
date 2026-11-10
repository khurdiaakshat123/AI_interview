import sys
import json
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from backend.app.engines.sandbox_runner import SandboxRunner

def test_large_java_lru_fixture():
    print("=== Testing Java LRU Cache Large Input (>65KB) ===")
    
    # Generate 3,000 operations (>75,000 bytes)
    ops = ["LRUCache"]
    args = [[100]]
    expected = ["null"]
    
    for i in range(1, 5000):
        if i % 2 == 1:
            ops.append("put")
            args.append([i, i * 10])
            expected.append("null")
        else:
            ops.append("get")
            args.append([i - 1])
            expected.append(str((i - 1) * 10))
            
    ops_json = json.dumps(ops)
    args_json = json.dumps(args)
    exp_json = "[" + ",".join(expected) + "]"
    
    fixture_input = f"{ops_json}\n{args_json}"
    fixture_size = len(fixture_input.encode("utf-8"))
    print(f"Total fixture input byte size: {fixture_size:,} bytes (exceeds JVM 65,535 limit)")
    assert fixture_size > 65535, f"Fixture size {fixture_size} must exceed 65535 bytes"
    
    java_lru_code = """
import java.util.*;

class LRUCache {
    private int capacity;
    private LinkedHashMap<Integer, Integer> map;

    public LRUCache(int capacity) {
        this.capacity = capacity;
        this.map = new LinkedHashMap<Integer, Integer>(capacity, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<Integer, Integer> eldest) {
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

    test_cases = [
        {
            "input": fixture_input,
            "expected_output": exp_json,
            "is_hidden": False,
            "is_custom": False
        }
    ]
    
    res = SandboxRunner.evaluate_code_against_tests(
        user_code=java_lru_code,
        language="java",
        test_cases=test_cases,
        approach="",
        timeout_seconds=10.0
    )
    
    print("Execution Status:", res.get("status"))
    print("Is Correct:", res.get("is_correct"))
    if res.get("compiler_output"):
        print("Compiler / Error Output:", res.get("compiler_output")[:500])
    
    assert res.get("status") == "ACCEPTED", f"Expected ACCEPTED, got {res.get('status')}: {res.get('compiler_output')}"
    assert res.get("is_correct") is True
    print("SUCCESS: Java LRU Cache successfully compiled and passed with >75KB fixture without 'constant string too long' error!")

if __name__ == "__main__":
    test_large_java_lru_fixture()
