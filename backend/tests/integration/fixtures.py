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


FIXTURES: list[ProblemFixture] = [
    ADD_TWO_INTS,
]
