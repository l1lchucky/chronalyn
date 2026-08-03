#!/usr/bin/env python3
"""Keep generated files and unfinished placeholders out of a release commit."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BAD_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
}
BAD_FILE_NAMES = {
    ".coverage",
    "release-audit.json",
    "MANIFEST.json",
    "test-results.txt",
    "compile-results.txt",
    "build-results.txt",
    "shell-results.txt",
}
UNFINISHED_MARKERS = (
    "lorem ipsum",
    "replace this placeholder",
    "unfinished draft",
)
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".txt",
    ".cff",
}


def release_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def main() -> int:
    problems: list[str] = []
    for path in release_files():
        relative = path.relative_to(ROOT)
        if relative == Path("scripts/check-release-tree.py"):
            continue
        if any(part in BAD_PATH_PARTS for part in relative.parts):
            problems.append(f"generated directory is tracked: {relative}")
        if path.name in BAD_FILE_NAMES or path.name.endswith("-results.txt"):
            problems.append(f"generated report is tracked: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for marker in UNFINISHED_MARKERS:
            if marker in text:
                problems.append(f"unfinished placeholder in {relative}: {marker!r}")
    if problems:
        print("Release-tree hygiene check failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("Release-tree hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
