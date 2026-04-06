"""Declarative registry of test fixtures for the integration harness matrix.

Adding a new case: append a ProblemFixture to FIXTURES. Each entry
auto-fans out across all four languages via the parametrized test in
test_harness_matrix.py. Solution sources must be known-good - the test
asserts status == "Accepted" and all test cases pass.
"""
from dataclasses import dataclass


@dataclass
class ProblemFixture:
    slug: str                        # unique id, used for test IDs (not DB)
    description: str                 # one-liner for assertion messages
    starter_code: dict[str, str]     # {lang: starter source} - drives func_name + param_types
    test_cases: list[dict]           # [{"input": {...}, "expected": ...}, ...]
    solutions: dict[str, str]        # {lang: known-good solution source}


# ---------- Fixture: primitives (int, int) -> int ----------

ADD_TWO_INTS = ProblemFixture(
    slug="add-two-ints",
    description="primitives in, primitive out",
    starter_code={
        "python": (
            "def add(a: int, b: int) -> int:\n"
            "    pass\n"
        ),
        "javascript": (
            "function add(a, b) {\n"
            "}\n"
        ),
        "go": (
            "func add(a int, b int) int {\n"
            "    return 0\n"
            "}\n"
        ),
        "java": (
            "public int add(int a, int b) {\n"
            "    return 0;\n"
            "}\n"
        ),
    },
    test_cases=[
        {"input": {"a": 1, "b": 2}, "expected": 3},
        {"input": {"a": -5, "b": 5}, "expected": 0},
        {"input": {"a": 1000, "b": 2000}, "expected": 3000},
    ],
    solutions={
        "python": (
            "def add(a, b):\n"
            "    return a + b\n"
        ),
        "javascript": (
            "function add(a, b) {\n"
            "    return a + b;\n"
            "}\n"
        ),
        "go": (
            "func add(a int, b int) int {\n"
            "    return a + b\n"
            "}\n"
        ),
        "java": (
            "public int add(int a, int b) {\n"
            "    return a + b;\n"
            "}\n"
        ),
    },
)


# ---------- Fixture: list[int] -> list[int] ----------

REVERSE_ARRAY = ProblemFixture(
    slug="reverse-array",
    description="list of ints in, list of ints out",
    starter_code={
        "python": (
            "def reverse_list(nums: list[int]) -> list[int]:\n"
            "    pass\n"
        ),
        "javascript": (
            "function reverse_list(nums) {\n"
            "}\n"
        ),
        "go": (
            "func reverse_list(nums []int) []int {\n"
            "    return nil\n"
            "}\n"
        ),
        "java": (
            "public int[] reverse_list(int[] nums) {\n"
            "    return new int[0];\n"
            "}\n"
        ),
    },
    test_cases=[
        {"input": {"nums": [1, 2, 3, 4, 5]}, "expected": [5, 4, 3, 2, 1]},
        {"input": {"nums": []}, "expected": []},
        {"input": {"nums": [42]}, "expected": [42]},
    ],
    solutions={
        "python": (
            "def reverse_list(nums):\n"
            "    return list(reversed(nums))\n"
        ),
        "javascript": (
            "function reverse_list(nums) {\n"
            "    return nums.slice().reverse();\n"
            "}\n"
        ),
        "go": (
            "func reverse_list(nums []int) []int {\n"
            "    out := make([]int, len(nums))\n"
            "    for i, v := range nums {\n"
            "        out[len(nums)-1-i] = v\n"
            "    }\n"
            "    return out\n"
            "}\n"
        ),
        "java": (
            "public int[] reverse_list(int[] nums) {\n"
            "    int[] out = new int[nums.length];\n"
            "    for (int i = 0; i < nums.length; i++) {\n"
            "        out[nums.length - 1 - i] = nums[i];\n"
            "    }\n"
            "    return out;\n"
            "}\n"
        ),
    },
)


# ---------- Fixture: str -> bool ----------

IS_PALINDROME = ProblemFixture(
    slug="is-palindrome",
    description="string in, bool out",
    starter_code={
        "python": (
            "def is_palindrome(s: str) -> bool:\n"
            "    pass\n"
        ),
        "javascript": (
            "function is_palindrome(s) {\n"
            "}\n"
        ),
        "go": (
            "func is_palindrome(s string) bool {\n"
            "    return false\n"
            "}\n"
        ),
        "java": (
            "public boolean is_palindrome(String s) {\n"
            "    return false;\n"
            "}\n"
        ),
    },
    test_cases=[
        {"input": {"s": "racecar"}, "expected": True},
        {"input": {"s": "hello"}, "expected": False},
        {"input": {"s": ""}, "expected": True},
        {"input": {"s": "a"}, "expected": True},
    ],
    solutions={
        "python": (
            "def is_palindrome(s):\n"
            "    return s == s[::-1]\n"
        ),
        "javascript": (
            "function is_palindrome(s) {\n"
            "    return s === s.split('').reverse().join('');\n"
            "}\n"
        ),
        "go": (
            "func is_palindrome(s string) bool {\n"
            "    n := len(s)\n"
            "    for i := 0; i < n/2; i++ {\n"
            "        if s[i] != s[n-1-i] {\n"
            "            return false\n"
            "        }\n"
            "    }\n"
            "    return true\n"
            "}\n"
        ),
        "java": (
            "public boolean is_palindrome(String s) {\n"
            "    int n = s.length();\n"
            "    for (int i = 0; i < n / 2; i++) {\n"
            "        if (s.charAt(i) != s.charAt(n - 1 - i)) return false;\n"
            "    }\n"
            "    return true;\n"
            "}\n"
        ),
    },
)


# ---------- Fixture: ListNode -> ListNode ----------

REVERSE_LINKED_LIST = ProblemFixture(
    slug="reverse-linked-list",
    description="ListNode in, ListNode out",
    starter_code={
        "python": (
            "from typing import Optional\n"
            "\n"
            "class ListNode:\n"
            "    def __init__(self, val=0, next=None):\n"
            "        self.val = val\n"
            "        self.next = next\n"
            "\n"
            "def reverse_list(head: Optional[ListNode]) -> Optional[ListNode]:\n"
            "    pass\n"
        ),
        "javascript": (
            "class ListNode {\n"
            "    constructor(val = 0, next = null) {\n"
            "        this.val = val;\n"
            "        this.next = next;\n"
            "    }\n"
            "}\n"
            "\n"
            "function reverse_list(head) {\n"
            "}\n"
        ),
        "go": (
            "type ListNode struct {\n"
            "    Val  int\n"
            "    Next *ListNode\n"
            "}\n"
            "\n"
            "func reverse_list(head *ListNode) *ListNode {\n"
            "    return nil\n"
            "}\n"
        ),
        "java": (
            "public ListNode reverse_list(ListNode head) {\n"
            "    return null;\n"
            "}\n"
        ),
    },
    test_cases=[
        {"input": {"head": [1, 2, 3, 4, 5]}, "expected": [5, 4, 3, 2, 1]},
        {"input": {"head": [1, 2]}, "expected": [2, 1]},
        {"input": {"head": []}, "expected": []},
        {"input": {"head": [42]}, "expected": [42]},
    ],
    solutions={
        "python": (
            "def reverse_list(head):\n"
            "    prev = None\n"
            "    while head:\n"
            "        nxt = head.next\n"
            "        head.next = prev\n"
            "        prev = head\n"
            "        head = nxt\n"
            "    return prev\n"
        ),
        "javascript": (
            "function reverse_list(head) {\n"
            "    let prev = null;\n"
            "    while (head) {\n"
            "        const nxt = head.next;\n"
            "        head.next = prev;\n"
            "        prev = head;\n"
            "        head = nxt;\n"
            "    }\n"
            "    return prev;\n"
            "}\n"
        ),
        "go": (
            "func reverse_list(head *ListNode) *ListNode {\n"
            "    var prev *ListNode\n"
            "    for head != nil {\n"
            "        next := head.Next\n"
            "        head.Next = prev\n"
            "        prev = head\n"
            "        head = next\n"
            "    }\n"
            "    return prev\n"
            "}\n"
        ),
        "java": (
            "public ListNode reverse_list(ListNode head) {\n"
            "    ListNode prev = null;\n"
            "    while (head != null) {\n"
            "        ListNode next = head.next;\n"
            "        head.next = prev;\n"
            "        prev = head;\n"
            "        head = next;\n"
            "    }\n"
            "    return prev;\n"
            "}\n"
        ),
    },
)


# ---------- Fixture: TreeNode -> int ----------

MAX_TREE_DEPTH = ProblemFixture(
    slug="max-tree-depth",
    description="TreeNode in, int out",
    starter_code={
        "python": (
            "from typing import Optional\n"
            "\n"
            "class TreeNode:\n"
            "    def __init__(self, val=0, left=None, right=None):\n"
            "        self.val = val\n"
            "        self.left = left\n"
            "        self.right = right\n"
            "\n"
            "def max_depth(root: Optional[TreeNode]) -> int:\n"
            "    pass\n"
        ),
        "javascript": (
            "class TreeNode {\n"
            "    constructor(val = 0, left = null, right = null) {\n"
            "        this.val = val;\n"
            "        this.left = left;\n"
            "        this.right = right;\n"
            "    }\n"
            "}\n"
            "\n"
            "function max_depth(root) {\n"
            "}\n"
        ),
        "go": (
            "type TreeNode struct {\n"
            "    Val   int\n"
            "    Left  *TreeNode\n"
            "    Right *TreeNode\n"
            "}\n"
            "\n"
            "func max_depth(root *TreeNode) int {\n"
            "    return 0\n"
            "}\n"
        ),
        "java": (
            "public int max_depth(TreeNode root) {\n"
            "    return 0;\n"
            "}\n"
        ),
    },
    test_cases=[
        {"input": {"root": [3, 9, 20, None, None, 15, 7]}, "expected": 3},
        {"input": {"root": [1, None, 2]}, "expected": 2},
        {"input": {"root": []}, "expected": 0},
        {"input": {"root": [1]}, "expected": 1},
    ],
    solutions={
        "python": (
            "def max_depth(root):\n"
            "    if root is None:\n"
            "        return 0\n"
            "    return 1 + max(max_depth(root.left), max_depth(root.right))\n"
        ),
        "javascript": (
            "function max_depth(root) {\n"
            "    if (root === null) return 0;\n"
            "    return 1 + Math.max(max_depth(root.left), max_depth(root.right));\n"
            "}\n"
        ),
        "go": (
            "func max_depth(root *TreeNode) int {\n"
            "    if root == nil {\n"
            "        return 0\n"
            "    }\n"
            "    l := max_depth(root.Left)\n"
            "    r := max_depth(root.Right)\n"
            "    if l > r {\n"
            "        return l + 1\n"
            "    }\n"
            "    return r + 1\n"
            "}\n"
        ),
        "java": (
            "public int max_depth(TreeNode root) {\n"
            "    if (root == null) return 0;\n"
            "    return 1 + Math.max(max_depth(root.left), max_depth(root.right));\n"
            "}\n"
        ),
    },
)


# ---------- Fixture: GraphNode -> int ----------

GRAPH_NODE_COUNT = ProblemFixture(
    slug="graph-node-count",
    description="GraphNode in, int out (count reachable nodes)",
    starter_code={
        "python": (
            "from typing import Optional\n"
            "\n"
            "class GraphNode:\n"
            "    def __init__(self, val=0, neighbors=None):\n"
            "        self.val = val\n"
            "        self.neighbors = neighbors if neighbors is not None else []\n"
            "\n"
            "def count_nodes(node: Optional[GraphNode]) -> int:\n"
            "    pass\n"
        ),
        "javascript": (
            "class GraphNode {\n"
            "    constructor(val = 0, neighbors = null) {\n"
            "        this.val = val;\n"
            "        this.neighbors = neighbors === null ? [] : neighbors;\n"
            "    }\n"
            "}\n"
            "\n"
            "function count_nodes(node) {\n"
            "}\n"
        ),
        "go": (
            "type GraphNode struct {\n"
            "    Val       int\n"
            "    Neighbors []*GraphNode\n"
            "}\n"
            "\n"
            "func count_nodes(node *GraphNode) int {\n"
            "    return 0\n"
            "}\n"
        ),
        "java": (
            "public int count_nodes(GraphNode node) {\n"
            "    return 0;\n"
            "}\n"
        ),
    },
    # Adjacency-list format: adj[i] = 1-indexed neighbors of node (i+1).
    # Example [[2,4],[1,3],[2,4],[1,3]] is K4-style:
    #   1 -- 2
    #   |    |
    #   4 -- 3
    test_cases=[
        {"input": {"node": [[2, 4], [1, 3], [2, 4], [1, 3]]}, "expected": 4},
        {"input": {"node": [[2], [1]]}, "expected": 2},
        {"input": {"node": [[]]}, "expected": 1},
        {"input": {"node": []}, "expected": 0},
    ],
    solutions={
        "python": (
            "def count_nodes(node):\n"
            "    if node is None:\n"
            "        return 0\n"
            "    seen = set()\n"
            "    stack = [node]\n"
            "    while stack:\n"
            "        n = stack.pop()\n"
            "        if id(n) in seen:\n"
            "            continue\n"
            "        seen.add(id(n))\n"
            "        for nb in n.neighbors:\n"
            "            stack.append(nb)\n"
            "    return len(seen)\n"
        ),
        "javascript": (
            "function count_nodes(node) {\n"
            "    if (node === null) return 0;\n"
            "    const seen = new Set();\n"
            "    const stack = [node];\n"
            "    while (stack.length) {\n"
            "        const n = stack.pop();\n"
            "        if (seen.has(n)) continue;\n"
            "        seen.add(n);\n"
            "        for (const nb of n.neighbors) stack.push(nb);\n"
            "    }\n"
            "    return seen.size;\n"
            "}\n"
        ),
        "go": (
            "func count_nodes(node *GraphNode) int {\n"
            "    if node == nil {\n"
            "        return 0\n"
            "    }\n"
            "    seen := map[*GraphNode]bool{}\n"
            "    stack := []*GraphNode{node}\n"
            "    for len(stack) > 0 {\n"
            "        n := stack[len(stack)-1]\n"
            "        stack = stack[:len(stack)-1]\n"
            "        if seen[n] {\n"
            "            continue\n"
            "        }\n"
            "        seen[n] = true\n"
            "        for _, nb := range n.Neighbors {\n"
            "            stack = append(stack, nb)\n"
            "        }\n"
            "    }\n"
            "    return len(seen)\n"
            "}\n"
        ),
        "java": (
            "public int count_nodes(GraphNode node) {\n"
            "    if (node == null) return 0;\n"
            "    java.util.Set<GraphNode> seen = new java.util.HashSet<>();\n"
            "    java.util.Deque<GraphNode> stack = new java.util.ArrayDeque<>();\n"
            "    stack.push(node);\n"
            "    while (!stack.isEmpty()) {\n"
            "        GraphNode n = stack.pop();\n"
            "        if (!seen.add(n)) continue;\n"
            "        for (GraphNode nb : n.neighbors) stack.push(nb);\n"
            "    }\n"
            "    return seen.size();\n"
            "}\n"
        ),
    },
)


FIXTURES: list[ProblemFixture] = [
    ADD_TWO_INTS,
    REVERSE_ARRAY,
    IS_PALINDROME,
    REVERSE_LINKED_LIST,
    MAX_TREE_DEPTH,
    GRAPH_NODE_COUNT,
]
