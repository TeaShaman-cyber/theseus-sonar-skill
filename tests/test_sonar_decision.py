import unittest

from scripts.sonar_decision import DecisionRoute, Evidence, ProbeMode, Receipt, decide


class SonarDecisionTest(unittest.TestCase):
    def test_two_independent_strong_modes_with_functional_evidence_are_ready(self) -> None:
        decision = decide(
            (
                Receipt(ProbeMode.LITERAL, Evidence.STRONG),
                Receipt(ProbeMode.FUNCTIONAL, Evidence.STRONG),
            ),
            remaining_budget=1,
        )
        self.assertEqual(decision.route, DecisionRoute.READY)
        self.assertEqual(decision.reason, "independent_strong_evidence")

    def test_repeated_strong_same_mode_is_not_independent(self) -> None:
        decision = decide(
            (
                Receipt(ProbeMode.FUNCTIONAL, Evidence.STRONG),
                Receipt(ProbeMode.FUNCTIONAL, Evidence.STRONG),
            ),
            remaining_budget=1,
        )
        self.assertEqual(decision.route, DecisionRoute.PROBE)

    def test_literal_plus_semantic_strong_still_needs_discriminating_probe(self) -> None:
        decision = decide(
            (
                Receipt(ProbeMode.LITERAL, Evidence.STRONG),
                Receipt(ProbeMode.SEMANTIC, Evidence.STRONG),
            ),
            remaining_budget=1,
        )
        self.assertEqual(decision.route, DecisionRoute.PROBE)

    def test_conflict_dominates_positive_evidence(self) -> None:
        decision = decide(
            (
                Receipt(ProbeMode.FUNCTIONAL, Evidence.STRONG),
                Receipt(ProbeMode.RELATIONAL, Evidence.STRONG),
                Receipt(ProbeMode.SEMANTIC, Evidence.CONFLICT),
            ),
            remaining_budget=1,
        )
        self.assertEqual(decision.route, DecisionRoute.PROBE)
        self.assertEqual(decision.reason, "conflict_requires_probe")

    def test_drift_dominates_positive_evidence(self) -> None:
        decision = decide(
            (
                Receipt(ProbeMode.FUNCTIONAL, Evidence.STRONG),
                Receipt(ProbeMode.RELATIONAL, Evidence.STRONG),
                Receipt(ProbeMode.SEMANTIC, Evidence.DRIFT),
            ),
            remaining_budget=1,
        )
        self.assertEqual(decision.route, DecisionRoute.PROBE)
        self.assertEqual(decision.reason, "drift_requires_probe")

    def test_exhausted_budget_returns_unknown_when_not_ready(self) -> None:
        decision = decide(
            (Receipt(ProbeMode.LITERAL, Evidence.WEAK),),
            remaining_budget=0,
        )
        self.assertEqual(decision.route, DecisionRoute.UNKNOWN)
        self.assertEqual(decision.reason, "budget_exhausted")

    def test_conflict_at_zero_budget_is_unknown_not_ready(self) -> None:
        decision = decide(
            (Receipt(ProbeMode.RELATIONAL, Evidence.CONFLICT),),
            remaining_budget=0,
        )
        self.assertEqual(decision.route, DecisionRoute.UNKNOWN)

    def test_empty_receipts_with_budget_requests_probe(self) -> None:
        self.assertEqual(
            decide((), remaining_budget=2).route,
            DecisionRoute.PROBE,
        )

    def test_negative_budget_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "remaining_budget"):
            decide((), remaining_budget=-1)


if __name__ == "__main__":
    unittest.main()
