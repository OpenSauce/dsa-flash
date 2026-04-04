import json
import re


def extract_func_name(starter_code: dict) -> str | None:
    """Extract the function name from starter_code's JavaScript entry."""
    js_code = starter_code.get("javascript", "")
    # Match: function twoSum(  or  const twoSum =
    match = re.search(r"function\s+(\w+)\s*\(", js_code)
    if not match:
        match = re.search(r"(?:const|let|var)\s+(\w+)\s*=", js_code)
    return match.group(1) if match else None


def build_test_harness(user_code: str, test_cases: list, func_name: str) -> str:
    """Build a Node.js test harness that runs user code against test cases.

    Outputs JSON array to stdout after a ===HARNESS_OUTPUT=== marker
    so user console.log() calls don't corrupt the result.
    """
    test_cases_json = json.dumps(test_cases)

    harness = f"""\
{user_code}

const _testCasesRaw = '{test_cases_json.replace(chr(92), chr(92)*2).replace("'", chr(92) + "'")}';

(function() {{
  if (typeof {func_name} !== 'function') {{
    console.log('===HARNESS_OUTPUT===');
    console.log(JSON.stringify([{{
      input: '', expected: '', actual: "Function '{func_name}' not found", passed: false
    }}]));
    process.exit(0);
  }}

  const _testCases = JSON.parse(_testCasesRaw);
  const _results = [];

  for (const _tc of _testCases) {{
    const _inp = _tc.input || {{}};
    const _expected = _tc.expected;
    try {{
      let _actual;
      if (typeof _inp === 'object' && !Array.isArray(_inp)) {{
        _actual = {func_name}(...Object.values(_inp));
      }} else {{
        _actual = {func_name}(_inp);
      }}
      const _passed = JSON.stringify(_actual) === JSON.stringify(_expected);
      _results.push({{
        input: JSON.stringify(_inp),
        expected: JSON.stringify(_expected),
        actual: JSON.stringify(_actual),
        passed: _passed,
      }});
    }} catch (_e) {{
      _results.push({{
        input: JSON.stringify(_inp),
        expected: JSON.stringify(_expected),
        actual: 'ERROR: ' + _e.message,
        passed: false,
      }});
    }}
  }}

  console.log('===HARNESS_OUTPUT===');
  console.log(JSON.stringify(_results));
}})();
"""
    return harness
