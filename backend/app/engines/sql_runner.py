import re
import json
import time
import math
from typing import List, Dict, Any, Tuple, Optional

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

try:
    import sqlglot
    HAS_SQLGLOT = True
except ImportError:
    HAS_SQLGLOT = False

import sqlite3

class SQLRunner:
    """
    Dedicated Relational SQL Compiler and Judge Engine for technical interviews.
    Powered by DuckDB in-memory engine with SQLGlot dialect transpilation (MySQL, PostgreSQL, T-SQL / SQL Server)
    and robust relational output verification.
    """

    @staticmethod
    def clean_query(sql: str) -> str:
        """Strip SQL comments and trailing semicolons."""
        clean = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
        clean = re.sub(r'#.*?$', '', clean, flags=re.MULTILINE)
        clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)
        return clean.strip().rstrip(';').strip()

    @classmethod
    def transpile_to_duckdb(cls, sql: str) -> str:
        """Transpile MySQL, Postgres, and T-SQL (SQL Server) syntax to DuckDB."""
        clean = cls.clean_query(sql)
        if not HAS_SQLGLOT:
            return clean
        for dialect in ["mysql", "postgres", "tsql"]:
            try:
                transpiled = sqlglot.transpile(clean, read=dialect, write="duckdb")[0]
                return transpiled
            except Exception:
                continue
        return clean

    @classmethod
    def parse_fixtures(cls, raw_input: str) -> Dict[str, Dict[str, Any]]:
        """
        Parses test fixtures from both JSON schema format and raw ASCII table format.
        Returns: {table_name: {"cols": [...], "rows": [...]}}
        """
        tables = {}
        if not raw_input or not isinstance(raw_input, str):
            return tables

        clean = raw_input.strip()
        # 1. Try JSON schema format
        if clean.startswith("{"):
            try:
                data = json.loads(clean)
                if isinstance(data, dict) and "headers" in data and "rows" in data:
                    for tbl, cols in data["headers"].items():
                        tables[tbl] = {
                            "cols": cols,
                            "rows": data["rows"].get(tbl, [])
                        }
                    return tables
            except Exception:
                pass

        # 2. Parse ASCII markdown tables (e.g. "Person table:\n+---+..." or "Table: Person\n...")
        lines = clean.splitlines()
        current_table = None
        table_lines = []

        def flush_table(tbl_name, tlines):
            if not tbl_name or not tlines:
                return
            data_lines = [l.strip() for l in tlines if l.strip().startswith("|") and l.strip().endswith("|")]
            if not data_lines:
                return
            cols = [c.strip() for c in data_lines[0][1:-1].split("|")]
            rows = []
            for dl in data_lines[1:]:
                cells = [c.strip() for c in dl[1:-1].split("|")]
                row_vals = []
                for cell in cells:
                    if cell.lower() in ("null", "none"):
                        row_vals.append(None)
                    else:
                        try:
                            f = float(cell)
                            row_vals.append(int(f) if f.is_integer() else f)
                        except ValueError:
                            row_vals.append(cell)
                rows.append(row_vals)
            tables[tbl_name] = {"cols": cols, "rows": rows}

        for line in lines:
            sline = line.strip()
            # Match table labels: "Person table:", "Table: Person", "Person:"
            m = re.match(r'^(?:Table\s*[:]?\s*)?([A-Za-z0-9_]+)(?:\s*table)?\s*:$', sline, re.IGNORECASE)
            if m:
                if current_table and table_lines:
                    flush_table(current_table, table_lines)
                current_table = m.group(1)
                table_lines = []
            elif sline.startswith("+") or sline.startswith("|"):
                table_lines.append(sline)

        if current_table and table_lines:
            flush_table(current_table, table_lines)

        return tables

    @staticmethod
    def parse_ascii_table(table_str: str) -> Tuple[List[str], List[List[str]]]:
        """Parse ASCII markdown table into headers and cell rows."""
        if not table_str or not isinstance(table_str, str):
            return [], []
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

    @staticmethod
    def format_ascii_table(headers: List[str], rows: List[Tuple]) -> str:
        """Format column headers and rows into clean ASCII markdown table."""
        if not headers and not rows:
            return "Empty Set"
        cols = headers if headers else [f"col_{i}" for i in range(len(rows[0])) if rows]
        str_rows = []
        for r in rows:
            row_vals = []
            for c in r:
                if c is None:
                    row_vals.append("null")
                elif isinstance(c, float) and c.is_integer():
                    row_vals.append(str(int(c)))
                else:
                    row_vals.append(str(c))
            str_rows.append(row_vals)

        col_widths = [len(str(c)) for c in cols]
        for r in str_rows:
            for i, val in enumerate(r):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(val))
                else:
                    col_widths.append(len(val))

        sep = "+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+"
        hdr_line = "|" + "|".join([f" {str(c).ljust(w)} " for c, w in zip(cols, col_widths)]) + "|"
        res = [sep, hdr_line, sep]
        for r in str_rows:
            res.append("|" + "|".join([f" {val.ljust(w)} " for val, w in zip(r, col_widths)]) + "|")
        res.append(sep)
        return "\n".join(res)

    @classmethod
    def normalize_cell_value(cls, val: Any) -> Any:
        """Normalize cell values across SQL types (nulls, floats, ints, dates)."""
        if val is None:
            return None
        s = str(val).strip()
        if s.lower() in ("null", "none"):
            return None
        try:
            f = float(s)
            if math.isnan(f):
                return None
            return round(f, 4)
        except (ValueError, TypeError):
            pass
        return s

    @classmethod
    def compare_cells(cls, act: Any, exp: Any) -> bool:
        """
        Compare two cells:
        - NULLs normalized identically.
        - Floats compared within 1e-3 tolerance.
        - Strings compared with STRICT CASE SENSITIVITY ('Allen' != 'ALLEN').
        """
        n_act = cls.normalize_cell_value(act)
        n_exp = cls.normalize_cell_value(exp)
        if n_act is None and n_exp is None:
            return True
        if n_act is None or n_exp is None:
            return False
        if isinstance(n_act, (int, float)) and isinstance(n_exp, (int, float)):
            return abs(n_act - n_exp) < 1e-3
        # Strict string equality (preserves case!)
        return str(n_act).strip() == str(n_exp).strip()

    @staticmethod
    def _is_reverse_sorted(exp_rows: List[Tuple], actual_rows: List[Tuple]) -> bool:
        """Detect if actual rows are sorted in opposite direction of a monotonically sorted numeric column."""
        if len(exp_rows) <= 1 or len(actual_rows) != len(exp_rows):
            return False
        for col_idx in range(len(exp_rows[0])):
            vals_exp = [r[col_idx] for r in exp_rows if isinstance(r[col_idx], (int, float))]
            vals_act = [r[col_idx] for r in actual_rows if isinstance(r[col_idx], (int, float))]
            if len(vals_exp) == len(exp_rows) and len(vals_act) == len(actual_rows):
                exp_desc = all(vals_exp[i] >= vals_exp[i+1] for i in range(len(vals_exp)-1)) and vals_exp[0] > vals_exp[-1]
                act_asc = all(vals_act[i] <= vals_act[i+1] for i in range(len(vals_act)-1)) and vals_act[0] < vals_act[-1]
                if exp_desc and act_asc:
                    return True
                exp_asc = all(vals_exp[i] <= vals_exp[i+1] for i in range(len(vals_exp)-1)) and vals_exp[0] < vals_exp[-1]
                act_desc = all(vals_act[i] >= vals_act[i+1] for i in range(len(vals_act)-1)) and vals_act[0] > vals_act[-1]
                if exp_asc and act_desc:
                    return True
        return False

    @classmethod
    def compare_results(cls, actual_cols: List[str], actual_rows: List[Tuple],
                        expected_ascii: str, query_has_order: bool = False,
                        is_ordered: Optional[bool] = None) -> Tuple[bool, str]:
        """
        Verify candidate query results against expected testcase ASCII table.
        - Column headers matched case-insensitively.
        - Cell values matched strictly.
        - If problem requires ordering (is_ordered=True), strict positional order is enforced.
        - If problem allows results in any order (is_ordered=False), multiset match is accepted.
        """
        exp_cols, exp_rows = cls.parse_ascii_table(expected_ascii)
        if not exp_cols and not exp_rows:
            if not actual_rows:
                return True, ""
            return False, f"Expected empty result, got {len(actual_rows)} rows" 

        # 1. Header count and names comparison (case-insensitive for column names)
        if len(actual_cols) != len(exp_cols):
            return False, f"Column count mismatch: expected {len(exp_cols)} ({exp_cols}), got {len(actual_cols)} ({actual_cols})"

        for ac, ec in zip(actual_cols, exp_cols):
            if ac.strip().lower() != ec.strip().lower():
                return False, f"Column name mismatch: expected '{ec}', got '{ac}'"

        # 2. Row count
        if len(actual_rows) != len(exp_rows):
            return False, f"Row count mismatch: expected {len(exp_rows)} rows, got {len(actual_rows)} rows"

        # 3. Positional exact comparison
        exact_match = True
        for ar, er in zip(actual_rows, exp_rows):
            if not all(cls.compare_cells(ac, ec) for ac, ec in zip(ar, er)):
                exact_match = False
                break
        if exact_match:
            return True, ""

        # 4. Check if problem strictly mandates ordering
        if is_ordered is True:
            return False, "Order mismatch: Result rows do not match required sort order."

        # 5. Multiset order-independent comparison
        matched_indices = set()
        for ar in actual_rows:
            found = False
            for e_idx, er in enumerate(exp_rows):
                if e_idx in matched_indices:
                    continue
                if all(cls.compare_cells(ac, ec) for ac, ec in zip(ar, er)):
                    matched_indices.add(e_idx)
                    found = True
                    break
            if not found:
                return False, f"Row mismatch: could not find matching row for {ar}"

        # 6. If multiset matched, check if query explicitly reversed a monotonic expected order
        if is_ordered is None and query_has_order and cls._is_reverse_sorted(exp_rows, actual_rows):
            return False, "Order mismatch: Result rows do not match required sort order."

        return True, ""

    @classmethod
    def evaluate(cls, user_code: str, test_cases: List[Dict[str, Any]], timeout: float = 4.0, is_ordered: Optional[bool] = None) -> Dict[str, Any]:
        """
        Executes candidate SQL query against testcases in an isolated in-memory engine.
        Returns LeetCode-compatible telemetry, status (ACCEPTED/WRONG_ANSWER), and output tables.
        """
        start_all = time.perf_counter()
        clean_user_sql = cls.clean_query(user_code)

        if not clean_user_sql:
            return {
                "status": "WRONG_ANSWER",
                "is_correct": False,
                "score_fraction": 0.0,
                "feedback": "Empty SQL query submitted.",
                "compiler_output": "Empty SQL query submitted.",
                "error": "Empty SQL query submitted.",
                "runtime_ms": 0.1,
                "memory_mb": None,
                "test_case_results": []
            }

        transpiled_sql = cls.transpile_to_duckdb(clean_user_sql)
        query_has_order = bool(re.search(r'\border\s+by\b', clean_user_sql, re.IGNORECASE))
        is_dml = bool(re.match(r'^(?:delete|update|insert)\b', clean_user_sql, re.IGNORECASE))

        results = []
        all_passed = True
        total_time_ms = 0.0

        for idx, tc in enumerate(test_cases):
            tc_start = time.perf_counter()
            raw_input = tc.get("input", "")
            raw_expected = tc.get("expected_output") or tc.get("expectedOutput") or ""

            # Spin up isolated in-memory DuckDB connection
            if HAS_DUCKDB:
                conn = duckdb.connect(":memory:")
            else:
                conn = sqlite3.connect(":memory:")

            try:
                # 1. Setup tables and load fixture rows from JSON or ASCII
                fixtures = cls.parse_fixtures(raw_input)
                first_table_name = None
                for tbl, data in fixtures.items():
                    if not first_table_name:
                        first_table_name = tbl
                    cols = data["cols"]
                    rows = data["rows"]
                    if rows and HAS_DUCKDB:
                        types = []
                        for col_idx in range(len(cols)):
                            sample_val = None
                            for r in rows:
                                if col_idx < len(r) and r[col_idx] is not None:
                                    sample_val = r[col_idx]
                                    break
                            if isinstance(sample_val, int):
                                types.append("BIGINT")
                            elif isinstance(sample_val, float):
                                types.append("DOUBLE")
                            elif isinstance(sample_val, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', sample_val):
                                types.append("DATE")
                            else:
                                types.append("VARCHAR")
                        col_defs = ", ".join([f'"{col}" {t}' for col, t in zip(cols, types)])
                    else:
                        col_defs = ", ".join([f'"{col}" VARCHAR' for col in cols])

                    conn.execute(f'CREATE TABLE "{tbl}" ({col_defs});')
                    if rows:
                        placeholders = ", ".join(["?"] * len(cols))
                        conn.executemany(f'INSERT INTO "{tbl}" VALUES ({placeholders});', rows)

                # 2. Execute candidate query
                try:
                    rel = conn.execute(transpiled_sql)
                except Exception:
                    rel = conn.execute(clean_user_sql)

                # 3. Handle DML (DELETE / UPDATE): verify remaining table state
                if is_dml:
                    target_table = first_table_name or "Person"
                    m_del = re.search(r'\b(?:from|update)\s+([A-Za-z0-9_]+)', clean_user_sql, re.IGNORECASE)
                    if m_del and m_del.group(1) in fixtures:
                        target_table = m_del.group(1)
                    rel = conn.execute(f'SELECT * FROM "{target_table}"')

                actual_rows = rel.fetchall()
                actual_cols = [desc[0] for desc in rel.description] if rel.description else []
                actual_table_str = cls.format_ascii_table(actual_cols, actual_rows)

                # 4. Compare with expected output
                case_is_ordered = tc.get("is_ordered", tc.get("ordered", is_ordered))
                passed, reason = cls.compare_results(actual_cols, actual_rows, raw_expected, query_has_order=query_has_order, is_ordered=case_is_ordered)
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
                    "error": reason if not passed else None,
                    "runtime_ms": max(0.1, tc_elapsed)
                })

            except Exception as query_err:
                all_passed = False
                tc_elapsed = round((time.perf_counter() - tc_start) * 1000, 2)
                total_time_ms += tc_elapsed
                clean_err_msg = str(query_err).splitlines()[0] if str(query_err) else "SQL Execution Error"
                results.append({
                    "test_case_index": idx + 1,
                    "input_data": raw_input,
                    "expected_output": raw_expected,
                    "actual_output": f"SQL Error: {clean_err_msg}",
                    "passed": False,
                    "error": clean_err_msg,
                    "runtime_ms": max(0.1, tc_elapsed)
                })
            finally:
                conn.close()

        passed_count = sum(1 for r in results if r["passed"])
        score_frac = round(passed_count / len(results), 4) if results else 0.0
        status = "ACCEPTED" if all_passed else "WRONG_ANSWER"

        return {
            "status": status,
            "is_correct": all_passed,
            "score_fraction": score_frac,
            "test_cases_passed": passed_count,
            "total_test_cases": len(results),
            "feedback": f"{passed_count}/{len(results)} test cases passed." if results else "No tests executed.",
            "compiler_output": "Execution completed successfully." if all_passed else (results[0].get("error") if results else "Execution failed."),
            "error": None if all_passed else (results[0].get("error") if results else "Execution failed."),
            "runtime_ms": max(0.1, round(total_time_ms, 2)),
            "memory_mb": 12.5,
            "test_case_results": results
        }
