import json
import re

_LISTNODE_TYPE = """\
type ListNode struct {
\tVal  int
\tNext *ListNode
}
"""

_LISTNODE_CONVERTERS = """\
func _arrayToListNode(arr []interface{}) *ListNode {
\tif len(arr) == 0 {
\t\treturn nil
\t}
\thead := &ListNode{Val: int(arr[0].(float64))}
\tcur := head
\tfor _, v := range arr[1:] {
\t\tcur.Next = &ListNode{Val: int(v.(float64))}
\t\tcur = cur.Next
\t}
\treturn head
}

func _listNodeToArray(node *ListNode) []int {
\tvar result []int
\tfor node != nil {
\t\tresult = append(result, node.Val)
\t\tnode = node.Next
\t}
\tif result == nil {
\t\treturn []int{}
\t}
\treturn result
}
"""

_TREENODE_TYPE = """\
type TreeNode struct {
\tVal   int
\tLeft  *TreeNode
\tRight *TreeNode
}
"""

_TREENODE_CONVERTERS = """\
func _arrayToTreeNode(arr []interface{}) *TreeNode {
\tif len(arr) == 0 {
\t\treturn nil
\t}
\tif arr[0] == nil {
\t\treturn nil
\t}
\troot := &TreeNode{Val: int(arr[0].(float64))}
\tqueue := []*TreeNode{root}
\ti := 1
\tfor len(queue) > 0 && i < len(arr) {
\t\tnode := queue[0]
\t\tqueue = queue[1:]
\t\tif i < len(arr) && arr[i] != nil {
\t\t\tnode.Left = &TreeNode{Val: int(arr[i].(float64))}
\t\t\tqueue = append(queue, node.Left)
\t\t}
\t\ti++
\t\tif i < len(arr) && arr[i] != nil {
\t\t\tnode.Right = &TreeNode{Val: int(arr[i].(float64))}
\t\t\tqueue = append(queue, node.Right)
\t\t}
\t\ti++
\t}
\treturn root
}

func _treeNodeToArray(root *TreeNode) []interface{} {
\tif root == nil {
\t\treturn []interface{}{}
\t}
\tvar result []interface{}
\tqueue := []*TreeNode{root}
\tfor len(queue) > 0 {
\t\tnode := queue[0]
\t\tqueue = queue[1:]
\t\tif node == nil {
\t\t\tresult = append(result, nil)
\t\t} else {
\t\t\tresult = append(result, node.Val)
\t\t\tqueue = append(queue, node.Left)
\t\t\tqueue = append(queue, node.Right)
\t\t}
\t}
\tfor len(result) > 0 && result[len(result)-1] == nil {
\t\tresult = result[:len(result)-1]
\t}
\tif result == nil {
\t\treturn []interface{}{}
\t}
\treturn result
}
"""

_GRAPHNODE_TYPE = """\
type GraphNode struct {
\tVal       int
\tNeighbors []*GraphNode
}
"""

_GRAPHNODE_CONVERTERS = """\
func _adjToGraphNode(adj []interface{}) *GraphNode {
\tif len(adj) == 0 {
\t\treturn nil
\t}
\tnodes := make([]*GraphNode, len(adj))
\tfor i := range nodes {
\t\tnodes[i] = &GraphNode{Val: i + 1}
\t}
\tfor i, neighbors := range adj {
\t\tnbList, _ := neighbors.([]interface{})
\t\tfor _, nb := range nbList {
\t\t\tj := int(nb.(float64)) - 1
\t\t\tnodes[i].Neighbors = append(nodes[i].Neighbors, nodes[j])
\t\t}
\t}
\treturn nodes[0]
}

func _graphNodeToAdj(node *GraphNode) [][]int {
\tif node == nil {
\t\treturn [][]int{}
\t}
\tvisited := map[int]*GraphNode{}
\torder := []*GraphNode{}
\tqueue := []*GraphNode{node}
\tfor len(queue) > 0 {
\t\tcur := queue[0]
\t\tqueue = queue[1:]
\t\tif _, seen := visited[cur.Val]; seen {
\t\t\tcontinue
\t\t}
\t\tvisited[cur.Val] = cur
\t\torder = append(order, cur)
\t\tfor _, nb := range cur.Neighbors {
\t\t\tif _, seen := visited[nb.Val]; !seen {
\t\t\t\tqueue = append(queue, nb)
\t\t\t}
\t\t}
\t}
\tn := len(order)
\tadj := make([][]int, n)
\tfor _, nd := range order {
\t\tidx := nd.Val - 1
\t\tfor _, nb := range nd.Neighbors {
\t\t\tadj[idx] = append(adj[idx], nb.Val)
\t\t}
\t\tif adj[idx] == nil {
\t\t\tadj[idx] = []int{}
\t\t} else {
\t\t\tsort.Ints(adj[idx])
\t\t}
\t}
\treturn adj
}
"""

_TYPE_DEFS = {
    "ListNode": _LISTNODE_TYPE,
    "TreeNode": _TREENODE_TYPE,
    "GraphNode": _GRAPHNODE_TYPE,
}

_CONVERTER_DEFS = {
    "ListNode": _LISTNODE_CONVERTERS,
    "TreeNode": _TREENODE_CONVERTERS,
    "GraphNode": _GRAPHNODE_CONVERTERS,
}


def extract_func_name(starter_code: dict) -> str | None:
    """Extract the function name from starter_code's Go entry."""
    go_code = starter_code.get("go", "")
    match = re.search(r"func\s+(\w+)\s*\(", go_code)
    return match.group(1) if match else None


def _func_exists(user_code: str, func_name: str) -> bool:
    """Check if user code defines a Go function with the given name."""
    return bool(re.search(rf"func\s+{re.escape(func_name)}\s*\(", user_code))


def _strip_go_package_and_imports(user_code: str) -> tuple[str, set[str]]:
    """Remove `package main` and import blocks from user code.

    Returns (stripped_code, extra_imports) where extra_imports is the set of
    import paths the user code requested. Callers merge these into the
    harness's own import list so user code can reference them without the
    harness redeclaring `package main`.
    """
    extra: set[str] = set()

    # Drop any `package <name>` line (typically `package main`).
    user_code = re.sub(r"^\s*package\s+\w+\s*\n", "", user_code, flags=re.MULTILINE)

    # Collect and drop single-line imports: `import "fmt"` or `import f "fmt"`.
    def _capture_single(match: re.Match) -> str:
        extra.add(match.group(1))
        return ""

    user_code = re.sub(
        r"^\s*import\s+(?:\w+\s+)?\"([^\"]+)\"\s*\n",
        _capture_single,
        user_code,
        flags=re.MULTILINE,
    )

    # Collect and drop multi-line import blocks: `import ( ... )`.
    def _capture_block(match: re.Match) -> str:
        for line in match.group(1).splitlines():
            m = re.search(r"\"([^\"]+)\"", line)
            if m:
                extra.add(m.group(1))
        return ""

    user_code = re.sub(
        r"^\s*import\s*\(\s*([^)]*)\)\s*\n",
        _capture_block,
        user_code,
        flags=re.MULTILINE,
    )
    return user_code, extra


def _build_struct_defs(user_code: str, needed_types: set) -> str:
    """Inject struct defs + converters for needed types.

    Skip the type definition itself when user code already declares it
    (Go disallows redeclaration), but ALWAYS inject the converter functions
    — they are harness-private (underscore-prefixed) and the generated
    _runTestCase call site references them unconditionally.
    """
    parts = []
    for type_name in ["ListNode", "TreeNode", "GraphNode"]:
        if type_name not in needed_types:
            continue
        if not re.search(rf"\btype\s+{re.escape(type_name)}\s+struct\b", user_code):
            parts.append(_TYPE_DEFS[type_name])
        parts.append(_CONVERTER_DEFS[type_name])
    return "\n".join(parts)


_PARAM_TO_DESERIALIZER = {
    "ListNode": "_arrayToListNode",
    "TreeNode": "_arrayToTreeNode",
    "GraphNode": "_adjToGraphNode",
}

_RETURN_SERIALIZER = {
    "ListNode": "_listNodeToArray",
    "TreeNode": "_treeNodeToArray",
    "GraphNode": "_graphNodeToAdj",
}

_TYPE_ASSERTION = {
    "ListNode": "*ListNode",
    "TreeNode": "*TreeNode",
    "GraphNode": "*GraphNode",
}


def _build_run_func(func_name: str, keys: list, param_types: dict) -> str:
    """Generate a _runTestCase function that handles custom-type arg/return conversion.

    Custom-type params (ListNode/TreeNode/GraphNode) are converted via the
    dedicated deserializers.  Non-custom params are converted via reflect so
    that the generated call compiles for typed signatures like (head *ListNode,
    n int) where n must be int, not interface{}.
    """
    lines = []
    arg_exprs = []

    has_plain_params = any(
        not (param_types.get(k) and param_types.get(k) in _PARAM_TO_DESERIALIZER)
        for k in keys
    )

    # reflect is needed to convert non-custom params to their concrete types.
    lines.append(f"\tfn := reflect.ValueOf({func_name})")
    if has_plain_params:
        lines.append("\tfnType := fn.Type()")

    for i, key in enumerate(keys):
        type_tag = param_types.get(key)
        if type_tag and type_tag in _PARAM_TO_DESERIALIZER:
            deser = _PARAM_TO_DESERIALIZER[type_tag]
            lines.append(
                f'\t_raw_{key} := inputMap["{key}"]'
            )
            lines.append(
                f'\tvar _p_{key} {_TYPE_ASSERTION[type_tag]}'
            )
            lines.append(
                f'\tif _raw_{key} != nil {{'
            )
            lines.append(
                f'\t\tif _arr, _ok := _raw_{key}.([]interface{{}}); _ok {{'
            )
            lines.append(
                f'\t\t\t_p_{key} = {deser}(_arr)'
            )
            lines.append(
                '\t\t}'
            )
            lines.append(
                '\t}'
            )
            arg_exprs.append(f"reflect.ValueOf(_p_{key})")
        else:
            lines.append(
                f'\t_conv_{key} := convertArg(inputMap["{key}"], fnType.In({i}))'
            )
            arg_exprs.append(f"_conv_{key}")

    lines.append(f"\t_out := fn.Call([]reflect.Value{{{', '.join(arg_exprs)}}})")

    ret_tag = param_types.get("__return__")
    if ret_tag and ret_tag in _RETURN_SERIALIZER:
        serializer = _RETURN_SERIALIZER[ret_tag]
        go_type = _TYPE_ASSERTION[ret_tag]
        lines.append(f"\t_ret := _out[0].Interface().({go_type})")
        lines.append(f"\treturn {serializer}(_ret)")
    else:
        lines.append("\tif len(_out) == 0 { return nil }")
        lines.append("\treturn _out[0].Interface()")

    body = "\n".join(lines)
    return f"func _runTestCase(inputMap map[string]interface{{}}) interface{{}} {{\n{body}\n}}"


def build_test_harness(
    user_code: str,
    test_cases: list,
    func_name: str,
    param_types: dict | None = None,
) -> str:
    """Build a Go test harness that runs user code against test cases.

    Produces a complete package main program. Test cases are embedded as a
    JSON string and parsed at runtime with encoding/json. Uses reflect to
    call the user function dynamically when no custom types are present.
    For custom types, generates a direct typed call via _runTestCase.
    Outputs JSON after a ===HARNESS_OUTPUT=== marker.
    """
    if param_types is None:
        param_types = {}

    # User starters occasionally include a leading `package main` declaration
    # and/or their own import block for documentation. The harness supplies
    # its own package clause and import list, so strip these from user code
    # to avoid "package main redeclared" and "non-declaration statement
    # outside function body" compile errors. Imports the user actually needs
    # are merged back into the harness import list below.
    user_code, user_imports = _strip_go_package_and_imports(user_code)

    if not _func_exists(user_code, func_name):
        return _build_missing_func_harness(func_name)

    test_cases_json = json.dumps(test_cases).replace(
        "\\", "\\\\"
    ).replace('"', '\\"')

    # Extract ordered key names from each test case's input dict
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

    needed_types = set(param_types.values())
    has_custom = bool(needed_types)

    struct_defs = _build_struct_defs(user_code, needed_types)

    # Get canonical key order
    canonical_keys: list = []
    for order in arg_orders:
        if order:
            canonical_keys = order
            break

    sort_import = '\t"sort"' if "GraphNode" in needed_types else ""

    if has_custom and canonical_keys:
        run_func = _build_run_func(func_name, canonical_keys, param_types)
        call_snippet = _CUSTOM_CALL_SNIPPET
        extra_imports = '\t"reflect"'
        loop_var = "_"
    else:
        run_func = ""
        call_snippet = _REFLECT_CALL_SNIPPET.format(func_name=func_name)
        extra_imports = '\t"reflect"'
        loop_var = "idx"

    # Merge user-requested imports that aren't already in the harness list,
    # so their solutions can reference packages like strconv/unicode/bytes.
    _already_imported = {
        "encoding/json", "fmt", "math", "os", "reflect", "sort", "strings",
    }
    user_extra = "\n".join(
        f'\t"{imp}"' for imp in sorted(user_imports) if imp not in _already_imported
    )

    harness = f"""\
package main

import (
\t"encoding/json"
\t"fmt"
\t"math"
\t"os"
{extra_imports}
{sort_import}
\t"strings"
{user_extra}
)

// Silence unused import errors — these are available for user code
var _ = math.MaxInt64
var _ = strings.Contains

{struct_defs}
{user_code}

{run_func}

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

{_REFLECT_CONVERT_IF_NEEDED}

func main() {{
\ttestJSON := "{test_cases_json}"
\tvar cases []testCase
\tif err := json.Unmarshal([]byte(testJSON), &cases); err != nil {{
\t\tfmt.Fprintf(os.Stderr, "Failed to parse test cases: %v\\n", err)
\t\tos.Exit(1)
\t}}

\targOrderJSON := "{arg_orders_json}"
\tvar argOrders [][]string
\tjson.Unmarshal([]byte(argOrderJSON), &argOrders)

\tresults := []result{{}}

\tfor {loop_var}, tc := range cases {{
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
{call_snippet}
\t\t}}()
\t}}

\tfmt.Println("===HARNESS_OUTPUT===")
\toutJSON, _ := json.Marshal(results)
\tfmt.Println(string(outJSON))
}}
"""
    return harness


_CUSTOM_CALL_SNIPPET = """\
\t\t\tif inputMap, ok := tc.Input.(map[string]interface{}); ok {
\t\t\t\tactual := _runTestCase(inputMap)
\t\t\t\tnormExpected := normalizeForComparison(tc.Expected)
\t\t\t\tpassed := toJSON(actual) == toJSON(normExpected)
\t\t\t\tresults = append(results, result{
\t\t\t\t\tInput:    toJSON(tc.Input),
\t\t\t\t\tExpected: toJSON(normExpected),
\t\t\t\t\tActual:   toJSON(actual),
\t\t\t\t\tPassed:   passed,
\t\t\t\t})
\t\t\t} else {
\t\t\t\tresults = append(results, result{
\t\t\t\t\tInput:    toJSON(tc.Input),
\t\t\t\t\tExpected: toJSON(tc.Expected),
\t\t\t\t\tActual:   "ERROR: unexpected non-map input",
\t\t\t\t\tPassed:   false,
\t\t\t\t})
\t\t\t}"""

_REFLECT_CALL_SNIPPET = """\
\t\t\tfn := reflect.ValueOf({func_name})
\t\t\tfnType := fn.Type()
\t\t\tvar args []reflect.Value
\t\t\tif inputMap, ok := tc.Input.(map[string]interface{{}}); ok {{
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
\t\t\t}})"""

_REFLECT_CONVERT_IF_NEEDED = """\
func convertArg(val interface{}, targetType reflect.Type) reflect.Value {
\tif val == nil {
\t\treturn reflect.Zero(targetType)
\t}
\tkind := targetType.Kind()
\tswitch kind {
\tcase reflect.Int:
\t\tif f, ok := val.(float64); ok {
\t\t\treturn reflect.ValueOf(int(f))
\t\t}
\tcase reflect.String:
\t\tif s, ok := val.(string); ok {
\t\t\treturn reflect.ValueOf(s)
\t\t}
\tcase reflect.Bool:
\t\tif b, ok := val.(bool); ok {
\t\t\treturn reflect.ValueOf(b)
\t\t}
\tcase reflect.Float64:
\t\tif f, ok := val.(float64); ok {
\t\t\treturn reflect.ValueOf(f)
\t\t}
\tcase reflect.Slice:
\t\tif arr, ok := val.([]interface{}); ok {
\t\t\telemType := targetType.Elem()
\t\t\tslice := reflect.MakeSlice(targetType, len(arr), len(arr))
\t\t\tfor i, item := range arr {
\t\t\t\tslice.Index(i).Set(convertArg(item, elemType))
\t\t\t}
\t\t\treturn slice
\t\t}
\t}
\trv := reflect.ValueOf(val)
\tif rv.Type().ConvertibleTo(targetType) {
\t\treturn rv.Convert(targetType)
\t}
\treturn reflect.ValueOf(val)
}"""


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
