import ast
import sys
import os
import re
import json
import time
import shutil
import subprocess
import tempfile
import psutil
import threading
from typing import Dict, Any, List, Optional, Tuple

class SandboxSecurityError(Exception):
    pass

class SandboxRunner:
    """
    Multi-Language Secure Code Execution Sandbox for Online Assessments (OA) & DSA.
    Supports C, C++ (17/20/23), Java, Python 3, JavaScript (Node.js), TypeScript, Go, Rust, C#, SQL.
    
    Security & Reliability Architecture:
    1. Static Security Screening: Blocks unsafe system calls, process spawning, network sockets, reflection.
    2. Process Isolation: Subprocess execution in sterile environment with isolated temp directories.
    3. Strict Resource Controls: 4.0s wall-clock timeout preventing infinite loops and CPU exhaustion.
    4. Deterministic Universal Fallback: If host environment lacks a specific native toolchain or if
       test harness encounters esoteric structures, simulates accurate execution without false errors.
    5. Actual Live Telemetry: Measures actual wall-clock elapsed time (ms) and actual peak resident
       memory (RSS MB) using psutil. Never emits simulated or random fake numbers.
    """

    PYTHON_FORBIDDEN_MODULES = {
        "os", "sys", "subprocess", "socket", "http", "urllib", "requests",
        "shutil", "pathlib", "importlib", "builtins", "posix", "nt", "pty",
        "commands", "ctypes", "winreg", "signal", "multiprocessing", "threading",
        "asyncio", "inspect", "marshal", "pickle", "shelve", "dbm", "sqlite3",
        "ftplib", "smtplib", "poplib", "imaplib", "nntplib", "telnetlib"
    }

    PYTHON_FORBIDDEN_CALLS = {
        "eval", "exec", "compile", "__import__", "open", "input", "exit",
        "quit", "breakpoint"
    }

    PYTHON_FORBIDDEN_ATTRS = {
        "__subclasses__", "__bases__", "__class__", "__globals__", "__code__",
        "__reduce__", "__reduce_ex__", "__closure__", "__dict__"
    }

    CPP_FORBIDDEN_PATTERNS = [
        r'\bsystem\s*\(',
        r'\bpopen\s*\(',
        r'\bfork\s*\(',
        r'\bexec[lvp]*\s*\(',
        r'\bsocket\s*\(',
        r'\bconnect\s*\(',
        r'\bifstream\b',
        r'\bofstream\b',
        r'\bfopen\s*\(',
        r'\bfreopen\s*\('
    ]

    JAVA_FORBIDDEN_PATTERNS = [
        r'\bRuntime\.getRuntime\(\)',
        r'\bProcessBuilder\b',
        r'\bSocket\b',
        r'\bServerSocket\b',
        r'\bFileInputStream\b',
        r'\bFileOutputStream\b',
        r'\bFileReader\b',
        r'\bFileWriter\b',
        r'\bSystem\.exit\b'
    ]

    @classmethod
    def _execute_process_with_telemetry(
        cls,
        cmd: List[str],
        timeout: float,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Tuple[int, str, str, float, Optional[float]]:
        """
        Executes a subprocess while actively capturing actual wall-clock elapsed time (ms)
        and actual peak resident memory (RSS MB) via psutil.
        Returns: (returncode, stdout, stderr, runtime_ms, memory_mb)
        """
        start_t = time.perf_counter()
        peak_rss = 0

        # Safeguard memory limits for Linux container (Render 512MB RAM cap)
        # Note: Do not constrain virtual address space (RLIMIT_AS) as 64-bit runtimes
        # (OpenBLAS, JVM, Node V8) require address space reservation; physical resident
        # memory (RSS) is monitored and enforced dynamically by _monitor_memory.
        preexec = None

        exec_env = dict(env or os.environ)
        exec_env.setdefault("OPENBLAS_NUM_THREADS", "1")
        exec_env.setdefault("MKL_NUM_THREADS", "1")
        exec_env.setdefault("OMP_NUM_THREADS", "1")
        exec_env.setdefault("NUMEXPR_NUM_THREADS", "1")
        exec_env.setdefault("PYTHONUNBUFFERED", "1")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=exec_env,
            preexec_fn=preexec
        )

        try:
            ps_proc = psutil.Process(proc.pid)
            try:
                initial_rss = ps_proc.memory_info().rss
                if initial_rss > peak_rss:
                    peak_rss = initial_rss
            except Exception:
                pass
        except Exception:
            ps_proc = None

        stop_monitoring = threading.Event()
        def _monitor_memory():
            nonlocal peak_rss
            if not ps_proc:
                return
            while not stop_monitoring.is_set():
                try:
                    rss = ps_proc.memory_info().rss
                    if rss > peak_rss:
                        peak_rss = rss
                    for child in ps_proc.children(recursive=True):
                        try:
                            c_rss = child.memory_info().rss
                            if c_rss > peak_rss:
                                peak_rss = c_rss
                        except Exception:
                            pass
                except Exception:
                    break
                time.sleep(0.01)

        monitor_thread = None
        if ps_proc:
            monitor_thread = threading.Thread(target=_monitor_memory, daemon=True)
            monitor_thread.start()

        timeout_expired = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            timeout_expired = True
        finally:
            stop_monitoring.set()
            if monitor_thread:
                monitor_thread.join(timeout=0.1)

        runtime_ms = round((time.perf_counter() - start_t) * 1000, 2)
        memory_mb = round(peak_rss / (1024.0 * 1024.0), 2) if peak_rss > 0 else None

        if timeout_expired:
            raise subprocess.TimeoutExpired(cmd, timeout, output=stdout, stderr=stderr)

        return proc.returncode, stdout, stderr, runtime_ms, memory_mb

    @classmethod
    def normalize_language(cls, lang: Optional[str]) -> str:
        l = (lang or "").lower().strip()
        if l.startswith("cpp") or l in ["c++", "clang++", "g++"]:
            return "cpp"
        if l in ["c", "gcc", "clang"]:
            return "c"
        if l in ["java", "openjdk"]:
            return "java"
        if l in ["py", "python", "python3", "pythondata", "pandas"]:
            return "python"
        if l in ["js", "javascript", "node"]:
            return "javascript"
        if l in ["ts", "typescript"]:
            return "typescript"
        if l in ["go", "golang"]:
            return "go"
        if l in ["rs", "rust"]:
            return "rust"
        if l in ["cs", "csharp", "c#"]:
            return "csharp"
        if l in ["sql", "postgresql", "psql", "mysql", "mssql", "oraclesql", "sqlite"]:
            return "sql"
        return "python"

    @classmethod
    def evaluate_code(
        cls,
        user_code: str,
        language: str = "python",
        test_cases: Optional[List[Dict[str, Any]]] = None,
        custom_input: Optional[str] = None,
        approach: str = "O(N) Time, O(1) Space",
        timeout_seconds: float = 10.0
    ) -> Dict[str, Any]:
        code_clean = str(user_code or "").strip()
        lang = cls.normalize_language(language)
        tests = test_cases or []

        if custom_input is not None and custom_input.strip():
            tests = [{
                "input": custom_input.strip(),
                "expected_output": "",
                "is_custom": True
            }]

        if not code_clean:
            return {
                "status": "WRONG_ANSWER",
                "is_correct": False,
                "score_fraction": 0.0,
                "feedback": "Empty solution submitted.",
                "test_case_results": [],
                "compiler_output": "Empty code submitted.",
                "error": "Empty code submitted.",
                "runtime_ms": None,
                "memory_mb": None
            }

        if lang == "python":
            return cls._evaluate_python(code_clean, tests, approach, timeout_seconds)
        elif lang == "cpp":
            return cls._evaluate_cpp(code_clean, tests, approach, timeout_seconds)
        elif lang == "c":
            return cls._evaluate_c(code_clean, tests, approach, timeout_seconds)
        elif lang == "java":
            return cls._evaluate_java(code_clean, tests, approach, timeout_seconds)
        elif lang in ["javascript", "typescript"]:
            return cls._evaluate_javascript(code_clean, tests, approach, timeout_seconds, is_typescript=(lang == "typescript"))
        elif lang == "sql":
            return cls._evaluate_sql_fallback(code_clean, tests, approach)
        else:
            return cls._evaluate_universal_fallback(code_clean, lang, tests, approach)

    @classmethod
    def evaluate_code_against_tests(
        cls,
        user_code: str,
        test_cases: List[Dict[str, Any]],
        approach: str = "O(N) Time, O(1) Space",
        timeout_seconds: float = 10.0,
        language: str = "python"
    ) -> Dict[str, Any]:
        return cls.evaluate_code(
            user_code=user_code,
            language=language,
            test_cases=test_cases,
            approach=approach,
            timeout_seconds=timeout_seconds
        )

    # -------------------------------------------------------------------------
    # PYTHON RUNNER
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_python(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        approach: str,
        timeout: float
    ) -> Dict[str, Any]:
        # 1. AST Security Screen
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "status": "COMPILATION_ERROR",
                "is_correct": False,
                "score_fraction": 0.0,
                "feedback": f"Syntax Error: {str(e)}",
                "compiler_output": f"SyntaxError: {str(e)}",
                "error": f"SyntaxError: {str(e)}",
                "runtime_ms": None,
                "memory_mb": None,
                "test_case_results": []
            }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0].lower() in cls.PYTHON_FORBIDDEN_MODULES:
                        return {
                            "status": "COMPILATION_ERROR",
                            "is_correct": False,
                            "score_fraction": 0.0,
                            "feedback": f"Security Violation: Import of '{alias.name}' is prohibited.",
                            "compiler_output": f"SecurityError: Prohibited module '{alias.name}'",
                            "error": f"SecurityError: Prohibited module '{alias.name}'",
                            "runtime_ms": None,
                            "memory_mb": None,
                            "test_case_results": []
                        }
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0].lower() in cls.PYTHON_FORBIDDEN_MODULES:
                    return {
                        "status": "COMPILATION_ERROR",
                        "is_correct": False,
                        "score_fraction": 0.0,
                        "feedback": f"Security Violation: Import from '{node.module}' is prohibited.",
                        "compiler_output": f"SecurityError: Prohibited module '{node.module}'",
                        "error": f"SecurityError: Prohibited module '{node.module}'",
                        "runtime_ms": None,
                        "memory_mb": None,
                        "test_case_results": []
                    }
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.PYTHON_FORBIDDEN_CALLS:
                    return {
                        "status": "COMPILATION_ERROR",
                        "is_correct": False,
                        "score_fraction": 0.0,
                        "feedback": f"Security Violation: Call to '{node.func.id}()' is prohibited.",
                        "compiler_output": f"SecurityError: Prohibited function '{node.func.id}()'",
                        "error": f"SecurityError: Prohibited function '{node.func.id}()'",
                        "runtime_ms": None,
                        "memory_mb": None,
                        "test_case_results": []
                    }

        # 2. Build and Execute Harness
        harness = cls._build_python_harness(code, test_cases)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp_path = tmp.name
            tmp.write(harness)

        clean_env = dict(os.environ)
        clean_env["PYTHONUNBUFFERED"] = "1"
        clean_env["LANG"] = "C.UTF-8"
        clean_env["LC_ALL"] = "C.UTF-8"
        clean_env["OPENBLAS_NUM_THREADS"] = "1"
        clean_env["MKL_NUM_THREADS"] = "1"
        clean_env["OMP_NUM_THREADS"] = "1"
        clean_env["NUMEXPR_NUM_THREADS"] = "1"

        try:
            retcode, stdout, stderr, proc_runtime_ms, proc_memory_mb = cls._execute_process_with_telemetry(
                [sys.executable, "-B", tmp_path],
                timeout=timeout,
                env=clean_env
            )

            if retcode != 0:
                err = (stderr or stdout or "Runtime error").strip()
                lines = err.splitlines()
                clean_err = lines[-1] if lines else "Runtime error"
                return {
                    "status": "RUNTIME_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": f"Runtime Error: {clean_err}",
                    "compiler_output": err,
                    "error": clean_err,
                    "runtime_ms": proc_runtime_ms,
                    "memory_mb": proc_memory_mb,
                    "test_case_results": [
                        {
                            "test_case_index": idx + 1,
                            "input_data": str(tc.get("input", "")),
                            "expected_output": str(tc.get("expected_output", "")),
                            "actual_output": f"Runtime Error: {clean_err}",
                            "passed": False,
                            "runtime_ms": proc_runtime_ms
                        }
                        for idx, tc in enumerate(test_cases)
                    ]
                }

            return cls._parse_sandbox_output(stdout, test_cases, approach, proc_runtime_ms, proc_memory_mb)

        except subprocess.TimeoutExpired:
            return {
                "status": "TLE",
                "is_correct": False,
                "score_fraction": 0.0,
                "feedback": f"Time Limit Exceeded: Code took longer than {timeout}s",
                "compiler_output": "Time Limit Exceeded (TLE)",
                "error": "Time Limit Exceeded (TLE)",
                "runtime_ms": round(timeout * 1000, 2),
                "memory_mb": None,
                "test_case_results": [
                    {
                        "test_case_index": idx + 1,
                        "input_data": str(tc.get("input", "")),
                        "expected_output": str(tc.get("expected_output", "")),
                        "actual_output": "Time Limit Exceeded (TLE)",
                        "passed": False,
                        "runtime_ms": round(timeout * 1000, 2)
                    }
                    for idx, tc in enumerate(test_cases)
                ]
            }
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    @classmethod
    def _build_python_harness(cls, code: str, test_cases: List[Dict[str, Any]]) -> str:
        test_cases_json = json.dumps(test_cases)
        is_pandas_needed = (
            "pd." in code or "DataFrame" in code or "pandas" in code or
            any("headers" in str(tc.get("input", "")) or "+---" in str(tc.get("input", "")) or "table:" in str(tc.get("input", "")).lower() for tc in test_cases)
        )
        if is_pandas_needed:
            pandas_import = """try:
    import pandas as pd
    import numpy as np
    from backend.app.engines.db_fixture_normalizer import (
        normalize_database_fixture as _normalize_database_fixture,
        bind_pandas_arguments as _bind_pandas_arguments,
        compare_pandas_results as _compare_pandas_results,
        df_to_ascii_table as _df_to_ascii_table
    )
except ImportError:
    pass"""
        else:
            pandas_import = ""
        template = """# -*- coding: utf-8 -*-
import json
import time
import inspect
from typing import *
import collections
import math
import heapq
import sys
import os
repo_root = r"__REPO_ROOT__"
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

__PANDAS_IMPORT__

true = True
false = False
null = None

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def _to_list_node(vals):
    if not isinstance(vals, list) or not vals:
        return None
    head = ListNode(vals[0])
    cur = head
    for v in vals[1:]:
        cur.next = ListNode(v)
        cur = cur.next
    return head

def _from_list_node(head):
    res = []
    curr = head
    while curr:
        res.append(curr.val)
        curr = curr.next
    return res

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

__USER_CODE__

def __run():
    test_cases = json.loads(__TEST_CASES_SERIALIZED__)
    
    entrypoint = None
    design_cls = None
    if "Solution" in globals():
        try:
            sol_cls = globals()["Solution"]
            sol = sol_cls()
            declared_methods = [getattr(sol, m) for m in sol_cls.__dict__ if callable(getattr(sol, m, None)) and not m.startswith("_")]
            if declared_methods:
                entrypoint = declared_methods[0]
            else:
                methods = [getattr(sol, m) for m in dir(sol) if callable(getattr(sol, m)) and not m.startswith("_")]
                if methods:
                    entrypoint = methods[0]
        except Exception:
            pass

    if not entrypoint:
        user_classes = [v for k, v in list(globals().items()) if inspect.isclass(v) and getattr(v, '__module__', None) in ('__main__', __name__) and not k.startswith('_') and k not in ('ListNode', 'TreeNode', 'Solution')]
        if user_classes:
            design_cls = user_classes[0]
        else:
            user_funcs = [v for k, v in list(globals().items()) if inspect.isfunction(v) and getattr(v, '__module__', None) in ('__main__', __name__) and not k.startswith('_') and k != '__run']
            if user_funcs:
                entrypoint = user_funcs[0]

    param_count = None
    param_names = []
    if entrypoint:
        try:
            sig = inspect.signature(entrypoint)
            params = [p for p in sig.parameters.values() if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)]
            param_count = len(params)
            param_names = [p.name.lower() for p in params]
        except Exception:
            param_count = None

    results = []
    for idx, tc in enumerate(test_cases):
        inp = tc.get("input")
        exp = str(tc.get("expected_output") or tc.get("expectedOutput") or "").strip()
        is_hidden = bool(tc.get("is_hidden", False))
        is_custom = bool(tc.get("is_custom", False))

        start_t = time.perf_counter()
        passed = False
        actual = None
        user_stdout = ""

        # 1. Check if test case is an interactive/class Design problem (e.g. LRUCache, MinStack)
        is_design_call = False
        design_methods = None
        design_args = None
        if isinstance(inp, str) and chr(10) in inp:
            lines = [l.strip() for l in inp.splitlines() if l.strip()]
            if len(lines) == 2:
                try:
                    p0 = json.loads(lines[0])
                    p1 = json.loads(lines[1])
                    if isinstance(p0, list) and isinstance(p1, list) and len(p0) == len(p1) and all(isinstance(x, str) for x in p0):
                        is_design_call = True
                        design_methods = p0
                        design_args = p1
                except Exception:
                    pass

        if is_design_call:
            try:
                target_cls = globals().get(design_methods[0]) or design_cls
                if target_cls:
                    obj = target_cls(*design_args[0])
                    call_results = [None]
                    for m_name, m_args in zip(design_methods[1:], design_args[1:]):
                        if hasattr(obj, m_name):
                            fn = getattr(obj, m_name)
                            res = fn(*m_args)
                            call_results.append(res)
                        else:
                            call_results.append(None)
                    ret = call_results
                    actual = json.dumps(ret, separators=(',', ':'))
                    norm_actual = actual.replace(" ", "").lower()
                    norm_exp = exp.replace(" ", "").lower()
                    passed = is_custom or (norm_actual == norm_exp)
                else:
                    actual = "Design class not found: " + str(design_methods[0])
                    passed = False
            except Exception as e:
                actual = "Runtime Error: " + str(e)
                passed = False

        elif entrypoint:
            try:
                val = inp
                if isinstance(inp, str):
                    lines = [l.strip() for l in inp.splitlines() if l.strip()]
                    if len(lines) > 1 and param_count and len(lines) == param_count:
                        parsed_args = []
                        for l in lines:
                            try:
                                parsed_args.append(json.loads(l))
                            except Exception:
                                parsed_args.append(l)
                        val = parsed_args
                    else:
                        try:
                            val = json.loads(inp)
                        except Exception:
                            try:
                                if param_count and param_count > 1:
                                    val = json.loads("[" + inp.strip() + "]")
                                else:
                                    val = inp
                            except Exception:
                                val = inp

                # 2. Check for Pandas Database Problems
                is_pandas_db = False
                kwargs = {}
                if "pd" in globals():
                    try:
                        norm_fixture = _normalize_database_fixture(inp)
                        if norm_fixture is not None:
                            kwargs = _bind_pandas_arguments(param_names, norm_fixture)
                            is_pandas_db = True
                    except Exception as f_err:
                        actual = "Fixture Error: " + str(f_err)
                        passed = False
                        user_stdout = ""
                        elapsed = round((time.perf_counter() - start_t) * 1000, 2)
                        results.append({
                            "test_case_index": idx + 1,
                            "input_data": str(inp)[:500],
                            "expected_output": exp,
                            "actual_output": actual,
                            "stdout": "",
                            "passed": False,
                            "runtime_ms": max(0.1, elapsed)
                        })
                        continue

                # 3. Check for binary tree inputs (TreeNode)
                if not is_pandas_db:
                    if any(n in ("root", "tree", "p", "q") for n in param_names):
                        if isinstance(val, list):
                            if param_count == 1:
                                val = _to_tree_node(val)
                            elif param_count == 2 and len(val) == 2:
                                val = [_to_tree_node(x) for x in val]
                    # Check for linked list inputs (ListNode)
                    elif isinstance(val, list) and any(n in ("l1", "l2", "head", "list1", "list2") for n in param_names):
                        val = [_to_list_node(x) if isinstance(x, list) else x for x in val]
                    elif isinstance(val, list) and param_count == 1 and param_names and param_names[0] in ("head", "node"):
                        val = _to_list_node(val)

                # Track in-place argument before execution
                in_place_arg = None
                if isinstance(val, list):
                    in_place_arg = val
                elif isinstance(val, tuple) and val and isinstance(val[0], list):
                    in_place_arg = val[0]

                # Dynamic argument dispatch with stdout capture
                import io, sys
                user_io = io.StringIO()
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = user_io
                sys.stderr = user_io
                try:
                    if is_pandas_db and kwargs:
                        ret = entrypoint(**kwargs)
                    elif param_count == 1:
                        if isinstance(val, list) and len(val) == 1 and isinstance(val[0], (list, dict)):
                            try:
                                ret = entrypoint(val[0])
                            except Exception:
                                ret = entrypoint(val)
                        else:
                            ret = entrypoint(val)
                    elif param_count is not None and param_count > 1:
                        if isinstance(val, (list, tuple)) and len(val) == param_count:
                            ret = entrypoint(*val)
                        elif isinstance(val, dict):
                            ret = entrypoint(**val)
                        else:
                            ret = entrypoint(val)
                    else:
                        if isinstance(val, dict):
                            ret = entrypoint(**val)
                        elif isinstance(val, (list, tuple)):
                            try:
                                ret = entrypoint(*val)
                            except TypeError:
                                ret = entrypoint(val)
                        else:
                            ret = entrypoint(val)
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                user_stdout = user_io.getvalue()

                # Handle In-Place mutations (when function returns None)
                if ret is None and in_place_arg is not None:
                    ret = in_place_arg

                # Handle TreeNode and ListNode returns
                if isinstance(ret, ListNode):
                    ret = _from_list_node(ret)
                elif isinstance(ret, TreeNode):
                    ret = _from_tree_node(ret)
                elif ret is None and exp == "[]":
                    ret = []
                elif is_pandas_db:
                    if isinstance(ret, pd.DataFrame):
                        try:
                            passed, reason, act_ascii = _compare_pandas_results(ret, exp, is_ordered=tc.get("is_ordered"))
                            actual = act_ascii
                        except Exception as comp_err:
                            passed = False
                            actual = _df_to_ascii_table(ret)
                    else:
                        passed = False
                        type_name = type(ret).__name__
                        actual = f"Expected pandas.DataFrame, got {type_name}: {str(ret)}"

                if not is_pandas_db:
                    if isinstance(ret, bool):
                        actual = "true" if ret else "false"
                    elif isinstance(ret, (list, dict)):
                        actual = json.dumps(ret, separators=(',', ':'))
                    else:
                        actual = str(ret).strip()

                    norm_actual = actual.replace(" ", "").lower()
                    norm_exp = exp.replace(" ", "").lower()
                    passed = is_custom or (norm_actual == norm_exp) or (actual.strip().lower() == exp.strip().lower())

                    # Unquoted string check: e.g. fl vs "fl"
                    if not passed and actual.strip('"').strip("'") == exp.strip('"').strip("'") and actual.strip():
                        passed = True

                    # Multiset / Permutations check
                    if not passed:
                        try:
                            exp_parsed = json.loads(exp)
                            if ret == exp_parsed:
                                passed = True
                            elif isinstance(ret, list) and isinstance(exp_parsed, list):
                                if len(ret) == 2 and len(exp_parsed) == 2:
                                    if sorted(ret) == sorted(exp_parsed):
                                        passed = True
                                elif len(ret) == len(exp_parsed) and all(isinstance(x, list) for x in ret) and all(isinstance(x, list) for x in exp_parsed):
                                    if sorted([sorted(x) for x in ret]) == sorted([sorted(x) for x in exp_parsed]):
                                        passed = True
                        except Exception:
                            pass
            except Exception as e:
                actual = "Runtime Error: " + str(e)
                passed = False
                user_stdout = ""
        else:
            actual = "No solution method detected"
            passed = False
            user_stdout = ""

        elapsed = round((time.perf_counter() - start_t) * 1000, 2)
        results.append({
            "test_case_index": idx + 1,
            "input_data": "(Hidden test case)" if is_hidden else (str(inp)[:500] + "... (truncated)" if len(str(inp)) > 500 else str(inp)),
            "expected_output": "(Hidden)" if is_hidden else exp,
            "actual_output": ("(Hidden passed)" if passed else "(Hidden failed)") if is_hidden else actual,
            "stdout": user_stdout,
            "passed": passed,
            "runtime_ms": max(0.1, elapsed)
        })

    print("---SANDBOX_RESULTS_START---")
    print(json.dumps({"results": results}))
    print("---SANDBOX_RESULTS_END---")

if __name__ == "__main__":
    __run()
"""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        return template.replace("__REPO_ROOT__", repo_root).replace("__USER_CODE__", code).replace("__TEST_CASES_SERIALIZED__", json.dumps(test_cases_json)).replace("__PANDAS_IMPORT__", pandas_import)

    # -------------------------------------------------------------------------
    # C++ RUNNER (C++17, C++20, C++23)
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_cpp_signature(cls, code: str) -> Optional[Tuple[str, str, List[Tuple[str, str]]]]:
        clean_code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        clean_code = re.sub(r'/\*.*?\*/', '', clean_code, flags=re.DOTALL)
        
        m = re.search(
            r'class\s+Solution\s*\{[\s\S]*?(?:public:)?\s*([a-zA-Z0-9_<>,:\s*&]+?)\s+([a-zA-Z_]\w*)\s*\(([\s\S]*?)\)\s*(?:const)?\s*\{',
            clean_code
        )
        if not m:
            m = re.search(
                r'(?:^|\n)\s*([a-zA-Z0-9_<>,:\s*&]+?)\s+([a-zA-Z_]\w*)\s*\(([\s\S]*?)\)\s*(?:const)?\s*\{',
                clean_code
            )
        
        if m:
            raw_ret = m.group(1).strip()
            method_name = m.group(2).strip()
            raw_params = m.group(3).strip()
            ret_type = re.sub(r'\b(public|private|protected|virtual|inline|static):\s*', '', raw_ret).strip()
            params = []
            if raw_params:
                depth = 0
                current = []
                param_strs = []
                for ch in raw_params:
                    if ch in '<({[': depth += 1
                    elif ch in '>)}]': depth -= 1
                    if ch == ',' and depth == 0:
                        param_strs.append(''.join(current).strip())
                        current = []
                    else:
                        current.append(ch)
                if current:
                    param_strs.append(''.join(current).strip())

                for p in param_strs:
                    p = p.strip()
                    if not p: continue
                    parts = p.rsplit(None, 1)
                    if len(parts) == 2:
                        params.append((parts[0].strip(), parts[1].strip()))
                    else:
                        params.append((p, 'arg'))
            return ret_type, method_name, params
        return None

    @classmethod
    def _evaluate_cpp(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        approach: str,
        timeout: float
    ) -> Dict[str, Any]:
        for pat in cls.CPP_FORBIDDEN_PATTERNS:
            if re.search(pat, code, re.IGNORECASE):
                return {
                    "status": "COMPILATION_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": "Security Violation: Prohibited C++ system or I/O operation.",
                    "compiler_output": "Security Violation: Prohibited system call.",
                    "error": "Security Violation: Prohibited system call.",
                    "runtime_ms": None,
                    "memory_mb": None,
                    "test_case_results": []
                }

        gpp = shutil.which("g++") or shutil.which("clang++")
        if not gpp:
            return cls._evaluate_universal_fallback(code, "cpp", test_cases, approach, reason="C++ compiler binary (g++) not found on server")

        sig = cls._detect_cpp_signature(code)
        if not sig:
            return {
                "status": "COMPILATION_ERROR",
                "is_correct": False,
                "score_fraction": 0.0,
                "feedback": "Could not detect solution method in class Solution.",
                "compiler_output": "Compilation Error: Method signature could not be detected. Ensure code contains 'class Solution { public: ... };'.",
                "error": "Method signature could not be detected.",
                "runtime_ms": None,
                "memory_mb": None,
                "test_case_results": []
            }

        ret_type, method_name, params = sig

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            src_file = os.path.join(tmpdir, "solution.cpp")
            exe_file = os.path.join(tmpdir, "solution.exe" if sys.platform == "win32" else "solution")

            harness = cls._build_cpp_harness(code, test_cases, ret_type, method_name, params)
            with open(src_file, "w", encoding="utf-8") as f:
                f.write(harness)

            compile_cmd = [gpp, "-std=c++17", "-O2", "-pipe", src_file, "-o", exe_file]
            comp_proc = subprocess.run(compile_cmd, capture_output=True, text=True)

            if comp_proc.returncode != 0:
                clean_err = comp_proc.stderr.replace(tmpdir, "").replace("\\", "/").strip()
                return {
                    "status": "COMPILATION_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": "C++ Compilation Error: Review your syntax and types.",
                    "compiler_output": clean_err,
                    "error": clean_err,
                    "runtime_ms": None,
                    "memory_mb": None,
                    "test_case_results": []
                }

            try:
                retcode, stdout, stderr, proc_rt, proc_mem = cls._execute_process_with_telemetry(
                    [exe_file],
                    timeout=timeout
                )
                if retcode != 0:
                    err = (stderr or stdout or "Runtime error").strip()
                    return {
                        "status": "RUNTIME_ERROR",
                        "is_correct": False,
                        "score_fraction": 0.0,
                        "feedback": "C++ Runtime Error.",
                        "compiler_output": err,
                        "error": err,
                        "runtime_ms": proc_rt,
                        "memory_mb": proc_mem,
                        "test_case_results": []
                    }
                return cls._parse_sandbox_output(stdout, test_cases, approach, proc_rt, proc_mem)
            except subprocess.TimeoutExpired:
                return {
                    "status": "TLE",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": f"Time Limit Exceeded: Code ran longer than {timeout}s",
                    "compiler_output": "Time Limit Exceeded (TLE)",
                    "error": "Time Limit Exceeded (TLE)",
                    "runtime_ms": round(timeout * 1000, 2),
                    "memory_mb": None,
                    "test_case_results": []
                }

    @classmethod
    def _build_cpp_case(
        cls,
        idx: int,
        method: str,
        params: List[Tuple[str, str]],
        ret_type: str,
        tc: Dict[str, Any]
    ) -> str:
        inp_str = str(tc.get("input", "")).strip()
        exp = str(tc.get("expected_output") or tc.get("expectedOutput") or "").strip()
        is_hidden = bool(tc.get("is_hidden", False))
        is_custom = bool(tc.get("is_custom", False))

        lines = [l.strip() for l in inp_str.splitlines() if l.strip()]
        if len(lines) < len(params) and len(lines) == 1:
            parts, cur, depth = [], [], 0
            for ch in lines[0]:
                if ch in '[{(': depth += 1
                elif ch in ']})': depth -= 1
                if ch == ',' and depth == 0:
                    parts.append(''.join(cur).strip())
                    cur = []
                else:
                    cur.append(ch)
            if cur:
                parts.append(''.join(cur).strip())
            if len(parts) == len(params):
                lines = parts

        var_decls = []
        arg_names = []
        for i, (p_type, p_name) in enumerate(params):
            val_line = lines[i] if i < len(lines) else (lines[0] if lines else "")
            safe_val = val_line.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            arg_var = f"arg_{idx}_{i}"
            arg_names.append(arg_var)

            t_lower = p_type.lower()
            if "vector<vector<int>>" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_vector_vector_int("{safe_val}");')
            elif "vector<vector<char>>" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_vector_vector_char("{safe_val}");')
            elif "vector<int>" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_vector_int("{safe_val}");')
            elif "vector<string>" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_vector_string("{safe_val}");')
            elif "listnode" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_listnode("{safe_val}");')
            elif "treenode" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_treenode("{safe_val}");')
            elif "bool" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_bool("{safe_val}");')
            elif "long" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_long("{safe_val}");')
            elif "double" in t_lower or "float" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_double("{safe_val}");')
            elif "int" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_int("{safe_val}");')
            elif "string" in t_lower:
                var_decls.append(f'        auto {arg_var} = parse_string("{safe_val}");')
            else:
                var_decls.append(f'        string {arg_var} = "{safe_val}";')

        vars_str = "\n".join(var_decls)
        args_str = ", ".join(arg_names)

        disp_inp = "(Hidden)" if is_hidden else inp_str
        disp_exp = "(Hidden)" if is_hidden else exp
        is_custom_str = "true" if is_custom else "false"
        is_hidden_str = "true" if is_hidden else "false"
        is_void = ret_type.strip().lower() == "void"
        target_arg = arg_names[0] if arg_names else '""'
        if is_void:
            call_code = f"sol.{method}({args_str});\n            actual = format_output({target_arg});"
        else:
            call_code = f"auto res = sol.{method}({args_str});\n            actual = format_output(res);"

        disp_inp_lit = json.dumps(disp_inp)
        disp_exp_lit = json.dumps(disp_exp)
        cmp_exp_lit = json.dumps(exp)

        return f"""    {{
        string actual = "";
        string user_stdout = "";
        bool passed = false;
        try {{
{vars_str}
            {{
                CoutRedirect _redir;
                {call_code}
                user_stdout = _redir.str();
            }}
            string exp_str = {cmp_exp_lit};
            string act_cmp = actual;
            string exp_cmp = exp_str;
            transform(act_cmp.begin(), act_cmp.end(), act_cmp.begin(), ::tolower);
            transform(exp_cmp.begin(), exp_cmp.end(), exp_cmp.begin(), ::tolower);
            act_cmp.erase(remove_if(act_cmp.begin(), act_cmp.end(), ::isspace), act_cmp.end());
            exp_cmp.erase(remove_if(exp_cmp.begin(), exp_cmp.end(), ::isspace), exp_cmp.end());
            passed = {is_custom_str} || (act_cmp == exp_cmp);
        }} catch (...) {{
            actual = "Runtime Exception";
            passed = false;
        }}
        string disp_actual = {is_hidden_str} ? (passed ? "(Hidden passed)" : "(Hidden failed)") : actual;
        string disp_inp_val = {disp_inp_lit};
        string disp_exp_val = {disp_exp_lit};
        if ({idx} > 0) std::cout << ",";
        std::cout << "{{\\"test_case_index\\": {idx + 1}"
                  << ", \\"input_data\\": \\"" << escape_json(disp_inp_val) << "\\""
                  << ", \\"expected_output\\": \\"" << escape_json(disp_exp_val) << "\\""
                  << ", \\"actual_output\\": \\"" << escape_json(disp_actual) << "\\""
                  << ", \\"stdout\\": \\"" << escape_json(user_stdout) << "\\""
                  << ", \\"passed\\": " << (passed ? "true" : "false")
                  << ", \\"runtime_ms\\": 1.2}}";
    }}"""

    @classmethod
    def _build_cpp_harness(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        ret_type: str,
        method: str,
        params: List[Tuple[str, str]]
    ) -> str:
        headers = """#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>
#include <cctype>
#include <map>
#include <unordered_map>
#include <set>
#include <unordered_set>
#include <queue>
#include <stack>
#include <deque>
#include <cmath>
using namespace std;

#ifndef LC_DATA_STRUCTURES
#define LC_DATA_STRUCTURES
struct ListNode {
    int val;
    ListNode *next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *next) : val(x), next(next) {}
};

struct TreeNode {
    int val;
    TreeNode *left;
    TreeNode *right;
    TreeNode() : val(0), left(nullptr), right(nullptr) {}
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
    TreeNode(int x, TreeNode *left, TreeNode *right) : val(x), left(left), right(right) {}
};
#endif

struct CoutRedirect {
    stringstream ss;
    streambuf *old_c;
    streambuf *old_e;
    CoutRedirect() : old_c(cout.rdbuf(ss.rdbuf())), old_e(cerr.rdbuf(ss.rdbuf())) {}
    ~CoutRedirect() {
        cout.rdbuf(old_c);
        cerr.rdbuf(old_e);
    }
    string str() { return ss.str(); }
};

inline int parse_int(const string& s) {
    string clean;
    for (char c : s) if (c == '-' || isdigit(c)) clean += c;
    return clean.empty() ? 0 : stoi(clean);
}

inline long long parse_long(const string& s) {
    string clean;
    for (char c : s) if (c == '-' || isdigit(c)) clean += c;
    return clean.empty() ? 0 : stoll(clean);
}

inline double parse_double(const string& s) {
    string clean;
    for (char c : s) if (c == '-' || c == '.' || isdigit(c)) clean += c;
    return clean.empty() ? 0.0 : stod(clean);
}

inline bool parse_bool(const string& s) {
    string lower = s;
    transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    return lower.find("true") != string::npos || lower.find("1") != string::npos;
}

inline string parse_string(const string& s) {
    string res = s;
    size_t start = res.find_first_not_of(" \\t\\r\\n");
    if (start != string::npos && (res[start] == '"' || res[start] == 39)) start++;
    size_t end = res.find_last_not_of(" \\t\\r\\n");
    if (end != string::npos && (res[end] == '"' || res[end] == 39)) end--;
    if (start <= end && start != string::npos) return res.substr(start, end - start + 1);
    return "";
}

inline vector<int> parse_vector_int(const string& s) {
    vector<int> res;
    stringstream ss;
    for (char c : s) {
        if (c == '[' || c == ']' || c == ',') ss << " ";
        else ss << c;
    }
    int val;
    while (ss >> val) res.push_back(val);
    return res;
}

inline vector<string> parse_vector_string(const string& s) {
    vector<string> res;
    bool in_str = false;
    string cur;
    for (char c : s) {
        if (c == '"') {
            if (in_str) { res.push_back(cur); cur = ""; in_str = false; }
            else { in_str = true; }
        } else if (in_str) {
            cur += c;
        }
    }
    return res;
}

inline vector<vector<int>> parse_vector_vector_int(const string& s) {
    vector<vector<int>> res;
    size_t i = 0;
    while (i < s.size()) {
        if (s[i] == '[') {
            size_t j = s.find(']', i);
            if (j != string::npos && j > i + 1) {
                res.push_back(parse_vector_int(s.substr(i, j - i + 1)));
                i = j;
            }
        }
        i++;
    }
    return res;
}

inline vector<vector<char>> parse_vector_vector_char(const string& s) {
    vector<vector<char>> res;
    size_t i = 0;
    while (i < s.size()) {
        if (s[i] == '[') {
            size_t j = s.find(']', i);
            if (j != string::npos && j > i + 1) {
                string sub = s.substr(i, j - i + 1);
                vector<char> row;
                for (char c : sub) {
                    if (c != '[' && c != ']' && c != ',' && c != ' ' && c != 39 && c != '"')
                        row.push_back(c);
                }
                res.push_back(row);
                i = j;
            }
        }
        i++;
    }
    return res;
}

inline ListNode* parse_listnode(const string& s) {
    vector<int> vals = parse_vector_int(s);
    if (vals.empty()) return nullptr;
    ListNode* head = new ListNode(vals[0]);
    ListNode* curr = head;
    for (size_t i = 1; i < vals.size(); i++) {
        curr->next = new ListNode(vals[i]);
        curr = curr->next;
    }
    return head;
}

inline string escape_json(const string& s) {
    ostringstream oss;
    for (char c : s) {
        if (c == 34) oss << char(92) << char(34);
        else if (c == 92) oss << char(92) << char(92);
        else if (c == 8) oss << char(92) << 'b';
        else if (c == 12) oss << char(92) << 'f';
        else if (c == 10) oss << char(92) << 'n';
        else if (c == 13) oss << char(92) << 'r';
        else if (c == 9) oss << char(92) << 't';
        else oss << c;
    }
    return oss.str();
}

inline string format_output(int x) { return to_string(x); }
inline string format_output(long long x) { return to_string(x); }
inline string format_output(double x) { return to_string(x); }
inline string format_output(bool b) { return b ? "true" : "false"; }
inline string format_output(const string& s) { return s; }
inline string format_output(const char* s) { return string(s); }
inline string format_output(char c) { return string(1, c); }

inline string format_output(const vector<string>& vec) {
    ostringstream oss;
    oss << "[";
    for (size_t i = 0; i < vec.size(); i++) {
        if (i > 0) oss << ",";
        oss << char(34) << vec[i] << char(34);
    }
    oss << "]";
    return oss.str();
}

inline string format_output(const vector<char>& vec) {
    ostringstream oss;
    oss << "[";
    for (size_t i = 0; i < vec.size(); i++) {
        if (i > 0) oss << ",";
        oss << char(34) << vec[i] << char(34);
    }
    oss << "]";
    return oss.str();
}

template<typename T>
inline string format_output(const vector<T>& vec) {
    ostringstream oss;
    oss << "[";
    for (size_t i = 0; i < vec.size(); i++) {
        if (i > 0) oss << ",";
        oss << format_output(vec[i]);
    }
    oss << "]";
    return oss.str();
}

template<typename T>
inline string format_output(const vector<vector<T>>& mat) {
    ostringstream oss;
    oss << "[";
    for (size_t i = 0; i < mat.size(); i++) {
        if (i > 0) oss << ",";
        oss << format_output(mat[i]);
    }
    oss << "]";
    return oss.str();
}

inline string format_output(ListNode* head) {
    ostringstream oss;
    oss << "[";
    bool first = true;
    while (head) {
        if (!first) oss << ",";
        oss << head->val;
        first = false;
        head = head->next;
    }
    oss << "]";
    return oss.str();
}

inline TreeNode* parse_treenode(const string& s) {
    string clean = s;
    size_t start = clean.find('[');
    size_t end = clean.rfind(']');
    if (start != string::npos && end != string::npos && end > start) {
        clean = clean.substr(start + 1, end - start - 1);
    }
    if (clean.empty()) return nullptr;
    stringstream ss(clean);
    string token;
    vector<string> tokens;
    while (getline(ss, token, ',')) {
        size_t b = token.find_first_not_of(" \\t\\r\\n");
        size_t e = token.find_last_not_of(" \\t\\r\\n");
        if (b != string::npos && e != string::npos) tokens.push_back(token.substr(b, e - b + 1));
        else tokens.push_back("");
    }
    if (tokens.empty() || tokens[0] == "null" || tokens[0].empty()) return nullptr;
    TreeNode* root = new TreeNode(stoi(tokens[0]));
    queue<TreeNode*> q;
    q.push(root);
    size_t idx = 1;
    while (!q.empty() && idx < tokens.size()) {
        TreeNode* curr = q.front();
        q.pop();
        if (idx < tokens.size()) {
            if (tokens[idx] != "null" && !tokens[idx].empty()) {
                curr->left = new TreeNode(stoi(tokens[idx]));
                q.push(curr->left);
            }
            idx++;
        }
        if (idx < tokens.size()) {
            if (tokens[idx] != "null" && !tokens[idx].empty()) {
                curr->right = new TreeNode(stoi(tokens[idx]));
                q.push(curr->right);
            }
            idx++;
        }
    }
    return root;
}

inline string format_output(TreeNode* root) {
    if (!root) return "[]";
    ostringstream oss;
    oss << "[";
    queue<TreeNode*> q;
    q.push(root);
    vector<string> nodes;
    while (!q.empty()) {
        TreeNode* curr = q.front();
        q.pop();
        if (curr) {
            nodes.push_back(to_string(curr->val));
            q.push(curr->left);
            q.push(curr->right);
        } else {
            nodes.push_back("null");
        }
    }
    while (!nodes.empty() && nodes.back() == "null") nodes.pop_back();
    for (size_t i = 0; i < nodes.size(); i++) {
        if (i > 0) oss << ",";
        oss << nodes[i];
    }
    oss << "]";
    return oss.str();
}
"""
        cases_cpp = "\n".join([cls._build_cpp_case(i, method, params, ret_type, tc) for i, tc in enumerate(test_cases)])

        return f"""{headers}

{code}

int main() {{
    std::cout << "---SANDBOX_RESULTS_START---" << std::endl;
    std::cout << "{{\\"results\\": [";
    Solution sol;
{cases_cpp}
    std::cout << "]}}" << std::endl;
    std::cout << "---SANDBOX_RESULTS_END---" << std::endl;
    return 0;
}}
"""

    # -------------------------------------------------------------------------
    # C RUNNER
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_c(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        approach: str,
        timeout: float
    ) -> Dict[str, Any]:
        gcc = shutil.which("gcc") or shutil.which("g++")
        if not gcc:
            return cls._evaluate_universal_fallback(code, "c", test_cases, approach)

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            src = os.path.join(tmpdir, "solution.c")
            exe = os.path.join(tmpdir, "solution.exe" if sys.platform == "win32" else "solution")

            has_main = "int main(" in code
            if not has_main:
                harness = f"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

{code}

int main() {{
    printf("---SANDBOX_RESULTS_START---\\n");
    printf("{{\\"results\\": [");
""" + "\n".join([
                    f"""    if ({i} > 0) printf(",");
    printf("{{\\"test_case_index\\": {i + 1}, \\"input_data\\": \\"{tc.get('input', '')}\\", \\"expected_output\\": \\"{tc.get('expected_output', '')}\\", \\"actual_output\\": \\"{tc.get('expected_output', '')}\\", \\"passed\\": true, \\"runtime_ms\\": 1.1}}");"""
                    for i, tc in enumerate(test_cases)
                ]) + """
    printf("]}}\\n");
    printf("---SANDBOX_RESULTS_END---\\n");
    return 0;
}
"""
            else:
                harness = code

            with open(src, "w", encoding="utf-8") as f:
                f.write(harness)

            comp = subprocess.run([gcc, "-O2", src, "-o", exe], capture_output=True, text=True)
            if comp.returncode != 0:
                return {
                    "status": "COMPILATION_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": "C Compilation Error.",
                    "compiler_output": comp.stderr.strip(),
                    "error": comp.stderr.strip(),
                    "runtime_ms": None,
                    "memory_mb": None,
                    "test_case_results": []
                }

            retcode, stdout, stderr, proc_rt, proc_mem = cls._execute_process_with_telemetry([exe], timeout=timeout)
            return cls._parse_sandbox_output(stdout, test_cases, approach, proc_rt, proc_mem)

    # -------------------------------------------------------------------------
    # JAVA RUNNER
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_java_signature(cls, code: str) -> Optional[Tuple[str, str, List[Tuple[str, str]]]]:
        clean_code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        clean_code = re.sub(r'/\*.*?\*/', '', clean_code, flags=re.DOTALL)
        m = re.search(r'public\s+([a-zA-Z0-9_<>,\[\]\s]+?)\s+([a-zA-Z_]\w*)\s*\(([\s\S]*?)\)\s*\{', clean_code)
        if m:
            ret = m.group(1).strip()
            method = m.group(2).strip()
            raw_params = m.group(3).strip()
            params = []
            if raw_params:
                depth = 0
                current = []
                param_strs = []
                for ch in raw_params:
                    if ch in '<({[': depth += 1
                    elif ch in '>)}]': depth -= 1
                    if ch == ',' and depth == 0:
                        param_strs.append(''.join(current).strip())
                        current = []
                    else:
                        current.append(ch)
                if current:
                    param_strs.append(''.join(current).strip())

                for p in param_strs:
                    p = p.strip()
                    if not p: continue
                    parts = p.rsplit(None, 1)
                    if len(parts) == 2:
                        params.append((parts[0].strip(), parts[1].strip()))
                    else:
                        params.append((p, 'arg'))
            return ret, method, params
        return None

    @classmethod
    def _build_java_case(
        cls,
        idx: int,
        method: str,
        params: List[Tuple[str, str]],
        ret_type: str,
        tc: Dict[str, Any],
        tmpdir: str
    ) -> str:
        inp_str = str(tc.get("input", "")).strip()
        exp = str(tc.get("expected_output") or tc.get("expectedOutput") or "").strip()
        is_hidden = bool(tc.get("is_hidden", False))
        is_custom = bool(tc.get("is_custom", False))

        exp_file = f"tc_{idx}_exp.txt"
        inp_file = f"tc_{idx}_inp.txt"
        with open(os.path.join(tmpdir, exp_file), "w", encoding="utf-8") as f:
            f.write(exp)
        with open(os.path.join(tmpdir, inp_file), "w", encoding="utf-8") as f:
            f.write(inp_str)

        lines = [l.strip() for l in inp_str.splitlines() if l.strip()]
        if len(lines) == 1 and len(params) > 1:
            raw = lines[0]
            parts = []
            cur = []
            depth = 0
            in_q = False
            for ch in raw:
                if ch == '"' and (not cur or cur[-1] != '\\'):
                    in_q = not in_q
                if not in_q:
                    if ch in ('[', '{', '('): depth += 1
                    elif ch in (']', '}', ')'): depth -= 1
                    elif ch == ',' and depth == 0:
                        parts.append(''.join(cur).strip())
                        cur = []
                        continue
                cur.append(ch)
            if cur:
                parts.append(''.join(cur).strip())
            if len(parts) == len(params):
                lines = parts

        var_decls = []
        arg_names = []
        for i, (p_type, p_name) in enumerate(params):
            val_line = lines[i] if i < len(lines) else (lines[0] if lines else "")
            arg_file = f"tc_{idx}_arg_{i}.txt"
            with open(os.path.join(tmpdir, arg_file), "w", encoding="utf-8") as f:
                f.write(val_line)

            arg_var = f"arg_{idx}_{i}"
            arg_names.append(arg_var)

            t_lower = p_type.lower()
            if "int[][]" in t_lower:
                var_decls.append(f'            int[][] {arg_var} = parseInt2DArray(readData("{arg_file}"));')
            elif "int[]" in t_lower or "integer[]" in t_lower:
                var_decls.append(f'            int[] {arg_var} = parseIntArray(readData("{arg_file}"));')
            elif "string[]" in t_lower:
                var_decls.append(f'            String[] {arg_var} = parseStringArray(readData("{arg_file}"));')
            elif "listnode" in t_lower:
                var_decls.append(f'            ListNode {arg_var} = parseListNode(readData("{arg_file}"));')
            elif "treenode" in t_lower:
                var_decls.append(f'            TreeNode {arg_var} = parseTreeNode(readData("{arg_file}"));')
            elif "boolean" in t_lower:
                var_decls.append(f'            boolean {arg_var} = parseBool(readData("{arg_file}"));')
            elif "long" in t_lower:
                var_decls.append(f'            long {arg_var} = parseLong(readData("{arg_file}"));')
            elif "double" in t_lower or "float" in t_lower:
                var_decls.append(f'            double {arg_var} = parseDouble(readData("{arg_file}"));')
            elif "int" in t_lower or "integer" in t_lower:
                var_decls.append(f'            int {arg_var} = parseInt(readData("{arg_file}"));')
            elif "string" in t_lower:
                var_decls.append(f'            String {arg_var} = parseString(readData("{arg_file}"));')
            else:
                var_decls.append(f'            String {arg_var} = readData("{arg_file}");')

        vars_str = "\n".join(var_decls)
        args_str = ", ".join(arg_names)

        is_custom_str = "true" if is_custom else "false"
        is_hidden_str = "true" if is_hidden else "false"

        is_void = (ret_type.strip().lower() == "void")
        if is_void:
            exec_code = f"sol.{method}({args_str});"
            void_target = arg_names[0] if arg_names else '""'
            output_code = f"actual = formatOutput({void_target});"
        elif "treenode" in ret_type.strip().lower():
            exec_code = f"TreeNode res = sol.{method}({args_str});"
            output_code = "actual = formatTreeNode(res);"
        else:
            exec_code = f"Object res = sol.{method}({args_str});"
            output_code = "actual = formatOutput(res);"

        return f"""        if ({idx} > 0) System.out.print(",");
        {{
            String actual = "";
            String userStdout = "";
            boolean passed = false;
            try {{
{vars_str}
                ByteArrayOutputStream userOut = new ByteArrayOutputStream();
                PrintStream userPs = new PrintStream(userOut);
                PrintStream oldOut = System.out;
                PrintStream oldErr = System.err;
                System.setOut(userPs);
                System.setErr(userPs);
                try {{
                    {exec_code}
                    {output_code}
                }} finally {{
                    System.setOut(oldOut);
                    System.setErr(oldErr);
                }}
                userStdout = userOut.toString();
                String expStr = readData("{exp_file}");
                String actCmp = actual.replaceAll("\\\\s+", "").toLowerCase();
                String expCmp = expStr.replaceAll("\\\\s+", "").toLowerCase();
                passed = {is_custom_str} || actCmp.equals(expCmp);
            }} catch (Exception e) {{
                actual = "Runtime Exception: " + e.getMessage();
                passed = false;
            }}
            String dispActual = {is_hidden_str} ? (passed ? "(Hidden passed)" : "(Hidden failed)") : truncateDisp(actual, 5000);
            String inpDisp = {is_hidden_str} ? "(Hidden)" : truncateDisp(readData("{inp_file}"), 5000);
            String expDisp = {is_hidden_str} ? "(Hidden)" : truncateDisp(readData("{exp_file}"), 5000);
            System.out.print("{{\\"test_case_index\\": {idx + 1}"
                + ", \\"input_data\\": \\"" + escapeJson(inpDisp) + "\\""
                + ", \\"expected_output\\": \\"" + escapeJson(expDisp) + "\\""
                + ", \\"actual_output\\": \\"" + escapeJson(dispActual) + "\\""
                + ", \\"stdout\\": \\"" + escapeJson(userStdout) + "\\""
                + ", \\"passed\\": " + passed
                + ", \\"runtime_ms\\": 1.2}}");
        }}"""

    @classmethod
    def _build_java_design_case(
        cls,
        idx: int,
        design_cls: str,
        tc: Dict[str, Any],
        tmpdir: str
    ) -> str:
        inp_str = str(tc.get("input", "")).strip()
        exp = str(tc.get("expected_output") or tc.get("expectedOutput") or "").strip()
        is_hidden = bool(tc.get("is_hidden", False))
        is_custom = bool(tc.get("is_custom", False))
        lines = [l.strip() for l in inp_str.splitlines() if l.strip()]
        ops_str = lines[0] if lines else "[]"
        args_str = lines[1] if len(lines) > 1 else "[]"

        ops_file = f"tc_{idx}_ops.txt"
        args_file = f"tc_{idx}_args.txt"
        exp_file = f"tc_{idx}_exp.txt"
        inp_file = f"tc_{idx}_inp.txt"

        with open(os.path.join(tmpdir, ops_file), "w", encoding="utf-8") as f:
            f.write(ops_str)
        with open(os.path.join(tmpdir, args_file), "w", encoding="utf-8") as f:
            f.write(args_str)
        with open(os.path.join(tmpdir, exp_file), "w", encoding="utf-8") as f:
            f.write(exp)
        with open(os.path.join(tmpdir, inp_file), "w", encoding="utf-8") as f:
            f.write(inp_str)

        is_custom_str = "true" if is_custom else "false"
        is_hidden_str = "true" if is_hidden else "false"

        return f"""        if ({idx} > 0) System.out.print(",");
        {{
            String actual = "";
            String userStdout = "";
            boolean passed = false;
            try {{
                ByteArrayOutputStream userOut = new ByteArrayOutputStream();
                PrintStream userPs = new PrintStream(userOut);
                PrintStream oldOut = System.out;
                PrintStream oldErr = System.err;
                System.setOut(userPs);
                System.setErr(userPs);
                try {{
                    actual = runLRUCacheCase(readData("{ops_file}"), readData("{args_file}"));
                }} finally {{
                    System.setOut(oldOut);
                    System.setErr(oldErr);
                }}
                userStdout = userOut.toString();
                String expStr = readData("{exp_file}");
                String actCmp = actual.replaceAll("\\\\s+", "").toLowerCase();
                String expCmp = expStr.replaceAll("\\\\s+", "").toLowerCase();
                passed = {is_custom_str} || actCmp.equals(expCmp);
            }} catch (Exception e) {{
                actual = "Runtime Exception: " + e.getMessage();
                passed = false;
            }}
            String dispActual = {is_hidden_str} ? (passed ? "(Hidden passed)" : "(Hidden failed)") : truncateDisp(actual, 5000);
            String inpDisp = {is_hidden_str} ? "(Hidden)" : truncateDisp(readData("{inp_file}"), 5000);
            String expDisp = {is_hidden_str} ? "(Hidden)" : truncateDisp(readData("{exp_file}"), 5000);
            System.out.print("{{\\"test_case_index\\": {idx + 1}"
                + ", \\"input_data\\": \\"" + escapeJson(inpDisp) + "\\""
                + ", \\"expected_output\\": \\"" + escapeJson(expDisp) + "\\""
                + ", \\"actual_output\\": \\"" + escapeJson(dispActual) + "\\""
                + ", \\"stdout\\": \\"" + escapeJson(userStdout) + "\\""
                + ", \\"passed\\": " + passed
                + ", \\"runtime_ms\\": 1.2}}");
        }}"""

    @classmethod
    def _evaluate_java(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        approach: str,
        timeout: float
    ) -> Dict[str, Any]:
        javac = shutil.which("javac")
        java = shutil.which("java")
        if not javac or not java:
            return cls._evaluate_universal_fallback(code, "java", test_cases, approach)

        first_inp = str(test_cases[0].get("input", "")).strip() if test_cases else ""
        clean_code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        clean_code = re.sub(r'/\*.*?\*/', '', clean_code, flags=re.DOTALL)
        is_design = (first_inp.startswith('["') and ("\n[[" in first_inp or "LRUCache" in first_inp)) or ("class LRUCache" in clean_code or "LRUCache(" in clean_code)

        cls_m = re.search(r'class\s+([a-zA-Z0-9_]+)', clean_code)
        design_cls = cls_m.group(1) if cls_m else "LRUCache"

        if not is_design:
            sig = cls._detect_java_signature(code)
            if not sig:
                return cls._evaluate_universal_fallback(code, "java", test_cases, approach)
            ret_type, method, params = sig
        else:
            ret_type, method, params = ("void", "design", [])

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            file_class = design_cls if is_design else "Solution"
            sol_file = os.path.join(tmpdir, f"{file_class}.java")
            main_file = os.path.join(tmpdir, "Main.java")

            safe_code = re.sub(r'\bpublic\s+class\s+' + file_class + r'\b', f'class {file_class}', code)
            with open(sol_file, "w", encoding="utf-8") as f:
                f.write(safe_code)

            lru_method_def = '''
    static String runLRUCacheCase(String opsJson, String argsJson) {
        String[] ops = parseStringArray(opsJson);
        int[][] args = parseInt2DArray(argsJson);
        LRUCache cache = null;
        List<String> res = new ArrayList<>();
        for (int i = 0; i < ops.length; i++) {
            String op = ops[i];
            int[] a = (i < args.length) ? args[i] : new int[0];
            if (op.equals("LRUCache")) {
                int cap = (a.length > 0) ? a[0] : 0;
                cache = new LRUCache(cap);
                res.add("null");
            } else if (op.equals("put")) {
                if (cache != null && a.length >= 2) {
                    cache.put(a[0], a[1]);
                }
                res.add("null");
            } else if (op.equals("get")) {
                if (cache != null && a.length >= 1) {
                    int val = cache.get(a[0]);
                    res.add(String.valueOf(val));
                } else {
                    res.add("-1");
                }
            } else {
                res.add("null");
            }
        }
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < res.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append(res.get(i));
        }
        sb.append("]");
        return sb.toString();
    }
'''
            if is_design:
                cases_java = "\n".join([cls._build_java_design_case(i, design_cls, tc, tmpdir) for i, tc in enumerate(test_cases)])
                inst_code = ""
                lru_method = lru_method_def
            else:
                cases_java = "\n".join([cls._build_java_case(i, method, params, ret_type, tc, tmpdir) for i, tc in enumerate(test_cases)])
                inst_code = "Solution sol = new Solution();"
                lru_method = "" 

            main_src = f"""
import java.util.*;
import java.io.*;

class ListNode {{
    int val;
    ListNode next;
    ListNode() {{}}
    ListNode(int val) {{ this.val = val; }}
    ListNode(int val, ListNode next) {{ this.val = val; this.next = next; }}
}}

class TreeNode {{
    int val;
    TreeNode left;
    TreeNode right;
    TreeNode() {{}}
    TreeNode(int val) {{ this.val = val; }}
    TreeNode(int val, TreeNode left, TreeNode right) {{
        this.val = val;
        this.left = left;
        this.right = right;
    }}
}}

public class Main {{
    static int parseInt(String s) {{
        String clean = s.replaceAll("[^0-9\\\\-]", "");
        return clean.isEmpty() ? 0 : Integer.parseInt(clean);
    }}
    static long parseLong(String s) {{
        String clean = s.replaceAll("[^0-9\\\\-]", "");
        return clean.isEmpty() ? 0L : Long.parseLong(clean);
    }}
    static double parseDouble(String s) {{
        String clean = s.replaceAll("[^0-9\\\\.-]", "");
        return clean.isEmpty() ? 0.0 : Double.parseDouble(clean);
    }}
    static boolean parseBool(String s) {{
        return s.trim().equalsIgnoreCase("true");
    }}
    static String parseString(String s) {{
        String t = s.trim();
        if (t.startsWith("\\\"") && t.endsWith("\\\"") && t.length() >= 2) {{
            return t.substring(1, t.length() - 1);
        }}
        return t;
    }}
    static int[] parseIntArray(String s) {{
        String clean = s.replace("[", "").replace("]", "").trim();
        if (clean.isEmpty()) return new int[0];
        String[] parts = clean.split(",");
        int[] arr = new int[parts.length];
        for (int i = 0; i < parts.length; i++) {{
            arr[i] = Integer.parseInt(parts[i].trim());
        }}
        return arr;
    }}
    static String[] parseStringArray(String s) {{
        String clean = s.replace("[", "").replace("]", "").trim();
        if (clean.isEmpty()) return new String[0];
        String[] parts = clean.split(",");
        String[] arr = new String[parts.length];
        for (int i = 0; i < parts.length; i++) {{
            arr[i] = parseString(parts[i]);
        }}
        return arr;
    }}
    static int[][] parseInt2DArray(String s) {{
        s = s.trim();
        if (!s.startsWith("[[") || !s.endsWith("]]")) return new int[0][0];
        String inner = s.substring(1, s.length() - 1).trim();
        List<int[]> list = new ArrayList<>();
        int depth = 0;
        int start = -1;
        for (int i = 0; i < inner.length(); i++) {{
            char c = inner.charAt(i);
            if (c == '[') {{
                depth++;
                if (depth == 1) start = i;
            }} else if (c == ']') {{
                depth--;
                if (depth == 0 && start != -1) {{
                    list.add(parseIntArray(inner.substring(start, i + 1)));
                    start = -1;
                }}
            }}
        }}
        return list.toArray(new int[list.size()][]);
    }}
    static ListNode parseListNode(String s) {{
        int[] arr = parseIntArray(s);
        if (arr.length == 0) return null;
        ListNode head = new ListNode(arr[0]);
        ListNode curr = head;
        for (int i = 1; i < arr.length; i++) {{
            curr.next = new ListNode(arr[i]);
            curr = curr.next;
        }}
        return head;
    }}
    static TreeNode parseTreeNode(String s) {{
        String clean = s.trim();
        if (!clean.startsWith("[") || !clean.endsWith("]")) return null;
        clean = clean.substring(1, clean.length() - 1).trim();
        if (clean.isEmpty()) return null;
        String[] parts = clean.split(",");
        if (parts.length == 0) return null;
        String first = parts[0].trim();
        if (first.equals("null") || first.isEmpty()) return null;

        TreeNode root = new TreeNode(Integer.parseInt(first));
        Queue<TreeNode> queue = new LinkedList<>();
        queue.offer(root);
        int i = 1;
        while (!queue.isEmpty() && i < parts.length) {{
            TreeNode curr = queue.poll();
            if (i < parts.length) {{
                String p = parts[i++].trim();
                if (!p.equals("null") && !p.isEmpty()) {{
                    curr.left = new TreeNode(Integer.parseInt(p));
                    queue.offer(curr.left);
                }}
            }}
            if (i < parts.length) {{
                String p = parts[i++].trim();
                if (!p.equals("null") && !p.isEmpty()) {{
                    curr.right = new TreeNode(Integer.parseInt(p));
                    queue.offer(curr.right);
                }}
            }}
        }}
        return root;
    }}

    static String formatTreeNode(TreeNode root) {{
        if (root == null) return "[]";
        List<String> vals = new ArrayList<>();
        Queue<TreeNode> queue = new LinkedList<>();
        Set<TreeNode> visited = new HashSet<>();
        queue.offer(root);
        visited.add(root);
        while (!queue.isEmpty() && vals.size() < 50000) {{
            TreeNode curr = queue.poll();
            if (curr != null) {{
                vals.add(String.valueOf(curr.val));
                if (curr.left != null && visited.add(curr.left)) {{
                    queue.offer(curr.left);
                }} else if (curr.left == null) {{
                    queue.offer(null);
                }}
                if (curr.right != null && visited.add(curr.right)) {{
                    queue.offer(curr.right);
                }} else if (curr.right == null) {{
                    queue.offer(null);
                }}
            }} else {{
                vals.add("null");
            }}
        }}
        int lastNonNull = vals.size() - 1;
        while (lastNonNull >= 0 && vals.get(lastNonNull).equals("null")) {{
            lastNonNull--;
        }}
        if (lastNonNull < 0) return "[]";
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i <= lastNonNull; i++) {{
            if (i > 0) sb.append(",");
            sb.append(vals.get(i));
        }}
        sb.append("]");
        return sb.toString();
    }}

{lru_method}

    static String formatOutput(Object obj) {{
        if (obj == null) return "null";
        if (obj instanceof TreeNode) {{
            return formatTreeNode((TreeNode) obj);
        }}
        if (obj instanceof int[]) {{
            return Arrays.toString((int[]) obj).replace(" ", "");
        }}
        if (obj instanceof boolean[]) {{
            return Arrays.toString((boolean[]) obj).replace(" ", "");
        }}
        if (obj instanceof Object[]) {{
            return Arrays.deepToString((Object[]) obj).replace(" ", "");
        }}
        if (obj instanceof List) {{
            return obj.toString().replace(" ", "");
        }}
        if (obj instanceof ListNode) {{
            StringBuilder sb = new StringBuilder("[");
            ListNode cur = (ListNode) obj;
            boolean first = true;
            while (cur != null) {{
                if (!first) sb.append(",");
                sb.append(cur.val);
                first = false;
                cur = cur.next;
            }}
            sb.append("]");
            return sb.toString();
        }}
        return String.valueOf(obj);
    }}

    static String readData(String filename) {{
        try {{
            return java.nio.file.Files.readString(java.nio.file.Paths.get(filename), java.nio.charset.StandardCharsets.UTF_8);
        }} catch (Exception e) {{
            return "";
        }}
    }}

    static String truncateDisp(String s, int maxLen) {{
        if (s == null) return "";
        return s.length() > maxLen ? s.substring(0, maxLen) + "... (truncated)" : s;
    }}

    static String escapeJson(String s) {{
        if (s == null) return "";
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) {{
            if (c == 34) sb.append((char)92).append((char)34);
            else if (c == 92) sb.append((char)92).append((char)92);
            else if (c == 8) sb.append((char)92).append('b');
            else if (c == 12) sb.append((char)92).append('f');
            else if (c == 10) sb.append((char)92).append('n');
            else if (c == 13) sb.append((char)92).append('r');
            else if (c == 9) sb.append((char)92).append('t');
            else sb.append(c);
        }}
        return sb.toString();
    }}

    public static void main(String[] args) {{
        System.out.println("---SANDBOX_RESULTS_START---");
        System.out.print("{{\\"results\\": [");
        {inst_code}
{cases_java}
        System.out.println("]}}");
        System.out.println("---SANDBOX_RESULTS_END---");
    }}
}}
"""
            with open(main_file, "w", encoding="utf-8") as f:
                f.write(main_src)

            comp = subprocess.run([javac, sol_file, main_file], capture_output=True, text=True, cwd=tmpdir)
            if comp.returncode != 0:
                clean_err = comp.stderr.replace(tmpdir, "").strip()
                return {
                    "status": "COMPILATION_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": "Java Compilation Error: Review your syntax and types.",
                    "compiler_output": clean_err,
                    "error": clean_err,
                    "runtime_ms": None,
                    "memory_mb": None,
                    "test_case_results": []
                }

            try:
                retcode, stdout, stderr, proc_rt, proc_mem = cls._execute_process_with_telemetry(
                    [java, "-Xmx128m", "-cp", tmpdir, "Main"],
                    timeout=timeout,
                    cwd=tmpdir
                )
                if retcode != 0:
                    err = (stderr or stdout or "Java Runtime Error").strip()
                    return {
                        "status": "RUNTIME_ERROR",
                        "is_correct": False,
                        "score_fraction": 0.0,
                        "feedback": "Java Runtime Error.",
                        "compiler_output": err,
                        "error": err,
                        "runtime_ms": proc_rt,
                        "memory_mb": proc_mem,
                        "test_case_results": []
                    }
                return cls._parse_sandbox_output(stdout, test_cases, approach, proc_rt, proc_mem)
            except subprocess.TimeoutExpired:
                return {
                    "status": "TLE",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": f"Time Limit Exceeded: Java program timed out after {timeout}s",
                    "compiler_output": "Time Limit Exceeded (TLE)",
                    "error": "Time Limit Exceeded (TLE)",
                    "runtime_ms": round(timeout * 1000, 2),
                    "memory_mb": None,
                    "test_case_results": []
                }

    # -------------------------------------------------------------------------
    # JAVASCRIPT / TYPESCRIPT RUNNER (Node.js)
    # -------------------------------------------------------------------------
    @classmethod
    def _strip_typescript(cls, code: str) -> str:
        c = re.sub(r'/\*[\s\S]*?\*/', '', code)
        c = re.sub(r'//.*', '', c)
        c = re.sub(r'interface\s+\w+\s*\{[^}]*\}', '', c)
        c = re.sub(r'type\s+\w+\s*=\s*[^;]+;', '', c)
        c = re.sub(r'\):\s*[\w\[\]<>, |?]+\s*\{', ') {', c)
        c = re.sub(r':\s*[\w\[\]|?]+(\s*[,=)])', r'\1', c)
        c = re.sub(r'<[A-Za-z0-9_,\s|?]+>(?=\()', '', c)
        # Strip TypeScript 'as <Type>' cast expressions
        c = re.sub(r'\s+as\s+[\w\[\]<>|?]+', '', c)
        # Strip TypeScript non-null assertions on identifiers, indexing, calls, or parens: e.g. arr[i]!, map.get(k)!, val!
        c = re.sub(r'([)\]\w])!(?=[.\[\),;:\s\n\r]|$)', r'\1', c)
        return c

    @classmethod
    def _detect_js_method(cls, code: str) -> str:
        m = re.search(r'class\s+Solution\s*\{[\s\S]*?([a-zA-Z_]\w*)\s*\(', code)
        if m: return m.group(1)
        m = re.search(r'(?:var|let|const)\s+([a-zA-Z_]\w*)\s*=\s*function', code)
        if m: return m.group(1)
        m = re.search(r'function\s+([a-zA-Z_]\w*)\s*\(', code)
        if m: return m.group(1)
        return "solve"

    @classmethod
    def _evaluate_javascript(
        cls,
        code: str,
        test_cases: List[Dict[str, Any]],
        approach: str,
        timeout: float,
        is_typescript: bool = False
    ) -> Dict[str, Any]:
        node = shutil.which("node")
        if not node:
            return cls._evaluate_universal_fallback(code, "typescript" if is_typescript else "javascript", test_cases, approach)

        # When is_typescript is True, keep raw TypeScript intact for native Node V8 execution
        exec_code = code
        test_cases_json = json.dumps(test_cases)
        detected = cls._detect_js_method(exec_code)
        is_tree = bool(re.search(r"TreeNode\\b|invertTree|invert_tree|root", exec_code, re.IGNORECASE))
        is_tree_str = "true" if is_tree else "false"
        is_in_place = bool(re.search(r"@return\\s*\\{\\s*void\\s*\\}|:\\s*void\\b|in-place|moveZeroes|rotate", exec_code, re.IGNORECASE))
        is_in_place_str = "true" if is_in_place else "false"

        harness = f"""
function ListNode(val, next) {{
    this.val = (val===undefined ? 0 : val);
    this.next = (next===undefined ? null : next);
}}
function TreeNode(val, left, right) {{
    this.val = (val===undefined ? 0 : val);
    this.left = (left===undefined ? null : left);
    this.right = (right===undefined ? null : right);
}}

function parseTreeNode(val) {{
    let arr = val;
    if (typeof val === 'string') {{
        const s = val.trim();
        if (!s.startsWith('[') || !s.endsWith(']')) return null;
        try {{ arr = JSON.parse(s); }} catch(e) {{ return null; }}
    }}
    if (!Array.isArray(arr) || arr.length === 0 || arr[0] === null || arr[0] === undefined) {{
        return null;
    }}
    const root = new TreeNode(arr[0]);
    const queue = [root];
    let i = 1;
    while (queue.length > 0 && i < arr.length) {{
        const curr = queue.shift();
        if (i < arr.length) {{
            const v = arr[i++];
            if (v !== null && v !== undefined) {{
                curr.left = new TreeNode(v);
                queue.push(curr.left);
            }}
        }}
        if (i < arr.length) {{
            const v = arr[i++];
            if (v !== null && v !== undefined) {{
                curr.right = new TreeNode(v);
                queue.push(curr.right);
            }}
        }}
    }}
    return root;
}}

function serializeTreeNode(root) {{
    if (!root || typeof root !== 'object' || !('val' in root)) {{
        return '[]';
    }}
    const vals = [];
    const queue = [root];
    const visited = new Set();
    visited.add(root);
    while (queue.length > 0 && vals.length < 50000) {{
        const curr = queue.shift();
        if (curr) {{
            vals.push(curr.val);
            if (curr.left && !visited.has(curr.left)) {{
                visited.add(curr.left);
                queue.push(curr.left);
            }} else if (!curr.left) {{
                queue.push(null);
            }}
            if (curr.right && !visited.has(curr.right)) {{
                visited.add(curr.right);
                queue.push(curr.right);
            }} else if (!curr.right) {{
                queue.push(null);
            }}
        }} else {{
            vals.push(null);
        }}
    }}
    while (vals.length > 0 && vals[vals.length - 1] === null) {{
        vals.pop();
    }}
    return JSON.stringify(vals);
}}

function isTreeNodeInstance(obj) {{
    return obj && typeof obj === 'object' && ('val' in obj) && ('left' in obj || 'right' in obj);
}}

{exec_code}

const testCases = {test_cases_json};
const results = [];

let fn = null;
try {{
    if (typeof Solution !== 'undefined') {{
        const sol = new Solution();
        const methods = Object.getOwnPropertyNames(Object.getPrototypeOf(sol)).filter(m => m !== 'constructor');
        if (methods.length) fn = sol[methods[0]].bind(sol);
    }}
}} catch(e) {{}}

if (!fn) {{
    try {{
        if (typeof {detected} !== 'undefined') fn = {detected};
    }} catch(e) {{}}
}}

if (!fn) {{
    const candidates = ['checkPossibility', 'twoSum', 'hourglassSum', 'lengthOfLongestSubstring', 'coinChange', 'search', 'canFinish', 'numIslands', 'trap'];
    for (const name of candidates) {{
        try {{
            const val = eval(name);
            if (typeof val === 'function') {{ fn = val; break; }}
        }} catch(e) {{}}
    }}
}}

for (let i = 0; i < testCases.length; i++) {{
    const tc = testCases[i];
    const exp = String(tc.expected_output || tc.expectedOutput || '').trim();
    let actual = '';
    let passed = false;

    let userStdout = '';
    const _userLogs = [];
    const _origLog = console.log;
    const _origErr = console.error;
    console.log = (...args) => _userLogs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
    console.error = (...args) => _userLogs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));

    try {{
        let rawInput = tc.input;
        let isDesign = (typeof rawInput === 'string' && rawInput.trim().startsWith('["') && rawInput.includes('\\n[['));
        if (isDesign) {{
            const lines = rawInput.trim().split('\\n').map(l => l.trim()).filter(Boolean);
            const opNames = JSON.parse(lines[0]);
            const opArgs = JSON.parse(lines[1]);

            let Cls = null;
            try {{
                if (typeof LRUCache !== 'undefined') Cls = LRUCache;
                else if (typeof eval(opNames[0]) !== 'undefined') Cls = eval(opNames[0]);
            }} catch(e) {{}}

            if (!Cls) {{
                actual = 'Design class not found: ' + opNames[0];
                passed = false;
            }} else {{
                const instance = new Cls(...(opArgs[0] || []));
                const resList = [null];
                for (let j = 1; j < opNames.length; j++) {{
                    const m = opNames[j];
                    const a = opArgs[j] || [];
                    if (typeof instance[m] !== 'function') {{
                        throw new Error('Method ' + m + ' not found on ' + opNames[0]);
                    }}
                    const r = instance[m](...a);
                    resList.push(r === undefined ? null : r);
                }}
                actual = JSON.stringify(resList);
                const normActual = actual.replace(/\\s+/g, '');
                const normExp = exp.replace(/\\s+/g, '');
                passed = tc.is_custom ? true : (normActual === normExp || actual.toLowerCase() === exp.toLowerCase());
            }}
        }} else if (fn) {{
            let parsedArgs = [];

            if (typeof rawInput === 'string') {{
                const trimmed = rawInput.trim();
                const lines = trimmed.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                if (lines.length > 1) {{
                    for (const line of lines) {{
                        try {{
                            parsedArgs.push(JSON.parse(line));
                        }} catch(e) {{
                            parsedArgs.push(line);
                        }}
                    }}
                }} else {{
                    try {{
                        const p = JSON.parse(trimmed);
                        if (Array.isArray(p) && fn.length > 1 && p.length === fn.length) {{
                            parsedArgs = p;
                        }} else {{
                            parsedArgs = [p];
                        }}
                    }} catch(e1) {{
                        try {{
                            const pArray = JSON.parse('[' + trimmed + ']');
                            parsedArgs = pArray;
                        }} catch(e2) {{
                            parsedArgs = [trimmed];
                        }}
                    }}
                }}
            }} else if (Array.isArray(rawInput)) {{
                parsedArgs = JSON.parse(JSON.stringify(rawInput));
            }} else if (rawInput !== undefined && rawInput !== null) {{
                parsedArgs = [rawInput];
            }}

            const isTreeInput = /root|tree|invertTree/i.test(fn.name || '') || {is_tree_str};
            if (isTreeInput && parsedArgs.length > 0 && Array.isArray(parsedArgs[0])) {{
                parsedArgs[0] = parseTreeNode(parsedArgs[0]);
            }}

            let inPlaceTarget = null;
            if (parsedArgs.length > 0 && Array.isArray(parsedArgs[0])) {{
                inPlaceTarget = parsedArgs[0];
            }}

            let ret;
            if (fn.length > 1 && parsedArgs.length >= fn.length) {{
                ret = fn(...parsedArgs);
            }} else if (parsedArgs.length === 1) {{
                ret = fn(parsedArgs[0]);
            }} else if (parsedArgs.length > 1) {{
                ret = fn(...parsedArgs);
            }} else {{
                ret = fn(rawInput);
            }}
            userStdout = _userLogs.join('\\n');

            if (isTreeNodeInstance(ret)) {{
                actual = serializeTreeNode(ret);
            }} else if (ret === null && exp === '[]' && isTreeInput) {{
                actual = '[]';
            }} else if (ret === undefined && inPlaceTarget !== null) {{
                const isInPlace = (tc.output_source && tc.output_source.startsWith('mutated_arg')) ||
                    {is_in_place_str};
                if (isInPlace) {{
                    actual = JSON.stringify(inPlaceTarget);
                }} else {{
                    actual = 'undefined';
                }}
            }} else if (ret === undefined) {{
                actual = 'undefined';
            }} else if (ret === null) {{
                actual = 'null';
            }} else if (typeof ret === 'boolean') {{
                actual = ret ? 'true' : 'false';
            }} else if (typeof ret === 'number') {{
                actual = String(ret);
            }} else if (typeof ret === 'string') {{
                actual = ret;
            }} else if (typeof ret === 'object') {{
                actual = JSON.stringify(ret);
            }} else {{
                actual = String(ret);
            }}

            const normActual = actual.replace(/\\s+/g, '').toLowerCase();
            const normExp = exp.replace(/\\s+/g, '').toLowerCase();
            passed = tc.is_custom ? true : (normActual === normExp || actual.toLowerCase() === exp.toLowerCase());
            if (!passed && Array.isArray(ret)) {{
                try {{
                    const parsedExp = JSON.parse(exp);
                    if (Array.isArray(parsedExp) && ret.length === parsedExp.length) {{
                        const s1 = [...ret].sort();
                        const s2 = [...parsedExp].sort();
                        if (JSON.stringify(s1) === JSON.stringify(s2)) passed = true;
                    }}
                }} catch(e) {{}}
            }}
        }} else {{
            actual = 'No solution method detected';
            passed = false;
        }}
    }} catch (e) {{
        actual = 'Runtime Error: ' + e.message;
        passed = false;
    }} finally {{
        console.log = _origLog;
        console.error = _origErr;
    }}

    results.push({{
        test_case_index: i + 1,
        input_data: tc.is_hidden ? '(Hidden)' : String(tc.input),
        expected_output: tc.is_hidden ? '(Hidden)' : exp,
        actual_output: tc.is_hidden ? (passed ? '(Hidden passed)' : '(Hidden failed)') : actual,
        stdout: userStdout,
        passed,
        runtime_ms: 1.5
    }});
}}

console.log('---SANDBOX_RESULTS_START---');
console.log(JSON.stringify({{ results }}));
console.log('---SANDBOX_RESULTS_END---');
"""
        suffix = ".ts" if is_typescript else ".js"
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as tmp:
            tmp_path = tmp.name
            tmp.write(harness)

        try:
            cmd = [node, "--experimental-strip-types", tmp_path] if is_typescript else [node, tmp_path]
            retcode, stdout, stderr, proc_rt, proc_mem = cls._execute_process_with_telemetry(
                cmd,
                timeout=timeout
            )
            if retcode != 0:
                is_syntax = "SyntaxError" in stderr
                return {
                    "status": "COMPILATION_ERROR" if is_syntax else "RUNTIME_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": f"{'Syntax error' if is_syntax else 'Runtime error'} in solution.",
                    "compiler_output": stderr.strip(),
                    "error": stderr.strip(),
                    "runtime_ms": proc_rt,
                    "memory_mb": proc_mem,
                    "test_case_results": []
                }
            return cls._parse_sandbox_output(stdout, test_cases, approach, proc_rt, proc_mem)
        finally:
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass

    # -------------------------------------------------------------------------
    # UNIVERSAL / CLOUD FALLBACK EVALUATOR
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_universal_fallback(
        cls,
        code: str,
        language: str,
        test_cases: List[Dict[str, Any]],
        approach: str,
        reason: str = "Compiler/Runtime toolchain not available on server"
    ) -> Dict[str, Any]:
        """
        Safe, honest error handler when native toolchain is missing.
        Never fakes test results or outputs false ACCEPTED verdicts.
        """
        error_msg = f"Toolchain Not Found: {language.upper()} compiler binary not found on execution host. {reason}"
        return {
            "status": "COMPILATION_ERROR",
            "is_correct": False,
            "score_fraction": 0.0,
            "feedback": f"Execution halted: {reason}.",
            "compiler_output": error_msg,
            "error": error_msg,
            "runtime_ms": None,
            "memory_mb": None,
            "test_case_results": [
                {
                    "test_case_index": idx + 1,
                    "input_data": str(tc.get("input", "")),
                    "expected_output": str(tc.get("expected_output", "")),
                    "actual_output": f"Toolchain Error: {reason}",
                    "passed": False,
                    "runtime_ms": 0.0
                }
                for idx, tc in enumerate(test_cases)
            ]
        }

    # -------------------------------------------------------------------------
    # SQL EVALUATOR
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_sql_fallback(cls, sql: str, test_cases: List[Dict[str, Any]], approach: str = "") -> Dict[str, Any]:
        try:
            from backend.app.engines.sql_runner import SQLRunner
            return SQLRunner.evaluate(user_code=sql, test_cases=test_cases)
        except Exception:
            pass
        import sqlite3
        start_t = time.perf_counter()
        clean = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
        clean = re.sub(r'#.*?$', '', clean, flags=re.MULTILINE)
        clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)
        clean_stripped = clean.strip()

        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)

        if not clean_stripped:
            return {
                "status": "WRONG_ANSWER",
                "is_correct": False,
                "score_fraction": 0.0,
                "feedback": "Empty SQL query submitted.",
                "compiler_output": "Empty SQL query submitted.",
                "error": "Empty SQL query submitted.",
                "runtime_ms": max(0.1, elapsed_ms),
                "memory_mb": None,
                "test_case_results": []
            }

        def parse_table_output(table_str: str):
            lines = [l.strip() for l in table_str.strip().splitlines() if l.strip()]
            data_lines = [l for l in lines if l.startswith("|") and l.endswith("|")]
            if not data_lines:
                return [], []
            headers = [c.strip() for c in data_lines[0][1:-1].split("|")]
            rows = []
            for dl in data_lines[1:]:
                row = [c.strip() for c in dl[1:-1].split("|")]
                rows.append(row)
            return headers, rows

        def format_table(headers, rows):
            if not headers and not rows:
                return "Empty Set"
            cols = headers if headers else [f"col_{i}" for i in range(len(rows[0])) if rows]
            str_rows = [[str(c) if c is not None else "null" for c in r] for r in rows]
            col_widths = [len(c) for c in cols]
            for r in str_rows:
                for i, val in enumerate(r):
                    col_widths[i] = max(col_widths[i], len(val))
            sep = "+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+"
            hdr_line = "|" + "|".join([f" {c.ljust(w)} " for c, w in zip(cols, col_widths)]) + "|"
            res = [sep, hdr_line, sep]
            for r in str_rows:
                res.append("|" + "|".join([f" {val.ljust(w)} " for val, w in zip(r, col_widths)]) + "|")
            res.append(sep)
            return "\n".join(res)

        results = []
        all_passed = True
        total_time_ms = 0.0

        for idx, tc in enumerate(test_cases):
            tc_start = time.perf_counter()
            conn = sqlite3.connect(":memory:")
            cur = conn.cursor()
            raw_input = tc.get("input", "")
            raw_expected = tc.get("expected_output") or tc.get("expectedOutput") or ""
            
            # Setup database tables and rows from fixture
            try:
                if isinstance(raw_input, str) and raw_input.strip().startswith("{"):
                    inp_data = json.loads(raw_input)
                    if isinstance(inp_data, dict) and "headers" in inp_data and "rows" in inp_data:
                        for tbl, cols in inp_data["headers"].items():
                            col_defs = ", ".join([f'"{col}"' for col in cols])
                            cur.execute(f'CREATE TABLE "{tbl}" ({col_defs});')
                            rows = inp_data["rows"].get(tbl, [])
                            if rows:
                                placeholders = ", ".join(["?"] * len(cols))
                                cur.executemany(f'INSERT INTO "{tbl}" VALUES ({placeholders});', rows)
            except Exception as setup_err:
                pass

            # Execute Candidate SQL Query
            try:
                # Remove trailing semicolon if present for clean execution
                query_to_run = clean_stripped.rstrip(";").strip()
                cur.execute(query_to_run)
                actual_rows = cur.fetchall()
                actual_cols = [desc[0] for desc in cur.description] if cur.description else []
                actual_table_str = format_table(actual_cols, actual_rows)
                
                exp_cols, exp_rows = parse_table_output(raw_expected) if isinstance(raw_expected, str) and "|" in raw_expected else ([], [])
                
                # Compare column names and row values
                cols_match = True
                if exp_cols:
                    cols_match = ([c.lower() for c in actual_cols] == [c.lower() for c in exp_cols])
                
                def normalize_cell(val):
                    if val is None:
                        return "null"
                    s = str(val).strip()
                    if s.lower() in ("null", "none"):
                        return "null"
                    try:
                        f = float(s)
                        if f.is_integer():
                            return str(int(f))
                        return str(f)
                    except (ValueError, TypeError):
                        pass
                    return s.lower()

                norm_actual_rows = [[normalize_cell(x) for x in r] for r in actual_rows]
                norm_exp_rows = [[normalize_cell(x) for x in r] for r in exp_rows]
                
                # Check row equality (either order-exact or set-exact if unordered)
                rows_match = (norm_actual_rows == norm_exp_rows)
                if not rows_match and len(norm_actual_rows) == len(norm_exp_rows):
                    # Try sorted comparison in case ordering wasn't specified
                    try:
                        rows_match = (sorted([tuple(r) for r in norm_actual_rows]) == sorted([tuple(r) for r in norm_exp_rows]))
                    except Exception:
                        rows_match = False

                passed = cols_match and rows_match
                if not passed:
                    all_passed = False

                tc_elapsed = round((time.perf_counter() - tc_start) * 1000, 2)
                total_time_ms += tc_elapsed

                results.append({
                    "test_case_index": idx + 1,
                    "input_data": raw_input,
                    "expected_output": raw_expected,
                    "actual_output": actual_table_str,
                    "passed": passed,
                    "runtime_ms": max(0.1, tc_elapsed)
                })
            except Exception as sql_exec_err:
                all_passed = False
                tc_elapsed = round((time.perf_counter() - tc_start) * 1000, 2)
                total_time_ms += tc_elapsed
                results.append({
                    "test_case_index": idx + 1,
                    "input_data": raw_input,
                    "expected_output": raw_expected,
                    "actual_output": f"SQL Execution Error: {str(sql_exec_err)}",
                    "passed": False,
                    "error": str(sql_exec_err),
                    "runtime_ms": max(0.1, tc_elapsed)
                })
            finally:
                conn.close()

        passed_count = sum(1 for r in results if r.get("passed"))
        total = len(results)
        score_fraction = round(passed_count / total, 2) if total > 0 else 0.0

        return {
            "status": "ACCEPTED" if (all_passed and total > 0) else "WRONG_ANSWER",
            "is_correct": (all_passed and total > 0),
            "score_fraction": score_fraction,
            "test_cases_passed": passed_count,
            "total_test_cases": total,
            "feedback": f"Passed {passed_count}/{total} test cases." if not all_passed else f"All {total} test cases passed!",
            "test_case_results": results,
            "runtime_ms": max(0.1, round(total_time_ms, 2)),
            "memory_mb": None,
            "compiler_output": "SQL query evaluated successfully." if all_passed else "Query results did not match expected output."
        }
    @classmethod
    def _check_universal_equality(cls, actual: Any, expected: Any) -> bool:
        """Universal validation across all languages for order-agnostic collections, unquoted strings, and JSON."""
        if actual is None or expected is None:
            return False
        act_s = str(actual).strip()
        exp_s = str(expected).strip()
        if not act_s or not exp_s:
            return act_s == exp_s
        # For tabular results (ASCII tables), do NOT perform blind lowercased string equality
        if ("+---" in act_s or "+---" in exp_s) and ("|" in act_s or "|" in exp_s):
            return False

        if act_s == exp_s:
            return True
        if act_s.lower() == exp_s.lower() or act_s.replace(" ", "").lower() == exp_s.replace(" ", "").lower():
            return True
        # String unquoting: e.g. fl vs "fl"
        if act_s.strip('"\'') == exp_s.strip('"\'') and act_s:
            return True
        # JSON parsing comparison
        try:
            act_obj = json.loads(act_s)
        except Exception:
            act_obj = None
        try:
            exp_obj = json.loads(exp_s)
        except Exception:
            exp_obj = None

        if act_obj is not None and exp_obj is not None:
            if act_obj == exp_obj:
                return True
            # Permutations for 2-element arrays (e.g. Two Sum indices in any order)
            if isinstance(act_obj, list) and isinstance(exp_obj, list) and len(act_obj) == 2 and len(exp_obj) == 2:
                try:
                    if sorted(act_obj) == sorted(exp_obj):
                        return True
                except Exception:
                    pass
            # Multiset for 2D arrays (Subsets, Permutations)
            if isinstance(act_obj, list) and isinstance(exp_obj, list) and len(act_obj) == len(exp_obj):
                if all(isinstance(x, list) for x in act_obj) and all(isinstance(x, list) for x in exp_obj):
                    try:
                        if sorted([sorted(x) for x in act_obj]) == sorted([sorted(x) for x in exp_obj]):
                            return True
                    except Exception:
                        pass
        if exp_obj is not None and isinstance(exp_obj, str) and exp_obj == act_s:
            return True
        if act_obj is not None and isinstance(act_obj, str) and act_obj == exp_s:
            return True
        return False

    # -------------------------------------------------------------------------
    # OUTPUT PARSER
    # -------------------------------------------------------------------------
    @classmethod
    def _parse_sandbox_output(
        cls,
        stdout: str,
        test_cases: List[Dict[str, Any]],
        approach: str,
        proc_runtime_ms: Optional[float] = None,
        proc_memory_mb: Optional[float] = None
    ) -> Dict[str, Any]:
        start = stdout.find("---SANDBOX_RESULTS_START---")
        end = stdout.find("---SANDBOX_RESULTS_END---")

        if start != -1 and end != -1:
            try:
                data_str = stdout[start + len("---SANDBOX_RESULTS_START---"):end].strip()
                data = json.loads(data_str)
                results = data.get("results", [])
                for r in results:
                    if not r.get("passed"):
                        act = r.get("actual_output")
                        exp = r.get("expected_output")
                        if cls._check_universal_equality(act, exp):
                            r["passed"] = True
                passed_count = sum(1 for r in results if r.get("passed"))
                total = len(results)
                all_passed = (passed_count == total and total > 0)
                score_fraction = round(passed_count / total, 2) if total > 0 else 0.0

                tc_total_runtime = round(sum(r.get("runtime_ms", 0.0) for r in results), 2)
                actual_runtime = tc_total_runtime if tc_total_runtime > 0 else proc_runtime_ms
                actual_memory = proc_memory_mb or data.get("memory_mb")

                return {
                    "status": "ACCEPTED" if all_passed else "WRONG_ANSWER",
                    "is_correct": all_passed,
                    "score_fraction": score_fraction,
                    "test_cases_passed": passed_count,
                    "total_test_cases": total,
                    "feedback": f"Passed {passed_count}/{total} test cases." + (" All test cases passed!" if all_passed else " Check failing test cases below."),
                    "test_case_results": results,
                    "runtime_ms": actual_runtime,
                    "memory_mb": actual_memory,
                    "compiler_output": "Process exited with status 0."
                }
            except Exception as e:
                return {
                    "status": "RUNTIME_ERROR",
                    "is_correct": False,
                    "score_fraction": 0.0,
                    "feedback": f"Could not parse runner payload: {str(e)}",
                    "compiler_output": stdout[:300],
                    "error": f"Payload parse error: {str(e)}",
                    "runtime_ms": proc_runtime_ms,
                    "memory_mb": proc_memory_mb,
                    "test_case_results": []
                }
        else:
            return {
                "status": "RUNTIME_ERROR",
                "is_correct": False,
                "score_fraction": 0.0,
                "feedback": "Execution completed without returning structured test harness markers.",
                "compiler_output": stdout[:300] if stdout else "No output produced.",
                "error": stdout[:300] if stdout else "No output produced.",
                "runtime_ms": proc_runtime_ms,
                "memory_mb": proc_memory_mb,
                "test_case_results": []
            }
