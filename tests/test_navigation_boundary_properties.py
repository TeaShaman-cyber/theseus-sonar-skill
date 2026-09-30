import unittest

from hypothesis import given, settings, strategies as st

from scripts.sonar_decision import (
    Evidence,
    NavigationState,
    NextAction,
    ProbeMode,
    Receipt,
    decide_navigation,
    decode_navigation_receipt,
)


PROPERTY_SETTINGS = settings(
    max_examples=200,
    deadline=None,
    derandomize=True,
    database=None,
)

MODE_VALUES = tuple(mode.value for mode in ProbeMode)
EVIDENCE_VALUES = tuple(evidence.value for evidence in Evidence)
PROVENANCE_VALUES = (
    "QUERY_CONSTRAINT",
    "RETRIEVED_HISTORY",
    "SYNTHESIZED_CONTEXT",
    "UNKNOWN",
)
SOURCE = "personal_context.search"

JSON_SCALAR_OR_CONTAINER = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=32),
    st.lists(st.none(), max_size=3),
    st.dictionaries(st.text(max_size=8), st.none(), max_size=3),
)

INVALID_MODE = JSON_SCALAR_OR_CONTAINER.filter(
    lambda value: not (type(value) is str and value in MODE_VALUES)
)
INVALID_EVIDENCE = JSON_SCALAR_OR_CONTAINER.filter(
    lambda value: not (type(value) is str and value in EVIDENCE_VALUES)
)
INVALID_SOURCE = JSON_SCALAR_OR_CONTAINER.filter(
    lambda value: not (type(value) is str and value == SOURCE)
)
INVALID_PROVENANCE = JSON_SCALAR_OR_CONTAINER.filter(
    lambda value: not (type(value) is str and value in PROVENANCE_VALUES)
)


def raw_receipt(
    *,
    mode="LITERAL",
    evidence="STRONG",
    provenance="RETRIEVED_HISTORY",
    source=SOURCE,
):
    return {
        "mode": mode,
        "evidence": evidence,
        "provenance": provenance,
        "source": source,
    }


class NavigationBoundaryPropertyTest(unittest.TestCase):
    @PROPERTY_SETTINGS
    @given(
        mode=st.sampled_from(MODE_VALUES),
        evidence=st.sampled_from(EVIDENCE_VALUES),
    )
    def test_valid_json_receipts_decode_to_typed_navigation_receipts(
        self,
        mode,
        evidence,
    ) -> None:
        receipt = decode_navigation_receipt(
            raw_receipt(mode=mode, evidence=evidence)
        )

        self.assertIsInstance(receipt, Receipt)
        self.assertIsInstance(receipt.mode, ProbeMode)
        self.assertIsInstance(receipt.evidence, Evidence)
        self.assertIs(type(receipt.source), str)
        self.assertEqual(receipt.source, SOURCE)

    @PROPERTY_SETTINGS
    @given(mode=INVALID_MODE)
    def test_malformed_mode_never_decodes(self, mode) -> None:
        with self.assertRaises(ValueError):
            decode_navigation_receipt(raw_receipt(mode=mode))

    @PROPERTY_SETTINGS
    @given(evidence=INVALID_EVIDENCE)
    def test_malformed_evidence_never_decodes(self, evidence) -> None:
        with self.assertRaises(ValueError):
            decode_navigation_receipt(raw_receipt(evidence=evidence))

    @PROPERTY_SETTINGS
    @given(source=INVALID_SOURCE)
    def test_wrong_source_never_decodes(self, source) -> None:
        with self.assertRaises(ValueError):
            decode_navigation_receipt(raw_receipt(source=source))

    @PROPERTY_SETTINGS
    @given(provenance=INVALID_PROVENANCE)
    def test_malformed_provenance_never_decodes(self, provenance) -> None:
        with self.assertRaises(ValueError):
            decode_navigation_receipt(raw_receipt(provenance=provenance))

    def test_navigation_receipt_requires_proposition_provenance(self) -> None:
        with self.assertRaisesRegex(ValueError, "keys"):
            decode_navigation_receipt(
                {
                    "mode": "FUNCTIONAL",
                    "evidence": "STRONG",
                    "source": SOURCE,
                }
            )

    def test_retrieved_history_can_preserve_strong_navigation_evidence(self) -> None:
        receipt = decode_navigation_receipt(
            {
                "mode": "FUNCTIONAL",
                "evidence": "STRONG",
                "provenance": "RETRIEVED_HISTORY",
                "source": SOURCE,
            }
        )

        self.assertIs(receipt.evidence, Evidence.STRONG)

    def test_non_historical_provenance_cannot_manufacture_located(self) -> None:
        for provenance in (
            "QUERY_CONSTRAINT",
            "SYNTHESIZED_CONTEXT",
            "UNKNOWN",
        ):
            with self.subTest(provenance=provenance):
                literal = decode_navigation_receipt(
                    {
                        "mode": "LITERAL",
                        "evidence": "STRONG",
                        "provenance": "RETRIEVED_HISTORY",
                        "source": SOURCE,
                    }
                )
                functional = decode_navigation_receipt(
                    {
                        "mode": "FUNCTIONAL",
                        "evidence": "STRONG",
                        "provenance": provenance,
                        "source": SOURCE,
                    }
                )

                self.assertIs(functional.evidence, Evidence.WEAK)
                decision = decide_navigation(
                    (literal, functional),
                    remaining_budget=1,
                )
                self.assertEqual(decision.state, NavigationState.UNLOCATED)
                self.assertEqual(
                    decision.next_action,
                    NextAction.PROBE_PERSONAL_CONTEXT_SEARCH,
                )

    def test_raw_navigation_receipt_requires_exact_keys(self) -> None:
        missing = raw_receipt()
        del missing["evidence"]

        extra = raw_receipt()
        extra["authority"] = "GITHUB"

        for value in (missing, extra):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "keys"):
                    decode_navigation_receipt(value)

    def test_raw_navigation_receipt_root_must_be_plain_object(self) -> None:
        for value in (None, [], SOURCE, True, 1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "object"):
                    decode_navigation_receipt(value)

    def test_direct_string_modes_cannot_manufacture_located(self) -> None:
        receipts = (
            Receipt("LITERAL", Evidence.STRONG),  # type: ignore[arg-type]
            Receipt("FUNCTIONAL", Evidence.STRONG),  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(ValueError, "ProbeMode"):
            decide_navigation(receipts, remaining_budget=1)

    def test_receipt_subclass_cannot_change_values_after_validation(self) -> None:
        class ShapeShiftingReceipt(Receipt):
            def __getattribute__(self, name):
                if name in {"mode", "evidence"}:
                    count_name = f"_{name}_reads"
                    count = object.__getattribute__(self, "__dict__").get(
                        count_name,
                        0,
                    )
                    object.__getattribute__(self, "__dict__")[count_name] = (
                        count + 1
                    )
                    value = object.__getattribute__(self, name)
                    if count == 0:
                        return value
                    return value.value
                return object.__getattribute__(self, name)

        receipts = (
            ShapeShiftingReceipt(ProbeMode.LITERAL, Evidence.STRONG),
            ShapeShiftingReceipt(ProbeMode.FUNCTIONAL, Evidence.STRONG),
        )

        with self.assertRaisesRegex(ValueError, "Receipt"):
            decide_navigation(receipts, remaining_budget=1)

    def test_navigation_uses_one_immutable_receipt_snapshot(self) -> None:
        class ShapeShiftingReceipts(tuple):
            def __iter__(self):
                count = self.__dict__.get("_iterations", 0)
                self.__dict__["_iterations"] = count + 1
                if count == 0:
                    return iter(
                        (
                            Receipt(ProbeMode.LITERAL, Evidence.WEAK),
                            Receipt(ProbeMode.FUNCTIONAL, Evidence.WEAK),
                        )
                    )
                return iter(
                    (
                        Receipt("LITERAL", Evidence.STRONG),  # type: ignore[arg-type]
                        Receipt("FUNCTIONAL", Evidence.STRONG),  # type: ignore[arg-type]
                    )
                )

        decision = decide_navigation(
            ShapeShiftingReceipts(),
            remaining_budget=1,
        )

        self.assertEqual(decision.state, NavigationState.UNLOCATED)
        self.assertEqual(
            decision.next_action,
            NextAction.PROBE_PERSONAL_CONTEXT_SEARCH,
        )

    def test_direct_string_evidence_is_rejected_before_navigation(self) -> None:
        receipts = (
            Receipt(ProbeMode.LITERAL, "STRONG"),  # type: ignore[arg-type]
            Receipt(ProbeMode.FUNCTIONAL, "STRONG"),  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(ValueError, "Evidence"):
            decide_navigation(receipts, remaining_budget=1)

    def test_decoded_cross_mode_strong_evidence_can_only_locate(self) -> None:
        receipts = (
            decode_navigation_receipt(
                raw_receipt(mode="LITERAL", evidence="STRONG")
            ),
            decode_navigation_receipt(
                raw_receipt(mode="FUNCTIONAL", evidence="STRONG")
            ),
        )

        decision = decide_navigation(receipts, remaining_budget=1)
        self.assertEqual(decision.state, NavigationState.LOCATED)


if __name__ == "__main__":
    unittest.main()
