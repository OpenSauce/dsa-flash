import json
import re

# Top-level class definitions (no static keyword, no converters)
_JAVA_TOPLEVEL_CLASS = {
    "ListNode": """\
class ListNode {
    int val;
    ListNode next;
    ListNode() {}
    ListNode(int val) { this.val = val; }
    ListNode(int val, ListNode next) { this.val = val; this.next = next; }
}
""",
    "TreeNode": """\
class TreeNode {
    int val;
    TreeNode left;
    TreeNode right;
    TreeNode() {}
    TreeNode(int val) { this.val = val; }
    TreeNode(int val, TreeNode left, TreeNode right) { this.val = val; this.left = left; this.right = right; }
}
""",
    "GraphNode": """\
class GraphNode {
    int val;
    java.util.List<GraphNode> neighbors;
    GraphNode() { val = 0; neighbors = new java.util.ArrayList<>(); }
    GraphNode(int val) { this.val = val; neighbors = new java.util.ArrayList<>(); }
    GraphNode(int val, java.util.List<GraphNode> neighbors) { this.val = val; this.neighbors = neighbors; }
}
""",
}

# Static converter methods to inject inside Main
_JAVA_CONVERTERS = {
    "ListNode": """\
    private static ListNode _arrayToListNode(List<?> arr) {
        if (arr == null || arr.isEmpty()) return null;
        ListNode head = new ListNode(((Number)arr.get(0)).intValue());
        ListNode cur = head;
        for (int i = 1; i < arr.size(); i++) {
            cur.next = new ListNode(((Number)arr.get(i)).intValue());
            cur = cur.next;
        }
        return head;
    }
    private static List<Integer> _listNodeToList(ListNode node) {
        List<Integer> result = new ArrayList<>();
        while (node != null) { result.add(node.val); node = node.next; }
        return result;
    }
""",
    "TreeNode": """\
    private static TreeNode _arrayToTreeNode(List<?> arr) {
        if (arr == null || arr.isEmpty()) return null;
        if (arr.get(0) == null) return null;
        TreeNode root = new TreeNode(((Number)arr.get(0)).intValue());
        Queue<TreeNode> queue = new LinkedList<>();
        queue.add(root);
        int i = 1;
        while (!queue.isEmpty() && i < arr.size()) {
            TreeNode node = queue.poll();
            if (i < arr.size() && arr.get(i) != null) {
                node.left = new TreeNode(((Number)arr.get(i)).intValue());
                queue.add(node.left);
            }
            i++;
            if (i < arr.size() && arr.get(i) != null) {
                node.right = new TreeNode(((Number)arr.get(i)).intValue());
                queue.add(node.right);
            }
            i++;
        }
        return root;
    }
    private static List<Object> _treeNodeToList(TreeNode root) {
        if (root == null) return new ArrayList<>();
        List<Object> result = new ArrayList<>();
        Queue<TreeNode> queue = new LinkedList<>();
        queue.add(root);
        while (!queue.isEmpty()) {
            TreeNode node = queue.poll();
            if (node == null) { result.add(null); continue; }
            result.add(node.val);
            queue.add(node.left);
            queue.add(node.right);
        }
        while (!result.isEmpty() && result.get(result.size()-1) == null)
            result.remove(result.size()-1);
        return result;
    }
""",
    "GraphNode": """\
    private static GraphNode _adjToGraphNode(List<?> adj) {
        if (adj == null || adj.isEmpty()) return null;
        List<GraphNode> nodes = new ArrayList<>();
        for (int i = 0; i < adj.size(); i++) nodes.add(new GraphNode(i + 1));
        for (int i = 0; i < adj.size(); i++) {
            List<?> nbList = (List<?>)adj.get(i);
            for (Object nb : nbList)
                nodes.get(i).neighbors.add(nodes.get(((Number)nb).intValue() - 1));
        }
        return nodes.get(0);
    }
    private static List<List<Integer>> _graphNodeToAdj(GraphNode node) {
        if (node == null) return new ArrayList<>();
        Map<Integer, GraphNode> visited = new LinkedHashMap<>();
        List<GraphNode> order = new ArrayList<>();
        Queue<GraphNode> queue = new LinkedList<>();
        queue.add(node);
        while (!queue.isEmpty()) {
            GraphNode cur = queue.poll();
            if (visited.containsKey(cur.val)) continue;
            visited.put(cur.val, cur);
            order.add(cur);
            for (GraphNode nb : cur.neighbors)
                if (!visited.containsKey(nb.val)) queue.add(nb);
        }
        List<List<Integer>> adj = new ArrayList<>();
        for (int i = 0; i < order.size(); i++) adj.add(new ArrayList<>());
        for (GraphNode nd : order) {
            List<Integer> nbVals = new ArrayList<>();
            for (GraphNode nb : nd.neighbors) nbVals.add(nb.val);
            Collections.sort(nbVals);
            adj.set(nd.val - 1, nbVals);
        }
        return adj;
    }
""",
}

_JAVA_DESERIALIZER = {
    "ListNode": "_arrayToListNode",
    "TreeNode": "_arrayToTreeNode",
    "GraphNode": "_adjToGraphNode",
}

_JAVA_SERIALIZER = {
    "ListNode": "_listNodeToList",
    "TreeNode": "_treeNodeToList",
    "GraphNode": "_graphNodeToAdj",
}

_JAVA_TYPE_DECL = {
    "ListNode": "ListNode",
    "TreeNode": "TreeNode",
    "GraphNode": "GraphNode",
}


def extract_func_name(strater_code_or_starter_code: dict) -> str | None:
    """Extract the method name from starter_code's Java entry.

    Strategy: scan the code once, tracking brace depth, and return the first
    method declaration found at the top level (depth 0) or inside a single
    `class Solution { ... }` wrapper (depth 1 with outer class Solution).
    This correctly ignores methods and constructors inside helper node
    classes like `class ListNode { int val; ListNode(int x) { ... } }`.

    Handles return types including primitives, arrays (any dim), nested
    generics, and qualified names. Excludes reserved words.
    """
    java_code = strater_code_or_starter_code.get("java", "")
    if not java_code:
        return None

    # Regex matches one method signature: optional modifiers, return type,
    # method name, open paren. Return type allows nested generics etc.
    sig_re = re.compile(
        r"(?:(?:public|private|protected|static|final|abstract)\s+)+"
        r"[\w<>?,.&\[\]\s]+?"
        r"\s+(\w+)\s*\(",
    )
    reserved = {"class", "interface", "enum", "extends", "implements", "throws"}

    # Walk char-by-char tracking brace depth and line starts. For each line,
    # if depth is 0 (top-level) or we're inside `class Solution` at depth 1,
    # try to match a method signature there.
    in_solution = False
    solution_depth: int | None = None
    depth = 0
    i = 0
    n = len(java_code)

    # Precompute positions of `class Solution {` to know when we enter it.
    solution_match = re.search(r"\bclass\s+Solution\b\s*\{", java_code)
    solution_open = solution_match.end() - 1 if solution_match else -1  # index of '{'

    while i < n:
        ch = java_code[i]
        if ch == "{":
            if i == solution_open:
                in_solution = True
                solution_depth = depth
            depth += 1
            i += 1
            continue
        if ch == "}":
            depth -= 1
            if in_solution and solution_depth is not None and depth == solution_depth:
                in_solution = False
            i += 1
            continue

        # Only try matching at top-level or inside the Solution class body.
        eligible = (depth == 0) or (in_solution and depth == (solution_depth or 0) + 1)
        if eligible:
            m = sig_re.match(java_code, i)
            if m:
                name = m.group(1)
                if name not in reserved:
                    return name
                i = m.end()
                continue
        i += 1

    return None


def _build_java_node_classes(needed_types: set) -> str:
    """Build top-level node class definitions for all needed types.

    Always inject — Java user code typically defines its own ListNode/TreeNode
    inline, but when the harness wraps user code in `class Solution { ... }`,
    the user's classes become nested (e.g. Solution.ListNode) and no longer
    satisfy the top-level type references in harness-generated converters.
    Callers should strip user's top-level node classes before wrapping
    (see _strip_user_node_classes) so this injection wins.
    """
    parts = []
    for type_name in ["ListNode", "TreeNode", "GraphNode"]:
        if type_name not in needed_types:
            continue
        parts.append(_JAVA_TOPLEVEL_CLASS[type_name])
    return "\n".join(parts)


def _strip_java_imports(user_code: str) -> tuple[str, set[str]]:
    """Remove `import ...;` lines from user code and return them.

    Imports inside the harness-injected `class Solution { ... }` wrapper are
    illegal in Java. Callers re-emit the collected imports at the top of
    Main.java so user solutions can still reference packages beyond the
    default `java.util.*`.
    """
    imports: set[str] = set()

    def _capture(match: re.Match) -> str:
        imports.add(match.group(1))
        return ""

    user_code = re.sub(
        r"^\s*import\s+([^;]+);\s*\n?",
        _capture,
        user_code,
        flags=re.MULTILINE,
    )
    return user_code, imports


def _strip_user_node_classes(user_code: str, needed_types: set) -> str:
    """Remove user's top-level `class ListNode { ... }` declarations.

    The harness provides its own canonical versions of these classes (LeetCode
    convention: fields `val`, `next`, `left`, `right`, `neighbors`). User YAML
    starter code frequently includes a minimal inline version for documentation;
    removing it avoids collisions when the surrounding code gets wrapped in
    `class Solution`, and ensures harness converters and user methods reference
    the same top-level class.

    Uses brace-balance counting rather than a regex so class bodies with
    nested braces (e.g. constructor bodies like `ListNode(int x) { val = x; }`)
    are handled correctly.
    """
    for type_name in ["ListNode", "TreeNode", "GraphNode"]:
        if type_name not in needed_types:
            continue
        pattern = re.compile(rf"\bclass\s+{re.escape(type_name)}\b")
        while True:
            match = pattern.search(user_code)
            if match is None:
                break
            # Find the opening brace after the class name.
            open_idx = user_code.find("{", match.end())
            if open_idx == -1:
                break
            # Walk to the matching closing brace.
            depth = 1
            i = open_idx + 1
            while i < len(user_code) and depth > 0:
                ch = user_code[i]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                i += 1
            if depth != 0:
                break  # unbalanced — leave the code alone
            # Strip leading whitespace before the class and any trailing
            # blank line(s) so we don't leave orphan newlines.
            start = match.start()
            while start > 0 and user_code[start - 1] in " \t":
                start -= 1
            end = i
            while end < len(user_code) and user_code[end] in " \t":
                end += 1
            if end < len(user_code) and user_code[end] == "\n":
                end += 1
            user_code = user_code[:start] + user_code[end:]
    return user_code


def _build_main_converters(needed_types: set) -> str:
    """Build static converter methods to go inside Main class."""
    parts = []
    for type_name in ["ListNode", "TreeNode", "GraphNode"]:
        if type_name not in needed_types:
            continue
        parts.append(_JAVA_CONVERTERS[type_name])
    return "\n".join(parts)


def _build_run_test_case(func_name: str, keys: list, param_types: dict) -> str:
    """Generate a Java _runTestCase method.

    Custom-type params use the dedicated deserializers.  Non-custom params are
    converted via convertArg with the reflected parameter type.  All args are
    passed through method.invoke() so mixed signatures like
    (ListNode head, int n) work — Java's reflection layer handles the
    Object→primitive unboxing automatically.
    """
    lines = []

    # Reflect on the method once to get concrete parameter types.
    lines.append("        java.lang.reflect.Method _m = null;")
    lines.append("        for (java.lang.reflect.Method _cm : Solution.class.getDeclaredMethods()) {")
    lines.append(f"            if (_cm.getName().equals(\"{func_name}\")) {{ _m = _cm; break; }}")
    lines.append("        }")
    lines.append(f"        if (_m == null) throw new RuntimeException(\"Method {func_name} not found\");")
    lines.append(f"        Object[] _invokeArgs = new Object[{len(keys)}];")

    for i, key in enumerate(keys):
        type_tag = param_types.get(key)
        if type_tag and type_tag in _JAVA_DESERIALIZER:
            deser = _JAVA_DESERIALIZER[type_tag]
            java_type = _JAVA_TYPE_DECL[type_tag]
            lines.append(
                f"        {java_type} _arg_{key} = null;"
            )
            lines.append(
                f"        if (inputMap.get(\"{key}\") instanceof List) {{"
            )
            lines.append(
                f"            _arg_{key} = {deser}((List<?>)inputMap.get(\"{key}\"));"
            )
            lines.append("        }")
            lines.append(f"        _invokeArgs[{i}] = _arg_{key};")
        else:
            lines.append(
                f"        _invokeArgs[{i}] = convertArg(inputMap.get(\"{key}\"),"
                f" _m.getParameterTypes()[{i}]);"
            )

    ret_tag = param_types.get("__return__")
    lines.append("        Object _ret = _m.invoke(sol, _invokeArgs);")
    if ret_tag and ret_tag in _JAVA_SERIALIZER:
        ser = _JAVA_SERIALIZER[ret_tag]
        ret_type = _JAVA_TYPE_DECL[ret_tag]
        lines.append(f"        return {ser}(({ret_type})_ret);")
    else:
        lines.append("        return _ret;")

    body = "\n".join(lines)
    return f"""\
    @SuppressWarnings("unchecked")
    private static Object _runTestCase(Map<String, Object> inputMap, Solution sol) throws Exception {{
{body}
    }}"""


def build_test_harness(
    user_code: str,
    test_cases: list,
    func_name: str,
    param_types: dict | None = None,
) -> str:
    """Build a Java test harness that runs user code against test cases.

    Generates a Main.java with the user's Solution class and a test runner.
    If user code doesn't contain a class declaration, wraps it in
    class Solution {}. Outputs JSON after ===HARNESS_OUTPUT=== marker.
    """
    if param_types is None:
        param_types = {}

    needed_types = set(param_types.values())

    test_cases_json = json.dumps(test_cases).replace("\\", "\\\\").replace('"', '\\"')

    # Strip user's `import` statements and collect them so they can be re-emitted
    # at the top of Main.java. Imports inside the wrapped `class Solution`
    # are illegal in Java, and some solutions reference packages beyond
    # java.util (e.g. java.util.stream, java.util.regex).
    user_code, user_imports = _strip_java_imports(user_code)

    # Strip any user-provided top-level node classes; harness will inject its
    # own canonical versions so converters and user code reference the same types.
    user_code = _strip_user_node_classes(user_code, needed_types)

    # Build top-level node class defs (before Solution)
    node_class_defs = _build_java_node_classes(needed_types)

    # Only skip wrapping if user code already declares class Solution
    has_solution_class = bool(re.search(r"\bclass\s+Solution\b", user_code))
    if has_solution_class:
        solution_code = user_code
    else:
        solution_code = f"class Solution {{\n{user_code}\n}}"

    # Build canonical key order
    canonical_keys: list = []
    for tc in test_cases:
        inp = tc.get("input", {})
        if isinstance(inp, dict) and inp:
            canonical_keys = list(inp.keys())
            break

    # Build run_test_case method and call block
    main_converters = _build_main_converters(needed_types)
    if needed_types and canonical_keys:
        run_test_case_method = _build_run_test_case(func_name, canonical_keys, param_types)
        call_block = _CUSTOM_CALL_BLOCK
    else:
        run_test_case_method = ""
        call_block = _REFLECT_CALL_BLOCK.format(func_name=func_name)

    # Re-emit user-requested imports at the top of Main.java (skip the ones
    # already in the harness's default import list).
    _already_imported = {"java.util.*"}
    extra_imports = "\n".join(
        f"import {imp};" for imp in sorted(user_imports) if imp not in _already_imported
    )

    harness = f"""\
import java.util.*;
{extra_imports}

{node_class_defs}
{solution_code}

public class Main {{
{main_converters}
{run_test_case_method}

    private static String toJSON(Object val) {{
        if (val == null) return "null";
        if (val instanceof Object[]) {{
            StringBuilder sb = new StringBuilder("[");
            Object[] arr = (Object[]) val;
            for (int i = 0; i < arr.length; i++) {{
                if (i > 0) sb.append(",");
                sb.append(toJSON(arr[i]));
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (val instanceof int[]) {{
            StringBuilder sb = new StringBuilder("[");
            int[] arr = (int[]) val;
            for (int i = 0; i < arr.length; i++) {{
                if (i > 0) sb.append(",");
                sb.append(arr[i]);
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (val instanceof boolean[]) {{
            StringBuilder sb = new StringBuilder("[");
            boolean[] arr = (boolean[]) val;
            for (int i = 0; i < arr.length; i++) {{
                if (i > 0) sb.append(",");
                sb.append(arr[i]);
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (val instanceof double[]) {{
            StringBuilder sb = new StringBuilder("[");
            double[] arr = (double[]) val;
            for (int i = 0; i < arr.length; i++) {{
                if (i > 0) sb.append(",");
                sb.append(arr[i]);
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (val instanceof List) {{
            StringBuilder sb = new StringBuilder("[");
            List<?> list = (List<?>) val;
            for (int i = 0; i < list.size(); i++) {{
                if (i > 0) sb.append(",");
                sb.append(toJSON(list.get(i)));
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (val instanceof String) {{
            String s = (String) val;
            s = s.replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"");
            s = s.replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t");
            return "\\"" + s + "\\"";
        }}
        return String.valueOf(val);
    }}

    @SuppressWarnings("unchecked")
    private static Object parseJSON(String s) {{
        s = s.trim();
        if (s.equals("null")) return null;
        if (s.equals("true")) return Boolean.TRUE;
        if (s.equals("false")) return Boolean.FALSE;
        if (s.startsWith("\\"") && s.endsWith("\\"")) {{
            String inner = s.substring(1, s.length() - 1);
            inner = inner.replace("\\\\\\\\", "\\\\");
            inner = inner.replace("\\\\\\"", "\\"");
            inner = inner.replace("\\\\n", "\\n");
            inner = inner.replace("\\\\r", "\\r");
            inner = inner.replace("\\\\t", "\\t");
            return inner;
        }}
        if (s.startsWith("[")) {{
            List<Object> list = new ArrayList<>();
            s = s.substring(1, s.length() - 1).trim();
            if (s.isEmpty()) return list;
            int depth = 0;
            int start = 0;
            boolean inStr = false;
            for (int i = 0; i < s.length(); i++) {{
                char c = s.charAt(i);
                if (c == '\\\\' && inStr) {{ i++; continue; }}
                if (c == '\\"') {{ inStr = !inStr; continue; }}
                if (inStr) continue;
                if (c == '[' || c == '{{') depth++;
                else if (c == ']' || c == '}}') depth--;
                else if (c == ',' && depth == 0) {{
                    list.add(parseJSON(s.substring(start, i)));
                    start = i + 1;
                }}
            }}
            list.add(parseJSON(s.substring(start)));
            return list;
        }}
        if (s.startsWith("{{")) {{
            Map<String, Object> map = new LinkedHashMap<>();
            s = s.substring(1, s.length() - 1).trim();
            if (s.isEmpty()) return map;
            int depth = 0;
            int start = 0;
            boolean inStr = false;
            List<String> parts = new ArrayList<>();
            for (int i = 0; i < s.length(); i++) {{
                char c = s.charAt(i);
                if (c == '\\\\' && inStr) {{ i++; continue; }}
                if (c == '\\"') {{ inStr = !inStr; continue; }}
                if (inStr) continue;
                if (c == '[' || c == '{{') depth++;
                else if (c == ']' || c == '}}') depth--;
                else if (c == ',' && depth == 0) {{
                    parts.add(s.substring(start, i).trim());
                    start = i + 1;
                }}
            }}
            parts.add(s.substring(start).trim());
            for (String part : parts) {{
                int colon = part.indexOf(':');
                String key = part.substring(0, colon).trim();
                if (key.startsWith("\\"")) key = key.substring(1, key.length() - 1);
                Object value = parseJSON(part.substring(colon + 1).trim());
                map.put(key, value);
            }}
            return map;
        }}
        if (s.contains(".")) return Double.parseDouble(s);
        return Integer.parseInt(s);
    }}

    private static int[] toIntArray(Object o) {{
        List<?> list = (List<?>) o;
        int[] arr = new int[list.size()];
        for (int i = 0; i < list.size(); i++) arr[i] = ((Number) list.get(i)).intValue();
        return arr;
    }}

    private static String[] toStringArray(Object o) {{
        List<?> list = (List<?>) o;
        String[] arr = new String[list.size()];
        for (int i = 0; i < list.size(); i++) arr[i] = (String) list.get(i);
        return arr;
    }}

    private static int[][] toIntMatrix(Object o) {{
        List<?> outer = (List<?>) o;
        int[][] arr = new int[outer.size()][];
        for (int i = 0; i < outer.size(); i++) {{
            List<?> inner = (List<?>) outer.get(i);
            arr[i] = new int[inner.size()];
            for (int j = 0; j < inner.size(); j++) arr[i][j] = ((Number) inner.get(j)).intValue();
        }}
        return arr;
    }}

    private static char[][] toCharMatrix(Object o) {{
        List<?> outer = (List<?>) o;
        char[][] arr = new char[outer.size()][];
        for (int i = 0; i < outer.size(); i++) {{
            List<?> inner = (List<?>) outer.get(i);
            arr[i] = new char[inner.size()];
            for (int j = 0; j < inner.size(); j++) {{
                Object v = inner.get(j);
                arr[i][j] = v instanceof String ? ((String) v).charAt(0) : (char) ((Number) v).intValue();
            }}
        }}
        return arr;
    }}

    private static String[][] toStringMatrix(Object o) {{
        List<?> outer = (List<?>) o;
        String[][] arr = new String[outer.size()][];
        for (int i = 0; i < outer.size(); i++) {{
            List<?> inner = (List<?>) outer.get(i);
            arr[i] = new String[inner.size()];
            for (int j = 0; j < inner.size(); j++) arr[i][j] = (String) inner.get(j);
        }}
        return arr;
    }}

    @SuppressWarnings("unchecked")
    public static void main(String[] args) {{
        String testJSON = "{test_cases_json}";
        List<?> cases = (List<?>) parseJSON(testJSON);
        Solution sol = new Solution();
        StringBuilder results = new StringBuilder("[");

        for (int i = 0; i < cases.size(); i++) {{
            Map<String, Object> tc = (Map<String, Object>) cases.get(i);
            Object input = tc.get("input");
            Object expected = tc.get("expected");
            String inputStr = toJSON(input);
            String expectedStr = toJSON(expected);

            try {{
                Object actual;
{call_block}
                String actualStr = toJSON(actual);
                boolean passed = actualStr.equals(expectedStr);
                if (i > 0) results.append(",");
                results.append("{{\\"input\\":")
                    .append("\\"").append(escape(inputStr)).append("\\",")
                    .append("\\"expected\\":")
                    .append("\\"").append(escape(expectedStr)).append("\\",")
                    .append("\\"actual\\":")
                    .append("\\"").append(escape(actualStr)).append("\\",")
                    .append("\\"passed\\":").append(passed).append("}}");
            }} catch (Exception e) {{
                String errMsg = e.getCause() != null ? e.getCause().getMessage() : e.getMessage();
                if (i > 0) results.append(",");
                results.append("{{\\"input\\":")
                    .append("\\"").append(escape(inputStr)).append("\\",")
                    .append("\\"expected\\":")
                    .append("\\"").append(escape(expectedStr)).append("\\",")
                    .append("\\"actual\\":")
                    .append("\\"ERROR: ").append(escape(errMsg != null ? errMsg : "unknown")).append("\\",")
                    .append("\\"passed\\":false}}");
            }}
        }}

        results.append("]");
        System.out.println("===HARNESS_OUTPUT===");
        System.out.println(results.toString());
    }}

    private static String escape(String s) {{
        return s.replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"");
    }}

    private static Object convertArg(Object val, Class<?> type) {{
        if (type == int.class || type == Integer.class) {{
            return ((Number) val).intValue();
        }}
        if (type == long.class || type == Long.class) {{
            return ((Number) val).longValue();
        }}
        if (type == double.class || type == Double.class) {{
            return ((Number) val).doubleValue();
        }}
        if (type == boolean.class || type == Boolean.class) {{
            return (Boolean) val;
        }}
        if (type == String.class) {{
            return (String) val;
        }}
        if (type == int[].class) {{
            return toIntArray(val);
        }}
        if (type == String[].class) {{
            return toStringArray(val);
        }}
        if (type == int[][].class) {{
            return toIntMatrix(val);
        }}
        if (type == char[][].class) {{
            return toCharMatrix(val);
        }}
        if (type == String[][].class) {{
            return toStringMatrix(val);
        }}
        if (type == List.class) {{
            return val;
        }}
        return val;
    }}
}}
"""
    return harness


_CUSTOM_CALL_BLOCK = """\
                if (input instanceof Map) {
                    actual = _runTestCase((Map<String, Object>)input, sol);
                } else {
                    actual = "ERROR: unexpected non-map input";
                }"""

_REFLECT_CALL_BLOCK = """\
                if (input instanceof Map) {{
                    Map<String, Object> inputMap = (Map<String, Object>) input;
                    Object[] vals = inputMap.values().toArray();
                    java.lang.reflect.Method[] methods = Solution.class.getDeclaredMethods();
                    java.lang.reflect.Method method = null;
                    for (java.lang.reflect.Method m : methods) {{
                        if (m.getName().equals("{func_name}")) {{ method = m; break; }}
                    }}
                    if (method == null) {{
                        System.out.println("===HARNESS_OUTPUT===");
                        System.out.println("[{{\\\"input\\\":\\\"\\\",\\\"expected\\\":\\\"\\\","
                            + "\\\"actual\\\":\\\"Method '{func_name}' not found\\\","
                            + "\\\"passed\\\":false}}]");
                        return;
                    }}
                    Class<?>[] paramTypes = method.getParameterTypes();
                    Object[] converted = new Object[vals.length];
                    for (int j = 0; j < vals.length; j++) {{
                        converted[j] = convertArg(vals[j], paramTypes[j]);
                    }}
                    actual = method.invoke(sol, converted);
                }} else {{
                    java.lang.reflect.Method[] methods = Solution.class.getDeclaredMethods();
                    java.lang.reflect.Method method = null;
                    for (java.lang.reflect.Method m : methods) {{
                        if (m.getName().equals("{func_name}")) {{ method = m; break; }}
                    }}
                    if (method == null) {{
                        System.out.println("===HARNESS_OUTPUT===");
                        System.out.println("[{{\\\"input\\\":\\\"\\\",\\\"expected\\\":\\\"\\\","
                            + "\\\"actual\\\":\\\"Method '{func_name}' not found\\\","
                            + "\\\"passed\\\":false}}]");
                        return;
                    }}
                    Class<?>[] paramTypes = method.getParameterTypes();
                    Object[] converted = new Object[]{{convertArg(input, paramTypes[0])}};
                    actual = method.invoke(sol, converted);
                }}"""
