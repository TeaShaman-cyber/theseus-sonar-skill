from pathlib import Path
import hashlib
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


class OpenAIPreflightContractTest(unittest.TestCase):
    def test_lock_pins_official_skill_validator_and_plugin_schema(self) -> None:
        lock = json.loads(
            (ROOT / "QA/openai-preflight.lock.json").read_text(encoding="utf-8")
        )

        skill = lock["openai_skill_validator"]
        self.assertEqual(skill["repo"], "openai/skills")
        self.assertEqual(
            skill["commit"],
            "49f948faa9258a0c61caceaf225e179651397431",
        )
        self.assertEqual(
            skill["path"],
            "skills/.system/skill-creator/scripts/quick_validate.py",
        )
        self.assertEqual(
            skill["git_blob_sha"],
            "0547b4041a5f58fa19892079a114a1df98286406",
        )

        schema = lock["agent_plugins_schema"]
        self.assertEqual(
            schema["source"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )

        for path, entry in (
            (ROOT / "third_party/openai/quick_validate.py", skill),
            (ROOT / "third_party/agent-plugins/plugin.schema.json", schema),
        ):
            data = path.read_bytes()
            self.assertEqual(
                hashlib.sha256(data).hexdigest(),
                entry["sha256"],
            )
            self.assertEqual(git_blob_sha(data), entry["git_blob_sha"])

    def test_preflight_runner_and_workflow_are_isolated(self) -> None:
        runner = (ROOT / "tools/qa/openai-preflight").read_text(encoding="utf-8")
        workflow = (
            ROOT / ".github/workflows/openai-preflight.yml"
        ).read_text(encoding="utf-8")
        requirements = (
            ROOT / "requirements/openai-preflight.txt"
        ).read_text(encoding="utf-8")

        self.assertIn('ROOT / "third_party" / "openai" / "quick_validate.py"', runner)
        self.assertIn('ROOT / "third_party" / "agent-plugins" / "plugin.schema.json"', runner)
        self.assertIn("OPENAI_PREFLIGHT_PASS", runner)
        self.assertIn("tools/qa/openai-preflight", workflow)
        self.assertIn("requirements/openai-preflight.txt", workflow)
        self.assertIn("PyYAML==6.0.3", requirements)
        self.assertIn("jsonschema==4.26.0", requirements)


if __name__ == "__main__":
    unittest.main()
