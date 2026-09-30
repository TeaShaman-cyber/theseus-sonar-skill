from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "mutation-decision-test.yml"
LOCK = ROOT / "requirements" / "ci-mutation.txt"
ENDPOINT = ROOT / "tools" / "ci" / "mutation-decision-test"
CONFIG = ROOT / "tools" / "ci" / "mutation-decision.cfg"
PROFILE_SHA = "0fa76f7aa1ccad2fb175591c9497157d8c60e481"


class MutationDecisionCiContractTest(unittest.TestCase):
    def test_workflow_pins_read_only_reusable_profile_and_scope(self) -> None:
        text = WORKFLOW.read_text()
        expected = (
            "uses: TeaShaman-cyber/marcopolo-cookbook/.github/workflows/"
            f"reusable-mutation-test.yml@{PROFILE_SHA}"
        )
        self.assertIn(expected, text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("- scripts/sonar_decision.py", text)
        self.assertIn("- tests/test_sonar_decision.py", text)
        self.assertNotIn("push:", text)
        self.assertNotIn("continue-on-error", text)
        self.assertNotIn("secrets:", text)

    def test_lock_is_hash_pinned(self) -> None:
        text = LOCK.read_text()
        self.assertIn("mutmut==3.8.0", text)
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", text)
        packages = [
            line
            for line in text.splitlines()
            if line and not line.startswith("#") and "==" in line
        ]
        self.assertEqual(len(packages), 19)
        self.assertEqual(len(hashes), 19)
        self.assertEqual(len(set(hashes)), 19)

    def test_mutmut_config_targets_decision_and_deterministic_tests_only(self) -> None:
        text = CONFIG.read_text()
        self.assertIn("only_mutate=scripts/sonar_decision.py", text)
        self.assertIn(
            "pytest_add_cli_args_test_selection=tests/test_sonar_decision.py",
            text,
        )
        self.assertIn("process_isolation=fork", text)
        self.assertIn("mutate_only_covered_lines=true", text)
        self.assertNotIn("boundary_properties", text)
        self.assertNotIn("hypothesis", text.lower())

    def test_endpoint_exports_classified_receipt(self) -> None:
        result = subprocess.run(
            ["sh", "-n", str(ENDPOINT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        text = ENDPOINT.read_text()
        self.assertIn("mutmut export-cicd-stats", text)
        self.assertIn("mutmut results", text)
        self.assertIn('"profile":"sonar_decision_boundary"', text)
        self.assertIn('"only_mutate":"scripts/sonar_decision.py"', text)
        self.assertIn('"tests":"tests/test_sonar_decision.py"', text)
        self.assertIn('classified != total', text)
        self.assertIn('"unclassified_mutants":max(total-classified,0)', text)
        self.assertIn("MUTATION_TEST_RECEIPT", text)
        self.assertIn("survivor_excerpt", text)
        self.assertIn("second_survivor_diff", text)
        self.assertIn("survivor_ids", text)
        self.assertIn("first_survivor_diff", text)
        self.assertIn('mutmut show "$first_survivor"', text)


if __name__ == "__main__":
    unittest.main()
