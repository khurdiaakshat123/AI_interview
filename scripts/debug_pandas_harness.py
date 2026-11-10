from backend.app.engines.sandbox_runner import SandboxRunner

code = """
import pandas as pd
def combine_two_tables(person: pd.DataFrame, address: pd.DataFrame) -> pd.DataFrame:
    merged = person.merge(address, on='personId', how='left')
    return merged[['firstName', 'lastName', 'city', 'state']]
"""

tcs = [{
    "input": '{"headers": {"Person": ["personId", "lastName", "firstName"], "Address": ["addressId", "personId", "city", "state"]}, "rows": {"Person": [[1, "Wang", "Allen"], [2, "Alice", "Bob"]], "Address": [[1, 2, "New York City", "New York"], [2, 3, "Leetcode", "California"]]}}',
    "expected_output": """+-----------+----------+---------------+----------+
| firstName | lastName | city          | state    |
+-----------+----------+---------------+----------+
| Allen     | Wang     | Null          | Null     |
| Bob       | Alice    | New York City | New York |
+-----------+----------+---------------+----------+"""
}]

harness = SandboxRunner._build_python_harness(code, tcs)
with open("temp_debug_harness.py", "w", encoding="utf-8") as f:
    f.write(harness)

import subprocess
res = subprocess.run(["python", "temp_debug_harness.py"], capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
