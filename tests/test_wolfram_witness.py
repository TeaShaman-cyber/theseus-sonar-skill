import json
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class WolframWitnessTest(unittest.TestCase):
    def test_decodes_verified_json_and_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            fake = tmp / "mcporter"
            fake.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' "
                "'Out[1]= \"{\\\"state_count\\\":16384,"
                "\\\"unsafe_ready\\\":0,\\\"probe_at_zero\\\":0,"
                "\\\"pass\\\":true}\"'\n",
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

            self.assertEqual(proc.returncode, 0, proc.stderr)
            receipt = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema"], "theseus.sonar-wolfram-witness.v1")
            self.assertEqual(receipt["status"], "VERIFIED")
            self.assertEqual(len(receipt["witness_sha256"]), 64)
            self.assertEqual(receipt["payload"]["state_count"], 16384)
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


if __name__ == "__main__":
    unittest.main()
