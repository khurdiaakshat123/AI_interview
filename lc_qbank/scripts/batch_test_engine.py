"""
Batch Test Engine for LeetCode Question Bank.
Generates up to 20 verified, non-null test cases per question covering edge cases,
tricky cases, and constraint boundaries, verified directly against accepted reference solutions.
"""

import sys
import os
import re
import json
import copy
import time
import argparse
import importlib.util
import concurrent.futures
from collections import deque

# Import preamble to inject types and math/itertools/heapq aliases
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import py_preamble

# --- Data Structure Helpers ---

def parse_tree(val):
    if val is None:
        return None
    if isinstance(val, str):
        val = json.loads(val)
    if not isinstance(val, list) or not val or val[0] is None:
        return None
    root = py_preamble.TreeNode(val[0])
    q = deque([root])
    i = 1
    while q and i < len(val):
        curr = q.popleft()
        if i < len(val):
            if val[i] is not None:
                curr.left = py_preamble.TreeNode(val[i])
                q.append(curr.left)
            i += 1
        if i < len(val):
            if val[i] is not None:
                curr.right = py_preamble.TreeNode(val[i])
                q.append(curr.right)
            i += 1
    return root

def serialize_tree(root):
    if not root:
        return "[]"
    res = []
    q = deque([root])
    while q:
        node = q.popleft()
        if node:
            res.append(node.val)
            q.append(node.left)
            q.append(node.right)
        else:
            res.append(None)
    while res and res[-1] is None:
        res.pop()
    return json.dumps(res, separators=(',', ':'))

def parse_listnode(val):
    if val is None:
        return None
    if isinstance(val, str):
        val = json.loads(val)
    if not isinstance(val, list) or not val:
        return None
    dummy = py_preamble.ListNode(0)
    curr = dummy
    for x in val:
        curr.next = py_preamble.ListNode(x)
        curr = curr.next
    return dummy.next

def serialize_listnode(head):
    if not head:
        return "[]"
    res = []
    curr = head
    visited = set()
    while curr:
        if id(curr) in visited: # Cycle protection
            break
        visited.add(id(curr))
        res.append(curr.val)
        curr = curr.next
    return json.dumps(res, separators=(',', ':'))

def parse_param(val_str, ptype):
    val_str = val_str.strip()
    ptype_lower = ptype.lower()
    
    if ptype_lower == 'treenode':
        return parse_tree(json.loads(val_str))
    elif ptype_lower == 'listnode':
        return parse_listnode(json.loads(val_str))
    elif ptype_lower == 'listnode[]':
        data = json.loads(val_str)
        return [parse_listnode(x) for x in data] if isinstance(data, list) else []
    elif ptype_lower == 'treenode[]':
        data = json.loads(val_str)
        return [parse_tree(x) for x in data] if isinstance(data, list) else []
    else:
        return json.loads(val_str)

def serialize_result(val, rtype, param_arg=None):
    if rtype == 'void' and param_arg is not None:
        val = param_arg
        
    if val is None:
        if rtype in ('ListNode', 'TreeNode', 'list<integer>', 'integer[]', 'list<string>'):
            return "[]"
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return f"{val:.5f}".rstrip('0').rstrip('.') if '.' in f"{val:.5f}" else str(val)
    if isinstance(val, str):
        return json.dumps(val)
    if isinstance(val, py_preamble.TreeNode):
        return serialize_tree(val)
    if isinstance(val, py_preamble.ListNode):
        return serialize_listnode(val)
    if isinstance(val, list):
        if val and isinstance(val[0], py_preamble.ListNode):
            return json.dumps([json.loads(serialize_listnode(x)) for x in val], separators=(',', ':'))
        if val and isinstance(val[0], py_preamble.TreeNode):
            return json.dumps([json.loads(serialize_tree(x)) for x in val], separators=(',', ':'))
        return json.dumps(val, separators=(',', ':'))
    return json.dumps(val, separators=(',', ':'))

# --- Templates for Domain Boundary Inputs ---

TREE_TEMPLATES = [
    [1],
    [0],
    [-1],
    [1, 2],
    [1, None, 2],
    [1, 2, 3],
    [1, 2, None, 3],
    [1, None, 2, None, 3],
    [1, 2, 3, 4, 5, 6, 7],
    [1, 2, 2, 3, 4, 4, 3],
    [5, 3, 6, 2, 4, None, None, 1],
    [10, 5, 15, None, None, 6, 20],
    [-10, 9, 20, None, None, 15, 7],
    [3, 1, 4, None, 2],
    [1, 2, 3, None, None, 4, 5],
    [2, 1, 3, 0, 7, 9, 1],
    [10, 5, -3, 3, 2, None, 11, 3, -2, None, 1],
    [0, 0, 0, 0, None, None, 0],
    [1, None, 2, None, 3, None, 4],
    [4, 2, 7, 1, 3, 6, 9],
    [1, 2, 3, None, None, None, 4],
]

LIST_TEMPLATES = [
    [],
    [0],
    [1],
    [-1],
    [1, 2],
    [2, 1],
    [1, 1],
    [-1, 1],
    [1, 2, 3],
    [3, 2, 1],
    [1, 1, 1],
    [1, 3, 5],
    [2, 4, 6],
    [-3, -1, 0],
    [-2, 1, 4],
    [1, 2, 3, 4, 5],
    [5, 4, 3, 2, 1],
    [10, 20, 30],
    [1, 1, 2, 2, 3, 3],
    [-10, 0, 10],
]

ARRAY_TEMPLATES = [
    [0],
    [1],
    [-1],
    [0, 0],
    [1, 2],
    [2, 1],
    [1, 1],
    [-1, 1],
    [1, 2, 3],
    [3, 2, 1],
    [1, 1, 1],
    [0, 1, 0],
    [1, 2, 3, 4, 5],
    [5, 4, 3, 2, 1],
    [-5, -4, -3, -2, -1],
    [1, 3, 2, 5, 4],
    [-10, 0, 10],
    [100, -100],
    [1, 1, 2, 2, 3, 3],
    [10, 20, 30, 40, 50],
    [0, 1, 0, 3, 12],
    [1, 0, 0],
    [0, 0, 1],
    [0, 0, 0, 0],
    [1, 2, 3, 4],
]

STRING_TEMPLATES = [
    "a", "b", "aa", "ab", "ba", "aba", "abba", "aaaaa",
    "abcde", "edcba", "aab", "aA", "0", "121", "racecar",
    "hello", "leetcode", "world", "()", "()[]{}", "(]", "([)]", "{[]}"
]

MATRIX_TEMPLATES = [
    [[1]],
    [[0]],
    [[1, 2], [3, 4]],
    [[0, 0], [0, 0]],
    [[1, 1], [1, 1]],
    [[1, 2, 3], [4, 5, 6]],
    [[1, 2], [3, 4], [5, 6]],
    [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
    [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    [[1, 1, 1], [1, 1, 1], [1, 1, 1]],
    [[1, 2, 3, 4]],
    [[1], [2], [3], [4]],
    [[9, 8, 7], [6, 5, 4], [3, 2, 1]],
    [[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]],
    [[0, 0, 0], [0, 1, 0], [0, 0, 0]],
    [[0, 1], [0, 0]],
    [[1, 3, 1], [1, 5, 1], [4, 2, 1]],
    [[1, 2], [1, 2]],
    [[1, 4], [2, 3]],
    [[1, 3], [2, 6], [8, 10], [15, 18]],
    [[1, 4], [4, 5]],
    [[1, 4], [0, 4]],
    [[1, 4], [0, 2], [3, 5]],
    [[1, 10], [2, 3], [4, 5], [6, 7], [8, 9]],
    [[1, 2], [3, 4], [5, 6]],
]

STRING_ARRAY_TEMPLATES = [
    ["a"],
    [""],
    ["a", "b"],
    ["a", "a"],
    ["ab", "ba"],
    ["abc", "bca", "cab"],
    ["eat", "tea", "tan", "ate", "nat", "bat"],
    ["cat", "dog", "tac", "god", "act"],
    ["one", "two", "three"],
    ["hello", "world"],
    ["a", "b", "c", "d"],
    ["flow", "flower", "flight"],
    ["word", "world", "row"],
    ["listen", "silent"],
    ["anagram", "nagaram"],
    ["rat", "car"],
    ["apple", "pear", "banana"],
    ["blue", "red", "green"],
    ["1", "2", "3"],
    ["code", "leet", "love"],
]

def mutate_arg(val, ptype):
    ptype_lower = ptype.lower()
    mutations = []
    
    if '[]' in ptype_lower and not '[][]' in ptype_lower:
        if isinstance(val, list) and val:
            if len(val) >= 2:
                mutations.append(val[:len(val)//2])
                mutations.append(val[len(val)//2:])
            mutations.append([val[0]])
            if len(val) >= 2:
                mutations.append([val[0], val[-1]])
                mutations.append([val[0], val[1]])
            mutations.append(val[::-1])
            try:
                mutations.append(sorted(val))
                mutations.append(sorted(val, reverse=True))
            except Exception:
                pass
            mutations.append([val[0]] * min(len(val), 5))
            if len(val) <= 8:
                mutations.append(val + val)
            if isinstance(val[0], (int, float)):
                mutations.append([x * 2 for x in val])
                mutations.append([x + 1 for x in val])
                mutations.append([x - 1 for x in val])
                mutations.append([-x for x in val])
                mutations.append([0] * min(len(val), 4))
                mutations.append([1] * min(len(val), 4))
        if 'string' in ptype_lower or 'character' in ptype_lower:
            mutations.extend(STRING_ARRAY_TEMPLATES)
        else:
            mutations.extend(ARRAY_TEMPLATES)
                
    elif ptype_lower == 'string':
        if isinstance(val, str) and val:
            if len(val) >= 2:
                mutations.append(val[:len(val)//2])
                mutations.append(val[len(val)//2:])
            mutations.append(val[0])
            if len(val) >= 2:
                mutations.append(val[:2])
            mutations.append(val[::-1])
            if len(val) <= 10:
                mutations.append(val + val)
            mutations.append(val[0] * min(len(val), 6))
            if len(val) <= 10:
                mutations.append(val + val[::-1])
            if val.isalpha():
                mutations.append(val.lower())
                mutations.append(val.upper())
        mutations.extend(STRING_TEMPLATES)
                
    elif 'int' in ptype_lower or 'long' in ptype_lower:
        if isinstance(val, int):
            max_base = abs(val)
            if max_base <= 10:
                # Small/combinatorial domain: strictly bound to prevent exponential explosion
                cands = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, val - 1, val + 1, val - 2, val + 2, val - 3, val + 3, -1, -2]
                mutations.extend([x for x in cands if -5 <= x <= min(max_base + 5, 10)])
            else:
                # Standard integer domain
                mutations.extend([
                    val - 1, val + 1, val - 2, val + 2, val - 3, val + 3,
                    val * 2 if abs(val) <= 1000 else val,
                    val // 2 if val else 0,
                    -val, 0, 1, 2, 3, 4, 5, -1, -2, -3, 10, 20, 50, 100
                ])
        else:
            mutations.extend([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
            
    elif '[][]' in ptype_lower:
        if isinstance(val, list) and val and isinstance(val[0], list):
            mutations.append([val[0]])
            mutations.append([[row[0]] for row in val])
            if len(val) >= 2:
                mutations.append(val[::-1])
            try:
                mutations.append([list(r) for r in zip(*val)])
            except Exception:
                pass
        if 'int' in ptype_lower or 'integer' in ptype_lower:
            mutations.extend(MATRIX_TEMPLATES)
                
    elif ptype_lower == 'treenode':
        if isinstance(val, list) and val:
            mutations.append([val[0]])
            if len(val) >= 2:
                mutations.append(val[:2])
                mutations.append(val[::-1])
            mutations.append([val[0], val[1] if len(val) > 1 else 1, None])
            mutations.append([val[0], None, val[1] if len(val) > 1 else 1])
        mutations.extend(TREE_TEMPLATES)

    elif ptype_lower == 'listnode':
        if isinstance(val, list) and val:
            mutations.append([val[0]])
            if len(val) >= 2:
                mutations.append(val[:2])
                mutations.append(val[::-1])
        mutations.extend(LIST_TEMPLATES)
                
    return mutations

# --- Engine Core ---

def make_tracer(max_steps=50000):
    steps = 0
    def tracer(frame, event, arg):
        nonlocal steps
        steps += 1
        if steps > max_steps:
            raise TimeoutError("Exceeded step limit")
        return tracer
    return tracer

class BatchTestEngine:
    def __init__(self, repo_root='.'):
        self.repo_root = repo_root
        self.questions_dir = os.path.join(repo_root, 'questions')
        self.raw_dir = os.path.join(repo_root, 'tmp', 'raw')
        self.manifest_path = os.path.join(repo_root, 'manifests', 'questions-index.json')
        self.doocs_dir = os.path.abspath(os.path.join(repo_root, '..', 'tmp_doocs', 'solution'))
        self.id_to_sol = self._build_solution_map()

    def _build_solution_map(self):
        id_map = {}
        if not os.path.exists(self.doocs_dir):
            return id_map
        for root, dirs, files in os.walk(self.doocs_dir):
            if 'Solution.py' in files:
                f = os.path.basename(root)
                parts = f.split('.', 1)
                if len(parts) == 2 and parts[0].isdigit():
                    qid = str(int(parts[0]))
                    id_map[qid] = os.path.join(root, 'Solution.py')
        return id_map

    def process_question(self, q_info):
        slug = q_info['slug']
        qid = str(q_info['id'])
        category = q_info.get('category', 'dsa')
        file_path = os.path.join(self.repo_root, q_info['path'])
        raw_path = os.path.join(self.raw_dir, f"{slug}.json")
        
        if not os.path.exists(file_path):
            return 0, "file_not_found"

        with open(file_path, 'r', encoding='utf-8') as f:
            question_data = json.load(f)

        # 1. Database questions: preserve table inputs/outputs
        if category == 'database':
            existing_tests = question_data.get('testCases') or []
            if not existing_tests:
                # Synthesize from publicTests and examples
                tests = []
                for pt in question_data.get('publicTests') or []:
                    if pt.get('input') and pt.get('expectedOutput') and pt['expectedOutput'] != 'null':
                        tests.append(pt)
                for ex in question_data.get('examples') or []:
                    if ex.get('input') and ex.get('output') and ex['output'] != 'null':
                        tests.append({"input": ex['input'], "expectedOutput": ex['output']})
                if tests:
                    question_data['testCases'] = tests
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(question_data, f, indent=2, ensure_ascii=False)
                        f.write('\n')
                    return len(tests), "db_preserved"
            return len(existing_tests), "db_existing"

        # 2. DSA questions without Solution.py: preserve verified examples/public tests
        sol_path = self.id_to_sol.get(qid)
        if not sol_path or not os.path.exists(sol_path) or not os.path.exists(raw_path):
            existing_tests = question_data.get('testCases') or []
            if not existing_tests:
                tests = []
                for pt in question_data.get('publicTests') or []:
                    if pt.get('input') and pt.get('expectedOutput') and pt['expectedOutput'] != 'null':
                        tests.append(pt)
                if tests:
                    question_data['testCases'] = tests
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(question_data, f, indent=2, ensure_ascii=False)
                        f.write('\n')
                    return len(tests), "dsa_no_sol_preserved"
            return len(existing_tests), "dsa_no_sol"

        # 3. DSA with Solution.py: run dynamic verification and generation
        try:
            with open(raw_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            meta = raw_data.get('metaData')
            if not meta:
                return 0, "no_metadata"
            if isinstance(meta, str):
                meta = json.loads(meta)

            # Skip system design classes without a single entry method
            if meta.get('systemdesign') or 'classname' in meta:
                existing_tests = question_data.get('testCases') or []
                return len(existing_tests), "design_skipped"

            func_name = meta.get('name')
            if not func_name:
                return 0, "no_func_name"

            params = meta.get('params', [])
            ret_type = meta.get('return', {}).get('type', 'unknown') if isinstance(meta.get('return'), dict) else meta.get('return')
            is_void = (ret_type == 'void')
            output_meta = meta.get('output', {})
            param_idx = output_meta.get('paramindex', 0) if is_void else None

            # Load solution module
            spec = importlib.util.spec_from_file_location(f"sol_{slug.replace('-', '_')}", sol_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sol_instance = mod.Solution()
            func = getattr(sol_instance, func_name)

            verified_cases = []
            seen_inputs = set()
            base_parsed = []

            def try_input_lines(lines):
                if len(verified_cases) >= 20:
                    return False
                input_str = '\n'.join(lines)
                if input_str in seen_inputs:
                    return False
                try:
                    parsed_args = [parse_param(lines[j], params[j]['type']) for j in range(len(params))]
                    exec_args = copy.deepcopy(parsed_args)
                    
                    # Run with instruction/step limit tracer protection
                    sys.settrace(make_tracer(50000))
                    try:
                        ret = func(*exec_args)
                    finally:
                        sys.settrace(None)
                    
                    out_arg = exec_args[param_idx] if is_void else None
                    out_str = serialize_result(ret, ret_type, out_arg)
                    
                    if out_str and out_str != "null" and out_str != "":
                        seen_inputs.add(input_str)
                        verified_cases.append({
                            "input": input_str,
                            "expectedOutput": out_str
                        })
                        return True
                except Exception:
                    return False
                return False

            # Step A: Official Public Judge Cases from exampleTestcaseList
            for tc in raw_data.get('exampleTestcaseList') or []:
                lines = tc.strip().split('\n')
                if len(lines) == len(params):
                    if try_input_lines(lines):
                        try:
                            base_parsed.append([json.loads(l) for l in lines])
                        except Exception:
                            pass

            # Step B: Official Public Tests from question JSON
            for pt in question_data.get('publicTests') or []:
                if len(verified_cases) >= 20:
                    break
                lines = pt.get('input', '').strip().split('\n')
                if len(lines) == len(params):
                    if try_input_lines(lines):
                        try:
                            base_parsed.append([json.loads(l) for l in lines])
                        except Exception:
                            pass

            # Step C: Single-Argument Mutations from base cases
            for b_args in list(base_parsed):
                if len(verified_cases) >= 20:
                    break
                for i in range(len(params)):
                    if len(verified_cases) >= 20:
                        break
                    muts = mutate_arg(b_args[i], params[i]['type'])
                    for m in muts:
                        if len(verified_cases) >= 20:
                            break
                        new_args = copy.deepcopy(b_args)
                        new_args[i] = m
                        try_input_lines([json.dumps(a, separators=(',', ':')) for a in new_args])

            # Step D: Coupled (Array, Int) Mutations (e.g. nums + target / k)
            if len(params) == 2 and '[]' in params[0]['type'] and 'int' in params[1]['type']:
                for b_args in list(base_parsed):
                    if len(verified_cases) >= 20:
                        break
                    arr = b_args[0]
                    if isinstance(arr, list) and len(arr) >= 2:
                        candidates_t = [arr[0], arr[-1], arr[0] + arr[1], arr[0] + arr[-1], 0, 1, len(arr), sum(arr)]
                        for ct in candidates_t:
                            if len(verified_cases) >= 20:
                                break
                            try_input_lines([json.dumps(arr, separators=(',', ':')), str(ct)])
                            try_input_lines([json.dumps(arr[::-1], separators=(',', ':')), str(ct)])

            # Step E: Pair template combinations if still < 20
            if len(verified_cases) < 20 and len(params) == 2 and base_parsed:
                p0_muts = mutate_arg(base_parsed[0][0], params[0]['type'])
                p1_muts = mutate_arg(base_parsed[0][1], params[1]['type'])
                for m0 in p0_muts[:15]:
                    for m1 in p1_muts[:15]:
                        if len(verified_cases) >= 20:
                            break
                        try_input_lines([json.dumps(m0, separators=(',', ':')), json.dumps(m1, separators=(',', ':'))])

            # Step F: Cross-pollination between different base cases
            if len(base_parsed) > 1 and len(params) >= 2 and len(verified_cases) < 20:
                for b1 in base_parsed:
                    for b2 in base_parsed:
                        if len(verified_cases) >= 20:
                            break
                        if b1 != b2:
                            hybrid = [b1[0]] + b2[1:]
                            try_input_lines([json.dumps(a, separators=(',', ':')) for a in hybrid])

            # Update question JSON if we generated verified cases
            if verified_cases:
                question_data['testCases'] = verified_cases[:20]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(question_data, f, indent=2, ensure_ascii=False)
                    f.write('\n')
                return len(verified_cases[:20]), "success"
            else:
                return 0, "no_verified_cases"

        except Exception as e:
            return 0, f"error: {str(e)[:50]}"

    def close(self):
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Batch Test Case Engine")
    parser.add_argument('--limit', type=int, default=None, help="Limit number of questions to process")
    parser.add_argument('--slug', type=str, default=None, help="Process single question by slug")
    parser.add_argument('--category', type=str, default=None, help="Process specific subcategory (e.g. arrays)")
    parser.add_argument('--start', type=int, default=0, help="Start offset")
    args = parser.parse_args()

    engine = BatchTestEngine(repo_root='.')
    
    with open('manifests/questions-index.json', 'r', encoding='utf-8') as f:
        idx = json.load(f)
    questions = idx['questions']

    if args.slug:
        questions = [q for q in questions if q['slug'] == args.slug]
    elif args.category:
        questions = [q for q in questions if q.get('subcategory') == args.category]

    if args.start:
        questions = questions[args.start:]
    if args.limit:
        questions = questions[:args.limit]

    print(f"Starting Batch Test Engine for {len(questions)} questions...", flush=True)
    t0 = time.time()
    success_count = 0
    full_20_count = 0
    total_testcases = 0

    try:
        for i, q in enumerate(questions):
            cnt, status = engine.process_question(q)
            if cnt > 0:
                success_count += 1
                total_testcases += cnt
                if cnt >= 20:
                    full_20_count += 1
            if (i + 1) % 50 == 0 or (i + 1) == len(questions):
                el = time.time() - t0
                rate = (i + 1) / el if el > 0 else 0
                print(f"[{i+1}/{len(questions)}] Processed. 20/20: {full_20_count}, Any: {success_count}, Total TCs: {total_testcases} ({rate:.1f} q/s)", flush=True)
    finally:
        engine.close()

    total_el = time.time() - t0
    report_data = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "totalProcessed": len(questions),
        "withTestCases": success_count,
        "withFull20": full_20_count,
        "totalTestCases": total_testcases,
        "elapsedSeconds": round(total_el, 2),
        "rateQuestionsPerSec": round(len(questions) / total_el, 1) if total_el > 0 else 0
    }
    os.makedirs('reports', exist_ok=True)
    with open('reports/testcase-generation-report.json', 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2)

    print(f"\nCompleted in {total_el:.1f}s.", flush=True)
    print(f"Total processed: {len(questions)}", flush=True)
    print(f"Questions with test cases: {success_count}", flush=True)
    print(f"Questions with 20/20 test cases: {full_20_count}", flush=True)
    print(f"Total test cases generated: {total_testcases}", flush=True)
    print(f"Report saved to reports/testcase-generation-report.json", flush=True)
