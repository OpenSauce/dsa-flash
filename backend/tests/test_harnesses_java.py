"""Tests for the Java test harness generation."""

import pytest

from app.harnesses import build, extract_func_name
from app.harnesses.java import build_test_harness
from app.harnesses.java import extract_func_name as java_extract


class TestExtractFuncName:
    def test_public_method(self):
        starter = {"java": "public int[] twoSum(int[] nums, int target) {\n}"}
        assert java_extract(starter) == "twoSum"

    def test_private_static_method(self):
        starter = {"java": "private static int solve(int n) {\n}"}
        assert java_extract(starter) == "solve"

    def test_no_access_modifier(self):
        starter = {"java": "int maxProfit(int[] prices) {\n}"}
        assert java_extract(starter) == "maxProfit"

    def test_boolean_return(self):
        starter = {"java": "public boolean isPalindrome(String s) {\n}"}
        assert java_extract(starter) == "isPalindrome"

    def test_generic_return(self):
        starter = {"java": "public List<Integer> getList(int[] nums) {\n}"}
        assert java_extract(starter) == "getList"

    def test_array_return(self):
        starter = {"java": "public int[] merge(int[] a, int[] b) {\n}"}
        assert java_extract(starter) == "merge"

    def test_no_match(self):
        starter = {"java": "// no method here"}
        assert java_extract(starter) is None

    def test_missing_language(self):
        starter = {"python": "def foo(): pass"}
        assert java_extract(starter) is None

    def test_dispatch(self):
        starter = {"java": "public int search(int[] arr, int target) {\n}"}
        assert extract_func_name("java", starter) == "search"


class TestBuildTestHarness:
    def test_generates_valid_java(self):
        code = "public int add(int a, int b) { return a + b; }"
        test_cases = [{"input": {"a": 1, "b": 2}, "expected": 3}]
        result = build_test_harness(code, test_cases, "add")

        assert "===HARNESS_OUTPUT===" in result
        assert "class Solution" in result
        assert "class Main" in result
        assert "public int add(int a, int b)" in result

    def test_contains_marker(self):
        code = "public int foo() { return 1; }"
        result = build_test_harness(code, [{"input": {}, "expected": 1}], "foo")
        assert "===HARNESS_OUTPUT===" in result

    def test_wraps_in_solution_class(self):
        """User code without class declaration gets wrapped in Solution."""
        code = "public int add(int a, int b) { return a + b; }"
        result = build_test_harness(code, [{"input": {"a": 1, "b": 2}, "expected": 3}], "add")
        assert "class Solution {" in result

    def test_preserves_existing_class(self):
        """User code with class declaration is used as-is."""
        code = "class Solution {\n    public int add(int a, int b) { return a + b; }\n}"
        result = build_test_harness(code, [{"input": {"a": 1, "b": 2}, "expected": 3}], "add")
        # Should not double-wrap
        assert result.count("class Solution") == 1

    def test_method_not_found_check(self):
        code = "public int other(int x) { return x; }"
        result = build_test_harness(code, [{"input": {}, "expected": 1}], "missing")
        assert "Method 'missing' not found" in result

    def test_error_handling(self):
        code = "public int boom() { throw new RuntimeException(\"kaboom\"); }"
        result = build_test_harness(
            code, [{"input": {}, "expected": 0}], "boom"
        )
        assert "catch (Exception e)" in result
        assert "ERROR:" in result

    def test_test_cases_embedded(self):
        test_cases = [
            {"input": {"nums": [2, 7, 11], "target": 9}, "expected": [0, 1]}
        ]
        result = build_test_harness(
            "public int[] f(int[] nums, int target) { return nums; }",
            test_cases, "f",
        )
        assert "parseJSON" in result

    def test_reflection_based_calling(self):
        code = "public int add(int a, int b) { return a + b; }"
        result = build_test_harness(code, [{"input": {"a": 1, "b": 2}, "expected": 3}], "add")
        assert "reflect" in result or "Method" in result
        assert "invoke" in result

    def test_wraps_non_solution_class(self):
        """User code with a different class name still gets wrapped in Solution."""
        code = "class Foo {\n    public int add(int a, int b) { return a + b; }\n}"
        result = build_test_harness(code, [{"input": {"a": 1, "b": 2}, "expected": 3}], "add")
        # Foo is NOT Solution, so it should be wrapped
        assert "class Solution {" in result

    def test_string_with_commas_in_test_cases(self):
        """parseJSON handles strings containing commas without splitting."""
        code = 'public String echo(String s) { return s; }'
        test_cases = [{"input": {"s": "a,b,c"}, "expected": "a,b,c"}]
        result = build_test_harness(code, test_cases, "echo")
        assert "a,b,c" in result
        assert "parseJSON" in result

    def test_toJSON_escapes_strings(self):
        """toJSON escapes quotes and backslashes in string values."""
        code = 'public String echo(String s) { return s; }'
        result = build_test_harness(code, [{"input": {"s": "hi"}, "expected": "hi"}], "echo")
        # Verify the escape method exists in generated code
        assert "s.replace" in result

    def test_dispatch_build(self):
        code = "public int add(int a, int b) { return a + b; }"
        test_cases = [{"input": {"a": 1, "b": 2}, "expected": 3}]
        result = build("java", code, test_cases, "add")
        assert "===HARNESS_OUTPUT===" in result


class TestFuncNameValidation:
    def test_valid_name(self):
        code = "public int f() { return 1; }"
        result = build("java", code, [{"input": {}, "expected": 1}], "f")
        assert "===HARNESS_OUTPUT===" in result

    def test_invalid_name_rejected(self):
        with pytest.raises(ValueError, match="Invalid function name"):
            build("java", "", [], "bad name!")

    def test_injection_attempt_rejected(self):
        with pytest.raises(ValueError, match="Invalid function name"):
            build("java", "", [], "f; System.exit(1); //")
