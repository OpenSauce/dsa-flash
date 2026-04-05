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


def extract_func_name(starter_code: dict) -> str | None:
    """Extract the method name from starter_code's Java entry."""
    java_code = starter_code.get("java", "")
    # Match Java method signatures with optional modifiers and return types
    # e.g. "public int[] twoSum(", "boolean isPalindrome(", "static List<Integer> solve("
    match = re.search(
        r"(?:public|private|protected|static|\s)*"
        r"\s*\w+(?:<[^>]+>)?(?:\[\])?\s+(\w+)\s*\(",
        java_code,
    )
    return match.group(1) if match else None


def _build_java_node_classes(user_code: str, needed_types: set) -> str:
    """Build top-level node class definitions for types not already in user_code."""
    parts = []
    for type_name in ["ListNode", "TreeNode", "GraphNode"]:
        if type_name not in needed_types:
            continue
        if re.search(rf"\bclass\s+{re.escape(type_name)}\b", user_code):
            continue
        parts.append(_JAVA_TOPLEVEL_CLASS[type_name])
    return "\n".join(parts)


def _build_main_converters(needed_types: set) -> str:
    """Build static converter methods to go inside Main class."""
    parts = []
    for type_name in ["ListNode", "TreeNode", "GraphNode"]:
        if type_name not in needed_types:
            continue
        parts.append(_JAVA_CONVERTERS[type_name])
    return "\n".join(parts)


def _build_run_test_case(func_name: str, keys: list, param_types: dict) -> str:
    """Generate a Java _runTestCase method."""
    lines = []
    arg_names = []

    for key in keys:
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
            arg_names.append(f"_arg_{key}")
        else:
            lines.append(f"        Object _arg_{key} = inputMap.get(\"{key}\");")
            arg_names.append(f"_arg_{key}")

    call_expr = f"sol.{func_name}({', '.join(arg_names)})"

    ret_tag = param_types.get("__return__")
    if ret_tag and ret_tag in _JAVA_SERIALIZER:
        ser = _JAVA_SERIALIZER[ret_tag]
        ret_type = _JAVA_TYPE_DECL[ret_tag]
        lines.append(f"        {ret_type} _ret = ({ret_type}){call_expr};")
        lines.append(f"        return {ser}(_ret);")
    else:
        lines.append(f"        return {call_expr};")

    body = "\n".join(lines)
    return f"""\
    @SuppressWarnings("unchecked")
    private static Object _runTestCase(Map<String, Object> inputMap, Solution sol) {{
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

    # Build top-level node class defs (before Solution)
    node_class_defs = _build_java_node_classes(user_code, needed_types)

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

    harness = f"""\
import java.util.*;

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
