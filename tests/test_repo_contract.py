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

    def test_readme_preserves_retrieval_boundary(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("search miss != historical absence", readme)
        self.assertIn("historical evidence != current authority", readme)


if __name__ == "__main__":
    unittest.main()
