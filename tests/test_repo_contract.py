from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepoContractTest(unittest.TestCase):
    def test_verifier_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, "scripts/verify_repo.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("REPO_CONTRACT_PASS", proc.stdout)

    def test_workflow_uses_canonical_dev_check(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("tools/dev/check", workflow)

    def test_local_docs_install_dev_requirements_before_canonical_check(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

        for document in (readme, contributing):
            self.assertIn("requirements-dev.txt", document)
            self.assertIn("tools/dev/check", document)

    def test_workflow_installs_pinned_dev_requirements(self) -> None:
        requirements = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertEqual(
            requirements.splitlines(),
            ["lark==1.3.1", "hypothesis==6.168.0"],
        )
        self.assertIn("python -m pip install -r requirements-dev.txt", workflow)
        self.assertTrue(
            (ROOT / "tests/test_resolution_boundary_properties.py").is_file()
        )
        self.assertTrue(
            (ROOT / "tests/test_navigation_boundary_properties.py").is_file()
        )

    def test_sonar_frontmatter_carries_high_value_negative_trigger_boundaries(self) -> None:
        skill = (ROOT / ".agents/skills/sonar/SKILL.md").read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1]

        self.assertIn("Do not use when current-conversation context is sufficient", frontmatter)
        self.assertIn("exact historical locator is already known", frontmatter)
        self.assertIn("only current authoritative state is needed", frontmatter)

    def test_sonar_openai_metadata_enables_implicit_invocation_explicitly(self) -> None:
        metadata = (
            ROOT / ".agents/skills/sonar/agents/openai.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn('display_name: "Sonar"', metadata)
        self.assertIn("allow_implicit_invocation: true", metadata)

    def test_sonar_skill_has_narrow_discovery_trigger_contract(self) -> None:
        skill = (ROOT / ".agents/skills/sonar/SKILL.md").read_text(encoding="utf-8")
        parts = skill.split("---", 2)
        self.assertEqual(len(parts), 3)

        frontmatter = parts[1]
        description = next(
            line.removeprefix("description: ").strip()
            for line in frontmatter.splitlines()
            if line.startswith("description: ")
        )

        self.assertTrue(description.startswith("Use when "))
        self.assertNotIn("personal_context.search", description)
        self.assertNotIn("provenance", description.lower())
        self.assertIn("## Trigger contract", skill)
        self.assertIn("TRIGGER when", skill)
        self.assertIn("DO_NOT_TRIGGER when", skill)
        self.assertIn("DISCOVERY != AUTO_TRIGGER", skill)

    def test_sonar_skill_uses_structural_probe_slots_not_llm_arithmetic(self) -> None:
        skill = (ROOT / ".agents/skills/sonar/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("## Probe slots", skill)
        self.assertIn("PROBE_SLOTS", skill)
        self.assertIn("LIGHT_LITERAL", skill)
        self.assertIn("LIGHT_FUNCTIONAL", skill)
        self.assertIn("LIGHT_RELATIONAL", skill)
        self.assertIn("FULL_EXTRA", skill)
        self.assertIn("UNUSED -> USED", skill)
        self.assertIn("LOCKED -> UNUSED -> USED", skill)
        self.assertNotIn("budget remains", skill)
        self.assertNotIn("budget exhausted", skill)
        self.assertNotIn("decrement", skill.lower())

    def test_sonar_skill_trace_preserves_correlation_identity(self) -> None:
        skill = (ROOT / ".agents/skills/sonar/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("correlation_id", skill)
        self.assertIn("GROUP <correlation_id>", skill)
        self.assertIn("at least two distinct correlation groups", skill)

    def test_sonar_skill_must_not_is_post_retrieval_exclusion_control(self) -> None:
        skill = (ROOT / ".agents/skills/sonar/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("MUST_NOT is post-retrieval exclusion metadata", skill)
        self.assertIn("Never render MUST_NOT text into personal_context.search", skill)
        self.assertIn("excluded group does not produce a Receipt", skill)
        self.assertIn("EXCLUDE GROUP <correlation_id> REASON MUST_NOT_MATCH", skill)

    def test_readme_preserves_retrieval_boundary(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("search miss != historical absence", readme)
        self.assertIn("historical evidence != current authority", readme)


if __name__ == "__main__":
    unittest.main()
