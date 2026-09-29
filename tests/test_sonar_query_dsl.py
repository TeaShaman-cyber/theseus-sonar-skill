from pathlib import Path
import unittest

from scripts.sonar_query import parse_probe, render_personal_context_query


ROOT = Path(__file__).resolve().parents[1]


class SonarQueryDslTest(unittest.TestCase):
    def test_functional_probe_parses_and_renders_bounded_query(self) -> None:
        probe = parse_probe(
            """PROBE FUNCTIONAL
TARGET "Library of Congress authority-search episode"
MUST "keyword discovery -> useful catalog records -> standardized subject headings"
SHOULD "controlled vocabulary and authority relations"
MUST_NOT "generic library recommendations"
TIME "2026-09-19"
LIMIT 5
"""
        )

        self.assertEqual(probe.mode, "FUNCTIONAL")
        self.assertEqual(probe.limit, 5)
        self.assertEqual(
            probe.must,
            ("keyword discovery -> useful catalog records -> standardized subject headings",),
        )

        rendered = render_personal_context_query(probe)

        self.assertIn("Library of Congress authority-search episode", rendered)
        self.assertIn("Require:", rendered)
        self.assertIn("Prefer:", rendered)
        self.assertIn("Exclude:", rendered)
        self.assertIn("2026-09-19", rendered)
        self.assertIn("at most 5", rendered)
        self.assertIn("process or function", rendered)

    def test_literal_probe_keeps_exact_anchor_instruction(self) -> None:
        probe = parse_probe(
            """PROBE LITERAL
TARGET "fractal cucumbers"
MUST "фрактальные огурцы"
LIMIT 3
"""
        )

        rendered = render_personal_context_query(probe)

        self.assertIn("exact names or phrases", rendered)
        self.assertIn("фрактальные огурцы", rendered)

    def test_unknown_mode_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported probe mode"):
            parse_probe(
                """PROBE MAGIC
TARGET "anything"
LIMIT 3
"""
            )

    def test_missing_target_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "TARGET is required"):
            parse_probe(
                """PROBE SEMANTIC
MUST "bounded historical clue"
LIMIT 3
"""
            )

    def test_limit_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "LIMIT must be between 1 and 10"):
            parse_probe(
                """PROBE RELATIONAL
TARGET "authority relation episode"
LIMIT 50
"""
            )

    def test_documented_lark_grammar_covers_light_sonar_modes(self) -> None:
        grammar = (ROOT / "sonar" / "sonar_query.lark").read_text(encoding="utf-8")

        for mode in ("LITERAL", "SEMANTIC", "FUNCTIONAL", "RELATIONAL"):
            self.assertIn(mode, grammar)

        for clause in ("TARGET", "MUST", "SHOULD", "MUST_NOT", "TIME", "LIMIT"):
            self.assertIn(clause, grammar)


if __name__ == "__main__":
    unittest.main()
