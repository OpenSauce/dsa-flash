"""Canonical known-good solutions for catalog smoke tests.

Keys are catalog problem titles (matching the `title:` field in the YAML).
Adding a smoke case: pick a catalog YAML, add its title as a new outer key
with {lang: solution} inner dict, then add the title to
test_catalog_smoke.CATALOG_SLUGS.
"""

CATALOG_SOLUTIONS: dict[str, dict[str, str]] = {
    # Function names must match each language's starter_code in the catalog YAML.
    # Python uses snake_case (two_sum), JS/Go/Java use camelCase (twoSum).
    "Two Sum": {
        "python": (
            "def two_sum(nums, target):\n"
            "    seen = {}\n"
            "    for i, n in enumerate(nums):\n"
            "        if target - n in seen:\n"
            "            return [seen[target - n], i]\n"
            "        seen[n] = i\n"
            "    return []\n"
        ),
        "javascript": (
            "function twoSum(nums, target) {\n"
            "    const seen = new Map();\n"
            "    for (let i = 0; i < nums.length; i++) {\n"
            "        const complement = target - nums[i];\n"
            "        if (seen.has(complement)) return [seen.get(complement), i];\n"
            "        seen.set(nums[i], i);\n"
            "    }\n"
            "    return [];\n"
            "}\n"
        ),
        "go": (
            "func twoSum(nums []int, target int) []int {\n"
            "    seen := map[int]int{}\n"
            "    for i, n := range nums {\n"
            "        if j, ok := seen[target-n]; ok {\n"
            "            return []int{j, i}\n"
            "        }\n"
            "        seen[n] = i\n"
            "    }\n"
            "    return []int{}\n"
            "}\n"
        ),
        "java": (
            "public int[] twoSum(int[] nums, int target) {\n"
            "    java.util.Map<Integer, Integer> seen = new java.util.HashMap<>();\n"
            "    for (int i = 0; i < nums.length; i++) {\n"
            "        int complement = target - nums[i];\n"
            "        if (seen.containsKey(complement)) {\n"
            "            return new int[]{seen.get(complement), i};\n"
            "        }\n"
            "        seen.put(nums[i], i);\n"
            "    }\n"
            "    return new int[0];\n"
            "}\n"
        ),
    },
    # JS/Go/Java use camelCase maxDepth to match catalog starter_code.
    "Maximum Depth of Binary Tree": {
        "python": (
            "def max_depth(root):\n"
            "    if root is None:\n"
            "        return 0\n"
            "    return 1 + max(max_depth(root.left), max_depth(root.right))\n"
        ),
        "javascript": (
            "function maxDepth(root) {\n"
            "    if (root === null) return 0;\n"
            "    return 1 + Math.max(maxDepth(root.left), maxDepth(root.right));\n"
            "}\n"
        ),
        "go": (
            "func maxDepth(root *TreeNode) int {\n"
            "    if root == nil {\n"
            "        return 0\n"
            "    }\n"
            "    l := maxDepth(root.Left)\n"
            "    r := maxDepth(root.Right)\n"
            "    if l > r {\n"
            "        return l + 1\n"
            "    }\n"
            "    return r + 1\n"
            "}\n"
        ),
        "java": (
            "public int maxDepth(TreeNode root) {\n"
            "    if (root == null) return 0;\n"
            "    return 1 + Math.max(maxDepth(root.left), maxDepth(root.right));\n"
            "}\n"
        ),
    },
}
