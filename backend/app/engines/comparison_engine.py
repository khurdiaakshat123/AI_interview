import json
import math
from typing import Any, Dict, Optional, Tuple, List
from collections import Counter

class ComparisonContract:
    """
    Authoritative answer comparison contract per LeetCode question.
    Eliminates blanket shortcuts (arbitrary sorting, case-insensitivity, whitespace stripping,
    treating all 2-element arrays as unordered).
    """

    KNOWN_ORDER_AGNOSTIC_2SUM = {
        "two-sum",
        "two-sum-ii-input-array-is-sorted"
    }

    KNOWN_UNORDERED_OUTER = {
        "3sum",
        "4sum",
        "subsets",
        "subsets-ii",
        "permutations",
        "permutations-ii",
        "combination-sum",
        "combination-sum-ii",
        "combination-sum-iii",
        "letter-combinations-of-a-phone-number",
        "generate-parentheses",
        "group-anagrams"
    }

    KNOWN_FLOAT_QUESTIONS = {
        "my-pow",
        "powx-n",
        "sqrtx",
        "find-median-from-data-stream"
    }

    @classmethod
    def _parse_val(cls, raw: Any) -> Any:
        if raw is None:
            return None
        if isinstance(raw, (int, float, bool, list, dict)):
            return raw
        s = str(raw).strip()
        if not s:
            return s
        if s.lower() == "true":
            return True
        if s.lower() == "false":
            return False
        if s.lower() == "null" or s.lower() == "none":
            return None
        try:
            return json.loads(s)
        except Exception:
            # Handle float or int
            try:
                if "." in s or "e" in s.lower():
                    return float(s)
                return int(s)
            except Exception:
                return s

    @classmethod
    def _canonical_element(cls, elem: Any) -> Any:
        if isinstance(elem, list):
            # Sort inner elements if inner elements are unordered, otherwise convert to tuple
            try:
                return tuple(sorted([cls._canonical_element(x) for x in elem]))
            except TypeError:
                return tuple([cls._canonical_element(x) for x in elem])
        elif isinstance(elem, dict):
            return tuple(sorted((k, cls._canonical_element(v)) for k, v in elem.items()))
        return elem

    @classmethod
    def compare(
        cls,
        actual_raw: Any,
        expected_raw: Any,
        question_slug: Optional[str] = None,
        contract: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Authoritative comparison function.
        Returns (passed: bool, mismatch_reason: Optional[str]).
        """
        slug = (question_slug or "").lower().strip()
        opts = contract or {}

        act = cls._parse_val(actual_raw)
        exp = cls._parse_val(expected_raw)

        # 1. Type mismatch check
        if act is None and exp is None:
            return True, None
        if act is None or exp is None:
            return False, f"Null mismatch: actual={repr(act)}, expected={repr(exp)}"

        # Strict Boolean check (ensure bool != int in Python)
        if isinstance(act, bool) or isinstance(exp, bool):
            if isinstance(act, bool) and isinstance(exp, bool):
                if act == exp:
                    return True, None
                return False, f"Boolean mismatch: actual={act}, expected={exp}"
            return False, f"Type mismatch: boolean expected, got {type(act).__name__}"

        # 2. Float comparisons with explicit epsilon tolerance
        is_float_q = slug in cls.KNOWN_FLOAT_QUESTIONS or opts.get("float_tolerance") is not None
        if (isinstance(act, (int, float)) and isinstance(exp, (int, float))) and (is_float_q or isinstance(act, float) or isinstance(exp, float)):
            tol = opts.get("float_tolerance", 1e-5)
            if math.isclose(float(act), float(exp), abs_tol=tol):
                return True, None
            return False, f"Float mismatch: actual={act}, expected={exp} (tolerance={tol})"

        # 3. Two Sum special contract: indices can be returned in any order
        is_2sum = slug in cls.KNOWN_ORDER_AGNOSTIC_2SUM or opts.get("order_agnostic_indices", False)
        if is_2sum and isinstance(act, list) and isinstance(exp, list) and len(act) == 2 and len(exp) == 2:
            if act == exp or act == exp[::-1]:
                return True, None
            return False, f"Indices mismatch: actual={act}, expected={exp} (any order permitted)"

        # 4. Group Anagrams: outer list unordered, inner lists can be sorted
        if slug == "group-anagrams" and isinstance(act, list) and isinstance(exp, list):
            if len(act) != len(exp):
                return False, f"Outer list length mismatch: actual has {len(act)}, expected {len(exp)}"
            act_canon = Counter(tuple(sorted(sub)) for sub in act if isinstance(sub, list))
            exp_canon = Counter(tuple(sorted(sub)) for sub in exp if isinstance(sub, list))
            if act_canon == exp_canon:
                return True, None
            return False, f"Group Anagrams multiset mismatch"

        # 5. Multiset for questions with unordered outer lists (3Sum, Subsets, etc.)
        is_unordered_outer = slug in cls.KNOWN_UNORDERED_OUTER or opts.get("unordered_outer", False)
        if is_unordered_outer and isinstance(act, list) and isinstance(exp, list):
            if len(act) != len(exp):
                return False, f"Outer list length mismatch: actual has {len(act)}, expected {len(exp)}"
            try:
                act_canon = Counter(cls._canonical_element(x) for x in act)
                exp_canon = Counter(cls._canonical_element(x) for x in exp)
                if act_canon == exp_canon:
                    return True, None
                return False, f"Multiset elements mismatch"
            except Exception as e:
                # Fallback to direct equality if elements cannot be canonicalized
                pass

        # 6. Default: STRICT EQUALITY
        # Lists must preserve exact order and types
        if isinstance(act, list) and isinstance(exp, list):
            if len(act) != len(exp):
                return False, f"Array length mismatch: actual has {len(act)}, expected {len(exp)}"
            for i in range(len(act)):
                sub_passed, sub_err = cls.compare(act[i], exp[i], slug, opts)
                if not sub_passed:
                    return False, f"Array index {i} mismatch: {sub_err}"
            return True, None

        # Dicts must match keys and values strictly
        if isinstance(act, dict) and isinstance(exp, dict):
            if act.keys() != exp.keys():
                return False, f"Key mismatch: actual={list(act.keys())}, expected={list(exp.keys())}"
            for k in act:
                sub_passed, sub_err = cls.compare(act[k], exp[k], slug, opts)
                if not sub_passed:
                    return False, f"Dict key '{k}' mismatch: {sub_err}"
            return True, None

        # Strings: Case-sensitive, exact match
        if isinstance(act, str) and isinstance(exp, str):
            if act == exp:
                return True, None
            return False, f"String mismatch: actual={repr(act)}, expected={repr(exp)}"

        # General scalar equality
        if act == exp:
            return True, None

        return False, f"Value mismatch: actual={repr(act)}, expected={repr(exp)}"
