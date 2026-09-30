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
_NAVIGATION_SOURCE = "personal_context.search"
_NAVIGATION_KEYS = frozenset({"mode", "evidence", "source"})
_RESOLUTION_KEYS = frozenset(
    {
        "authority",
        "available",
        "exact_object_found",
        "readback_verified",
    }
)


def _validate_navigation_receipt(receipt: Receipt) -> None:
    if not isinstance(receipt, Receipt):
        raise ValueError("navigation receipt must be a Receipt")
    if not isinstance(receipt.mode, ProbeMode):
        raise ValueError("navigation mode must be a ProbeMode")
    if not isinstance(receipt.evidence, Evidence):
        raise ValueError("navigation evidence must be an Evidence")
    if type(receipt.source) is not str or receipt.source != _NAVIGATION_SOURCE:
        raise ValueError(
            "navigation receipts must come from personal_context.search"
        )


def decode_navigation_receipt(raw: object) -> Receipt:
    if type(raw) is not dict:
        raise ValueError("navigation receipt must be a JSON object")

    if set(raw) != _NAVIGATION_KEYS:
        raise ValueError("navigation receipt keys must match the contract exactly")

    mode_raw = raw["mode"]
    if type(mode_raw) is not str:
        raise ValueError("navigation mode must be a string enum value")
    try:
        mode = ProbeMode(mode_raw)
    except ValueError as exc:
        raise ValueError("navigation mode is not an allowed ProbeMode") from exc

    evidence_raw = raw["evidence"]
    if type(evidence_raw) is not str:
        raise ValueError("navigation evidence must be a string enum value")
    try:
        evidence = Evidence(evidence_raw)
    except ValueError as exc:
        raise ValueError("navigation evidence is not an allowed Evidence") from exc

    source_raw = raw["source"]
    if type(source_raw) is not str or source_raw != _NAVIGATION_SOURCE:
        raise ValueError(
            "navigation source must be personal_context.search"
        )

    receipt = Receipt(mode=mode, evidence=evidence, source=source_raw)
    _validate_navigation_receipt(receipt)
    return receipt


def _validate_resolution_receipt(receipt: ResolutionReceipt) -> None:
    if not isinstance(receipt.authority, AuthorityLayer):
        raise ValueError("authority must be an AuthorityLayer")
    if any(
        type(value) is not bool
        for value in (
            receipt.available,
            receipt.exact_object_found,
            receipt.readback_verified,
        )
    ):
        raise ValueError("resolution evidence flags must be bool")
    if receipt.readback_verified and not receipt.exact_object_found:
        raise ValueError("readback_verified requires exact_object_found")
    if receipt.exact_object_found and not receipt.available:
        raise ValueError("exact_object_found requires available authority")


def decode_resolution_receipt(raw: object) -> ResolutionReceipt:
    if type(raw) is not dict:
        raise ValueError("resolution receipt must be a JSON object")

    if set(raw) != _RESOLUTION_KEYS:
        raise ValueError("resolution receipt keys must match the contract exactly")

    authority_raw = raw["authority"]
    if type(authority_raw) is not str:
        raise ValueError("authority must be a string enum value")
    try:
        authority = AuthorityLayer(authority_raw)
    except ValueError as exc:
        raise ValueError("authority is not an allowed AuthorityLayer") from exc

    receipt = ResolutionReceipt(
        authority=authority,
        available=raw["available"],
        exact_object_found=raw["exact_object_found"],
        readback_verified=raw["readback_verified"],
    )
    _validate_resolution_receipt(receipt)
    return receipt


def decide_navigation(
    receipts: tuple[Receipt, ...],
    remaining_budget: int,
) -> NavigationDecision:
    if remaining_budget < 0:
        raise ValueError("remaining_budget must be non-negative")

    for receipt in receipts:
        _validate_navigation_receipt(receipt)

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
    _validate_resolution_receipt(receipt)

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
