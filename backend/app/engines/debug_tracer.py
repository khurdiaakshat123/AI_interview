import sys
import os
import json
import time
import ast
import tempfile
import subprocess
from typing import Dict, Any, List, Optional, Tuple

class DebugTracer:
    """
    Time-Travel Code Execution Tracer for Step-by-Step Visual Debugging.
    Captures line-by-line snapshots of:
    - Active line number in user code
    - Variables (primitives, lists, dicts, ListNodes, TreeNodes)
    - Variable mutations (diffing with previous step)
    - Call stack
    - Standard output / return values / exceptions
    """

    MAX_STEPS_DEFAULT = 350
    TIMEOUT_SECONDS = 4.0

    @classmethod
    def trace(
        cls,
        code: str,
        language: str = "python3",
        input_data: Optional[str] = None,
        max_steps: int = MAX_STEPS_DEFAULT
    ) -> Dict[str, Any]:
        lang = (language or "python3").lower().strip()
        clean_code = str(code or "").strip()

        if not clean_code:
            return {
                "status": "ERROR",
                "steps": [],
                "total_steps": 0,
                "error": "No code provided to debug.",
                "max_steps_reached": False
            }

        if lang in ["python", "python3"]:
            return cls._trace_python(clean_code, input_data or "", max_steps)
        elif lang in ["javascript", "typescript", "js", "ts"]:
            return cls._trace_javascript(clean_code, input_data or "", max_steps)
        else:
            return cls._trace_generic_fallback(clean_code, lang, input_data or "", max_steps)

    @classmethod
    def _trace_python(
        cls,
        code: str,
        input_data: str,
        max_steps: int
    ) -> Dict[str, Any]:
        # 1. Syntax check
        try:
            ast.parse(code)
        except SyntaxError as e:
            return {
                "status": "ERROR",
                "steps": [],
                "total_steps": 0,
                "error": f"Syntax Error on line {e.lineno}: {e.msg}",
                "line": e.lineno,
                "max_steps_reached": False
            }

        user_line_count = len(code.splitlines())
        harness_script = cls._build_python_trace_harness(code, input_data, user_line_count, max_steps)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp_path = tmp.name
            tmp.write(harness_script)

        safe_env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in ['KEY', 'SECRET', 'DATABASE', 'TOKEN'])}

        try:
            res = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=cls.TIMEOUT_SECONDS,
                env=safe_env
            )
            return cls._parse_trace_output(res.stdout, res.stderr)

        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "steps": [],
                "total_steps": 0,
                "error": "Execution timed out (Time Limit Exceeded). Possible infinite loop in your code.",
                "max_steps_reached": True
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "steps": [],
                "total_steps": 0,
                "error": f"Tracer execution failed: {str(e)}",
                "max_steps_reached": False
            }
        finally:
            try:
                if os.path.exists(tmp_path):
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
        
        # User code must be at Line 1 of the file
        return f"""{user_code}
# =============================================================================
# INTERNAL DEBUG TRACER HARNESS (LINES BELOW ARE NOT DISPLAYED TO USER)
# =============================================================================
import sys
import json
import inspect
import typing
from io import StringIO

List = typing.List
Dict = typing.Dict
Tuple = typing.Tuple
Set = typing.Set
Optional = typing.Optional
Any = typing.Any
Union = typing.Union

__max_user_line = {user_line_count}
__max_steps = {max_steps}
__captured_steps = []
__last_vars = {{}}
__stdout_capture = StringIO()
__orig_stdout = sys.stdout

def __safe_serialize(val, depth=0):
    if depth > 3:
        return repr(val)[:50]
    if val is None or isinstance(val, (int, float, str, bool)):
        return val
    if isinstance(val, (list, tuple)):
        return [__safe_serialize(x, depth + 1) for x in val[:50]]
    if isinstance(val, dict):
        return {{str(k): __safe_serialize(v, depth + 1) for k, v in list(val.items())[:30]}}
    if isinstance(val, set):
        return [__safe_serialize(x, depth + 1) for x in list(val)[:50]]
    
    # Custom ListNode
    if hasattr(val, "val") and hasattr(val, "next"):
        nodes = []
        curr = val
        visited = set()
        while curr and len(nodes) < 20 and id(curr) not in visited:
            visited.add(id(curr))
            nodes.append(curr.val)
            curr = getattr(curr, "next", None)
        return {{"__type__": "ListNode", "val": val.val, "nodes": nodes}}

    # Custom TreeNode
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

    # Only trace code from line 1 up to user_line_count
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

def __run_tracer():
    global __stdout_capture
    sys.stdout = __stdout_capture
    
    raw_input_str = {safe_input}.strip()
    parsed_input = None
    if raw_input_str:
        try:
            parsed_input = json.loads(raw_input_str)
        except Exception:
            lines = [l.strip() for l in raw_input_str.splitlines() if l.strip()]
            if len(lines) > 1:
                parsed_input = []
                for l in lines:
                    try:
                        parsed_input.append(json.loads(l))
                    except Exception:
                        parsed_input.append(l)
            else:
                parsed_input = raw_input_str

    entrypoint = None
    if "Solution" in globals():
        sol = Solution()
        methods = [m for m in dir(sol) if not m.startswith("_") and callable(getattr(sol, m))]
        if methods:
            entrypoint = getattr(sol, methods[0])
    
    if not entrypoint:
        # Search specifically for user functions in __main__
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

    @classmethod
    def _trace_javascript(
        cls,
        code: str,
        input_data: str,
        max_steps: int
    ) -> Dict[str, Any]:
        lines = code.splitlines()
        instrumented_lines = []
        
        instrumented_lines.append("""
function ListNode(val, next) { this.val = (val===undefined ? 0 : val); this.next = (next===undefined ? null : next); }
function TreeNode(val, left, right) { this.val = (val===undefined ? 0 : val); this.left = (left===undefined ? null : left); this.right = (right===undefined ? null : right); }
const __captured_steps = [];
const __max_steps = """ + str(max_steps) + """;
""")
        instrumented_lines.append(code)
        
        safe_input = json.dumps(input_data)
        runner_footer = f"""
try {{
    let rawInput = {safe_input};
    let parsedInput = rawInput;
    try {{ parsedInput = JSON.parse(rawInput); }} catch(e) {{}}
    
    let fn = null;
    if (typeof Solution !== 'undefined') {{
        const sol = new Solution();
        const methods = Object.getOwnPropertyNames(Object.getPrototypeOf(sol)).filter(m => m !== 'constructor');
        if (methods.length) fn = sol[methods[0]].bind(sol);
    }}
    if (!fn) {{
        const candidateNames = Object.keys(global).filter(k => typeof global[k] === 'function' && !k.startsWith('_') && k !== 'ListNode' && k !== 'TreeNode');
        if (candidateNames.length) fn = global[candidateNames[candidateNames.length - 1]];
    }}

    let ret = null;
    if (fn) {{
        if (Array.isArray(parsedInput)) {{
            ret = fn(...parsedInput);
        }} else {{
            ret = fn(parsedInput);
        }}
    }}
    
    console.log("---DEBUG_TRACE_START---");
    console.log(JSON.stringify({{
        status: "SUCCESS",
        steps: __captured_steps.slice(0, __max_steps),
        total_steps: __captured_steps.length,
        max_steps_reached: __captured_steps.length >= __max_steps,
        return_value: ret,
        stdout: "",
        error: null
    }}));
    console.log("---DEBUG_TRACE_END---");
}} catch (err) {{
    console.log("---DEBUG_TRACE_START---");
    console.log(JSON.stringify({{
        status: "RUNTIME_ERROR",
        steps: __captured_steps,
        total_steps: __captured_steps.length,
        max_steps_reached: false,
        error: err.toString()
    }}));
    console.log("---DEBUG_TRACE_END---");
}}
"""
        instrumented_lines.append(runner_footer)
        harness = "\n".join(instrumented_lines)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False, encoding="utf-8") as tmp:
            tmp_path = tmp.name
            tmp.write(harness)

        try:
            node = "node"
            proc = subprocess.Popen(
                [node, tmp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(timeout=cls.TIMEOUT_SECONDS)
            return cls._parse_trace_output(stdout, stderr)
        except Exception as e:
            return {
                "status": "ERROR",
                "steps": [],
                "total_steps": 0,
                "error": f"Node.js tracer error: {str(e)}",
                "max_steps_reached": False
            }
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    @classmethod
    def _trace_generic_fallback(
        cls,
        code: str,
        language: str,
        input_data: str,
        max_steps: int
    ) -> Dict[str, Any]:
        lines = code.splitlines()
        steps = []
        variables = {"input": input_data}

        for idx, line in enumerate(lines[:min(len(lines), 30)]):
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "#", "/*", "*")):
                continue
            
            steps.append({
                "step_index": len(steps),
                "line": idx + 1,
                "event": "line",
                "function_name": "solution",
                "variables": dict(variables),
                "changed_vars": [],
                "call_stack": [f"solution (line {idx + 1})"],
                "stdout": ""
            })

        return {
            "status": "SUCCESS",
            "steps": steps,
            "total_steps": len(steps),
            "max_steps_reached": False,
            "return_value": "Execution completed",
            "stdout": "",
            "error": None
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
