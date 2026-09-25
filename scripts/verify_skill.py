#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re
import sys
from urllib.parse import unquote

SPEC_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
}

SECRET_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}\b")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
)

MACHINE_PATH_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])/(?:Users|home)/[^/\s]+/"),
    re.compile(r"\b[A-Za-z]:\\Users\\[^\\\s]+\\"),
)

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str


def _error(code: str, message: str) -> Finding:
    return Finding("ERROR", code, message)


def _warning(code: str, message: str) -> Finding:
    return Finding("WARNING", code, message)


def _strip_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _split_frontmatter(text: str) -> tuple[list[str], str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], "\n".join(lines[index + 1 :]).strip()

    return None


def _parse_frontmatter(lines: list[str]) -> tuple[dict[str, str], list[Finding]]:
    values: dict[str, str] = {}
    findings: list[Finding] = []
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            index += 1
            continue

        if raw_line[:1].isspace():
            findings.append(
                _error("frontmatter-indent", f"unexpected indented top-level YAML at line {index + 2}")
            )
            index += 1
            continue

        match = re.match(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$", raw_line)
        if not match:
            findings.append(
                _error("frontmatter-syntax", f"unsupported frontmatter syntax at line {index + 2}")
            )
            index += 1
            continue

        key = match.group(1)
        value = (match.group(2) or "").strip()

        if key in values:
            findings.append(_error("frontmatter-duplicate", f"duplicate frontmatter field: {key}"))

        if value in {">", ">-", "|", "|-"}:
            folded = value.startswith(">")
            block: list[str] = []
            index += 1
            while index < len(lines):
                child = lines[index]
                if child and not child[:1].isspace():
                    index -= 1
                    break
                block.append(child.strip())
                index += 1
            value = (" " if folded else "\n").join(part for part in block if part)
        elif value == "" and key == "metadata":
            nested: list[str] = []
            index += 1
            while index < len(lines):
                child = lines[index]
                if child and not child[:1].isspace():
                    index -= 1
                    break
                if child.strip():
                    nested.append(child.strip())
                index += 1
            value = "\n".join(nested)

        values[key] = _strip_scalar(value)
        index += 1

    for key in sorted(set(values) - SPEC_FIELDS):
        findings.append(_error("frontmatter-field", f"non-spec frontmatter field: {key}"))

    return values, findings


def _relative_links(root: Path, skill_md: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    root_resolved = root.resolve()

    for raw_target in MARKDOWN_LINK.findall(text):
        target = raw_target.strip().strip("<>")
        if not target or target.startswith(("#", "http://", "https://", "mailto:", "data:")):
            continue

        if " " in target:
            target = target.split(" ", 1)[0]

        target = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not target:
            continue

        if target.startswith("/"):
            findings.append(_warning("absolute-link", f"absolute file link is not portable: {target}"))
            continue

        resolved = (skill_md.parent / target).resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError:
            findings.append(_error("link-escape", f"relative link escapes skill root: {target}"))
            continue

        if not resolved.exists():
            findings.append(_error("broken-link", f"missing relative link target: {target}"))

    return findings


def _scan_content(root: Path) -> list[Finding]:
    findings: list[Finding] = []

    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.stat().st_size > 1_000_000:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        rel = path.relative_to(root)

        for name, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(_error("secret-pattern", f"{rel}: looks like embedded {name}"))

        for pattern in MACHINE_PATH_PATTERNS:
            if pattern.search(text):
                findings.append(
                    _warning("machine-path", f"{rel}: contains a machine-specific user path")
                )
                break

    return findings


def validate_skill(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    root = root.resolve()

    if not root.is_dir():
        return [_error("missing-root", f"skill directory does not exist: {root}")]

    files = [path for path in root.rglob("*") if path.is_file()]

    if len(files) > 500:
        findings.append(
            _error("file-count", f"skill has {len(files)} files; OpenAI upload limit is 500")
        )

    total_size = 0
    for path in files:
        size = path.stat().st_size
        total_size += size
        if size > 25 * 1024 * 1024:
            findings.append(
                _error(
                    "file-size",
                    f"{path.relative_to(root)} is {size} bytes; OpenAI uncompressed-file limit is 25 MB",
                )
            )

    if total_size > 50 * 1024 * 1024:
        findings.append(
            _warning(
                "bundle-size",
                "uncompressed skill size exceeds 50 MB; verify packaged zip stays within OpenAI's 50 MB upload limit",
            )
        )

    candidates = [path for path in files if path.name.lower() == "skill.md"]
    if len(candidates) != 1:
        findings.append(
            _error(
                "skill-md-count",
                f"expected exactly one case-insensitive SKILL.md, found {len(candidates)}",
            )
        )
        return findings + _scan_content(root)

    skill_md = candidates[0]
    if skill_md.name != "SKILL.md":
        findings.append(
            _error("skill-md-case", f"Agent Skills canonical filename is SKILL.md, found {skill_md.name}")
        )

    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        findings.append(_error("skill-md-encoding", "SKILL.md must be UTF-8 text"))
        return findings + _scan_content(root)

    split = _split_frontmatter(text)
    if split is None:
        findings.append(
            _error("frontmatter", "SKILL.md must start with YAML frontmatter delimited by ---")
        )
        return findings + _scan_content(root)

    frontmatter_lines, body = split
    values, frontmatter_findings = _parse_frontmatter(frontmatter_lines)
    findings.extend(frontmatter_findings)

    name = values.get("name", "").strip()
    description = values.get("description", "").strip()
    compatibility = values.get("compatibility", "").strip()

    if not name:
        findings.append(_error("name-missing", "frontmatter name is required"))
    else:
        if len(name) > 64:
            findings.append(_error("name-length", "name exceeds Agent Skills 64-character limit"))
        if not NAME_RE.fullmatch(name):
            findings.append(
                _error(
                    "name-format",
                    "name must use lowercase ASCII letters, digits, and single hyphens only",
                )
            )
        if name != root.name:
            findings.append(
                _error("name-directory", f"name {name!r} must match parent directory {root.name!r}")
            )

    if not description:
        findings.append(_error("description-missing", "frontmatter description is required"))
    else:
        if len(description) > 1024:
            findings.append(
                _error("description-length", "description exceeds Agent Skills 1024-character limit")
            )
        if len(description) > 500:
            findings.append(
                _warning(
                    "description-budget",
                    "description exceeds the project 500-character discovery budget",
                )
            )
        if not description.startswith("Use when "):
            findings.append(
                _warning(
                    "description-trigger",
                    'project discovery policy expects description to start with "Use when "',
                )
            )

    if compatibility and len(compatibility) > 500:
        findings.append(
            _error("compatibility-length", "compatibility exceeds Agent Skills 500-character limit")
        )

    if "allowed-tools" in values:
        findings.append(
            _warning(
                "allowed-tools-experimental",
                "allowed-tools is experimental and support varies across skill clients",
            )
        )

    if not body:
        findings.append(_error("body-empty", "SKILL.md must contain instructions after frontmatter"))
    else:
        body_lines = body.splitlines()
        if len(body_lines) > 500:
            findings.append(
                _warning("body-lines", "SKILL.md body exceeds the Agent Skills 500-line recommendation")
            )
        approx_tokens = max(1, len(body.encode("utf-8")) // 4)
        if approx_tokens > 5000:
            findings.append(
                _warning(
                    "body-token-budget",
                    f"SKILL.md body is roughly {approx_tokens} tokens; recommended budget is under 5000",
                )
            )

        fences = sum(1 for line in body_lines if line.lstrip().startswith("```"))
        if fences % 2:
            findings.append(_error("code-fence", "SKILL.md has an unclosed triple-backtick fence"))

    findings.extend(_relative_links(root, skill_md, text))
    findings.extend(_scan_content(root))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate one Agent Skill directory.")
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat project-policy warnings as failures",
    )
    args = parser.parse_args(argv)

    findings = validate_skill(args.path)
    for finding in findings:
        print(f"{finding.severity} {finding.code}: {finding.message}")

    errors = [finding for finding in findings if finding.severity == "ERROR"]
    warnings = [finding for finding in findings if finding.severity == "WARNING"]

    if errors or (args.strict and warnings):
        print(
            f"SKILL_VALIDATE_FAIL errors={len(errors)} warnings={len(warnings)}",
            file=sys.stderr,
        )
        return 1

    print(f"SKILL_VALIDATE_PASS warnings={len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
