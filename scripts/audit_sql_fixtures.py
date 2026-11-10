import os
import json
import glob

db_dir = r"lc_qbank/questions/database"
files = glob.glob(f"{db_dir}/**/*.json", recursive=True)

print(f"Total database question files: {len(files)}")

identical_cases_count = 0
only_one_unique_case = 0
suspicious_files = []

for fp in sorted(files):
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)
    tcs = data.get("testCases") or []
    if len(tcs) <= 1:
        only_one_unique_case += 1
        suspicious_files.append((data.get("slug"), fp, len(tcs), "Only 1 case"))
    else:
        # Check if all cases have identical inputs
        inputs = [str(tc.get("input", "")).replace(" ", "") for tc in tcs]
        if len(set(inputs)) == 1:
            identical_cases_count += 1
            suspicious_files.append((data.get("slug"), fp, len(tcs), "Identical inputs"))

print(f"Questions with identical test case inputs: {identical_cases_count}")
print(f"Questions with only <= 1 test case: {only_one_unique_case}")
print(f"Total suspicious: {len(suspicious_files)}")
for slug, fp, count, reason in suspicious_files[:20]:
    print(f"  {slug} ({reason}, {count} cases)")
