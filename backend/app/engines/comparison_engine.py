"""Comparison at the serialization boundary, followed by typed comparison."""
import json
import math
from collections import Counter
from typing import Any, Dict, Optional, Tuple


class ComparisonContract:
    KNOWN_ORDER_AGNOSTIC_2SUM = {"two-sum", "two-sum-ii-input-array-is-sorted"}
    KNOWN_UNORDERED_OUTER = {
        "3sum", "4sum", "subsets", "subsets-ii", "permutations", "permutations-ii",
        "combination-sum", "combination-sum-ii", "combination-sum-iii",
        "letter-combinations-of-a-phone-number", "generate-parentheses", "group-anagrams",
    }
    KNOWN_UNORDERED_INNER = {
        "3sum", "4sum", "subsets", "subsets-ii", "combination-sum",
        "combination-sum-ii", "combination-sum-iii", "group-anagrams",
    }
    KNOWN_FLOAT_QUESTIONS = {"my-pow", "powx-n", "sqrtx", "find-median-from-data-stream"}

    @staticmethod
    def _parse_val(raw: Any) -> Any:
        # Decode only the outer wire value. Never reinterpret strings inside it.
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except (ValueError, TypeError):
                pass
        return raw

    @classmethod
    def compare(cls, actual_raw: Any, expected_raw: Any, question_slug: Optional[str] = None,
                contract: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        opts = contract or {}
        slug = (question_slug or "").lower().strip()
        act, exp = cls._parse_val(actual_raw), cls._parse_val(expected_raw)
        tol = opts.get("float_tolerance")
        if tol is None and slug in cls.KNOWN_FLOAT_QUESTIONS:
            tol = 1e-5
        unordered = opts.get("unordered_outer", not opts["is_ordered"] if opts.get("is_ordered") is not None
                             else slug in cls.KNOWN_UNORDERED_OUTER)
        indices = opts.get("order_agnostic_indices", slug in cls.KNOWN_ORDER_AGNOSTIC_2SUM)
        inner = opts.get("unordered_inner", slug in cls.KNOWN_UNORDERED_INNER)
        if slug == "group-anagrams" and any(
                not isinstance(value, list) or any(not isinstance(group, list) or
                any(not isinstance(word, str) for word in group) for group in value)
                for value in (act, exp)):
            return False, "Expected an array of arrays of strings."

        def freeze(value, depth):
            if isinstance(value, list):
                items = [freeze(item, depth + 1) for item in value]
                if depth == 1 and inner:
                    items.sort(key=repr)
                return ("list", tuple(items))
            if isinstance(value, dict):
                return ("dict", tuple(sorted((key, freeze(val, depth + 1)) for key, val in value.items())))
            # Numeric equality across integer/float representations is deliberate;
            # booleans and string cells retain their own type tags.
            tag = "number" if type(value) in (int, float) else type(value).__name__
            return tag, value

        def equal(a, b, depth=0):
            if a is None or b is None:
                return a is None and b is None
            if isinstance(a, bool) or isinstance(b, bool):
                return type(a) is type(b) and a == b
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                # Retain the existing numeric tolerance for floating point outputs.
                # String cells never reach this branch by numeric coercion.
                cell_tolerance = tol if tol is not None else (1e-5 if isinstance(a, float) or isinstance(b, float) else None)
                if cell_tolerance is not None:
                    return math.isfinite(a) and math.isfinite(b) and math.isclose(
                        a, b, rel_tol=0.0, abs_tol=float(cell_tolerance))
                return a == b
            if type(a) is not type(b):
                return False
            if isinstance(a, list):
                if len(a) != len(b):
                    return False
                any_order = (depth == 0 and (unordered or indices)) or (depth == 1 and inner)
                if any_order:
                    if tol is None:
                        return Counter(freeze(v, depth + 1) for v in a) == Counter(freeze(v, depth + 1) for v in b)
                    remaining = list(b)
                    for value in a:
                        for i, candidate in enumerate(remaining):
                            if equal(value, candidate, depth + 1):
                                remaining.pop(i)
                                break
                        else:
                            return False
                    return True
                return all(equal(x, y, depth + 1) for x, y in zip(a, b))
            if isinstance(a, dict):
                return a.keys() == b.keys() and all(equal(a[k], b[k], depth + 1) for k in a)
            return a == b

        passed = equal(act, exp)
        return passed, None if passed else "Output differs from the question's value, type, or ordering contract."
