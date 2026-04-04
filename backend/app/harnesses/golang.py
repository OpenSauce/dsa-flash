import json
import re


def extract_func_name(starter_code: dict) -> str | None:
    """Extract the function name from starter_code's Go entry."""
    go_code = starter_code.get("go", "")
    match = re.search(r"func\s+(\w+)\s*\(", go_code)
    return match.group(1) if match else None


def _func_exists(user_code: str, func_name: str) -> bool:
    """Check if user code defines a Go function with the given name."""
    return bool(re.search(rf"func\s+{re.escape(func_name)}\s*\(", user_code))


def build_test_harness(user_code: str, test_cases: list, func_name: str) -> str:
    """Build a Go test harness that runs user code against test cases.

    Produces a complete package main program. Test cases are embedded as a
    JSON string and parsed at runtime with encoding/json. Uses reflect to
    call the user function dynamically. Outputs JSON after a
    ===HARNESS_OUTPUT=== marker so user fmt.Println() doesn't corrupt results.

    If the function is not found in user code, emits a harness that prints
    an error result without referencing the missing identifier (which would
    cause a compile error).
    """
    if not _func_exists(user_code, func_name):
        return _build_missing_func_harness(func_name)

    test_cases_json = json.dumps(test_cases).replace(
        "\\", "\\\\"
    ).replace('"', '\\"')

    # Extract ordered key names from each test case's input dict so Go
    # can look them up in insertion order (Go maps lose ordering).
    arg_orders = []
    for tc in test_cases:
        inp = tc.get("input", {})
        if isinstance(inp, dict):
            arg_orders.append(list(inp.keys()))
        else:
            arg_orders.append([])
    arg_orders_json = json.dumps(arg_orders).replace(
        "\\", "\\\\"
    ).replace('"', '\\"')

    harness = f"""\
package main

import (
\t"encoding/json"
\t"fmt"
\t"math"
\t"os"
\t"reflect"
\t"strings"
)

// Silence unused import errors — these are available for user code
var _ = math.MaxInt
var _ = strings.Contains

{user_code}

type testCase struct {{
\tInput    interface{{}} `json:"input"`
\tExpected interface{{}} `json:"expected"`
}}

type result struct {{
\tInput    string `json:"input"`
\tExpected string `json:"expected"`
\tActual   string `json:"actual"`
\tPassed   bool   `json:"passed"`
}}

func toJSON(v interface{{}}) string {{
\tb, err := json.Marshal(v)
\tif err != nil {{
\t\treturn fmt.Sprintf("%v", v)
\t}}
\treturn string(b)
}}

func convertArg(val interface{{}}, targetType reflect.Type) reflect.Value {{
\tif val == nil {{
\t\treturn reflect.Zero(targetType)
\t}}
\tkind := targetType.Kind()

\tswitch kind {{
\tcase reflect.Int:
\t\tif f, ok := val.(float64); ok {{
\t\t\treturn reflect.ValueOf(int(f))
\t\t}}
\tcase reflect.String:
\t\tif s, ok := val.(string); ok {{
\t\t\treturn reflect.ValueOf(s)
\t\t}}
\tcase reflect.Bool:
\t\tif b, ok := val.(bool); ok {{
\t\t\treturn reflect.ValueOf(b)
\t\t}}
\tcase reflect.Float64:
\t\tif f, ok := val.(float64); ok {{
\t\t\treturn reflect.ValueOf(f)
\t\t}}
\tcase reflect.Slice:
\t\tif arr, ok := val.([]interface{{}}); ok {{
\t\t\telemType := targetType.Elem()
\t\t\tslice := reflect.MakeSlice(targetType, len(arr), len(arr))
\t\t\tfor i, item := range arr {{
\t\t\t\tslice.Index(i).Set(convertArg(item, elemType))
\t\t\t}}
\t\t\treturn slice
\t\t}}
\t}}

\t// Fallback: try direct conversion
\trv := reflect.ValueOf(val)
\tif rv.Type().ConvertibleTo(targetType) {{
\t\treturn rv.Convert(targetType)
\t}}
\treturn reflect.ValueOf(val)
}}

func normalizeForComparison(val interface{{}}) interface{{}} {{
\tswitch v := val.(type) {{
\tcase float64:
\t\tif v == float64(int(v)) {{
\t\t\treturn int(v)
\t\t}}
\t\treturn v
\tcase []interface{{}}:
\t\tout := make([]interface{{}}, len(v))
\t\tfor i, item := range v {{
\t\t\tout[i] = normalizeForComparison(item)
\t\t}}
\t\treturn out
\tdefault:
\t\treturn val
\t}}
}}

func main() {{
\ttestJSON := "{test_cases_json}"
\tvar cases []testCase
\tif err := json.Unmarshal([]byte(testJSON), &cases); err != nil {{
\t\tfmt.Fprintf(os.Stderr, "Failed to parse test cases: %v\\n", err)
\t\tos.Exit(1)
\t}}

\t// Ordered arg keys per test case (from Python, preserves JSON key order)
\targOrderJSON := "{arg_orders_json}"
\tvar argOrders [][]string
\tjson.Unmarshal([]byte(argOrderJSON), &argOrders)

\tfn := reflect.ValueOf({func_name})
\tfnType := fn.Type()
\tresults := []result{{}}

\tfor idx, tc := range cases {{
\t\tfunc() {{
\t\t\tdefer func() {{
\t\t\t\tif r := recover(); r != nil {{
\t\t\t\t\tresults = append(results, result{{
\t\t\t\t\t\tInput:    toJSON(tc.Input),
\t\t\t\t\t\tExpected: toJSON(tc.Expected),
\t\t\t\t\t\tActual:   fmt.Sprintf("ERROR: %v", r),
\t\t\t\t\t\tPassed:   false,
\t\t\t\t\t}})
\t\t\t\t}}
\t\t\t}}()

\t\t\tvar args []reflect.Value
\t\t\tif inputMap, ok := tc.Input.(map[string]interface{{}}); ok {{
\t\t\t\t// Use ordered keys from Python to preserve argument order
\t\t\t\tvar keys []string
\t\t\t\tif idx < len(argOrders) {{
\t\t\t\t\tkeys = argOrders[idx]
\t\t\t\t}}
\t\t\t\tfor i, key := range keys {{
\t\t\t\t\tif i < fnType.NumIn() {{
\t\t\t\t\t\targs = append(args, convertArg(inputMap[key], fnType.In(i)))
\t\t\t\t\t}}
\t\t\t\t}}
\t\t\t}} else {{
\t\t\t\tif fnType.NumIn() > 0 {{
\t\t\t\t\targs = append(args, convertArg(tc.Input, fnType.In(0)))
\t\t\t\t}}
\t\t\t}}

\t\t\tout := fn.Call(args)
\t\t\tvar actual interface{{}}
\t\t\tif len(out) > 0 {{
\t\t\t\tactual = out[0].Interface()
\t\t\t}}

\t\t\tnormExpected := normalizeForComparison(tc.Expected)
\t\t\tpassed := toJSON(actual) == toJSON(normExpected)

\t\t\tresults = append(results, result{{
\t\t\t\tInput:    toJSON(tc.Input),
\t\t\t\tExpected: toJSON(normExpected),
\t\t\t\tActual:   toJSON(actual),
\t\t\t\tPassed:   passed,
\t\t\t}})
\t\t}}()
\t}}

\tfmt.Println("===HARNESS_OUTPUT===")
\toutJSON, _ := json.Marshal(results)
\tfmt.Println(string(outJSON))
}}
"""
    return harness


def _build_missing_func_harness(func_name: str) -> str:
    """Emit a Go program that prints an error result for a missing function."""
    return f"""\
package main

import (
\t"encoding/json"
\t"fmt"
)

type result struct {{
\tInput    string `json:"input"`
\tExpected string `json:"expected"`
\tActual   string `json:"actual"`
\tPassed   bool   `json:"passed"`
}}

func main() {{
\terrMsg := "Function '{func_name}' not found"
\tout, _ := json.Marshal([]result{{{{Actual: errMsg, Passed: false}}}})
\tfmt.Println("===HARNESS_OUTPUT===")
\tfmt.Println(string(out))
}}
"""
