import re


def extract_func_name(starter_code: dict) -> str | None:
    """Extract the function name from starter_code's Python def line."""
    python_code = starter_code.get("python", "")
    match = re.search(r"def\s+(\w+)\s*\(", python_code)
    return match.group(1) if match else None


def build_test_harness(user_code: str, test_cases: list, func_name: str) -> str:
    """Build a Python test harness that runs user code at module top-level.

    User code is placed at module scope (not exec'd) so that
    `from __future__ import annotations` works correctly on Python 3.7
    (Judge0 CE). Typing imports are injected for runtime subscript compat.
    """
    harness = f"""from __future__ import annotations
from typing import List, Dict, Tuple, Set, Optional, Any, Union
import json, sys

{user_code}

try:
    _func = {func_name}
except NameError:
    print(json.dumps([{{"input": "", "expected": "", "actual": "Function '{func_name}' not found", "passed": False}}]))
    sys.exit(0)

_test_cases = {repr(test_cases)}
_results = []

for _tc in _test_cases:
    _inp = _tc.get("input", {{}})
    _expected = _tc.get("expected")
    try:
        if isinstance(_inp, dict):
            _actual = _func(**_inp)
        else:
            _actual = _func(_inp)
        _passed = _actual == _expected
        _results.append({{
            "input": str(_inp),
            "expected": str(_expected),
            "actual": str(_actual),
            "passed": _passed,
        }})
    except Exception as _e:
        _results.append({{
            "input": str(_inp),
            "expected": str(_expected),
            "actual": f"ERROR: {{_e}}",
            "passed": False,
        }})

print(json.dumps(_results))
"""
    return harness
