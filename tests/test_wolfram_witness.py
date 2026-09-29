import json
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def write_success_fake_mcporter(path: pathlib.Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import json
import pathlib
import re
import sys

if "--version" in sys.argv:
    print("0.13.8")
    raise SystemExit(0)

code_arg = next(arg for arg in sys.argv if arg.startswith("code=@"))
program = pathlib.Path(code_arg[len("code=@"):]).read_text(encoding="utf-8")

def extract(name):
    match = re.search(rf'{name} = "([^"]+)";', program)
    if not match:
        raise SystemExit(3)
    return match.group(1)

payload = {
    "state_count": 16384,
    "implementation_match": True,
    "mismatch_count": 0,
    "unsafe_conflict_located": 0,
    "unsafe_drift_located": 0,
    "located_without_independent_strong": 0,
    "located_without_discriminating_strong": 0,
    "probe_at_zero": 0,
    "located_reachable": True,
    "probe_reachable": True,
    "unknown_reachable": True,
    "python_table_sha256": extract("pythonTableSHA256"),
    "decision_source_sha256": extract("decisionSourceSHA256"),
    "pass": True,
}
print("Out[1]= " + json.dumps(json.dumps(payload)))
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


class WolframWitnessTest(unittest.TestCase):
    def test_decodes_complete_verified_json_and_writes_v2_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            fake = tmp / "mcporter"
            write_success_fake_mcporter(fake)
            out = tmp / "receipt.json"

            proc = subprocess.run(
                [
                    str(ROOT / "tools/research/wolfram-witness"),
                    "--out",
                    str(out),
                    "--mcporter",
                    str(fake),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            receipt = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema"], "theseus.sonar-wolfram-witness.v2")
            self.assertEqual(receipt["status"], "VERIFIED")
            self.assertEqual(len(receipt["witness_sha256"]), 64)
            self.assertEqual(len(receipt["python_table_sha256"]), 64)
            self.assertEqual(len(receipt["decision_source_sha256"]), 64)
            self.assertTrue(receipt["payload"]["implementation_match"])
            self.assertEqual(receipt["payload"]["mismatch_count"], 0)
            self.assertEqual(receipt["transport"]["tool"], "WolframLanguageEvaluator")

    def test_transport_failure_is_degraded_not_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = pathlib.Path(tmpdir) / "receipt.json"
            proc = subprocess.run(
                [
                    str(ROOT / "tools/research/wolfram-witness"),
                    "--out",
                    str(out),
                    "--mcporter",
                    str(pathlib.Path(tmpdir) / "missing-mcporter"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 2)
            receipt = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "DEGRADED_EXTERNAL_WITNESS")
            self.assertIsNone(receipt["payload"])

    def test_partial_pass_true_payload_is_not_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            fake = tmp / "mcporter"
            fake.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' 'Out[1]= \"{\\\"pass\\\":true}\"'\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            out = tmp / "receipt.json"

            proc = subprocess.run(
                [
                    str(ROOT / "tools/research/wolfram-witness"),
                    "--out",
                    str(out),
                    "--mcporter",
                    str(fake),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 2)
            receipt = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "DEGRADED_EXTERNAL_WITNESS")

    def test_client_timeout_is_degraded_and_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            fake = tmp / "mcporter"
            fake.write_text("#!/bin/sh\nsleep 2\n", encoding="utf-8")
            fake.chmod(0o755)
            out = tmp / "receipt.json"

            proc = subprocess.run(
                [
                    str(ROOT / "tools/research/wolfram-witness"),
                    "--out",
                    str(out),
                    "--mcporter",
                    str(fake),
                    "--client-timeout",
                    "0.05",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=2,
            )

            self.assertEqual(proc.returncode, 2)
            receipt = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "DEGRADED_EXTERNAL_WITNESS")
            self.assertEqual(receipt["transport"]["returncode"], 124)

    def test_generated_wolfram_invocation_contains_python_behavior_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            captured = tmp / "captured.wl"
            fake = tmp / "mcporter"
            fake.write_text(
                "#!/bin/sh\n"
                "for arg in \"$@\"; do\n"
                "  case \"$arg\" in code=@*) path=$(printf '%s' \"$arg\" | sed 's/^code=@//'); cp \"$path\" \"" + str(captured) + "\" ;; esac\n"
                "done\n"
                "exit 1\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            out = tmp / "receipt.json"

            subprocess.run(
                [
                    str(ROOT / "tools/research/wolfram-witness"),
                    "--out",
                    str(out),
                    "--mcporter",
                    str(fake),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            wolfram = captured.read_text(encoding="utf-8")
            self.assertIn("pythonOutcomes =", wolfram)
            self.assertIn("pythonTableSHA256 =", wolfram)
            self.assertIn("implementationMatch", wolfram)
            outcomes = re_search_assignment(wolfram, "pythonOutcomes")
            self.assertEqual(len(outcomes), 16384)


def re_search_assignment(text: str, name: str) -> str:
    import re

    match = re.search(rf'{name} = "([^"]+)";', text)
    if not match:
        raise AssertionError(f"missing assignment: {name}")
    return match.group(1)


if __name__ == "__main__":
    unittest.main()
