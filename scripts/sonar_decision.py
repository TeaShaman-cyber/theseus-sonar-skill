from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Evidence(str, Enum):
    STRONG = "STRONG"
    WEAK = "WEAK"
    DRIFT = "DRIFT"
    CONFLICT = "CONFLICT"
    NONE = "NONE"


class ProbeMode(str, Enum):
    LITERAL = "LITERAL"
    SEMANTIC = "SEMANTIC"
    FUNCTIONAL = "FUNCTIONAL"
    RELATIONAL = "RELATIONAL"


class DecisionRoute(str, Enum):
    READY = "READY"
    PROBE = "PROBE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Receipt:
    mode: ProbeMode
    evidence: Evidence


@dataclass(frozen=True)
class Decision:
    route: DecisionRoute
    reason: str


_DISCRIMINATING_MODES = frozenset({ProbeMode.FUNCTIONAL, ProbeMode.RELATIONAL})


def decide(receipts: tuple[Receipt, ...], remaining_budget: int) -> Decision:
    if remaining_budget < 0:
        raise ValueError("remaining_budget must be non-negative")

    evidence = {receipt.evidence for receipt in receipts}

    if Evidence.CONFLICT in evidence:
        if remaining_budget > 0:
            return Decision(DecisionRoute.PROBE, "conflict_requires_probe")
        return Decision(DecisionRoute.UNKNOWN, "budget_exhausted")

    if Evidence.DRIFT in evidence:
        if remaining_budget > 0:
            return Decision(DecisionRoute.PROBE, "drift_requires_probe")
        return Decision(DecisionRoute.UNKNOWN, "budget_exhausted")

    strong_modes = {
        receipt.mode
        for receipt in receipts
        if receipt.evidence is Evidence.STRONG
    }
    has_discriminating_strong = bool(strong_modes & _DISCRIMINATING_MODES)

    if len(strong_modes) >= 2 and has_discriminating_strong:
        return Decision(DecisionRoute.READY, "independent_strong_evidence")

    if remaining_budget > 0:
        return Decision(DecisionRoute.PROBE, "insufficient_evidence")

    return Decision(DecisionRoute.UNKNOWN, "budget_exhausted")
