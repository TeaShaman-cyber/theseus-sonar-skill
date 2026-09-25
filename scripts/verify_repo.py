#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "README.md",
    "RULES.md",
    "CONTRIBUTING.md",
    ".gitignore",
    "tools/dev/check",
    "scripts/verify_repo.py",
    "tests/test_repo_contract.py",
    ".github/workflows/ci.yml",
)

PRIVATE_EXACT = {
    ".env",
    "auth.json",
    "conversations.json",
    "chat.html",
}

PRIVATE_PARTS = {
    "private",
    ".private",
}

REQUIRED_README_MARKERS = (
    "openai/codex#48166",
    "issue #1",
    "tools/dev/check",
)

REQUIRED_RULE_MARKERS = (
    "search miss != historical absence",
    "Capability is not permission.",
    "tools/dev/check",
)


def tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in proc.stdout.splitlines() if line]


def check_required_files(errors: list[str]) -> None:
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required file: {rel}")


def check_markers(path: str, markers: tuple[str, ...], errors: list[str]) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            errors.append(f"{path}: missing contract marker: {marker}")


def check_private_paths(errors: list[str]) -> None:
    for rel in tracked_files():
        p = Path(rel)
        lowered = {part.lower() for part in p.parts}
        if p.name.lower() in PRIVATE_EXACT:
            errors.append(f"tracked private/local artifact name: {rel}")
        if lowered & PRIVATE_PARTS:
            errors.append(f"tracked private/local artifact path: {rel}")
        if p.suffix.lower() in {".sqlite", ".sqlite3"}:
            errors.append(f"tracked local search database: {rel}")


def main() -> int:
    errors: list[str] = []
    check_required_files(errors)

    if not errors:
        check_markers("README.md", REQUIRED_README_MARKERS, errors)
        check_markers("RULES.md", REQUIRED_RULE_MARKERS, errors)

    check_private_paths(errors)

    if errors:
        for error in errors:
            print(f"REPO_CONTRACT_FAIL: {error}", file=sys.stderr)
        return 1

    print("REPO_CONTRACT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
