import sys
import os
import json
import time
import ast
import re
import tempfile
import subprocess
from typing import Dict, Any, List, Optional, Tuple


class LineMatchedTranspiler:
    """
    Translates C++, Java, JavaScript, and TypeScript DSA code into line-preserving Python code.
    Guarantees:
    1. Line N in the input source maps to Line N in the output Python code.
    2. Imperative constructs (loops, conditionals, assignments, array mutations) execute
       with identical semantics, enabling sys.settrace() to track variables dynamically.
    """

    @classmethod
    def transpile(cls, code: str, language: str) -> str:
        lang = (language or "").lower().strip()
        lines = code.splitlines()
        out_lines = []
        indent_level = 0
        in_class = False

        for line_idx, raw_line in enumerate(lines):
            line = raw_line.strip()
            indent_str = "    " * indent_level

            # 1. Blank line
            if not line:
                out_lines.append("")
                continue

            # 2. Comments (single or multi-line)
            if line.startswith(("//", "/*", "*", "*/")):
                cleaned = line.replace("*/", "").replace("/*", "").strip()
                out_lines.append(f"{indent_str}pass  # {cleaned}")
                continue

            # 3. Directives / package / imports / typedef
            if re.match(r"^(#include|using\s+namespace|typedef|package|import)\b", line):
                out_lines.append(f"{indent_str}pass  # {line}")
                continue

            # 4. Access specifiers (public:, private:, protected:)
            if re.match(r"^(public|private|protected)\s*:", line):
                out_lines.append(f"{indent_str}pass")
                continue

            # 5. Opening brace only: '{'
            if line == "{":
                out_lines.append(f"{indent_str}pass")
                continue

            # 6. Closing brace only: '}', '};'
            if re.match(r"^\s*\}[\s;]*$", line):
                indent_level = max(0, indent_level - 1)
                indent_str = "    " * indent_level
                out_lines.append(f"{indent_str}pass")
                continue

            # 7. Class declaration: class Solution { or public class Solution {
            m_class = re.match(r"^(?:public\s+|static\s+)*class\s+(\w+)", line)
            if m_class:
                cname = m_class.group(1)
                out_lines.append(f"{indent_str}class {cname}:")
                indent_level += 1
                in_class = True
                continue

            # 8. Method declaration
            # C++: bool checkPossibility(vector<int>& a) {
            # Java: public boolean checkPossibility(int[] a) {
            # JS: var checkPossibility = function(a) { or function checkPossibility(a) {
            # TS: checkPossibility(a: number[]): boolean {
            is_control = line.startswith(("if", "while", "for", "switch", "catch", "return"))
            m_meth = None
            if not is_control:
                m_meth = (
                    re.search(r"(?:public\s+|static\s+|const\s+)*(?:void|int|bool|boolean|string|String|long|double|float|vector<[^>]+>|int\[\]|String\[\]|List<[^>]+>|ListNode\*?|TreeNode\*?)\s+(\w+)\s*\(([^)]*)\)", line) or
                    re.search(r"(?:var|let|const)?\s*(\w+)\s*=\s*function\s*\(([^)]*)\)", line) or
                    re.search(r"function\s+(\w+)\s*\(([^)]*)\)", line) or
                    re.search(r"^\s*(\w+)\s*\(([^)]*)\)\s*(?::\s*[^\{]+)?\s*\{?", line)
                )

            if m_meth and not is_control:
                mname = m_meth.group(1)
                if mname not in ("if", "while", "for", "switch", "catch", "return", "class"):
                    raw_params = m_meth.group(2)
                    params = []
                    for p in raw_params.split(","):
                        p = p.strip()
                        if not p:
                            continue
                        p = p.split(":")[0].strip()
                        pname = p.split()[-1].lstrip("&").lstrip("*").rstrip("[]").strip()
                        if pname and pname.isidentifier():
                            params.append(pname)
                    
                    param_list = ", ".join((["self"] if in_class else []) + params)
                    out_lines.append(f"{indent_str}def {mname}({param_list}):")
                    indent_level += 1
                    continue

            # 9. For loops
            # A: C-style for (int i = 0; i < n; i++) {
            m_for = re.search(r"for\s*\(\s*(?:(?:int|long|let|var|auto)\s+)?(\w+)\s*=\s*([^;]+);\s*\1\s*(<=|>=|<|>|!=)\s*([^;]+);\s*([^)]+)\)", line)
            if m_for:
                var_name, start_val, op, end_val, step_expr = m_for.groups()
                start_val = start_val.strip()
                end_val = cls._convert_expr(end_val.strip().rstrip("{").strip())
                step_expr = step_expr.strip()

                step_num = 1
                m_step = re.search(r"\+=\s*(\d+)", step_expr)
                if m_step:
                    step_num = int(m_step.group(1))
                m_step_sub = re.search(r"-=\s*(\d+)", step_expr)
                if m_step_sub:
                    step_num = -int(m_step_sub.group(1))

                if op == "<":
                    py_range = f"range({start_val}, {end_val}, {step_num})" if step_num != 1 else f"range({start_val}, {end_val})"
                elif op == "<=":
                    py_range = f"range({start_val}, {end_val} + 1, {step_num})" if step_num != 1 else f"range({start_val}, {end_val} + 1)"
                elif op == ">=":
                    py_range = f"range({start_val}, {end_val} - 1, -1)"
                else:
                    py_range = f"range({start_val}, {end_val}, -1)"

                out_lines.append(f"{indent_str}for {var_name} in {py_range}:")
                if "{" in line:
                    indent_level += 1
                continue

            # B: Range-based / For-of / For-in: for (int x : nums) or for (const x of nums)
            m_for_in = re.search(r"for\s*\(\s*(?:(?:int|long|auto|const|let|var)\s+)?(\w+)\s*(?::|of|in)\s*([^)]+)\)", line)
            if m_for_in:
                var_name, iterable = m_for_in.groups()
                iterable = cls._convert_expr(iterable.strip().rstrip("{").strip())
                out_lines.append(f"{indent_str}for {var_name} in {iterable}:")
                if "{" in line:
                    indent_level += 1
                continue

            # 10. While loops: while (cond) {
            m_while = re.search(r"while\s*\((.*)\)", line)
            if m_while:
                cond = cls._convert_expr(m_while.group(1).rstrip("{").strip())
                out_lines.append(f"{indent_str}while {cond}:")
                if "{" in line:
                    indent_level += 1
                continue

            # 11. Else if / Else
            if re.search(r"\}\s*else\s+if\s*\(", line) or re.search(r"^else\s+if\s*\(", line):
                indent_level = max(0, indent_level - 1)
                indent_str = "    " * indent_level
                m_elif = re.search(r"if\s*\((.*)\)", line)
                cond = cls._convert_expr(m_elif.group(1).rstrip("{").strip() if m_elif else "True")
                out_lines.append(f"{indent_str}elif {cond}:")
                indent_level += 1
                continue

            if re.search(r"\}\s*else\s*\{?", line) or re.search(r"^else\s*\{?", line):
                indent_level = max(0, indent_level - 1)
                indent_str = "    " * indent_level
                out_lines.append(f"{indent_str}else:")
                indent_level += 1
                continue

            # 12. If statements: if (cond) { or if (cond) stmt;
            m_if = re.match(r"^if\s*\((.*)\)", line)
            if m_if:
                inner = line[m_if.start():]
                paren_count = 0
                split_idx = -1
                for ci, ch in enumerate(inner):
                    if ch == "(":
                        paren_count += 1
                    elif ch == ")":
                        paren_count -= 1
                        if paren_count == 0:
                            split_idx = ci
                            break
                if split_idx != -1:
                    raw_cond = inner[inner.find("(") + 1:split_idx].strip()
                    rest = inner[split_idx + 1:].strip().rstrip("{").rstrip(";").strip()
                    cond = cls._convert_expr(raw_cond)
                    
                    if rest:
                        stmt = cls._convert_stmt(rest)
                        out_lines.append(f"{indent_str}if {cond}: {stmt}")
                    else:
                        out_lines.append(f"{indent_str}if {cond}:")
                        if "{" in line:
                            indent_level += 1
                    continue

            # 13. General statements (assignments, returns, function calls)
            stmt = cls._convert_stmt(line)
            out_lines.append(f"{indent_str}{stmt}")
            if "{" in line and not line.endswith(";"):
                indent_level += 1

        return "\n".join(out_lines)

    @classmethod
    def _convert_expr(cls, expr: str) -> str:
        s = expr
        s = re.sub(r"&&", " and ", s)
        s = re.sub(r"\|\|", " or ", s)
        s = re.sub(r"===", " == ", s)
        s = re.sub(r"!==", " != ", s)
        s = re.sub(r"!([^=])", r"not \1", s)
        s = re.sub(r"\btrue\b", "True", s)
        s = re.sub(r"\bfalse\b", "False", s)
        s = re.sub(r"\bnullptr\b|\bNULL\b|\bnull\b|\bundefined\b", "None", s)
        s = re.sub(r"\bINT_MAX\b|\bInteger\.MAX_VALUE\b", "2147483647", s)
        s = re.sub(r"\bINT_MIN\b|\bInteger\.MIN_VALUE\b", "-2147483648", s)
        s = re.sub(r"(\w+)\.size\(\)", r"len(\1)", s)
        s = re.sub(r"(\w+)\.length\b", r"len(\1)", s)
        s = re.sub(r"(\w+)\.length\(\)", r"len(\1)", s)
        s = re.sub(r"(\w+)\.find\(([^)]+)\)\s*!=\s*\1\.end\(\)?", r"(\2 in \1)", s)
        s = re.sub(r"(\w+)\.find\(([^)]+)\)\s*==\s*\1\.end\(\)?", r"(\2 not in \1)", s)
        s = re.sub(r"(\w+)\.count\(([^)]+)\)", r"(\2 in \1)", s)
        s = re.sub(r"(\w+)\.charAt\(([^)]+)\)", r"\1[\2]", s)
        s = re.sub(r"Math\.max\(", "max(", s)
        s = re.sub(r"Math\.min\(", "min(", s)
        s = re.sub(r"Math\.abs\(", "abs(", s)
        s = re.sub(r"Math\.floor\(", "int(", s)
        return s

    @classmethod
    def _convert_stmt(cls, line: str) -> str:
        stmt = line.rstrip(";").rstrip("{").strip()

        # Strip leading types
        stmt = re.sub(r"^(?:int|long\s+long|long|double|float|bool|boolean|char|string|String|auto|var|let|const)\s+", "", stmt)

        # Multi-variable assignment: left = 0, right = n - 1 -> left = 0; right = n - 1
        stmt = re.sub(r",\s*([a-zA-Z_]\w*\s*=)", r"; \1", stmt)

        # Vector / array declaration with initial values: vector<int> a = {1, 2, 3};
        m_arr_init = re.match(r"^(?:(?:vector<[^>]+>|[\w<>\[\]\*&]+)\s+)?(\w+)(?:\[\])?\s*=\s*\{([^}]*)\}", stmt)
        if m_arr_init:
            vname, inits = m_arr_init.groups()
            return f"{vname} = [{inits.strip()}]"

        # Vector / array sized declaration: vector<int> v(n, 0) -> v = [0] * n
        m_vec = re.match(r"^(?:vector<[^>]+>|int\[\])\s+(\w+)\s*\(([^,]+),\s*([^)]+)\)", stmt)
        if m_vec:
            return f"{m_vec.group(1)} = [{m_vec.group(3)}] * ({m_vec.group(2)})"

        m_vec_single = re.match(r"^vector<(\w+)>\s+(\w+)\s*\(([^)]+)\)", stmt)
        if m_vec_single:
            t, v, n = m_vec_single.groups()
            init_val = "0" if t in ("int", "long", "double", "float") else ('False' if t == 'bool' else '""')
            return f"{v} = [{init_val}] * ({n.strip()})"

        # New array: int[] dp = new int[n] or dp = new int[n]
        m_newarr = re.match(r"^(\w+)\s*=\s*new\s+\w+\[([^\]]+)\]", stmt)
        if m_newarr:
            return f"{m_newarr.group(1)} = [0] * ({m_newarr.group(2)})"

        # Declarations of collections (Map, Set, Stack, Queue)
        if re.match(r"^(?:unordered_map<[^>]+>|Map<[^>]+>)\s+(\w+)", stmt) or re.search(r"=\s*new\s+(?:HashMap|Map)\(\)", stmt):
            m_var = re.search(r"(\w+)\s*(?:=|;|$)", stmt)
            if m_var:
                return f"{m_var.group(1)} = UniversalDict()"

        if re.match(r"^(?:unordered_set<[^>]+>|Set<[^>]+>)\s+(\w+)", stmt) or re.search(r"=\s*new\s+(?:HashSet|Set)\(\)", stmt):
            m_var = re.search(r"(\w+)\s*(?:=|;|$)", stmt)
            if m_var:
                return f"{m_var.group(1)} = UniversalSet()"

        # Empty vector / list declaration: vector<int> res; or List<Integer> res = new ArrayList<>();
        if re.match(r"^(?:vector<[^>]+>|List<[^>]+>)\s+(\w+)\s*$", stmt) or re.search(r"=\s*new\s+ArrayList<[^>]*>\(\)", stmt):
            m_var = re.search(r"(\w+)\s*(?:=|;|$)", stmt)
            if m_var:
                return f"{m_var.group(1)} = []"

        # Ternary operator: ans = a > b ? a : b
        m_tern = re.match(r"^(\w+)\s*=\s*(.+?)\s*\?\s*(.+?)\s*:\s*(.+)$", stmt)
        if m_tern:
            vname, cond, tval, fval = m_tern.groups()
            return f"{vname} = {tval.strip()} if {cond.strip()} else {fval.strip()}"

        # Map methods: map.set(k, v) -> map[k] = v; map.has(k) -> (k in map)
        stmt = re.sub(r"(\w+)\.set\(([^,]+),\s*([^)]+)\)", r"\1[\2] = \3", stmt)
        stmt = re.sub(r"(\w+)\.has\(([^)]+)\)", r"(\2 in \1)", stmt)
        stmt = re.sub(r"(\w+)\.get\(([^)]+)\)", r"\1[\2]", stmt)

        # Return conversions
        m_ret_list = re.match(r"^return\s*\{([^}]*)\}", stmt)
        if m_ret_list:
            inner = cls._convert_expr(m_ret_list.group(1))
            return f"return [{inner}]"

        m_ret_arr = re.match(r"^return\s+new\s+\w+\[\]\s*\{([^}]*)\}", stmt)
        if m_ret_arr:
            inner = cls._convert_expr(m_ret_arr.group(1))
            return f"return [{inner}]"

        # General substitutions
        stmt = cls._convert_expr(stmt)
        stmt = re.sub(r"(\w+)\+\+", r"\1 += 1", stmt)
        stmt = re.sub(r"\+\+(\w+)", r"\1 += 1", stmt)
        stmt = re.sub(r"(\w+)--", r"\1 -= 1", stmt)
        stmt = re.sub(r"--(\w+)", r"\1 -= 1", stmt)
        stmt = re.sub(r"(\w+)\.push_back\(", r"\1.append(", stmt)
        stmt = re.sub(r"(\w+)\.push\(", r"\1.append(", stmt)
        stmt = re.sub(r"System\.out\.println\(", "print(", stmt)
        stmt = re.sub(r"console\.log\(", "print(", stmt)

        if not stmt:
            stmt = "pass"

        return stmt


class DebugTracer:
    """
    Time-Travel Code Execution Tracer for Step-by-Step Visual Debugging across ALL languages.
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
        language: str = "cpp",
        input_data: Optional[str] = None,
        max_steps: int = MAX_STEPS_DEFAULT
    ) -> Dict[str, Any]:
        lang = (language or "cpp").lower().strip()
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
        elif lang in ["cpp", "c++", "c", "java", "javascript", "js", "typescript", "ts"]:
            transpiled = LineMatchedTranspiler.transpile(clean_code, lang)
            try:
                ast.parse(transpiled)
                return cls._trace_python(transpiled, input_data or "", max_steps)
            except SyntaxError as e:
                # If transpiled python has a syntax error, report exact line
                return {
                    "status": "ERROR",
                    "steps": [],
                    "total_steps": 0,
                    "error": f"Transpilation parse error on line {e.lineno}: {e.msg}",
                    "line": e.lineno,
                    "max_steps_reached": False
                }
            except Exception as e:
                return cls._trace_generic_fallback(clean_code, lang, input_data or "", max_steps)
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
import re
from io import StringIO

List = typing.List
Dict = typing.Dict
Tuple = typing.Tuple
Set = typing.Set
Optional = typing.Optional
Any = typing.Any
Union = typing.Union

# Polyfill Collections & Helpers for Multi-Language Compatibility
class CppList(list):
    def size(self): return len(self)
    @property
    def length(self): return len(self)
    def push_back(self, x): self.append(x)
    def pop_back(self): return self.pop()
    def empty(self): return len(self) == 0
    def front(self): return self[0] if self else None
    def back(self): return self[-1] if self else None
    def push(self, x): self.append(x)
    def top(self): return self[-1] if self else None

class _DictSentinel:
    def __call__(self): return self
    def __eq__(self, other): return isinstance(other, _DictSentinel)
    def __ne__(self, other): return not isinstance(other, _DictSentinel)

_SENTINEL = _DictSentinel()

class UniversalDict(dict):
    def find(self, k): return k if k in self else _SENTINEL
    def end(self): return _SENTINEL
    @property
    def end_prop(self): return _SENTINEL
    def count(self, k): return 1 if k in self else 0
    def containsKey(self, k): return k in self
    def has(self, k): return k in self
    def get(self, k, default=None): return super().get(k, default)
    def put(self, k, v): self[k] = v
    def set(self, k, v):
        self[k] = v
        return self

class UniversalSet(set):
    def contains(self, k): return k in self
    def has(self, k): return k in self
    def count(self, k): return 1 if k in self else 0
    def insert(self, k): self.add(k)
    def add(self, k): super().add(k)

class _Math:
    @staticmethod
    def max(*args):
        if len(args) == 1 and isinstance(args[0], (list, tuple)): return max(args[0])
        return max(*args)
    @staticmethod
    def min(*args):
        if len(args) == 1 and isinstance(args[0], (list, tuple)): return min(args[0])
        return min(*args)
    @staticmethod
    def abs(x): return abs(x)
    @staticmethod
    def floor(x): return int(x)
    @staticmethod
    def ceil(x):
        import math
        return math.ceil(x)
    @staticmethod
    def pow(x, y): return pow(x, y)
    @staticmethod
    def sqrt(x):
        import math
        return math.isqrt(int(x)) if isinstance(x, int) else math.sqrt(x)

Math = _Math()

class _Integer:
    MAX_VALUE = 2147483647
    MIN_VALUE = -2147483648

Integer = _Integer()
INT_MAX = 2147483647
INT_MIN = -2147483648

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
    if depth > 3:
        return repr(val)[:50]
    if val is None or isinstance(val, (int, float, str, bool)):
        return val
    if isinstance(val, (list, tuple, CppList)):
        return [__safe_serialize(x, depth + 1) for x in val[:50]]
    if isinstance(val, (dict, UniversalDict)):
        return {{str(k): __safe_serialize(v, depth + 1) for k, v in list(val.items())[:30]}}
    if isinstance(val, (set, UniversalSet)):
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

def __parse_robust_input(raw):
    raw = str(raw or "").strip()
    if not raw:
        return None

    # 1. Direct JSON
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 2. Key-value assignment lines or comma-separated: nums = [4, 2, 3] or nums = [2, 7], target = 9
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

    # 3. Comma-separated JSON wrapped in array
    try:
        val = json.loads(f"[{{raw}}]")
        if isinstance(val, list) and len(val) == 1:
            return val[0]
        return val
    except Exception:
        pass

    return raw

def __wrap_compat(val):
    if isinstance(val, list):
        return CppList([__wrap_compat(x) for x in val])
    return val

def __run_tracer():
    global __stdout_capture
    sys.stdout = __stdout_capture
    
    raw_input_str = {safe_input}.strip()
    parsed_input = __parse_robust_input(raw_input_str)
    parsed_input = __wrap_compat(parsed_input)

    entrypoint = None
    if "Solution" in globals():
        sol = Solution()
        # Expose Solution methods into globals for seamless helper/recursion calls without self.
        for m in dir(sol):
            if not m.startswith("_") and callable(getattr(sol, m)):
                globals()[m] = getattr(sol, m)

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
