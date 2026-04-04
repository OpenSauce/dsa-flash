import json
import re


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


def build_test_harness(user_code: str, test_cases: list, func_name: str) -> str:
    """Build a Java test harness that runs user code against test cases.

    Generates a Main.java with the user's Solution class and a test runner.
    If user code doesn't contain a class declaration, wraps it in
    class Solution {}. Outputs JSON after ===HARNESS_OUTPUT=== marker.
    """
    test_cases_json = json.dumps(test_cases).replace("\\", "\\\\").replace('"', '\\"')

    # Only skip wrapping if user code already declares class Solution
    has_solution_class = bool(re.search(r"\bclass\s+Solution\b", user_code))
    if has_solution_class:
        solution_code = user_code
    else:
        solution_code = f"class Solution {{\n{user_code}\n}}"

    harness = f"""\
import java.util.*;

{solution_code}

public class Main {{
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
                if (input instanceof Map) {{
                    Map<String, Object> inputMap = (Map<String, Object>) input;
                    Object[] vals = inputMap.values().toArray();
                    // Call method via reflection
                    java.lang.reflect.Method[] methods = Solution.class.getDeclaredMethods();
                    java.lang.reflect.Method method = null;
                    for (java.lang.reflect.Method m : methods) {{
                        if (m.getName().equals("{func_name}")) {{
                            method = m;
                            break;
                        }}
                    }}
                    if (method == null) {{
                        System.out.println("===HARNESS_OUTPUT===");
                        System.out.println("[{{\\"input\\":\\"\\",\\"expected\\":\\"\\","
                            + "\\"actual\\":\\"Method '{func_name}' not found\\","
                            + "\\"passed\\":false}}]");
                        return;
                    }}
                    // Convert args to match parameter types
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
                        if (m.getName().equals("{func_name}")) {{
                            method = m;
                            break;
                        }}
                    }}
                    if (method == null) {{
                        System.out.println("===HARNESS_OUTPUT===");
                        System.out.println("[{{\\"input\\":\\"\\",\\"expected\\":\\"\\","
                            + "\\"actual\\":\\"Method '{func_name}' not found\\","
                            + "\\"passed\\":false}}]");
                        return;
                    }}
                    Class<?>[] paramTypes = method.getParameterTypes();
                    Object[] converted = new Object[]{{convertArg(input, paramTypes[0])}};
                    actual = method.invoke(sol, converted);
                }}
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
