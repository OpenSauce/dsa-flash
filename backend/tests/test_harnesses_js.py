"""Tests for the JavaScript test harness generation."""

from app.harnesses import build, extract_func_name
from app.harnesses.javascript import build_test_harness
from app.harnesses.javascript import extract_func_name as js_extract


class TestExtractFuncName:
    def test_function_declaration(self):
        starter = {"javascript": "function twoSum(nums, target) {\n}"}
        assert js_extract(starter) == "twoSum"

    def test_const_arrow(self):
        starter = {"javascript": "const twoSum = (nums, target) => {\n}"}
        assert js_extract(starter) == "twoSum"

    def test_let_assignment(self):
        starter = {"javascript": "let solve = function(nums) {\n}"}
        assert js_extract(starter) == "solve"

    def test_no_match(self):
        starter = {"javascript": "// no function here"}
        assert js_extract(starter) is None

    def test_missing_language(self):
        starter = {"python": "def foo(): pass"}
        assert js_extract(starter) is None

    def test_dispatch(self):
        starter = {"javascript": "function search(arr, target) {\n}"}
        assert extract_func_name("javascript", starter) == "search"


class TestBuildTestHarness:
    def test_generates_valid_js(self):
        code = "function add(a, b) { return a + b; }"
        test_cases = [{"input": {"a": 1, "b": 2}, "expected": 3}]
        result = build_test_harness(code, test_cases, "add")

        assert "===HARNESS_OUTPUT===" in result
        assert "function add(a, b)" in result
        assert "JSON.parse" in result
        assert "typeof add !== 'function'" in result

    def test_contains_marker(self):
        code = "function foo() { return 1; }"
        result = build_test_harness(code, [{"input": {}, "expected": 1}], "foo")
        assert result.count("===HARNESS_OUTPUT===") == 2  # check + output

    def test_missing_function_check(self):
        code = "// no function"
        result = build_test_harness(code, [{"input": {}, "expected": 1}], "missing")
        assert "typeof missing !== 'function'" in result
        assert "Function 'missing' not found" in result

    def test_error_handling(self):
        code = "function boom() { throw new Error('kaboom'); }"
        result = build_test_harness(
            code, [{"input": {}, "expected": None}], "boom"
        )
        assert "catch (_e)" in result
        assert "ERROR:" in result

    def test_test_cases_embedded_as_json(self):
        test_cases = [
            {"input": {"nums": [2, 7, 11], "target": 9}, "expected": [0, 1]}
        ]
        result = build_test_harness("function f() {}", test_cases, "f")
        assert "JSON.parse" in result

    def test_dispatch_build(self):
        code = "function add(a, b) { return a + b; }"
        test_cases = [{"input": {"a": 1, "b": 2}, "expected": 3}]
        result = build("javascript", code, test_cases, "add")
        assert "===HARNESS_OUTPUT===" in result

    def test_single_quotes_escaped(self):
        """Test that single quotes in test cases don't break the JSON string."""
        test_cases = [{"input": {"s": "it's"}, "expected": "it's"}]
        result = build_test_harness("function f(s) { return s; }", test_cases, "f")
        assert "===HARNESS_OUTPUT===" in result


class TestFuncNameValidation:
    def test_valid_name(self):
        result = build("javascript", "function f(){}", [{"input": {}, "expected": 1}], "f")
        assert "===HARNESS_OUTPUT===" in result

    def test_invalid_name_rejected(self):
        import pytest

        with pytest.raises(ValueError, match="Invalid function name"):
            build("javascript", "", [], "bad name!")

    def test_injection_attempt_rejected(self):
        import pytest

        with pytest.raises(ValueError, match="Invalid function name"):
            build("javascript", "", [], "f; process.exit(1); //")
