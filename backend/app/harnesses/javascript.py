import json
import re

_JS_LISTNODE_CLASS = """\
class ListNode {
  constructor(val = 0, next = null) {
    this.val = val;
    this.next = next;
  }
}
"""

_JS_LISTNODE_CONVERTERS = """\
function _arrayToListNode(arr) {
  if (!arr || arr.length === 0) return null;
  const head = new ListNode(arr[0]);
  let cur = head;
  for (let i = 1; i < arr.length; i++) {
    cur.next = new ListNode(arr[i]);
    cur = cur.next;
  }
  return head;
}
function _listNodeToArray(node) {
  const result = [];
  while (node !== null) {
    result.push(node.val);
    node = node.next;
  }
  return result;
}
"""

_JS_TREENODE_CLASS = """\
class TreeNode {
  constructor(val = 0, left = null, right = null) {
    this.val = val;
    this.left = left;
    this.right = right;
  }
}
"""

_JS_TREENODE_CONVERTERS = """\
function _arrayToTreeNode(arr) {
  if (!arr || arr.length === 0) return null;
  if (arr[0] === null) return null;
  const root = new TreeNode(arr[0]);
  const queue = [root];
  let i = 1;
  while (queue.length > 0 && i < arr.length) {
    const node = queue.shift();
    if (i < arr.length && arr[i] !== null) {
      node.left = new TreeNode(arr[i]);
      queue.push(node.left);
    }
    i++;
    if (i < arr.length && arr[i] !== null) {
      node.right = new TreeNode(arr[i]);
      queue.push(node.right);
    }
    i++;
  }
  return root;
}
function _treeNodeToArray(root) {
  if (root === null) return [];
  const result = [];
  const queue = [root];
  while (queue.length > 0) {
    const node = queue.shift();
    if (node === null) {
      result.push(null);
    } else {
      result.push(node.val);
      queue.push(node.left);
      queue.push(node.right);
    }
  }
  while (result.length > 0 && result[result.length - 1] === null) {
    result.pop();
  }
  return result;
}
"""

_JS_GRAPHNODE_CLASS = """\
class GraphNode {
  constructor(val = 0, neighbors = []) {
    this.val = val;
    this.neighbors = neighbors;
  }
}
"""

_JS_GRAPHNODE_CONVERTERS = """\
function _adjToGraphNode(adj) {
  if (!adj || adj.length === 0) return null;
  const nodes = adj.map((_, i) => new GraphNode(i + 1));
  for (let i = 0; i < adj.length; i++) {
    nodes[i].neighbors = (adj[i] || []).map(j => nodes[j - 1]);
  }
  return nodes[0];
}
function _graphNodeToAdj(node) {
  if (node === null) return [];
  const visited = new Map();
  const order = [];
  const queue = [node];
  while (queue.length > 0) {
    const cur = queue.shift();
    if (visited.has(cur.val)) continue;
    visited.set(cur.val, cur);
    order.push(cur);
    for (const nb of cur.neighbors) {
      if (!visited.has(nb.val)) queue.push(nb);
    }
  }
  const adj = Array.from({length: order.length}, () => []);
  for (const nd of order) {
    adj[nd.val - 1] = nd.neighbors.map(nb => nb.val).sort((a, b) => a - b);
  }
  return adj;
}
"""

_JS_CLASS_DEFS = {
    "ListNode": _JS_LISTNODE_CLASS,
    "TreeNode": _JS_TREENODE_CLASS,
    "GraphNode": _JS_GRAPHNODE_CLASS,
}

_JS_CONVERTER_DEFS = {
    "ListNode": _JS_LISTNODE_CONVERTERS,
    "TreeNode": _JS_TREENODE_CONVERTERS,
    "GraphNode": _JS_GRAPHNODE_CONVERTERS,
}

_JS_DESERIALIZER = {
    "ListNode": "_arrayToListNode",
    "TreeNode": "_arrayToTreeNode",
    "GraphNode": "_adjToGraphNode",
}

_JS_SERIALIZER = {
    "ListNode": "_listNodeToArray",
    "TreeNode": "_treeNodeToArray",
    "GraphNode": "_graphNodeToAdj",
}


def extract_func_name(starter_code: dict) -> str | None:
    """Extract the function name from starter_code's JavaScript entry."""
    js_code = starter_code.get("javascript", "")
    # Match: function twoSum(  or  const twoSum =
    match = re.search(r"function\s+(\w+)\s*\(", js_code)
    if not match:
        match = re.search(r"(?:const|let|var)\s+(\w+)\s*=", js_code)
    return match.group(1) if match else None


def _build_js_preamble(user_code: str, needed_types: set) -> str:
    """Inject class defs + converters for needed types.

    Skip the class definition itself when user code already declares it
    (redeclaration is a SyntaxError in JS), but ALWAYS inject the converter
    functions — they are harness-private and the generated runner references
    them unconditionally.
    """
    parts = []
    for type_name in ["ListNode", "TreeNode", "GraphNode"]:
        if type_name not in needed_types:
            continue
        if not re.search(rf"\bclass\s+{re.escape(type_name)}\b", user_code):
            parts.append(_JS_CLASS_DEFS[type_name])
        parts.append(_JS_CONVERTER_DEFS[type_name])
    return "\n".join(parts)


def build_test_harness(
    user_code: str,
    test_cases: list,
    func_name: str,
    param_types: dict | None = None,
) -> str:
    """Build a Node.js test harness that runs user code against test cases.

    Outputs JSON array to stdout after a ===HARNESS_OUTPUT=== marker
    so user console.log() calls don't corrupt the result.
    """
    if param_types is None:
        param_types = {}

    needed_types = set(param_types.values())
    preamble = _build_js_preamble(user_code, needed_types)

    # Build canonical key order from first test case
    canonical_keys: list = []
    for tc in test_cases:
        inp = tc.get("input", {})
        if isinstance(inp, dict) and inp:
            canonical_keys = list(inp.keys())
            break

    test_cases_json = json.dumps(test_cases)

    # Build conversion snippet for inputs
    if needed_types and canonical_keys:
        convert_lines = []
        arg_names = []
        for key in canonical_keys:
            type_tag = param_types.get(key)
            if type_tag and type_tag in _JS_DESERIALIZER:
                deser = _JS_DESERIALIZER[type_tag]
                convert_lines.append(
                    f"      const _arg_{key} = Array.isArray(_inp['{key}']) "
                    f"? {deser}(_inp['{key}']) : _inp['{key}'];"
                )
            else:
                convert_lines.append(f"      const _arg_{key} = _inp['{key}'];")
            arg_names.append(f"_arg_{key}")

        ret_tag = param_types.get("__return__")
        if ret_tag and ret_tag in _JS_SERIALIZER:
            ser = _JS_SERIALIZER[ret_tag]
            args_str = ", ".join(arg_names)
            call_expr = (
                f"const _rawActual = {func_name}({args_str});\n"
                f"      const _actual = {ser}(_rawActual);"
            )
        else:
            call_expr = f"const _actual = {func_name}({', '.join(arg_names)});"

        convert_block = "\n".join(convert_lines)
        call_block = f"""\
      {convert_block}
      {call_expr}"""
    else:
        call_block = f"""\
      let _actual;
      if (typeof _inp === 'object' && !Array.isArray(_inp)) {{
        _actual = {func_name}(...Object.values(_inp));
      }} else {{
        _actual = {func_name}(_inp);
      }}"""

    harness = f"""\
{preamble}
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
{call_block}
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
