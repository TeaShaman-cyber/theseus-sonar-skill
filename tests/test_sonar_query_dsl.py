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
        self.assertEqual(probe.must_not, ("generic library recommendations",))

        rendered = render_personal_context_query(probe)

        self.assertNotIn("Library of Congress authority-search episode", rendered)
        self.assertIn("Require:", rendered)
        self.assertIn("Prefer:", rendered)
        self.assertNotIn("generic library recommendations", rendered)
        self.assertNotIn("Exclude:", rendered)
        self.assertIn("2026-09-19", rendered)
        self.assertIn("at most 5", rendered)
        self.assertIn("process or function", rendered)

    def test_target_is_operator_metadata_not_retrieval_text(self) -> None:
        probe = parse_probe(
            """PROBE RELATIONAL
TARGET "headline attractor that must stay operator-side"
MUST "typed authority relation"
LIMIT 3
"""
        )

        rendered = render_personal_context_query(probe)

        self.assertEqual(probe.target, "headline attractor that must stay operator-side")
        self.assertNotIn(probe.target, rendered)
        self.assertIn("typed authority relation", rendered)

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
        self.assertNotIn("fractal cucumbers", rendered)

    def test_unknown_mode_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported probe mode"):
            parse_probe(
                """PROBE MAGIC
TARGET "anything"
MUST "anchor"
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

    def test_positive_retrieval_anchor_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one MUST or SHOULD"):
            parse_probe(
                """PROBE FUNCTIONAL
TARGET "operator-only label"
LIMIT 3
"""
            )

    def test_limit_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "integer between 1 and 10"):
            parse_probe(
                """PROBE RELATIONAL
TARGET "authority relation episode"
MUST "typed relation"
LIMIT 50
"""
            )

    def test_limit_spelling_matches_grammar(self) -> None:
        for value in ("03", "+3", "3 "):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_probe(
                        f"""PROBE SEMANTIC
TARGET "bounded target"
MUST "anchor"
LIMIT {value}
"""
                    )

    def test_repeated_clauses_are_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "MUST may appear at most 2 times"):
            parse_probe(
                """PROBE SEMANTIC
TARGET "bounded target"
MUST "one"
MUST "two"
MUST "three"
LIMIT 3
"""
            )

    def test_singleton_clauses_are_rejected_when_repeated(self) -> None:
        with self.assertRaisesRegex(ValueError, "TIME may appear only once"):
            parse_probe(
                """PROBE SEMANTIC
TARGET "bounded target"
MUST "anchor"
TIME "2026-09"
TIME "2026-08"
LIMIT 3
"""
            )

    def test_clause_order_matches_grammar(self) -> None:
        with self.assertRaisesRegex(ValueError, "canonical order"):
            parse_probe(
                """PROBE RELATIONAL
TARGET "authority relation episode"
SHOULD "typed relation"
MUST "exact anchor"
LIMIT 3
"""
            )

    def test_whitespace_language_matches_grammar(self) -> None:
        invalid = (
            """PROBE SEMANTIC

TARGET "bounded target"
MUST "anchor"
LIMIT 3
""",
            """PROBE   SEMANTIC
TARGET "bounded target"
MUST "anchor"
LIMIT 3
""",
            """ PROBE SEMANTIC
TARGET "bounded target"
MUST "anchor"
LIMIT 3
""",
            """PROBE SEMANTIC
TARGET   "bounded target"
MUST "anchor"
LIMIT 3
""",
        )

        for source in invalid:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    parse_probe(source)

    def test_final_newline_is_required_to_match_grammar(self) -> None:
        with self.assertRaisesRegex(ValueError, "end with a newline"):
            parse_probe(
                'PROBE SEMANTIC\nTARGET "bounded target"\nMUST "anchor"\nLIMIT 3'
            )

    def test_parser_uses_only_grammar_line_separators(self) -> None:
        lf = chr(10)
        crlf = chr(13) + chr(10)
        unicode_separator_char = chr(0x2028)

        unicode_separator = parse_probe(
            f'PROBE SEMANTIC{lf}TARGET "bounded{unicode_separator_char}target"'
            f'{lf}MUST "anchor"{lf}LIMIT 3{lf}'
        )
        crlf_probe = parse_probe(
            f'PROBE SEMANTIC{crlf}TARGET "bounded target"'
            f'{crlf}MUST "anchor"{crlf}LIMIT 3{crlf}'
        )

        self.assertEqual(
            unicode_separator.target,
            f"bounded{unicode_separator_char}target",
        )
        self.assertEqual(crlf_probe.limit, 3)

    def test_documented_lark_grammar_is_bounded_and_matches_light_sonar(self) -> None:
        grammar = (ROOT / "sonar" / "sonar_query.lark").read_text(encoding="utf-8")

        for mode in ("LITERAL", "SEMANTIC", "FUNCTIONAL", "RELATIONAL"):
            self.assertIn(mode, grammar)

        for clause in ("TARGET", "MUST", "SHOULD", "MUST_NOT", "TIME", "LIMIT"):
            self.assertIn(clause, grammar)

        self.assertIn("positive_block:", grammar)
        self.assertIn("must_not_block:", grammar)
        self.assertIn('QUOTED: /"[^"\\r\\n]{1,240}"/', grammar)
        self.assertIn("NL: /\\r?\\n/", grammar)
        self.assertNotIn("\\\\r", grammar)
        self.assertNotIn("\\\\n", grammar)


if __name__ == "__main__":
    unittest.main()
