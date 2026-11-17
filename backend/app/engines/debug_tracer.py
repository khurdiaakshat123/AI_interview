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
from backend.app.engines.execution_serialization import json_safe_trace


class DebugTracer:
    """
    Genuine Multi-Language Debug Tracer.
    Implements native execution step tracing behind a unified interface:
    - Python: sys.settrace() native execution hooks
    - C / C++: GDB machine interface / batch stepping with GCC/G++ debug symbols (-g -O0)
    - JavaScript / TypeScript: Node.js V8 Inspector, with TypeScript compilation and source maps
    - Java: javac -g and JDI execution events
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
        max_steps = max(1, min(int(max_steps), cls.MAX_STEPS_DEFAULT))

        if not clean_code:
            return {
                "status": "ERROR",
                "steps": [],
                "total_steps": 0,
                "error": "No code provided to debug.",
                "max_steps_reached": False
            }

        if lang in ["python", "python3", "py"]:
            result = cls._trace_python(clean_code, input_data or "", max_steps)
        elif lang in ["c"]:
            result = cls._trace_c_gdb(clean_code, input_data or "", max_steps)
        elif lang in ["cpp", "c++"]:
            result = cls._trace_cpp_gdb(clean_code, input_data or "", max_steps)
        elif lang in ["javascript", "js"]:
            result = cls._trace_node_inspector(clean_code, input_data or "", max_steps, is_ts=False)
        elif lang in ["typescript", "ts"]:
            result = cls._trace_node_inspector(clean_code, input_data or "", max_steps, is_ts=True)
        elif lang in ["java"]:
            result = cls._trace_java_jdb(clean_code, input_data or "", max_steps)
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
        return json_safe_trace(result)

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

        return f"""
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
    if frame.f_code.co_filename != '<candidate>':
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

def __bind_argument(param, value):
    annotation = str(param.annotation)
    if isinstance(value, list) and 'ListNode' in annotation:
        dummy = ListNode()
        tail = dummy
        for item in value:
            tail.next = ListNode(item)
            tail = tail.next
        return dummy.next
    if isinstance(value, list) and 'TreeNode' in annotation:
        if not value or value[0] is None:
            return None
        root = TreeNode(value[0])
        queue, index = [root], 1
        for node in queue:
            for side in ('left', 'right'):
                if index >= len(value):
                    break
                item = value[index]
                index += 1
                if item is not None:
                    child = TreeNode(item)
                    setattr(node, side, child)
                    queue.append(child)
        return root
    return value

def __run_tracer():
    global __orig_stdout
    raw_input = {safe_input}
    parsed_input = __parse_robust_input(raw_input)

    sys.stdout = __stdout_capture

    entrypoint = None
    if "Solution" in globals() and isinstance(globals()["Solution"], type):
        sol_class = globals()["Solution"]
        sol = sol_class()
        methods = [m for m in sol_class.__dict__ if not m.startswith("_") and callable(getattr(sol, m))]
        if not methods:
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
            annotation = str(params[0].annotation)
            structured = ('ListNode' in annotation or 'TreeNode' in annotation or
                          annotation in ('list', 'List', 'tuple', 'Tuple', 'dict', 'Dict', 'set', 'Set', 'Sequence') or
                          params[0].annotation in (list, tuple, dict, set) or
                          typing.get_origin(params[0].annotation) in (list, tuple, dict, set) or
                          any(token in annotation for token in ('List[', 'list[', 'Tuple[', 'tuple[', 'Dict[', 'dict[', 'Set[', 'set[', 'Sequence[')))
            value = parsed_input
            if not structured and isinstance(value, list) and len(value) == 1 and not isinstance(value[0], list):
                value = value[0]
            ret_val = entrypoint(__bind_argument(params[0], value))
        else:
            if isinstance(parsed_input, (list, tuple)) and len(parsed_input) == param_count:
                ret_val = entrypoint(*[__bind_argument(p, v) for p, v in zip(params, parsed_input)])
            elif isinstance(parsed_input, dict):
                ret_val = entrypoint(**{{p.name: __bind_argument(p, parsed_input[p.name]) for p in params if p.name in parsed_input}})
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
    exec(compile({json.dumps(user_code)}, '<candidate>', 'exec'), globals())
    __run_tracer()
"""

    # =========================================================================
    # C NATIVE DEBUG TRACER (GCC + GDB)
    # =========================================================================

    @classmethod
    def _trace_c_gdb(cls, code, input_data, max_steps):
        from backend.app.engines.native_debugger import trace_gdb
        return trace_gdb(code, 'c', input_data, max_steps, cls.TIMEOUT_SECONDS)

    @classmethod
    def _trace_cpp_gdb(cls, code, input_data, max_steps):
        from backend.app.engines.native_debugger import trace_gdb
        return trace_gdb(code, 'cpp', input_data, max_steps, cls.TIMEOUT_SECONDS)

    @classmethod
    def _trace_node_inspector(cls, code, input_data, max_steps, is_ts=False):
        from backend.app.engines.native_debugger import trace_node
        return trace_node(code, input_data, max_steps, cls.TIMEOUT_SECONDS, is_ts)

    @classmethod
    def _trace_java_jdb(cls, code, input_data, max_steps):
        from backend.app.engines.native_debugger import trace_java
        return trace_java(code, input_data, max_steps, cls.TIMEOUT_SECONDS)

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
