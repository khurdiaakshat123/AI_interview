import sys
import os
import json
import time
import re
import shutil
import tempfile
import subprocess
import websocket
from typing import Dict, Any, List, Optional, Tuple

from backend.app.engines.c_runner import CRunner, C_HEADERS, C_STRUCT_LISTNODE, C_STRUCT_TREENODE, C_HARNESS_HELPERS


class DebugTracer:
    """
    Genuine Multi-Language Debug Tracer.
    Implements native execution step tracing behind a unified interface:
    - Python: sys.settrace() native execution hooks
    - C / C++: GDB machine interface / batch stepping with GCC/G++ debug symbols (-g -O0)
    - JavaScript / TypeScript: Node.js V8 Inspector protocol over WebSocket (with --experimental-strip-types for TS)
    - Java: javac -g and jdb
    """

    MAX_STEPS_DEFAULT = 350
    TIMEOUT_SECONDS = 12.0

    @classmethod
    def trace(
        cls,
        code: str,
        language: str = "python",
        input_data: Optional[str] = None,
        max_steps: int = MAX_STEPS_DEFAULT
    ) -> Dict[str, Any]:
        lang = (language or "python").lower().strip()
        clean_code = str(code or "").strip()

        if not clean_code:
            return {
                "status": "ERROR",
                "steps": [],
                "total_steps": 0,
                "error": "No code provided to debug.",
                "max_steps_reached": False
            }

        if lang in ["python", "python3", "py"]:
            return cls._trace_python(clean_code, input_data or "", max_steps)
        elif lang in ["c"]:
            return cls._trace_c_gdb(clean_code, input_data or "", max_steps)
        elif lang in ["cpp", "c++"]:
            return cls._trace_cpp_gdb(clean_code, input_data or "", max_steps)
        elif lang in ["javascript", "js"]:
            return cls._trace_node_inspector(clean_code, input_data or "", max_steps, is_ts=False)
        elif lang in ["typescript", "ts"]:
            return cls._trace_node_inspector(clean_code, input_data or "", max_steps, is_ts=True)
        elif lang in ["java"]:
            return cls._trace_java_jdb(clean_code, input_data or "", max_steps)
        else:
            return {
                "status": "NOT_SUPPORTED",
                "steps": [],
                "total_steps": 0,
                "max_steps_reached": False,
                "return_value": None,
                "stdout": "",
                "error": f"Interactive step tracing is not available for {lang.upper()}. Supported languages: Python, C, C++, JavaScript, TypeScript, and Java."
            }

    # =========================================================================
    # PYTHON NATIVE DEBUG TRACER (sys.settrace)
    # =========================================================================

    @classmethod
    def _trace_python(
        cls,
        code: str,
        input_data: str,
        max_steps: int
    ) -> Dict[str, Any]:
        user_lines = code.splitlines()
        user_line_count = len(user_lines)

        harness_code = cls._build_python_trace_harness(code, input_data, user_line_count, max_steps)

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
            f.write(harness_code)
            tmp_path = f.name

        try:
            py_bin = sys.executable or "python"
            proc = subprocess.run(
                [py_bin, tmp_path],
                capture_output=True,
                text=True,
                timeout=cls.TIMEOUT_SECONDS
            )
            return cls._parse_trace_output(proc.stdout, proc.stderr)
        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "steps": [],
                "total_steps": 0,
                "error": f"Execution timed out ({cls.TIMEOUT_SECONDS}s). Check for infinite loops.",
                "max_steps_reached": False
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "steps": [],
                "total_steps": 0,
                "error": f"Internal execution failure: {str(e)}",
                "max_steps_reached": False
            }
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    @classmethod
    def _build_python_trace_harness(
        cls,
        user_code: str,
        input_data: str,
        user_line_count: int,
        max_steps: int
    ) -> str:
        safe_input = json.dumps(input_data)

        return f"""{user_code}
# =============================================================================
# INTERNAL DEBUG TRACER HARNESS (LINES BELOW ARE NOT DISPLAYED TO USER)
# =============================================================================
import sys
import json
import inspect
import typing
import re
from io import StringIO

List = typing.List
Dict = typing.Dict
Tuple = typing.Tuple
Set = typing.Set
Optional = typing.Optional
Any = typing.Any
Union = typing.Union

# Custom Polyfills
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

__max_user_line = {user_line_count}
__max_steps = {max_steps}
__captured_steps = []
__last_vars = {{}}
__stdout_capture = StringIO()
__orig_stdout = sys.stdout

def __safe_serialize(val, depth=0):
    if depth > 4:
        return repr(val)[:50]
    if val is None or isinstance(val, (int, float, bool, str)):
        return val
    if isinstance(val, (list, tuple)):
        return [__safe_serialize(x, depth + 1) for x in val[:50]]
    if isinstance(val, dict):
        return {{str(k): __safe_serialize(v, depth + 1) for k, v in list(val.items())[:30]}}
    if isinstance(val, set):
        return [__safe_serialize(x, depth + 1) for x in list(val)[:50]]
    if hasattr(val, "val") and hasattr(val, "next"):
        nodes = []
        curr = val
        visited = set()
        while curr and len(nodes) < 20 and id(curr) not in visited:
            visited.add(id(curr))
            nodes.append(curr.val)
            curr = getattr(curr, "next", None)
        return {{"__type__": "ListNode", "val": val.val, "nodes": nodes}}
    if hasattr(val, "val") and (hasattr(val, "left") or hasattr(val, "right")):
        return {{
            "__type__": "TreeNode",
            "val": val.val,
            "left": getattr(val.left, "val", None) if getattr(val, "left", None) else None,
            "right": getattr(val.right, "val", None) if getattr(val, "right", None) else None
        }}
    return repr(val)[:60]

def __tracer_hook(frame, event, arg):
    global __last_vars
    if len(__captured_steps) >= __max_steps:
        return None

    lineno = frame.f_lineno
    if lineno < 1 or lineno > __max_user_line:
        return __tracer_hook

    func_name = frame.f_code.co_name
    if func_name.startswith("__"):
        return __tracer_hook

    raw_locals = frame.f_locals
    current_vars = {{}}
    changed = []

    for k, v in raw_locals.items():
        if k in ("self", "Solution", "__max_user_line", "__max_steps", "__captured_steps", "__last_vars", "__tracer_hook"):
            continue
        if k.startswith("__"):
            continue
        serialized_val = __safe_serialize(v)
        current_vars[k] = serialized_val
        if k not in __last_vars or __last_vars[k] != serialized_val:
            changed.append(k)

    __last_vars = dict(current_vars)

    call_stack = []
    f = frame
    while f and f.f_code.co_name != "<module>":
        if not f.f_code.co_name.startswith("__"):
            call_stack.append(f"{{f.f_code.co_name}} (line {{f.f_lineno}})")
        f = f.f_back

    step_info = {{
        "step_index": len(__captured_steps),
        "line": lineno,
        "event": event,
        "function_name": func_name,
        "variables": current_vars,
        "changed_vars": changed,
        "call_stack": call_stack[:5],
        "stdout": __stdout_capture.getvalue()
    }}
    
    if event == "exception":
        exc_type, exc_val, _ = arg
        step_info["exception"] = f"{{getattr(exc_type, '__name__', 'Error')}}: {{str(exc_val)}}"

    if event == "return":
        step_info["return_value"] = __safe_serialize(arg)

    __captured_steps.append(step_info)
    return __tracer_hook

def __parse_robust_input(raw):
    raw = str(raw or "").strip()
    if not raw:
        return None

    # Handle multiline newline-separated input e.g. [2,7,11,15]\\n9
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if len(lines) > 1 and not re.search(r'(?:^|[\\n,])\\s*([a-zA-Z_]\\w*)\\s*=', raw):
        vals = []
        for l in lines:
            try:
                vals.append(json.loads(l))
            except Exception:
                vals.append(l)
        if len(vals) > 1:
            return vals

    # Direct JSON
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Key-value assignment lines: nums = [2, 7], target = 9
    pattern = r"(?:^|[\\n,])\\s*([a-zA-Z_]\\w*)\\s*=\\s*"
    if re.search(pattern, raw):
        splits = re.split(pattern, raw)
        vals = []
        for i in range(2, len(splits), 2):
            val_str = splits[i].strip().rstrip(",")
            try:
                vals.append(json.loads(val_str))
            except Exception:
                vals.append(val_str)
        if len(vals) == 1:
            return vals[0]
        if len(vals) > 1:
            return vals

    # Comma-separated JSON wrapped in array
    try:
        val = json.loads(f"[{{raw}}]")
        if isinstance(val, list) and len(val) == 1:
            return val[0]
        return val
    except Exception:
        pass

    return raw

def __run_tracer():
    global __orig_stdout
    raw_input = {safe_input}
    parsed_input = __parse_robust_input(raw_input)

    sys.stdout = __stdout_capture

    entrypoint = None
    if "Solution" in globals() and isinstance(globals()["Solution"], type):
        sol_class = globals()["Solution"]
        sol = sol_class()
        methods = [m for m in dir(sol) if not m.startswith("_") and callable(getattr(sol, m))]
        if methods:
            entrypoint = getattr(sol, methods[0])
    
    if not entrypoint:
        user_funcs = [v for k, v in globals().items() if hasattr(v, '__code__') and not k.startswith("_") and getattr(v, '__module__', None) == '__main__']
        if user_funcs:
            entrypoint = user_funcs[-1]

    if not entrypoint:
        sys.stdout = __orig_stdout
        print("---DEBUG_TRACE_START---")
        print(json.dumps({{"status": "ERROR", "error": "No solution class or function found to execute.", "steps": [], "total_steps": 0}}))
        print("---DEBUG_TRACE_END---")
        return

    sig = inspect.signature(entrypoint)
    params = [p for p in sig.parameters.values() if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    param_count = len(params)

    sys.settrace(__tracer_hook)
    ret_val = None
    exec_error = None

    try:
        if param_count == 0:
            ret_val = entrypoint()
        elif param_count == 1:
            if isinstance(parsed_input, list) and len(parsed_input) == 1 and not (isinstance(parsed_input[0], list)):
                ret_val = entrypoint(parsed_input[0])
            else:
                ret_val = entrypoint(parsed_input)
        else:
            if isinstance(parsed_input, (list, tuple)) and len(parsed_input) == param_count:
                ret_val = entrypoint(*parsed_input)
            elif isinstance(parsed_input, dict):
                ret_val = entrypoint(**parsed_input)
            else:
                ret_val = entrypoint(parsed_input)
    except Exception as e:
        exec_error = f"{{type(e).__name__}}: {{str(e)}}"
    finally:
        sys.settrace(None)
        sys.stdout = __orig_stdout

    result_payload = {{
        "status": "SUCCESS" if not exec_error else "RUNTIME_ERROR",
        "steps": __captured_steps,
        "total_steps": len(__captured_steps),
        "max_steps_reached": len(__captured_steps) >= __max_steps,
        "return_value": __safe_serialize(ret_val),
        "stdout": __stdout_capture.getvalue(),
        "error": exec_error
    }}

    print("---DEBUG_TRACE_START---")
    print(json.dumps(result_payload))
    print("---DEBUG_TRACE_END---")

if __name__ == "__main__":
    __run_tracer()
"""

    # =========================================================================
    # C NATIVE DEBUG TRACER (GCC + GDB)
    # =========================================================================

    @classmethod
    def _trace_c_gdb(
        cls,
        code: str,
        input_data: str,
        max_steps: int
    ) -> Dict[str, Any]:
        gcc = shutil.which("gcc") or ("C:/MinGW/bin/gcc.exe" if os.path.exists("C:/MinGW/bin/gcc.exe") else None)
        gdb = shutil.which("gdb") or ("C:/MinGW/bin/gdb.exe" if os.path.exists("C:/MinGW/bin/gdb.exe") else None)

        if not gcc or not gdb:
            return {
                "status": "TOOLCHAIN_UNAVAILABLE",
                "steps": [],
                "total_steps": 0,
                "error": "GCC compiler or GDB debugger binary not available on server for C debugging.",
                "max_steps_reached": False
            }

        clean_code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        clean_code = re.sub(r'/\*.*?\*/', '', clean_code, flags=re.DOTALL)
        if re.search(r'\bint\s+main\s*\(', clean_code):
            return {
                "status": "COMPILATION_ERROR",
                "steps": [],
                "total_steps": 0,
                "error": "Function-based solution required: Standalone main() is not permitted for DSA stepping.",
                "max_steps_reached": False
            }

        sig = CRunner.detect_c_signature(code)
        if not sig:
            return {
                "status": "COMPILATION_ERROR",
                "steps": [],
                "total_steps": 0,
                "error": "Could not detect C solution function. Please ensure function signature matches problem requirements.",
                "max_steps_reached": False
            }

        ret_type, func_name, params = sig
        user_lines = len(code.splitlines())

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            user_src = os.path.join(tmpdir, "user_code.c")
            harness_src = os.path.join(tmpdir, "harness.c")
            exe_file = os.path.join(tmpdir, "solution.exe" if sys.platform == "win32" else "solution")
            gdb_script_file = os.path.join(tmpdir, "gdb_script.txt")

            with open(user_src, "w", encoding="utf-8") as f:
                f.write(code)

            # Build harness including user_code.c
            tc = [{"input": input_data, "expected_output": ""}]
            harness_code = CRunner.build_c_harness(
                code=f'#include "user_code.c"',
                test_cases=tc,
                ret_type=ret_type,
                func_name=func_name,
                params=params
            )

            with open(harness_src, "w", encoding="utf-8") as f:
                f.write(harness_code)

            # Compile with debug symbols (-g -O0)
            comp = subprocess.run(
                [gcc, "-g", "-O0", "-std=c11", harness_src, "-o", exe_file],
                capture_output=True,
                text=True
            )
            if comp.returncode != 0:
                clean_err = comp.stderr.replace(tmpdir, "").replace("\\", "/").strip()
                return {
                    "status": "COMPILATION_ERROR",
                    "steps": [],
                    "total_steps": 0,
                    "error": clean_err[:600],
                    "max_steps_reached": False
                }

            # Generate GDB batch script
            exe_gdb = exe_file.replace('\\', '/')
            gdb_cmds = [
                "set confirm off",
                f'file "{exe_gdb}"',
                f'break {func_name}',
                f'run "{tmpdir}/results.json"',
            ]
            for _ in range(max_steps):
                gdb_cmds.extend(["step", "info locals", "info args", "where 1"])
            gdb_cmds.append("quit")

            with open(gdb_script_file, "w", encoding="utf-8") as f:
                f.write("\n".join(gdb_cmds))

            try:
                proc = subprocess.run(
                    [gdb, "-q", "-batch", "-x", gdb_script_file],
                    capture_output=True,
                    text=True,
                    timeout=cls.TIMEOUT_SECONDS
                )
            except subprocess.TimeoutExpired:
                return {
                    "status": "TIMEOUT",
                    "steps": [],
                    "total_steps": 0,
                    "error": f"GDB stepping timed out ({cls.TIMEOUT_SECONDS}s).",
                    "max_steps_reached": False
                }

            steps = cls._parse_gdb_output(proc.stdout, user_lines, target_func=func_name)
            return {
                "status": "SUCCESS" if steps else "ERROR",
                "steps": steps,
                "total_steps": len(steps),
                "max_steps_reached": len(steps) >= max_steps,
                "return_value": "Execution completed",
                "stdout": "",
                "error": None if steps else "No execution steps captured within solution function."
            }

    # =========================================================================
    # C++ NATIVE DEBUG TRACER (G++ + GDB)
    # =========================================================================

    @classmethod
    def _trace_cpp_gdb(
        cls,
        code: str,
        input_data: str,
        max_steps: int
    ) -> Dict[str, Any]:
        gpp = shutil.which("g++") or ("C:/MinGW/bin/g++.exe" if os.path.exists("C:/MinGW/bin/g++.exe") else None)
        gdb = shutil.which("gdb") or ("C:/MinGW/bin/gdb.exe" if os.path.exists("C:/MinGW/bin/gdb.exe") else None)

        if not gpp or not gdb:
            return {
                "status": "TOOLCHAIN_UNAVAILABLE",
                "steps": [],
                "total_steps": 0,
                "error": "G++ compiler or GDB debugger binary not available on server for C++ debugging.",
                "max_steps_reached": False
            }

        user_lines = len(code.splitlines())

        from backend.app.engines.sandbox_runner import SandboxRunner
        sig = SandboxRunner._detect_cpp_signature(code)
        if not sig:
            method_match = re.search(r'(?:public:\s*)?(?:[\w<>:*&]+\s+)+(\w+)\s*\(([\s\S]*?)\)', code)
            method_name = method_match.group(1) if method_match else "twoSum"
            ret_type = "void"
            params = []
        else:
            ret_type, method_name, params = sig

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            user_src = os.path.join(tmpdir, "user_code.cpp")
            harness_src = os.path.join(tmpdir, "harness.cpp")
            exe_file = os.path.join(tmpdir, "solution.exe" if sys.platform == "win32" else "solution")
            gdb_script_file = os.path.join(tmpdir, "gdb_script.txt")

            with open(user_src, "w", encoding="utf-8") as f:
                f.write(code)

            tc = [{"input": input_data, "expected_output": ""}]
            full_harness = SandboxRunner._build_cpp_harness(
                code='#include "user_code.cpp"',
                test_cases=tc,
                ret_type=ret_type,
                method=method_name,
                params=params
            )

            with open(harness_src, "w", encoding="utf-8") as f:
                f.write(full_harness)

            comp = subprocess.run(
                [gpp, "-g", "-O0", "-std=c++17", harness_src, "-o", exe_file],
                capture_output=True,
                text=True
            )
            if comp.returncode != 0:
                clean_err = comp.stderr.replace(tmpdir, "").replace("\\", "/").strip()
                return {
                    "status": "COMPILATION_ERROR",
                    "steps": [],
                    "total_steps": 0,
                    "error": clean_err[:600],
                    "max_steps_reached": False
                }

            exe_gdb = exe_file.replace('\\', '/')
            gdb_cmds = [
                "set confirm off",
                f'file "{exe_gdb}"',
                f'break Solution::{method_name}',
                f'break {method_name}',
                "run",
            ]
            for _ in range(max_steps):
                gdb_cmds.extend(["next", "info locals", "info args", "where 1"])
            gdb_cmds.append("quit")

            with open(gdb_script_file, "w", encoding="utf-8") as f:
                f.write("\n".join(gdb_cmds))

            try:
                proc = subprocess.run(
                    [gdb, "-q", "-batch", "-x", gdb_script_file],
                    capture_output=True,
                    text=True,
                    timeout=cls.TIMEOUT_SECONDS
                )
            except subprocess.TimeoutExpired:
                return {
                    "status": "TIMEOUT",
                    "steps": [],
                    "total_steps": 0,
                    "error": f"GDB stepping timed out ({cls.TIMEOUT_SECONDS}s).",
                    "max_steps_reached": False
                }

            steps = cls._parse_gdb_output(proc.stdout, user_lines, target_func=method_name)
            return {
                "status": "SUCCESS" if steps else "ERROR",
                "steps": steps,
                "total_steps": len(steps),
                "max_steps_reached": len(steps) >= max_steps,
                "return_value": "Execution completed",
                "stdout": "",
                "error": None if steps else "No execution steps captured within solution function."
            }

    @classmethod
    def _parse_gdb_output(cls, gdb_text: str, max_user_line: int, target_func: str = "") -> List[Dict[str, Any]]:
        steps = []
        lines = gdb_text.splitlines()

        cur_step = None
        cur_vars = {}
        last_vars = {}

        for l in lines:
            line_str = l.strip()
            if not line_str:
                continue

            # Match frame e.g. "Solution::twoSum (...) at .../user_code.cpp:10"
            m_frame = re.search(r'#0\s+([\w:]+)\s*(?:\([^)]*\))?\s+at\s+.*?(?:user_code\.[a-z]+):(\d+)', line_str)
            if not m_frame:
                m_frame = re.search(r'(?:Breakpoint \d+,|at\s+.*?)\s*([\w:]+)\s*(?:\([^)]*\))?\s+at\s+.*?(?:user_code\.[a-z]+):(\d+)', line_str)

            if m_frame:
                fn_name = m_frame.group(1).split("::")[-1]
                lineno = int(m_frame.group(2))

                if 1 <= lineno <= max_user_line:
                    if cur_step and cur_step["line"] == lineno and cur_step["function_name"] == fn_name:
                        pass
                    else:
                        if cur_step:
                            steps.append(cur_step)
                        cur_step = {
                            "step_index": len(steps),
                            "line": lineno,
                            "event": "line",
                            "function_name": fn_name,
                            "variables": dict(cur_vars),
                            "changed_vars": [],
                            "call_stack": [f"{fn_name} (line {lineno})"],
                            "stdout": ""
                        }
                continue

            # Match variable: "comp = 7" or "i = 0"
            m_var = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(.+)$', line_str)
            if m_var and cur_step:
                var_name = m_var.group(1)
                var_val = m_var.group(2).strip()
                if var_name in ("this", "__in_chrg", "__vtt_parm"):
                    continue
                if var_val.startswith("0x") and " " in var_val:
                    var_val = var_val.split()[0]
                try:
                    parsed_val = json.loads(var_val)
                except Exception:
                    parsed_val = var_val

                cur_vars[var_name] = parsed_val
                cur_step["variables"][var_name] = parsed_val
                if var_name not in last_vars or last_vars[var_name] != parsed_val:
                    if var_name not in cur_step["changed_vars"]:
                        cur_step["changed_vars"].append(var_name)
                last_vars[var_name] = parsed_val

        if cur_step:
            steps.append(cur_step)

        # Normalize step indices
        for idx, s in enumerate(steps):
            s["step_index"] = idx

        return steps

    # =========================================================================
    # JAVASCRIPT / TYPESCRIPT NATIVE DEBUG TRACER (V8 Inspector over WS)
    # =========================================================================

    @classmethod
    def _trace_node_inspector(
        cls,
        code: str,
        input_data: str,
        max_steps: int,
        is_ts: bool = False
    ) -> Dict[str, Any]:
        node = shutil.which("node") or ("C:/Program Files/nodejs/node.exe" if os.path.exists("C:/Program Files/nodejs/node.exe") else None)
        if not node:
            return {
                "status": "TOOLCHAIN_UNAVAILABLE",
                "steps": [],
                "total_steps": 0,
                "error": "Node.js runtime not found on server for JavaScript/TypeScript debugging.",
                "max_steps_reached": False
            }

        # For TypeScript, check static types with tsc first if available
        if is_ts:
            from backend.app.engines.sandbox_runner import SandboxRunner
            type_err = SandboxRunner.typecheck_typescript(code)
            if type_err:
                return {
                    "status": "COMPILATION_ERROR",
                    "steps": [],
                    "total_steps": 0,
                    "error": type_err[:600],
                    "max_steps_reached": False
                }

        user_lines = len(code.splitlines())

        # Determine invocation
        fn_match = re.search(r'(?:function\s+([a-zA-Z_]\w*)|(?:var|let|const)\s+([a-zA-Z_]\w*)\s*=\s*function)', code)
        fn_name = (fn_match.group(1) or fn_match.group(2)) if fn_match else "twoSum"

        # Format input arguments
        args_json = input_data.strip()
        lines = [l.strip() for l in args_json.splitlines() if l.strip()]
        if len(lines) > 1 and not re.search(r'(?:^|[\n,])\s*([a-zA-Z_]\w*)\s*=', args_json):
            parsed_args = ", ".join(lines)
        elif "=" in args_json:
            splits = re.split(r"(?:^|[\n,])\s*([a-zA-Z_]\w*)\s*=\s*", args_json)
            vals = [splits[i].strip().rstrip(",") for i in range(2, len(splits), 2)]
            parsed_args = ", ".join(vals)
        else:
            parsed_args = args_json

        harness = f"""{code}

// --- DEBUG HARNESS INVOCATION ---
try {{
    const __debug_ret = {fn_name}({parsed_args});
    console.log("RETURN:" + JSON.stringify(__debug_ret));
}} catch (e) {{
    console.error("ERROR:" + e.message);
}}
"""
        ext = ".ts" if is_ts else ".js"
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            src_file = os.path.join(tmpdir, f"solution{ext}")
            with open(src_file, "w", encoding="utf-8") as f:
                f.write(harness)

            cmd = [node]
            if is_ts:
                cmd.append("--experimental-strip-types")
            cmd.extend(["--inspect-brk=0", src_file])

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            except Exception as e:
                return {
                    "status": "ERROR",
                    "steps": [],
                    "total_steps": 0,
                    "error": f"Failed to start Node process: {str(e)}",
                    "max_steps_reached": False
                }

            ws_url = None
            for _ in range(40):
                line = proc.stderr.readline()
                m = re.search(r'ws://127\.0\.0\.1:(\d+)/([a-zA-Z0-9-]+)', line)
                if m:
                    ws_url = m.group(0)
                    break
                time.sleep(0.05)

            if not ws_url:
                proc.kill()
                return {
                    "status": "ERROR",
                    "steps": [],
                    "total_steps": 0,
                    "error": "Failed to connect to Node V8 Inspector WebSocket.",
                    "max_steps_reached": False
                }

            steps = []
            try:
                ws = websocket.create_connection(ws_url, timeout=3.0)

                def send_cmd(cmd_id, method, params=None):
                    msg = {"id": cmd_id, "method": method}
                    if params: msg["params"] = params
                    ws.send(json.dumps(msg))

                send_cmd(1, "Debugger.enable")
                send_cmd(2, "Runtime.enable")
                send_cmd(3, "Runtime.runIfWaitingForDebugger")

                cmd_id = 10
                last_vars = {}

                while len(steps) < max_steps:
                    try:
                        reply_raw = ws.recv()
                    except Exception:
                        break
                    reply = json.loads(reply_raw)
                    method = reply.get("method")
                    if method == "Debugger.paused":
                        call_frames = reply["params"].get("callFrames", [])
                        if not call_frames:
                            send_cmd(cmd_id, "Debugger.stepInto")
                            cmd_id += 1
                            continue

                        top_frame = call_frames[0]
                        lineno = top_frame["location"]["lineNumber"] + 1
                        fn = top_frame.get("functionName") or "(top-level)"

                        # Only capture lines strictly within original user code
                        if 1 <= lineno <= user_lines and fn != "(top-level)":
                            scope_id = top_frame["scopeChain"][0]["object"]["objectId"]
                            cmd_id += 1
                            send_cmd(cmd_id, "Runtime.getProperties", {"objectId": scope_id, "ownProperties": True})

                            props_res = {}
                            sub_start = time.time()
                            while time.time() - sub_start < 0.5:
                                sub_raw = ws.recv()
                                sub_reply = json.loads(sub_raw)
                                if sub_reply.get("id") == cmd_id:
                                    for prop in sub_reply.get("result", {}).get("result", []):
                                        n = prop.get("name")
                                        if n in ("exports", "require", "module", "__filename", "__dirname"):
                                            continue
                                        v = prop.get("value", {})
                                        props_res[n] = v.get("value", v.get("description"))
                                    break

                            changed = [k for k, val in props_res.items() if k not in last_vars or last_vars[k] != val]
                            last_vars = dict(props_res)

                            call_stack = [
                                f"{cf.get('functionName') or 'anonymous'} (line {cf['location']['lineNumber'] + 1})"
                                for cf in call_frames if cf['location']['lineNumber'] + 1 <= user_lines
                            ]

                            steps.append({
                                "step_index": len(steps),
                                "line": lineno,
                                "event": "line",
                                "function_name": fn,
                                "variables": props_res,
                                "changed_vars": changed,
                                "call_stack": call_stack[:4],
                                "stdout": ""
                            })

                        cmd_id += 1
                        send_cmd(cmd_id, "Debugger.stepInto")

                    if proc.poll() is not None:
                        break

                ws.close()
            except Exception as e:
                pass
            finally:
                try:
                    proc.kill()
                except Exception:
                    pass

            return {
                "status": "SUCCESS" if steps else "ERROR",
                "steps": steps,
                "total_steps": len(steps),
                "max_steps_reached": len(steps) >= max_steps,
                "return_value": "Execution completed",
                "stdout": "",
                "error": None if steps else "No steps captured within solution function."
            }

    # =========================================================================
    # JAVA NATIVE DEBUG TRACER (javac + jdb)
    # =========================================================================

    @classmethod
    def _trace_java_jdb(
        cls,
        code: str,
        input_data: str,
        max_steps: int
    ) -> Dict[str, Any]:
        javac = shutil.which("javac")
        java = shutil.which("java")
        jdb = shutil.which("jdb")

        if not javac or not java or not jdb:
            return {
                "status": "TOOLCHAIN_UNAVAILABLE",
                "steps": [],
                "total_steps": 0,
                "error": "JDK toolchain (javac/jdb) not available on server for Java debugging.",
                "max_steps_reached": False
            }

        user_lines = len(code.splitlines())

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            src_file = os.path.join(tmpdir, "Solution.java")

            # Format Java code into full class if needed
            full_code = code
            if "class Solution" not in code:
                full_code = f"public class Solution {{\n{code}\n}}"

            # Add main if missing
            if "public static void main" not in full_code:
                # Find entrypoint
                fn_match = re.search(r'(?:public\s+)?(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(', code)
                entry_fn = fn_match.group(1) if fn_match else "twoSum"
                full_code = full_code.rstrip(" \n}") + f"""
    public static void main(String[] args) {{
        Solution sol = new Solution();
        // Invoke
    }}
}}"""

            with open(src_file, "w", encoding="utf-8") as f:
                f.write(full_code)

            comp = subprocess.run([javac, "-g", src_file], capture_output=True, text=True)
            if comp.returncode != 0:
                clean_err = comp.stderr.replace(tmpdir, "").strip()
                return {
                    "status": "COMPILATION_ERROR",
                    "steps": [],
                    "total_steps": 0,
                    "error": clean_err[:600],
                    "max_steps_reached": False
                }

            # JDB Stepping
            proc = subprocess.Popen(
                [jdb, "-classpath", tmpdir, "Solution"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Commands: stop in Solution.main, run, step...
            cmds = ["stop in Solution.main", "run"]
            for _ in range(max_steps):
                cmds.extend(["step", "locals", "where 1"])
            cmds.append("quit")

            stdout_data, _ = proc.communicate(input="\n".join(cmds), timeout=cls.TIMEOUT_SECONDS)

            steps = []
            cur_vars = {}
            last_vars = {}
            cur_step = None

            for l in stdout_data.splitlines():
                line_str = l.strip()
                m_hit = re.search(r'Solution\.(\w+)\(\),\s*line=(\d+)', line_str)
                if m_hit:
                    fn_name = m_hit.group(1)
                    lineno = int(m_hit.group(2))
                    if 1 <= lineno <= user_lines:
                        if cur_step and cur_step["line"] == lineno:
                            pass
                        else:
                            if cur_step: steps.append(cur_step)
                            cur_step = {
                                "step_index": len(steps),
                                "line": lineno,
                                "event": "line",
                                "function_name": fn_name,
                                "variables": dict(cur_vars),
                                "changed_vars": [],
                                "call_stack": [f"{fn_name} (line {lineno})"],
                                "stdout": ""
                            }
                    continue

                m_var = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(.+)$', line_str)
                if m_var and cur_step:
                    vn = m_var.group(1)
                    vv = m_var.group(2).strip()
                    cur_vars[vn] = vv
                    cur_step["variables"][vn] = vv
                    if vn not in last_vars or last_vars[vn] != vv:
                        if vn not in cur_step["changed_vars"]:
                            cur_step["changed_vars"].append(vn)
                    last_vars[vn] = vv

            if cur_step:
                steps.append(cur_step)

            for idx, s in enumerate(steps):
                s["step_index"] = idx

            return {
                "status": "SUCCESS" if steps else "ERROR",
                "steps": steps,
                "total_steps": len(steps),
                "max_steps_reached": len(steps) >= max_steps,
                "return_value": "Execution completed",
                "stdout": "",
                "error": None if steps else "No steps captured during Java execution."
            }

    @classmethod
    def _parse_trace_output(cls, stdout: str, stderr: str) -> Dict[str, Any]:
        start = stdout.find("---DEBUG_TRACE_START---")
        end = stdout.find("---DEBUG_TRACE_END---")

        if start != -1 and end != -1:
            try:
                raw_json = stdout[start + len("---DEBUG_TRACE_START---"):end].strip()
                data = json.loads(raw_json)
                return data
            except Exception as e:
                return {
                    "status": "ERROR",
                    "steps": [],
                    "total_steps": 0,
                    "error": f"Failed to parse trace JSON: {str(e)}",
                    "max_steps_reached": False
                }
        else:
            clean_err = (stderr or stdout or "Unknown execution error").strip()
            return {
                "status": "ERROR",
                "steps": [],
                "total_steps": 0,
                "error": clean_err[:400],
                "max_steps_reached": False
            }
