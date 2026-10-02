import unittest

from scripts.sonar_decision import (
    AuthorityLayer,
    Evidence,
    NavigationState,
    NextAction,
    ProbeMode,
    PropositionProvenance,
    Receipt,
    ResolutionReceipt,
    advance_resolution,
    decide_navigation,
)


def history_receipt(mode, evidence, correlation_id):
    return Receipt(
        mode,
        evidence,
        PropositionProvenance.RETRIEVED_HISTORY,
        correlation_id,
    )


class SonarDecisionTest(unittest.TestCase):
    def test_independent_personal_context_search_hits_locate_but_do_not_verify(self) -> None:
        decision = decide_navigation(
            (
                history_receipt(ProbeMode.LITERAL, Evidence.STRONG, "literal"),
                history_receipt(ProbeMode.FUNCTIONAL, Evidence.STRONG, "functional"),
            ),
            remaining_budget=1,
        )

        self.assertEqual(decision.state, NavigationState.LOCATED)
        self.assertEqual(decision.next_action, NextAction.RESOLVE_AUTHORITY)
        self.assertEqual(
            decision.reason,
            "independent_personal_context_search_evidence",
        )

    def test_repeated_strong_same_mode_requests_another_personal_context_search_probe(self) -> None:
        decision = decide_navigation(
            (
                history_receipt(ProbeMode.FUNCTIONAL, Evidence.STRONG, "functional"),
                history_receipt(ProbeMode.FUNCTIONAL, Evidence.STRONG, "functional"),
            ),
            remaining_budget=1,
        )

        self.assertEqual(decision.state, NavigationState.UNLOCATED)
        self.assertEqual(decision.next_action, NextAction.PROBE_PERSONAL_CONTEXT_SEARCH)

    def test_literal_plus_semantic_strong_still_needs_discriminating_probe(self) -> None:
        decision = decide_navigation(
            (
                history_receipt(ProbeMode.LITERAL, Evidence.STRONG, "literal"),
                history_receipt(ProbeMode.SEMANTIC, Evidence.STRONG, "semantic"),
            ),
            remaining_budget=1,
        )

        self.assertEqual(decision.state, NavigationState.UNLOCATED)
        self.assertEqual(decision.next_action, NextAction.PROBE_PERSONAL_CONTEXT_SEARCH)

    def test_conflict_or_drift_cannot_become_located(self) -> None:
        for evidence in (Evidence.CONFLICT, Evidence.DRIFT):
            with self.subTest(evidence=evidence):
                decision = decide_navigation(
                    (
                        history_receipt(ProbeMode.FUNCTIONAL, Evidence.STRONG, "functional"),
                        history_receipt(ProbeMode.RELATIONAL, Evidence.STRONG, "relational"),
                        history_receipt(ProbeMode.SEMANTIC, evidence, "semantic"),
                    ),
                    remaining_budget=1,
                )
                self.assertEqual(decision.state, NavigationState.UNLOCATED)
                self.assertEqual(
                    decision.next_action,
                    NextAction.PROBE_PERSONAL_CONTEXT_SEARCH,
                )

    def test_conflict_or_drift_at_zero_budget_is_terminal_unknown(self) -> None:
        for evidence in (Evidence.CONFLICT, Evidence.DRIFT):
            with self.subTest(evidence=evidence):
                decision = decide_navigation(
                    (
                        history_receipt(ProbeMode.FUNCTIONAL, Evidence.STRONG, "functional"),
                        history_receipt(ProbeMode.RELATIONAL, Evidence.STRONG, "relational"),
                        history_receipt(ProbeMode.SEMANTIC, evidence, "semantic"),
                    ),
                    remaining_budget=0,
                )

                self.assertEqual(decision.state, NavigationState.UNKNOWN)
                self.assertEqual(decision.next_action, NextAction.NONE)
                self.assertEqual(
                    decision.reason,
                    "navigation_budget_exhausted",
                )

    def test_exhausted_navigation_budget_is_unknown(self) -> None:
        decision = decide_navigation(
            (history_receipt(ProbeMode.LITERAL, Evidence.WEAK, "literal"),),
            remaining_budget=0,
        )

        self.assertEqual(decision.state, NavigationState.UNKNOWN)
        self.assertEqual(decision.next_action, NextAction.NONE)

    def test_exact_object_without_readback_is_resolved_not_verified(self) -> None:
        decision = advance_resolution(
            ResolutionReceipt(
                authority=AuthorityLayer.SESSION_SEARCH,
                available=True,
                exact_object_found=True,
                readback_verified=False,
            )
        )

        self.assertEqual(decision.state, NavigationState.RESOLVED)
        self.assertEqual(decision.next_action, NextAction.VERIFY_READBACK)

    def test_verified_readback_is_the_only_verified_state(self) -> None:
        decision = advance_resolution(
            ResolutionReceipt(
                authority=AuthorityLayer.GITHUB,
                available=True,
                exact_object_found=True,
                readback_verified=True,
            )
        )

        self.assertEqual(decision.state, NavigationState.VERIFIED)
        self.assertEqual(decision.next_action, NextAction.NONE)

    def test_selected_authority_without_exact_object_is_routed(self) -> None:
        decision = advance_resolution(
            ResolutionReceipt(
                authority=AuthorityLayer.MEMORY_PROVIDER,
                available=True,
                exact_object_found=False,
                readback_verified=False,
            )
        )

        self.assertEqual(decision.state, NavigationState.ROUTED)
        self.assertEqual(decision.next_action, NextAction.RESOLVE_AUTHORITY)

    def test_unavailable_authority_is_degraded(self) -> None:
        decision = advance_resolution(
            ResolutionReceipt(
                authority=AuthorityLayer.SESSION_SEARCH,
                available=False,
                exact_object_found=False,
                readback_verified=False,
            )
        )

        self.assertEqual(decision.state, NavigationState.DEGRADED)
        self.assertEqual(decision.next_action, NextAction.NONE)

    def test_resolution_receipt_subclass_cannot_shape_shift_to_verified(self) -> None:
        class ShapeShiftingResolutionReceipt(ResolutionReceipt):
            def __getattribute__(self, name):
                if name == "readback_verified":
                    reads = object.__getattribute__(self, "__dict__").get(
                        "_readback_reads",
                        0,
                    )
                    object.__getattribute__(self, "__dict__")["_readback_reads"] = (
                        reads + 1
                    )
                    if reads < 2:
                        return False
                    return True
                return object.__getattribute__(self, name)

        receipt = ShapeShiftingResolutionReceipt(
            authority=AuthorityLayer.GITHUB,
            available=True,
            exact_object_found=True,
            readback_verified=False,
        )

        with self.assertRaisesRegex(ValueError, "ResolutionReceipt"):
            advance_resolution(receipt)

    def test_non_enum_authority_cannot_cross_resolution_boundary(self) -> None:
        receipt = ResolutionReceipt(
            authority="personal_context.search",  # type: ignore[arg-type]
            available=True,
            exact_object_found=True,
            readback_verified=True,
        )

        with self.assertRaisesRegex(ValueError, "authority"):
            advance_resolution(receipt)

    def test_allowed_authority_string_is_still_rejected_without_enum_identity(self) -> None:
        receipt = ResolutionReceipt(
            authority="GITHUB",  # type: ignore[arg-type]
            available=True,
            exact_object_found=True,
            readback_verified=True,
        )

        with self.assertRaisesRegex(ValueError, "authority"):
            advance_resolution(receipt)

    def test_resolution_flags_must_be_actual_booleans(self) -> None:
        malformed = (
            ResolutionReceipt(
                authority=AuthorityLayer.GITHUB,
                available="false",  # type: ignore[arg-type]
                exact_object_found=False,
                readback_verified=False,
            ),
            ResolutionReceipt(
                authority=AuthorityLayer.GITHUB,
                available=True,
                exact_object_found="false",  # type: ignore[arg-type]
                readback_verified=False,
            ),
            ResolutionReceipt(
                authority=AuthorityLayer.GITHUB,
                available=True,
                exact_object_found=True,
                readback_verified="false",  # type: ignore[arg-type]
            ),
        )

        for receipt in malformed:
            with self.subTest(receipt=receipt):
                with self.assertRaisesRegex(ValueError, "bool"):
                    advance_resolution(receipt)

    def test_non_personal_context_search_source_is_rejected(self) -> None:
        receipt = Receipt(
            ProbeMode.FUNCTIONAL,
            Evidence.STRONG,
            PropositionProvenance.RETRIEVED_HISTORY,
            "functional",
            source="other-source",
        )

        with self.assertRaisesRegex(ValueError, "personal_context.search"):
            decide_navigation((receipt,), remaining_budget=1)

    def test_navigation_budget_must_be_an_exact_integer(self) -> None:
        for value in (True, 0.5, "1", None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "remaining_budget"):
                    decide_navigation((), remaining_budget=value)  # type: ignore[arg-type]

    def test_negative_budget_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "remaining_budget"):
            decide_navigation((), remaining_budget=-1)


if __name__ == "__main__":
    unittest.main()
