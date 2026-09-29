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


class NavigationState(str, Enum):
    UNLOCATED = "UNLOCATED"
    LOCATED = "LOCATED"
    ROUTED = "ROUTED"
    RESOLVED = "RESOLVED"
    VERIFIED = "VERIFIED"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class NextAction(str, Enum):
    PROBE_PERSONAL_CONTEXT_SEARCH = "PROBE_PERSONAL_CONTEXT_SEARCH"
    RESOLVE_AUTHORITY = "RESOLVE_AUTHORITY"
    VERIFY_READBACK = "VERIFY_READBACK"
    NONE = "NONE"


class AuthorityLayer(str, Enum):
    SESSION_SEARCH = "SESSION_SEARCH"
    GITHUB = "GITHUB"
    MEMORY_PROVIDER = "MEMORY_PROVIDER"
    FILES = "FILES"
    OTHER = "OTHER"


@dataclass(frozen=True)
class Receipt:
    mode: ProbeMode
    evidence: Evidence
    source: str = "personal_context.search"


@dataclass(frozen=True)
class NavigationDecision:
    state: NavigationState
    next_action: NextAction
    reason: str


@dataclass(frozen=True)
class ResolutionReceipt:
    authority: AuthorityLayer
    available: bool
    exact_object_found: bool
    readback_verified: bool


_DISCRIMINATING_MODES = frozenset({ProbeMode.FUNCTIONAL, ProbeMode.RELATIONAL})


def decide_navigation(
    receipts: tuple[Receipt, ...],
    remaining_budget: int,
) -> NavigationDecision:
    if remaining_budget < 0:
        raise ValueError("remaining_budget must be non-negative")

    if any(receipt.source != "personal_context.search" for receipt in receipts):
        raise ValueError("navigation receipts must come from personal_context.search")

    evidence = {receipt.evidence for receipt in receipts}

    if Evidence.CONFLICT in evidence:
        if remaining_budget > 0:
            return NavigationDecision(
                NavigationState.UNLOCATED,
                NextAction.PROBE_PERSONAL_CONTEXT_SEARCH,
                "personal_context_search_conflict_requires_probe",
            )
        return NavigationDecision(
            NavigationState.UNKNOWN,
            NextAction.NONE,
            "navigation_budget_exhausted",
        )

    if Evidence.DRIFT in evidence:
        if remaining_budget > 0:
            return NavigationDecision(
                NavigationState.UNLOCATED,
                NextAction.PROBE_PERSONAL_CONTEXT_SEARCH,
                "personal_context_search_drift_requires_probe",
            )
        return NavigationDecision(
            NavigationState.UNKNOWN,
            NextAction.NONE,
            "navigation_budget_exhausted",
        )

    strong_modes = {
        receipt.mode
        for receipt in receipts
        if receipt.evidence is Evidence.STRONG
    }
    has_discriminating_strong = bool(strong_modes & _DISCRIMINATING_MODES)

    if len(strong_modes) >= 2 and has_discriminating_strong:
        return NavigationDecision(
            NavigationState.LOCATED,
            NextAction.RESOLVE_AUTHORITY,
            "independent_personal_context_search_evidence",
        )

    if remaining_budget > 0:
        return NavigationDecision(
            NavigationState.UNLOCATED,
            NextAction.PROBE_PERSONAL_CONTEXT_SEARCH,
            "insufficient_personal_context_search_evidence",
        )

    return NavigationDecision(
        NavigationState.UNKNOWN,
        NextAction.NONE,
        "navigation_budget_exhausted",
    )


def advance_resolution(receipt: ResolutionReceipt) -> NavigationDecision:
    if receipt.readback_verified and not receipt.exact_object_found:
        raise ValueError("readback_verified requires exact_object_found")
    if receipt.exact_object_found and not receipt.available:
        raise ValueError("exact_object_found requires available authority")

    if not receipt.available:
        return NavigationDecision(
            NavigationState.DEGRADED,
            NextAction.NONE,
            "authority_unavailable",
        )

    if receipt.readback_verified:
        return NavigationDecision(
            NavigationState.VERIFIED,
            NextAction.NONE,
            "authority_readback_verified",
        )

    if receipt.exact_object_found:
        return NavigationDecision(
            NavigationState.RESOLVED,
            NextAction.VERIFY_READBACK,
            "exact_object_resolved",
        )

    return NavigationDecision(
        NavigationState.ROUTED,
        NextAction.RESOLVE_AUTHORITY,
        "authority_selected",
    )
