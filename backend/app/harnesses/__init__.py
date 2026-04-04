import re

from .golang import build_test_harness as _go_build
from .golang import extract_func_name as _go_extract
from .java import build_test_harness as _java_build
from .java import extract_func_name as _java_extract
from .javascript import build_test_harness as _js_build
from .javascript import extract_func_name as _js_extract
from .python import build_test_harness as _python_build
from .python import extract_func_name as _python_extract

_FUNC_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

_BUILDERS = {
    "python": _python_build,
    "javascript": _js_build,
    "go": _go_build,
    "java": _java_build,
}

_EXTRACTORS = {
    "python": _python_extract,
    "javascript": _js_extract,
    "go": _go_extract,
    "java": _java_extract,
}


def build(language: str, user_code: str, test_cases: list, func_name: str) -> str:
    if not _FUNC_NAME_RE.match(func_name):
        raise ValueError(f"Invalid function name: {func_name}")
    builder = _BUILDERS.get(language)
    if builder is None:
        raise ValueError(f"Unsupported language: {language}")
    return builder(user_code, test_cases, func_name)


def extract_func_name(language: str, starter_code: dict) -> str | None:
    extractor = _EXTRACTORS.get(language)
    if extractor is None:
        raise ValueError(f"Unsupported language: {language}")
    return extractor(starter_code)
