import ast
import re

# Supported custom types (V1)
_CUSTOM_TYPES = {"ListNode", "TreeNode", "GraphNode"}

_LISTNODE_DEF = """\
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
"""

_TREENODE_DEF = """\
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
"""

_GRAPHNODE_DEF = """\
class GraphNode:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []
"""

_CONVERTERS = """\
def _list_to_listnode(arr):
    if not arr:
        return None
    head = ListNode(arr[0])
    cur = head
    for v in arr[1:]:
        cur.next = ListNode(v)
        cur = cur.next
    return head

def _listnode_to_list(node):
    result = []
    while node:
        result.append(node.val)
        node = node.next
    return result

def _list_to_treenode(arr):
    if not arr:
        return None
    root = TreeNode(arr[0])
    queue = [root]
    i = 1
    while queue and i < len(arr):
        node = queue.pop(0)
        if i < len(arr) and arr[i] is not None:
            node.left = TreeNode(arr[i])
            queue.append(node.left)
        i += 1
        if i < len(arr) and arr[i] is not None:
            node.right = TreeNode(arr[i])
            queue.append(node.right)
        i += 1
    return root

def _treenode_to_list(root):
    if root is None:
        return []
    result = []
    queue = [root]
    while queue:
        node = queue.pop(0)
        if node is None:
            result.append(None)
        else:
            result.append(node.val)
            queue.append(node.left)
            queue.append(node.right)
    while result and result[-1] is None:
        result.pop()
    return result

def _adj_to_graphnodes(adj):
    if not adj:
        return None
    nodes = [GraphNode(i + 1) for i in range(len(adj))]
    for i, neighbors in enumerate(adj):
        nodes[i].neighbors = [nodes[j - 1] for j in neighbors]
    return nodes[0]

def _graphnodes_to_adj(node):
    if node is None:
        return []
    visited = {}
    order = []
    queue = [node]
    while queue:
        cur = queue.pop(0)
        if cur.val in visited:
            continue
        visited[cur.val] = cur
        order.append(cur)
        for nb in cur.neighbors:
            if nb.val not in visited:
                queue.append(nb)
    n = len(order)
    adj = [[] for _ in range(n)]
    for nd in order:
        idx = nd.val - 1
        adj[idx] = sorted(nb.val for nb in nd.neighbors)
    return adj
"""


_BUILTINS = {
    "int", "str", "float", "bool", "list", "dict", "set", "tuple",
    "None", "Optional", "List", "Dict", "Set", "Tuple", "Any", "Union",
    "Sequence", "Iterable", "Iterator", "Generator",
}


def _extract_type_tag(annotation_str: str) -> str | None:
    """Return a custom type tag from a stringified annotation, or None."""
    for t in _CUSTOM_TYPES:
        if t in annotation_str:
            return t
    return None


def _check_for_unknown_custom_type(ann_str: str) -> None:
    """Raise ValueError if ann_str references an unknown custom class."""
    names = re.findall(r"\b([A-Z][a-zA-Z0-9]+)\b", ann_str)
    for name in names:
        if name not in _CUSTOM_TYPES and name not in _BUILTINS:
            raise ValueError(
                f"Unsupported custom type '{name}' — supported: "
                + ", ".join(sorted(_CUSTOM_TYPES))
            )


def parse_python_param_types(starter_code: str) -> dict[str, str]:
    """Parse the top-level function signature from Python starter code.

    Returns a dict mapping parameter names to custom type tags
    (e.g. {"head": "ListNode"}). Parameters with no custom type are omitted.
    Raises ValueError for unsupported custom type names found in annotations.
    """
    try:
        tree = ast.parse(starter_code)
    except SyntaxError:
        return {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.col_offset != 0:
            continue
        if node.name.startswith("__") and node.name.endswith("__"):
            continue

        param_types: dict[str, str] = {}
        args = node.args
        all_args = args.args + args.posonlyargs + args.kwonlyargs

        for arg in all_args:
            if arg.annotation is None:
                continue
            ann_str = ast.unparse(arg.annotation)
            tag = _extract_type_tag(ann_str)
            if tag is not None:
                param_types[arg.arg] = tag
            else:
                _check_for_unknown_custom_type(ann_str)

        if node.returns is not None:
            ret_str = ast.unparse(node.returns)
            tag = _extract_type_tag(ret_str)
            if tag is not None:
                param_types["__return__"] = tag
            else:
                _check_for_unknown_custom_type(ret_str)

        return param_types

    return {}


def extract_func_name(starter_code: dict) -> str | None:
    """Extract the top-level function name from starter_code's Python def.

    Skips class-body defs and returns the first top-level function definition
    (col_offset == 0, not a dunder method).
    """
    python_code = starter_code.get("python", "")
    try:
        tree = ast.parse(python_code)
    except SyntaxError:
        match = re.search(r"^def\s+(\w+)\s*\(", python_code, re.MULTILINE)
        return match.group(1) if match else None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.col_offset == 0:
            if not (node.name.startswith("__") and node.name.endswith("__")):
                return node.name

    return None


def _build_preamble(param_types: dict[str, str]) -> str:
    """Build preamble with needed class defs and converters."""
    needed_types = set(param_types.values())
    parts = []

    if "ListNode" in needed_types:
        parts.append(_LISTNODE_DEF)
    if "TreeNode" in needed_types:
        parts.append(_TREENODE_DEF)
    if "GraphNode" in needed_types:
        parts.append(_GRAPHNODE_DEF)

    if needed_types:
        parts.append(_CONVERTERS)

    return "\n".join(parts)


def build_test_harness(
    user_code: str,
    test_cases: list,
    func_name: str,
    param_types: dict[str, str] | None = None,
) -> str:
    """Build a Python test harness that runs user code at module top-level.

    User code is placed at module scope (not exec'd) so that
    `from __future__ import annotations` works correctly on Python 3.7
    (Judge0 CE). Typing imports are injected for runtime subscript compat.
    """
    if param_types is None:
        param_types = {}

    preamble = _build_preamble(param_types)

    harness = f"""from __future__ import annotations
from typing import List, Dict, Tuple, Set, Optional, Any, Union
import json, sys

{preamble}
{user_code}

try:
    _func = {func_name}
except NameError:
    print(json.dumps([{{"input": "", "expected": "", "actual": "Function '{func_name}' not found", "passed": False}}]))
    sys.exit(0)

_PARAM_TYPES = {repr(param_types)}
_test_cases = {repr(test_cases)}
_results = []

def _deserialize(val, type_tag):
    if type_tag == "ListNode":
        return _list_to_listnode(val)
    if type_tag == "TreeNode":
        return _list_to_treenode(val)
    if type_tag == "GraphNode":
        return _adj_to_graphnodes(val)
    return val

def _serialize(val, type_tag):
    if type_tag == "ListNode":
        return _listnode_to_list(val)
    if type_tag == "TreeNode":
        return _treenode_to_list(val)
    if type_tag == "GraphNode":
        return _graphnodes_to_adj(val)
    return val

for _tc in _test_cases:
    _inp = _tc.get("input", {{}})
    _expected = _tc.get("expected")
    try:
        if isinstance(_inp, dict):
            _converted = {{}}
            for _k, _v in _inp.items():
                _tag = _PARAM_TYPES.get(_k)
                _converted[_k] = _deserialize(_v, _tag) if _tag else _v
            _actual = _func(**_converted)
        else:
            _actual = _func(_inp)

        _ret_tag = _PARAM_TYPES.get("__return__")
        if _ret_tag:
            _actual_serialized = _serialize(_actual, _ret_tag)
        else:
            _actual_serialized = _actual

        _passed = _actual_serialized == _expected
        _results.append({{
            "input": str(_inp),
            "expected": str(_expected),
            "actual": str(_actual_serialized),
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
