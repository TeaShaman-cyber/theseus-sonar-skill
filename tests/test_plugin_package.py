from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PluginPackageTest(unittest.TestCase):
    def test_builds_exact_skills_only_plugin_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "sonar-plugin.zip"
            proc = subprocess.run(
                [sys.executable, "tools/package-plugin", "--out", str(out)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("PLUGIN_PACKAGE_PASS", proc.stdout)

            with zipfile.ZipFile(out) as zf:
                self.assertEqual(
                    zf.namelist(),
                    [
                        "sonar/plugin.json",
                        "sonar/skills/sonar/SKILL.md",
                        "sonar/skills/sonar/agents/openai.yaml",
                    ],
                )
                manifest = json.loads(zf.read("sonar/plugin.json"))
                packaged_skill = zf.read("sonar/skills/sonar/SKILL.md").decode("utf-8")
                packaged_openai = zf.read(
                    "sonar/skills/sonar/agents/openai.yaml"
                ).decode("utf-8")

        canonical_skill = (
            ROOT / ".agents/skills/sonar/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(manifest["name"], "sonar")
        self.assertEqual(manifest["version"], "0.1.1")
        self.assertLessEqual(
            len(
                manifest["extensions"]["com.openai"]["interface"][
                    "shortDescription"
                ]
            ),
            30,
        )
        self.assertEqual(packaged_skill, canonical_skill)
        canonical_openai = (
            ROOT / ".agents/skills/sonar/agents/openai.yaml"
        ).read_text(encoding="utf-8")
        self.assertEqual(packaged_openai, canonical_openai)
        self.assertIn("allow_implicit_invocation: true", packaged_openai)

    def test_manifest_and_skill_identity_match(self) -> None:
        manifest = json.loads(
            (ROOT / "packaging/sonar/plugin.json").read_text(encoding="utf-8")
        )
        skill = (
            ROOT / ".agents/skills/sonar/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(manifest["name"], "sonar")
        self.assertIn("\nname: sonar\n", f"\n{skill.split('---', 2)[1]}\n")


if __name__ == "__main__":
    unittest.main()
