from .python import build_test_harness as _python_build
from .python import extract_func_name as _python_extract


def build(language: str, user_code: str, test_cases: list, func_name: str) -> str:
    if language == "python":
        return _python_build(user_code, test_cases, func_name)
    raise ValueError(f"Unsupported language: {language}")


def extract_func_name(language: str, starter_code: dict) -> str | None:
    if language == "python":
        return _python_extract(starter_code)
    raise ValueError(f"Unsupported language: {language}")
