from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "verify_skill.py"
SPEC = importlib.util.spec_from_file_location("verify_skill", MODULE_PATH)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VERIFY
SPEC.loader.exec_module(VERIFY)


def write_skill(root: Path, name: str, description: str, body: str = "# Skill\\n\\nDo the thing.") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text(
        "---\\n"
        f"name: {name}\\n"
        f"description: {description}\\n"
        "---\\n\\n"
        f"{body}\\n",
        encoding="utf-8",
    )
    return root


def codes(findings):
    return {finding.code for finding in findings}


class SkillValidatorTest(unittest.TestCase):
    def test_reference_fixture_passes_strict_cli(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/verify_skill.py",
                "--strict",
                "tests/fixtures/skills/reference-good",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("SKILL_VALIDATE_PASS", proc.stdout)

    def test_missing_description_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "missing-description"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "---\\nname: missing-description\\n---\\n\\n# Body\\n",
                encoding="utf-8",
            )
            self.assertIn("description-missing", codes(VERIFY.validate_skill(root)))

    def test_name_must_match_directory_and_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = write_skill(
                Path(tmp) / "valid-dir",
                "Invalid_Name",
                "Use when testing an invalid skill name.",
            )
            result = codes(VERIFY.validate_skill(root))
            self.assertIn("name-format", result)
            self.assertIn("name-directory", result)

    def test_description_over_spec_limit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = write_skill(
                Path(tmp) / "long-description",
                "long-description",
                "Use when " + ("x" * 1020),
            )
            self.assertIn("description-length", codes(VERIFY.validate_skill(root)))

    def test_description_over_project_budget_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = write_skill(
                Path(tmp) / "wide-description",
                "wide-description",
                "Use when " + ("x" * 510),
            )
            self.assertIn("description-budget", codes(VERIFY.validate_skill(root)))

    def test_description_trigger_policy_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = write_skill(
                Path(tmp) / "weak-trigger",
                "weak-trigger",
                "Helps with historical retrieval.",
            )
            self.assertIn("description-trigger", codes(VERIFY.validate_skill(root)))

    def test_unclosed_code_fence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = write_skill(
                Path(tmp) / "broken-fence",
                "broken-fence",
                "Use when testing code-fence validation.",
                "# Skill\\n\\n```text\\nnot closed",
            )
            self.assertIn("code-fence", codes(VERIFY.validate_skill(root)))

    def test_broken_relative_link_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = write_skill(
                Path(tmp) / "broken-link",
                "broken-link",
                "Use when testing relative-link validation.",
                "# Skill\\n\\nSee [missing](references/missing.md).",
            )
            self.assertIn("broken-link", codes(VERIFY.validate_skill(root)))

    def test_external_link_does_not_require_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = write_skill(
                Path(tmp) / "external-link",
                "external-link",
                "Use when testing external-link handling.",
                "# Skill\\n\\nSee [spec](https://agentskills.io/specification).",
            )
            self.assertNotIn("broken-link", codes(VERIFY.validate_skill(root)))

    def test_machine_specific_path_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = write_skill(
                Path(tmp) / "machine-path",
                "machine-path",
                "Use when testing machine-specific path detection.",
                "# Skill\\n\\nRead /home/example/private.txt.",
            )
            self.assertIn("machine-path", codes(VERIFY.validate_skill(root)))

    def test_embedded_secret_pattern_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = write_skill(
                Path(tmp) / "secret-pattern",
                "secret-pattern",
                "Use when testing secret-pattern detection.",
                "# Skill\\n\\nToken: ghp_abcdefghijklmnopqrstuvwxyz123456",
            )
            self.assertIn("secret-pattern", codes(VERIFY.validate_skill(root)))

    def test_multiple_case_insensitive_skill_files_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = write_skill(
                Path(tmp) / "duplicate-skill",
                "duplicate-skill",
                "Use when testing duplicate manifest detection.",
            )
            (root / "skill.md").write_text("# duplicate\\n", encoding="utf-8")
            self.assertIn("skill-md-count", codes(VERIFY.validate_skill(root)))


if __name__ == "__main__":
    unittest.main()
