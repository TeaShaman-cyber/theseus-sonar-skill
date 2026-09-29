from pathlib import Path
import itertools
import unittest

from lark import Lark, UnexpectedInput

from scripts.sonar_query import parse_probe


ROOT = Path(__file__).resolve().parents[1]
GRAMMAR = (ROOT / "sonar" / "sonar_query.lark").read_text(encoding="utf-8")


def build_lark() -> Lark:
    return Lark(GRAMMAR, parser="lalr", start="start")


class SonarLarkGrammarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = build_lark()

    def assertSameAcceptance(self, source: str) -> None:
        try:
            parse_probe(source)
            handwritten = True
        except ValueError:
            handwritten = False

        try:
            self.parser.parse(source)
            grammar = True
        except UnexpectedInput:
            grammar = False

        self.assertEqual(
            handwritten,
            grammar,
            msg=f"parser/grammar acceptance drift for: {source!r}",
        )

    def test_representative_functional_probe_parses(self) -> None:
        source = """PROBE FUNCTIONAL
TARGET "operator-side target"
MUST "keyword discovery -> useful records -> standardized headings"
SHOULD "authority relation"
MUST_NOT "headline attractor"
TIME "2026-09-19"
LIMIT 5
"""
        self.parser.parse(source)

    def test_generated_canonical_space_matches_handwritten_parser(self) -> None:
        modes = ("LITERAL", "SEMANTIC", "FUNCTIONAL", "RELATIONAL")
        limits = (None, 1, 10)

        cases = 0
        for mode, must_n, should_n, must_not_n, with_time, limit in itertools.product(
            modes,
            range(3),
            range(3),
            range(3),
            (False, True),
            limits,
        ):
            if must_n == 0 and should_n == 0:
                continue

            lines = [f"PROBE {mode}", 'TARGET "target"']
            lines.extend(f'MUST "must-{i}"' for i in range(must_n))
            lines.extend(f'SHOULD "should-{i}"' for i in range(should_n))
            lines.extend(f'MUST_NOT "exclude-{i}"' for i in range(must_not_n))
            if with_time:
                lines.append('TIME "2026-09-19"')
            if limit is not None:
                lines.append(f"LIMIT {limit}")

            self.assertSameAcceptance("\n".join(lines) + "\n")
            cases += 1

        self.assertEqual(cases, 576)

    def test_known_invalid_forms_match_handwritten_parser(self) -> None:
        invalid = (
            'PROBE SEMANTIC\nTARGET "target"\nMUST "one"\nMUST "two"\nMUST "three"\n',
            'PROBE SEMANTIC\nTARGET "target"\nSHOULD "s"\nMUST "m"\n',
            'PROBE SEMANTIC\nTARGET "target"\nMUST "m"\nLIMIT 03\n',
            'PROBE SEMANTIC\nTARGET "target"\nMUST "m"\nLIMIT 3',
            'PROBE   SEMANTIC\nTARGET "target"\nMUST "m"\n',
            'PROBE SEMANTIC\n\nTARGET "target"\nMUST "m"\n',
        )
        for source in invalid:
            with self.subTest(source=source):
                self.assertSameAcceptance(source)

    def test_unicode_separator_inside_quoted_text_is_data(self) -> None:
        sep = chr(0x2028)
        source = (
            'PROBE SEMANTIC\n'
            f'TARGET "bounded{sep}target"\n'
            'MUST "anchor"\n'
            'LIMIT 3\n'
        )
        self.assertSameAcceptance(source)


if __name__ == "__main__":
    unittest.main()
