# -*- coding: utf-8 -*-
"""
Database Fixture Normalizer and Typed DataFrame Comparator for Intervyn.

Supports:
1. Canonical structured JSON: {"headers": {"Person": [...]}, "rows": {"Person": [...]}}
2. JSON-encoded strings of the above.
3. Legacy named ASCII table formats: "Person table:\n+---+...\nAddress table:\n+---+..."
4. Scalar parameter extraction (e.g. "argument": 2, "n = 2").
5. Case-sensitive typed DataFrame comparison with problem-level ordering contracts.
6. Genuine ASCII DataFrame serialization without index or expected output masking.
"""

import re
import json
import math
from typing import Dict, List, Any, Optional, Tuple

try:
    import pandas as pd
    import numpy as np
except ImportError:
    pd = None
    np = None


class FixtureError(Exception):
    """Raised when a test fixture is malformed, ambiguous, or missing required tables."""
    pass


def parse_single_ascii_table(block: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single ASCII table block bounded by +---+ lines.
    Returns {"columns": [...], "rows": [...]} or None if invalid.
    """
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    border_indices = [
        idx for idx, l in enumerate(lines)
        if l.startswith("+") and l.endswith("+") and "-" in l
    ]
    if len(border_indices) < 2:
        return None

    header_idx = border_indices[0] + 1
    if header_idx >= border_indices[1]:
        return None

    header_line = lines[header_idx]
    if not (header_line.startswith("|") and header_line.endswith("|")):
        return None

    columns = [c.strip() for c in header_line.split("|")[1:-1]]
    if not columns:
        return None

    rows = []
    data_start = border_indices[1] + 1
    data_end = border_indices[2] if len(border_indices) >= 3 else len(lines)

    for row_idx in range(data_start, data_end):
        line = lines[row_idx]
        if line.startswith("+") and line.endswith("+"):
            break
        if line.startswith("|") and line.endswith("|"):
            raw_cells = [c.strip() for c in line.split("|")[1:-1]]
            # Ensure cell count matches column count
            if len(raw_cells) != len(columns):
                continue
            typed_cells = []
            for c in raw_cells:
                c_lower = c.lower()
                if c_lower in ("null", "none"):
                    typed_cells.append(None)
                else:
                    # Attempt numeric parse
                    try:
                        if "." in c:
                            typed_cells.append(float(c))
                        else:
                            typed_cells.append(int(c))
                    except ValueError:
                        typed_cells.append(c)
            rows.append(typed_cells)

    return {"columns": columns, "rows": rows}


def normalize_database_fixture(raw_input: Any) -> Dict[str, Any]:
    """
    Normalizes any database fixture (JSON dict, JSON string, or ASCII table string)
    into a canonical dictionary contract:
    {
        "tables": {
            "table_name": {
                "columns": ["col1", "col2"],
                "rows": [[val1, val2], ...]
            }
        },
        "scalars": {
            "n": 2, ...
        }
    }
    """
    if raw_input is None:
        raise FixtureError("Test case input is empty or None.")

    data = raw_input
    if isinstance(data, str):
        data_str = data.strip()
        # 1. Try parsing as JSON first
        if data_str.startswith("{") and data_str.endswith("}"):
            try:
                data = json.loads(data_str)
            except Exception:
                data = data_str

    # Case A: Structured JSON format
    if isinstance(data, dict):
        headers_dict = data.get("headers")
        rows_dict = data.get("rows")
        if not isinstance(headers_dict, dict) or not isinstance(rows_dict, dict):
            raise FixtureError("Structured JSON fixture must contain 'headers' and 'rows' dictionaries.")

        tables = {}
        for tbl_name, cols in headers_dict.items():
            if not isinstance(cols, list):
                raise FixtureError(f"Table '{tbl_name}' columns must be a list.")
            tbl_rows = rows_dict.get(tbl_name, [])
            if not isinstance(tbl_rows, list):
                raise FixtureError(f"Table '{tbl_name}' rows must be a list.")
            tables[tbl_name.lower()] = {
                "name": tbl_name,
                "columns": list(cols),
                "rows": list(tbl_rows)
            }

        scalars = {}
        for k, v in data.items():
            if k not in ("headers", "rows"):
                scalars[k.lower()] = v
                if k.lower() == "argument":
                    scalars["n"] = v

        return {"tables": tables, "scalars": scalars}

    # Case B: Legacy Named ASCII table format
    if isinstance(data, str):
        tables = {}
        scalars = {}

        # Extract scalar assignments like "n = 2"
        scalar_matches = re.findall(
            r'(?i)^\s*([a-zA-Z_]\w*)\s*=\s*(-?\d+(?:\.\d+)?)\s*$',
            data,
            flags=re.MULTILINE
        )
        for var_name, var_val in scalar_matches:
            try:
                scalars[var_name.lower()] = int(var_val) if '.' not in var_val else float(var_val)
            except ValueError:
                scalars[var_name.lower()] = var_val

        # Extract named tables e.g. "Person table:\n+---...+"
        table_splits = re.split(r'(?i)(?:^|\n)\s*([a-zA-Z0-9_]+)\s+table:\s*', data)
        if len(table_splits) > 1:
            for i in range(1, len(table_splits), 2):
                tbl_name = table_splits[i].strip()
                block = table_splits[i + 1]
                t_data = parse_single_ascii_table(block)
                if t_data is not None:
                    tables[tbl_name.lower()] = {
                        "name": tbl_name,
                        "columns": t_data["columns"],
                        "rows": t_data["rows"]
                    }
        else:
            # Try single unnamed table
            t_data = parse_single_ascii_table(data)
            if t_data is not None:
                tables["default"] = {
                    "name": "default",
                    "columns": t_data["columns"],
                    "rows": t_data["rows"]
                }

        if not tables and not scalars:
            raise FixtureError(f"Unable to parse database fixture from string: {data[:200]}")

        return {"tables": tables, "scalars": scalars}

    raise FixtureError(f"Unsupported fixture type: {type(data).__name__}")


def bind_pandas_arguments(
    param_names: List[str],
    fixture_contract: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Binds DataFrames and scalars to entrypoint function parameters.
    Validates missing tables and avoids ambiguous or fuzzy mappings.
    """
    if pd is None:
        raise RuntimeError("pandas is not installed in the environment.")

    tables = fixture_contract.get("tables", {})
    scalars = fixture_contract.get("scalars", {})
    kwargs = {}

    for p_name in param_names:
        p_lower = p_name.lower()
        matched_tbl = None

        # 1. Exact match
        if p_lower in tables:
            matched_tbl = tables[p_lower]
        # 2. Singular/Plural match (e.g. param 'person' vs table 'persons', 'employee' vs 'employees')
        elif p_lower + "s" in tables:
            matched_tbl = tables[p_lower + "s"]
        elif p_lower.endswith("s") and p_lower[:-1] in tables:
            matched_tbl = tables[p_lower[:-1]]
        elif p_lower.endswith("es") and p_lower[:-2] in tables:
            matched_tbl = tables[p_lower[:-2]]

        if matched_tbl is not None:
            cols = matched_tbl["columns"]
            rows = matched_tbl["rows"]
            kwargs[p_name] = pd.DataFrame(rows, columns=cols)
            continue

        # 3. Check scalars (e.g. n or N)
        if p_lower in scalars:
            kwargs[p_name] = scalars[p_lower]
            continue
        if "argument" in scalars and p_lower in ("n", "arg", "k", "limit"):
            kwargs[p_name] = scalars["argument"]
            continue

        # 4. Single-table function fallback
        if len(param_names) == 1 and len(tables) == 1:
            only_tbl = next(iter(tables.values()))
            kwargs[p_name] = pd.DataFrame(only_tbl["rows"], columns=only_tbl["columns"])
            continue

        raise FixtureError(
            f"Cannot bind required parameter '{p_name}'. Available tables: {list(tables.keys())}, scalars: {list(scalars.keys())}"
        )

    return kwargs


def df_to_ascii_table(df: Any) -> str:
    """
    Renders a pandas DataFrame as a standard LeetCode ASCII table without DataFrame index.
    Preserves genuine values, casing, column names, and row order.
    Null values (None, NaN, pd.NA) are rendered as 'null'.
    """
    if pd is None or not isinstance(df, pd.DataFrame):
        return str(df)

    cols = [str(c) for c in df.columns]
    if not cols:
        return "+---+\n|   |\n+---+"

    rows = []
    for _, r in df.iterrows():
        row_vals = []
        for c in df.columns:
            val = r[c]
            if val is None:
                row_vals.append("null")
            elif pd.isna(val):
                row_vals.append("null")
            else:
                row_vals.append(str(val))
        rows.append(row_vals)

    # Compute column widths
    widths = []
    for i, col in enumerate(cols):
        cell_max = max((len(r[i]) for r in rows), default=0)
        widths.append(max(len(col), cell_max))

    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header = "| " + " | ".join(col.ljust(widths[i]) for i, col in enumerate(cols)) + " |"

    lines = [border, header, border]
    for row in rows:
        row_line = "| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " |"
        lines.append(row_line)
    lines.append(border)

    return "\n".join(lines)


def parse_expected_ascii_or_json(exp_input: Any) -> Tuple[List[str], List[List[Any]]]:
    """
    Parses expected output table from ASCII string or JSON.
    Returns: (columns, rows)
    """
    if isinstance(exp_input, dict) and "headers" in exp_input and "values" in exp_input:
        return exp_input["headers"], exp_input["values"]

    exp_str = str(exp_input or "").strip()
    if exp_str.startswith("{") and exp_str.endswith("}"):
        try:
            parsed = json.loads(exp_str)
            if isinstance(parsed, dict) and "headers" in parsed:
                return parsed["headers"], parsed.get("values", parsed.get("rows", []))
        except Exception:
            pass

    # Parse ASCII table lines
    lines = [l.strip() for l in exp_str.splitlines() if l.strip() and not l.startswith("+") and "|" in l]
    if not lines:
        return [], []

    header = [c.strip() for c in lines[0].split("|")[1:-1]]
    rows = []
    for line in lines[1:]:
        raw_cells = [c.strip() for c in line.split("|")[1:-1]]
        typed_cells = []
        for c in raw_cells:
            c_lower = c.lower()
            if c_lower in ("null", "none"):
                typed_cells.append(None)
            else:
                try:
                    if "." in c:
                        typed_cells.append(float(c))
                    else:
                        typed_cells.append(int(c))
                except ValueError:
                    typed_cells.append(c)
        rows.append(typed_cells)

    return header, rows


def _is_null_val(val: Any) -> bool:
    if val is None:
        return True
    if pd is not None and pd.isna(val):
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    return False


def _cell_equal(act: Any, exp: Any) -> bool:
    act_null = _is_null_val(act)
    exp_null = _is_null_val(exp)

    if act_null and exp_null:
        return True
    if act_null != exp_null:
        return False

    # Check numeric comparison with tolerance
    if isinstance(act, (int, float)) and isinstance(exp, (int, float)):
        if isinstance(act, float) or isinstance(exp, float):
            return abs(float(act) - float(exp)) < 1e-3
        return int(act) == int(exp)

    # If types differ numeric vs str
    if isinstance(act, (int, float)) and isinstance(exp, str):
        try:
            exp_num = float(exp) if "." in exp else int(exp)
            if isinstance(act, float) or isinstance(exp_num, float):
                return abs(float(act) - float(exp_num)) < 1e-3
            return int(act) == int(exp_num)
        except ValueError:
            pass
    elif isinstance(act, str) and isinstance(exp, (int, float)):
        try:
            act_num = float(act) if "." in act else int(act)
            if isinstance(exp, float) or isinstance(act_num, float):
                return abs(float(act_num) - float(exp)) < 1e-3
            return int(act_num) == int(exp)
        except ValueError:
            pass

    # Strict case-sensitive string comparison
    return str(act) == str(exp)


def _row_equal(act_row: List[Any], exp_row: List[Any]) -> bool:
    if len(act_row) != len(exp_row):
        return False
    return all(_cell_equal(a, e) for a, e in zip(act_row, exp_row))


def compare_pandas_results(
    actual_result: Any,
    expected_output_raw: Any,
    is_ordered: Optional[bool] = None
) -> Tuple[bool, str, str]:
    """
    Compares candidate's returned object against expected output.
    Returns: (passed: bool, reason: str, actual_ascii_output: str)
    """
    if pd is None:
        return False, "pandas is not installed in the environment.", str(actual_result)

    if not isinstance(actual_result, pd.DataFrame):
        type_name = type(actual_result).__name__
        return False, f"Expected pandas.DataFrame, got {type_name}.", str(actual_result)

    # Generate genuine actual output ASCII table immediately
    actual_ascii = df_to_ascii_table(actual_result)

    exp_cols, exp_rows = parse_expected_ascii_or_json(expected_output_raw)
    if not exp_cols and not exp_rows:
        # Expected empty result
        if len(actual_result) == 0:
            return True, "Passed (empty result matched).", actual_ascii
        return False, f"Expected empty result, got {len(actual_result)} rows.", actual_ascii

    act_cols = list(actual_result.columns)

    # 1. Column matching (case-insensitive column alignment)
    if len(act_cols) != len(exp_cols):
        return False, f"Column count mismatch: expected {len(exp_cols)} columns {exp_cols}, got {len(act_cols)} columns {act_cols}.", actual_ascii

    aligned_col_names = []
    used_act_cols = set()
    for e_col in exp_cols:
        matches = [c for c in act_cols if c.strip().lower() == e_col.strip().lower() and c not in used_act_cols]
        if not matches:
            return False, f"Missing required column '{e_col}'. Actual columns: {act_cols}.", actual_ascii
        if len(matches) > 1:
            return False, f"Ambiguous column matching for '{e_col}'.", actual_ascii
        matched_c = matches[0]
        aligned_col_names.append(matched_c)
        used_act_cols.add(matched_c)

    # Reorder actual DataFrame columns according to expected column order
    aligned_df = actual_result[aligned_col_names]

    # 2. Row count check
    if len(aligned_df) != len(exp_rows):
        return False, f"Row count mismatch: expected {len(exp_rows)} rows, got {len(aligned_df)} rows.", actual_ascii

    # Extract actual rows as typed lists
    act_rows = []
    for _, r in aligned_df.iterrows():
        act_rows.append([r[col] for col in aligned_col_names])

    # 3. Order checking
    if is_ordered is True:
        for idx, (a_row, e_row) in enumerate(zip(act_rows, exp_rows)):
            if not _row_equal(a_row, e_row):
                return False, f"Row mismatch at row index {idx}.", actual_ascii
        return True, "Passed with exact row order.", actual_ascii

    # 4. Multiset matching (order-independent, preserves duplicate counts)
    unmatched_exp_indices = list(range(len(exp_rows)))
    for a_idx, a_row in enumerate(act_rows):
        found_idx = None
        for e_idx in unmatched_exp_indices:
            if _row_equal(a_row, exp_rows[e_idx]):
                found_idx = e_idx
                break
        if found_idx is None:
            return False, f"Row {a_idx} does not match any expected row.", actual_ascii
        unmatched_exp_indices.remove(found_idx)

    return True, "Passed (multiset row match).", actual_ascii
