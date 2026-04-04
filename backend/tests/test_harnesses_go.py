"""Tests for the Go test harness generation."""

from app.harnesses import build, extract_func_name
from app.harnesses.golang import build_test_harness
from app.harnesses.golang import extract_func_name as go_extract


class TestExtractFuncName:
    def test_func_declaration(self):
        starter = {"go": "func twoSum(nums []int, target int) []int {\n}"}
        assert go_extract(starter) == "twoSum"

    def test_func_no_return(self):
        starter = {"go": "func solve(input string) {\n}"}
        assert go_extract(starter) == "solve"

    def test_no_match(self):
        starter = {"go": "// no function here"}
        assert go_extract(starter) is None

    def test_missing_language(self):
        starter = {"python": "def foo(): pass"}
        assert go_extract(starter) is None

    def test_dispatch(self):
        starter = {"go": "func search(arr []int, target int) int {\n}"}
        assert extract_func_name("go", starter) == "search"


class TestBuildTestHarness:
    def test_generates_package_main(self):
        code = "func add(a, b int) int { return a + b }"
        test_cases = [{"input": {"a": 1, "b": 2}, "expected": 3}]
        result = build_test_harness(code, test_cases, "add")

        assert "package main" in result
        assert "===HARNESS_OUTPUT===" in result
        assert "func add(a, b int)" in result

    def test_contains_marker(self):
        code = "func foo() int { return 1 }"
        result = build_test_harness(code, [{"input": {}, "expected": 1}], "foo")
        assert "===HARNESS_OUTPUT===" in result

    def test_imports_present(self):
        code = "func foo() int { return 1 }"
        result = build_test_harness(code, [{"input": {}, "expected": 1}], "foo")
        assert '"encoding/json"' in result
        assert '"fmt"' in result
        assert '"reflect"' in result

    def test_missing_function_emits_error_harness(self):
        """Missing function detected at generation time, not compile time."""
        code = "// no function"
        result = build_test_harness(code, [{"input": {}, "expected": 1}], "missing")
        assert "Function 'missing' not found" in result
        assert "===HARNESS_OUTPUT===" in result
        # Should NOT reference the missing identifier (would fail to compile)
        assert "reflect.ValueOf(missing)" not in result

    def test_defer_recover_for_panics(self):
        code = "func boom() int { panic(42) }"
        result = build_test_harness(
            code, [{"input": {}, "expected": 0}], "boom"
        )
        assert "defer func()" in result
        assert "recover()" in result

    def test_test_cases_embedded_as_json(self):
        test_cases = [
            {"input": {"nums": [2, 7, 11], "target": 9}, "expected": [0, 1]}
        ]
        result = build_test_harness("func f() {}", test_cases, "f")
        assert "json.Unmarshal" in result

    def test_type_conversion_support(self):
        """Harness includes convertArg for JSON float64 -> Go int."""
        code = "func f(n int) int { return n }"
        result = build_test_harness(code, [{"input": {"n": 5}, "expected": 5}], "f")
        assert "convertArg" in result
        assert "reflect.Int" in result

    def test_arg_order_preserved(self):
        """Dict input args are passed in JSON key order, not random Go map order."""
        code = "func sub(a, b int) int { return a - b }"
        test_cases = [{"input": {"a": 10, "b": 3}, "expected": 7}]
        result = build_test_harness(code, test_cases, "sub")
        # The harness should embed ordered key names
        assert "argOrderJSON" in result
        # Keys are embedded as escaped JSON: \\"a\\"
        assert '\\"a\\"' in result
        assert '\\"b\\"' in result

    def test_dispatch_build(self):
        code = "func add(a, b int) int { return a + b }"
        test_cases = [{"input": {"a": 1, "b": 2}, "expected": 3}]
        result = build("go", code, test_cases, "add")
        assert "package main" in result
        assert "===HARNESS_OUTPUT===" in result


class TestFuncNameValidation:
    def test_valid_name(self):
        result = build("go", "func f() {}", [{"input": {}, "expected": 1}], "f")
        assert "===HARNESS_OUTPUT===" in result

    def test_invalid_name_rejected(self):
        import pytest

        with pytest.raises(ValueError, match="Invalid function name"):
            build("go", "", [], "bad name!")

    def test_injection_attempt_rejected(self):
        import pytest

        with pytest.raises(ValueError, match="Invalid function name"):
            build("go", "", [], "f; os.Exit(1); //")
