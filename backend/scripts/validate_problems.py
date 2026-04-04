#!/usr/bin/env python3
"""Validate all coding problem solutions against their test cases.

Usage:
    python backend/scripts/validate_problems.py
    python backend/scripts/validate_problems.py --category algorithms
    python backend/scripts/validate_problems.py --language python
    python backend/scripts/validate_problems.py --category algorithms --language go
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

# Allow importing from backend/app/
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app import harnesses  # noqa: E402

# Path to the dsa-flash-cards submodule, relative to repo root
_CARDS_ROOT = _REPO_ROOT / "dsa-flash-cards"

_RUNTIMES = {
    "python": "python3",
    "javascript": "node",
    "go": "go",
    "java": "javac",
}


def _runtime_available(language: str) -> bool:
    exe = _RUNTIMES.get(language)
    if exe is None:
        return False
    return shutil.which(exe) is not None


def _run_python(code: str) -> tuple[bool, str]:
    """Write code to a temp file and run with python3. Returns (ok, output)."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout + result.stderr
    finally:
        os.unlink(tmp_path)


def _run_javascript(code: str) -> tuple[bool, str]:
    """Write code to a temp file and run with node. Returns (ok, output)."""
    with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["node", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout + result.stderr
    finally:
        os.unlink(tmp_path)


def _run_go(code: str) -> tuple[bool, str]:
    """Write code to a temp file and run with go run. Returns (ok, output)."""
    with tempfile.NamedTemporaryFile(suffix=".go", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["go", "run", tmp_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0, result.stdout + result.stderr
    finally:
        os.unlink(tmp_path)


def _run_java(code: str) -> tuple[bool, str]:
    """Write Main.java to a temp dir, compile, and run. Returns (ok, output)."""
    tmp_dir = tempfile.mkdtemp()
    java_file = os.path.join(tmp_dir, "Main.java")
    try:
        with open(java_file, "w") as f:
            f.write(code)
        compile_result = subprocess.run(
            ["javac", java_file],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if compile_result.returncode != 0:
            return False, compile_result.stdout + compile_result.stderr
        run_result = subprocess.run(
            ["java", "-cp", tmp_dir, "Main"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return run_result.returncode == 0, run_result.stdout + run_result.stderr
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


_RUNNERS = {
    "python": _run_python,
    "javascript": _run_javascript,
    "go": _run_go,
    "java": _run_java,
}


def _parse_results(output: str) -> list[dict] | None:
    """Extract JSON test results from harness output.

    Python harnesses print raw JSON directly.
    JS/Go/Java harnesses use an ===HARNESS_OUTPUT=== marker.
    """
    if "===HARNESS_OUTPUT===" in output:
        marker_idx = output.rfind("===HARNESS_OUTPUT===")
        json_text = output[marker_idx + len("===HARNESS_OUTPUT==="):].strip()
    else:
        json_text = output.strip()

    if not json_text:
        return None

    # Take only the first line if there are multiple (extra prints from user code)
    lines = [ln for ln in json_text.splitlines() if ln.strip()]
    if not lines:
        return None

    try:
        results = json.loads(lines[0])
        if isinstance(results, list):
            return results
    except json.JSONDecodeError:
        pass

    return None


def validate_problem(
    problem_file: Path,
    filter_language: str | None = None,
) -> dict:
    """Validate a single problem file. Returns a result dict."""
    try:
        data = yaml.safe_load(problem_file.read_text()) or {}
    except Exception as e:
        return {"file": str(problem_file), "error": f"YAML parse error: {e}", "languages": {}}

    if not isinstance(data, dict):
        return {"file": str(problem_file), "error": "Root is not a dict", "languages": {}}

    title = data.get("title", problem_file.stem)
    starter_code = data.get("starter_code") or {}
    solution = data.get("solution") or {}
    test_cases = data.get("test_cases") or []

    languages = set(starter_code.keys()) & set(solution.keys())
    if filter_language:
        languages = {filter_language} if filter_language in languages else set()

    lang_results = {}

    for lang in sorted(languages):
        if not _runtime_available(lang):
            lang_results[lang] = {"status": "SKIP", "reason": f"{_RUNTIMES.get(lang, lang)} not installed"}
            continue

        runner = _RUNNERS.get(lang)
        if runner is None:
            lang_results[lang] = {"status": "SKIP", "reason": f"No runner for language '{lang}'"}
            continue

        try:
            func_name = harnesses.extract_func_name(lang, starter_code)
        except ValueError as e:
            lang_results[lang] = {"status": "FAIL", "reason": str(e)}
            continue

        if not func_name:
            lang_results[lang] = {"status": "FAIL", "reason": "Could not extract function name"}
            continue

        # Dunder names (e.g. __init__) mean the extractor hit a class method
        # rather than the standalone function. The harness can't handle
        # class-based problems (custom data structures like ListNode/TreeNode)
        # so skip them with a warning instead of reporting a false failure.
        if func_name.startswith("__") and func_name.endswith("__"):
            lang_results[lang] = {
                "status": "SKIP",
                "reason": f"Class-based problem (extracted '{func_name}'); harness unsupported",
            }
            continue

        try:
            code = harnesses.build(lang, solution[lang], test_cases, func_name)
        except Exception as e:
            lang_results[lang] = {"status": "FAIL", "reason": f"Harness build error: {e}"}
            continue

        try:
            ok, output = runner(code)
        except subprocess.TimeoutExpired:
            lang_results[lang] = {"status": "FAIL", "reason": "Execution timed out"}
            continue
        except Exception as e:
            lang_results[lang] = {"status": "FAIL", "reason": f"Execution error: {e}"}
            continue

        if not ok and not output.strip():
            lang_results[lang] = {"status": "FAIL", "reason": "Process exited with error and no output"}
            continue

        results = _parse_results(output)
        if results is None:
            lang_results[lang] = {
                "status": "FAIL",
                "reason": f"Could not parse harness output: {output[:200]}",
            }
            continue

        failed = [r for r in results if not r.get("passed", False)]
        if failed:
            lang_results[lang] = {
                "status": "FAIL",
                "reason": f"{len(failed)}/{len(results)} test cases failed",
                "failures": failed[:3],
            }
        else:
            lang_results[lang] = {"status": "PASS", "count": len(results)}

    return {"file": str(problem_file), "title": title, "languages": lang_results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate coding problem solutions")
    parser.add_argument("--category", help="Only validate problems in this category")
    parser.add_argument("--language", help="Only validate this language")
    args = parser.parse_args()

    if not _CARDS_ROOT.exists():
        print(f"ERROR: dsa-flash-cards submodule not found at {_CARDS_ROOT}")
        print("Run: git submodule update --init --recursive")
        return 1

    problem_files = list(_CARDS_ROOT.rglob("problems/*.yaml")) + list(_CARDS_ROOT.rglob("problems/*.yml"))

    if args.category:
        problem_files = [
            f for f in problem_files
            if f.relative_to(_CARDS_ROOT).parts[0].replace(" ", "-") == args.category
        ]

    if not problem_files:
        print("No problem files found.")
        return 0

    problem_files = sorted(problem_files)

    total_pass = 0
    total_fail = 0
    total_skip = 0

    print(f"\nValidating {len(problem_files)} problem(s)...\n")

    for problem_file in problem_files:
        result = validate_problem(problem_file, filter_language=args.language)

        if "error" in result:
            print(f"  ERROR  {result.get('title', problem_file.stem)}: {result['error']}")
            total_fail += 1
            continue

        title = result["title"]
        lang_results = result["languages"]

        if not lang_results:
            print(f"  --     {title} (no languages to validate)")
            continue

        for lang, lang_result in sorted(lang_results.items()):
            status = lang_result["status"]
            if status == "PASS":
                count = lang_result.get("count", "?")
                print(f"  PASS   {title} [{lang}] ({count} test cases)")
                total_pass += 1
            elif status == "SKIP":
                reason = lang_result.get("reason", "")
                print(f"  SKIP   {title} [{lang}] — {reason}")
                total_skip += 1
            else:
                reason = lang_result.get("reason", "")
                print(f"  FAIL   {title} [{lang}] — {reason}")
                failures = lang_result.get("failures", [])
                for failure in failures:
                    print(f"         input={failure.get('input')} expected={failure.get('expected')} got={failure.get('actual')}")
                total_fail += 1

    print(f"\nResults: {total_pass} passed, {total_fail} failed, {total_skip} skipped\n")

    return 1 if total_fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
