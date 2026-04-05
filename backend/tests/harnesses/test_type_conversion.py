"""Round-trip tests for custom type (ListNode, TreeNode, GraphNode) conversion
across all four harness languages.

Each test:
 1. Builds a harness using the language's solution code + param_types derived
    from the Python starter signature.
 2. Runs the generated code locally (requires python3 / node / go / javac).
 3. Asserts all test cases passed.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

from app.harnesses import build, get_param_types
from app.harnesses.python import parse_python_param_types

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _run_python(code: str) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        r = subprocess.run(["python3", path], capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, f"Python error: {r.stderr[:300]}"
        return json.loads(r.stdout.strip())
    finally:
        os.unlink(path)


def _run_javascript(code: str) -> list[dict]:
    if not shutil.which("node"):
        pytest.skip("node not installed")
    with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, f"Node error: {r.stderr[:300]}"
        marker = "===HARNESS_OUTPUT==="
        out = r.stdout
        if marker in out:
            out = out[out.rfind(marker) + len(marker):].strip()
        return json.loads(out)
    finally:
        os.unlink(path)


def _run_go(code: str) -> list[dict]:
    if not shutil.which("go"):
        pytest.skip("go not installed")
    with tempfile.NamedTemporaryFile(suffix=".go", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        r = subprocess.run(["go", "run", path], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, f"Go error: {r.stderr[:300]}"
        marker = "===HARNESS_OUTPUT==="
        out = r.stdout
        if marker in out:
            out = out[out.rfind(marker) + len(marker):].strip()
        return json.loads(out)
    finally:
        os.unlink(path)


def _run_java(code: str) -> list[dict]:
    if not shutil.which("javac"):
        pytest.skip("javac not installed")
    tmp_dir = tempfile.mkdtemp()
    java_file = os.path.join(tmp_dir, "Main.java")
    try:
        with open(java_file, "w") as f:
            f.write(code)
        r = subprocess.run(["javac", java_file], capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, f"Java compile error: {r.stderr[:500]}"
        r2 = subprocess.run(
            ["java", "-cp", tmp_dir, "Main"], capture_output=True, text=True, timeout=30
        )
        assert r2.returncode == 0, f"Java run error: {r2.stderr[:300]}"
        marker = "===HARNESS_OUTPUT==="
        out = r2.stdout
        if marker in out:
            out = out[out.rfind(marker) + len(marker):].strip()
        return json.loads(out)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _assert_all_passed(results: list[dict]) -> None:
    failed = [r for r in results if not r.get("passed", False)]
    assert not failed, f"Failed test cases: {failed}"


# ---------------------------------------------------------------------------
# Python starter snippets + solutions per type
# ---------------------------------------------------------------------------

_PYTHON_STARTERS = {
    "ListNode": """
from typing import Optional

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def reverse_list(head: Optional[ListNode]) -> Optional[ListNode]:
    pass
""",
    "TreeNode": """
from typing import Optional

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def invert_tree(root: Optional[TreeNode]) -> Optional[TreeNode]:
    pass
""",
    "GraphNode": """
from typing import Optional

class GraphNode:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []

def clone_graph(node: Optional[GraphNode]) -> Optional[GraphNode]:
    pass
""",
}

_SOLUTIONS = {
    "python": {
        "ListNode": """
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def reverse_list(head):
    prev = None
    while head:
        nxt = head.next
        head.next = prev
        prev = head
        head = nxt
    return prev
""",
        "TreeNode": """
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def invert_tree(root):
    if not root:
        return None
    root.left, root.right = root.right, root.left
    invert_tree(root.left)
    invert_tree(root.right)
    return root
""",
        "GraphNode": """
class GraphNode:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []

def clone_graph(node):
    if not node:
        return None
    mapping = {}
    def dfs(n):
        if n.val in mapping:
            return mapping[n.val]
        clone = GraphNode(n.val)
        mapping[n.val] = clone
        for nb in n.neighbors:
            clone.neighbors.append(dfs(nb))
        return clone
    return dfs(node)
""",
    },
    "javascript": {
        "ListNode": """
function reverseList(head) {
    let prev = null, curr = head;
    while (curr) {
        let next = curr.next;
        curr.next = prev;
        prev = curr;
        curr = next;
    }
    return prev;
}
""",
        "TreeNode": """
function invertTree(root) {
    if (!root) return null;
    [root.left, root.right] = [root.right, root.left];
    invertTree(root.left);
    invertTree(root.right);
    return root;
}
""",
        "GraphNode": """
function cloneGraph(node) {
    if (!node) return null;
    const map = new Map();
    function dfs(n) {
        if (map.has(n.val)) return map.get(n.val);
        const clone = new GraphNode(n.val);
        map.set(n.val, clone);
        for (const nb of n.neighbors) clone.neighbors.push(dfs(nb));
        return clone;
    }
    return dfs(node);
}
""",
    },
    "go": {
        "ListNode": """
func reverseList(head *ListNode) *ListNode {
    var prev *ListNode
    curr := head
    for curr != nil {
        next := curr.Next
        curr.Next = prev
        prev = curr
        curr = next
    }
    return prev
}
""",
        "TreeNode": """
func invertTree(root *TreeNode) *TreeNode {
    if root == nil {
        return nil
    }
    root.Left, root.Right = root.Right, root.Left
    invertTree(root.Left)
    invertTree(root.Right)
    return root
}
""",
        "GraphNode": """
func cloneGraph(node *GraphNode) *GraphNode {
    if node == nil {
        return nil
    }
    mapping := map[int]*GraphNode{}
    var dfs func(*GraphNode) *GraphNode
    dfs = func(n *GraphNode) *GraphNode {
        if c, ok := mapping[n.Val]; ok {
            return c
        }
        clone := &GraphNode{Val: n.Val}
        mapping[n.Val] = clone
        for _, nb := range n.Neighbors {
            clone.Neighbors = append(clone.Neighbors, dfs(nb))
        }
        return clone
    }
    return dfs(node)
}
""",
    },
    "java": {
        "ListNode": """
public ListNode reverseList(ListNode head) {
    ListNode prev = null, curr = head;
    while (curr != null) {
        ListNode next = curr.next;
        curr.next = prev;
        prev = curr;
        curr = next;
    }
    return prev;
}
""",
        "TreeNode": """
public TreeNode invertTree(TreeNode root) {
    if (root == null) return null;
    TreeNode tmp = root.left;
    root.left = root.right;
    root.right = tmp;
    invertTree(root.left);
    invertTree(root.right);
    return root;
}
""",
        "GraphNode": """
public GraphNode cloneGraph(GraphNode node) {
    if (node == null) return null;
    Map<Integer, GraphNode> map = new HashMap<>();
    return dfs(node, map);
}
private GraphNode dfs(GraphNode node, Map<Integer, GraphNode> map) {
    if (map.containsKey(node.val)) return map.get(node.val);
    GraphNode clone = new GraphNode(node.val);
    map.put(node.val, clone);
    for (GraphNode nb : node.neighbors) clone.neighbors.add(dfs(nb, map));
    return clone;
}
""",
    },
}

_TEST_CASES = {
    "ListNode": {
        "func_name": {
            "python": "reverse_list",
            "javascript": "reverseList",
            "go": "reverseList",
            "java": "reverseList",
        },
        "cases": [
            {"input": {"head": [1, 2, 3, 4, 5]}, "expected": [5, 4, 3, 2, 1]},
            {"input": {"head": [1, 2]}, "expected": [2, 1]},
            {"input": {"head": []}, "expected": []},
            {"input": {"head": [42]}, "expected": [42]},
        ],
    },
    "TreeNode": {
        "func_name": {
            "python": "invert_tree",
            "javascript": "invertTree",
            "go": "invertTree",
            "java": "invertTree",
        },
        "cases": [
            {"input": {"root": [4, 2, 7, 1, 3, 6, 9]}, "expected": [4, 7, 2, 9, 6, 3, 1]},
            {"input": {"root": [2, 1, 3]}, "expected": [2, 3, 1]},
            {"input": {"root": []}, "expected": []},
            {"input": {"root": [1]}, "expected": [1]},
        ],
    },
    "GraphNode": {
        "func_name": {
            "python": "clone_graph",
            "javascript": "cloneGraph",
            "go": "cloneGraph",
            "java": "cloneGraph",
        },
        "cases": [
            {"input": {"node": [[2, 4], [1, 3], [2, 4], [1, 3]]}, "expected": [[2, 4], [1, 3], [2, 4], [1, 3]]},
            {"input": {"node": [[2], [1]]}, "expected": [[2], [1]]},
            {"input": {"node": []}, "expected": []},
        ],
    },
}

_RUNNERS = {
    "python": _run_python,
    "javascript": _run_javascript,
    "go": _run_go,
    "java": _run_java,
}


# ---------------------------------------------------------------------------
# Parametrized tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("type_name", ["ListNode", "TreeNode", "GraphNode"])
@pytest.mark.parametrize("language", ["python", "javascript", "go", "java"])
def test_round_trip(type_name: str, language: str) -> None:
    starter_code = _PYTHON_STARTERS[type_name]
    param_types = parse_python_param_types(starter_code)

    # Adjust param key for GraphNode (param name is "node" not type-name)
    tc_info = _TEST_CASES[type_name]
    func_name = tc_info["func_name"][language]
    test_cases = tc_info["cases"]

    solution = _SOLUTIONS[language][type_name]

    harness = build(language, solution, test_cases, func_name, param_types)

    runner = _RUNNERS[language]
    results = runner(harness)
    _assert_all_passed(results)


# ---------------------------------------------------------------------------
# Specific bug-fix tests
# ---------------------------------------------------------------------------

def test_extract_func_name_skips_init() -> None:
    """extract_func_name should return the top-level function, not __init__."""
    from app.harnesses.python import extract_func_name

    starter_code = {
        "python": """
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def reverse_list(head):
    pass
"""
    }
    assert extract_func_name(starter_code) == "reverse_list"


def test_extract_func_name_simple() -> None:
    from app.harnesses.python import extract_func_name

    starter = {"python": "def two_sum(nums, target):\n    pass\n"}
    assert extract_func_name(starter) == "two_sum"


def test_parse_python_param_types_listnode() -> None:
    from app.harnesses.python import parse_python_param_types

    code = """
from typing import Optional
class ListNode:
    pass
def reverse_list(head: Optional[ListNode]) -> Optional[ListNode]:
    pass
"""
    result = parse_python_param_types(code)
    assert result == {"head": "ListNode", "__return__": "ListNode"}


def test_parse_python_param_types_treenode() -> None:
    from app.harnesses.python import parse_python_param_types

    code = """
from typing import Optional
class TreeNode:
    pass
def invert_tree(root: Optional[TreeNode]) -> Optional[TreeNode]:
    pass
"""
    result = parse_python_param_types(code)
    assert result == {"root": "TreeNode", "__return__": "TreeNode"}


def test_parse_python_param_types_no_custom() -> None:
    from app.harnesses.python import parse_python_param_types

    code = "def two_sum(nums: list, target: int) -> list:\n    pass\n"
    result = parse_python_param_types(code)
    assert result == {}


def test_parse_python_param_types_unknown_type_raises() -> None:
    from app.harnesses.python import parse_python_param_types

    code = """
def solve(node: Trie) -> Trie:
    pass
"""
    with pytest.raises(ValueError, match="Unsupported custom type 'Trie'"):
        parse_python_param_types(code)


def test_get_param_types_unknown_raises() -> None:

    starter = {
        "python": """
def solve(node: Trie) -> int:
    pass
"""
    }
    with pytest.raises(ValueError, match="Unsupported custom type 'Trie'"):
        get_param_types(starter)
