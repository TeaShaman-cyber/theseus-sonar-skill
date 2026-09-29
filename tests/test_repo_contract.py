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

    def test_readme_preserves_retrieval_boundary(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("search miss != historical absence", readme)
        self.assertIn("historical evidence != current authority", readme)


if __name__ == "__main__":
    unittest.main()
