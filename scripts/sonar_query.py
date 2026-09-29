from __future__ import annotations

from dataclasses import dataclass


ALLOWED_MODES = ("LITERAL", "SEMANTIC", "FUNCTIONAL", "RELATIONAL")
MAX_TEXT_LENGTH = 240
MAX_CLAUSES_PER_KIND = 2
DEFAULT_LIMIT = 5

_CLAUSE_ORDER = {
    "TARGET": 0,
    "MUST": 1,
    "SHOULD": 2,
    "MUST_NOT": 3,
    "TIME": 4,
    "LIMIT": 5,
}


@dataclass(frozen=True)
class SonarProbe:
    mode: str
    target: str
    must: tuple[str, ...] = ()
    should: tuple[str, ...] = ()
    must_not: tuple[str, ...] = ()
    time: str | None = None
    limit: int = DEFAULT_LIMIT


def _parse_quoted(value: str, field: str) -> str:
    value = value.strip()
    if len(value) < 2 or not (value.startswith('"') and value.endswith('"')):
        raise ValueError(f"{field} must be a double-quoted string")
    parsed = value[1:-1]
    if not parsed:
        raise ValueError(f"{field} must not be empty")
    if '"' in parsed or "\n" in parsed or "\r" in parsed:
        raise ValueError(f"{field} contains unsupported quoting or newline")
    if len(parsed) > MAX_TEXT_LENGTH:
        raise ValueError(f"{field} exceeds {MAX_TEXT_LENGTH} characters")
    return parsed


def _append_bounded(values: list[str], raw_value: str, field: str) -> None:
    if len(values) >= MAX_CLAUSES_PER_KIND:
        raise ValueError(f"{field} may appear at most {MAX_CLAUSES_PER_KIND} times")
    values.append(_parse_quoted(raw_value, field))


def parse_probe(text: str) -> SonarProbe:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("PROBE "):
        raise ValueError("PROBE mode is required")

    mode = lines[0][len("PROBE ") :].strip()
    if mode not in ALLOWED_MODES:
        raise ValueError(f"unsupported probe mode: {mode}")

    target: str | None = None
    must: list[str] = []
    should: list[str] = []
    must_not: list[str] = []
    time_value: str | None = None
    limit = DEFAULT_LIMIT
    saw_limit = False
    last_order = -1

    for line in lines[1:]:
        if " " not in line:
            raise ValueError(f"invalid clause: {line}")
        keyword, raw_value = line.split(" ", 1)

        if keyword not in _CLAUSE_ORDER:
            raise ValueError(f"unsupported clause: {keyword}")

        order = _CLAUSE_ORDER[keyword]
        if order < last_order:
            raise ValueError(
                "clauses must follow canonical order: "
                "TARGET, MUST, SHOULD, MUST_NOT, TIME, LIMIT"
            )
        last_order = order

        if keyword == "TARGET":
            if target is not None:
                raise ValueError("TARGET may appear only once")
            target = _parse_quoted(raw_value, "TARGET")
        elif keyword == "MUST":
            _append_bounded(must, raw_value, "MUST")
        elif keyword == "SHOULD":
            _append_bounded(should, raw_value, "SHOULD")
        elif keyword == "MUST_NOT":
            _append_bounded(must_not, raw_value, "MUST_NOT")
        elif keyword == "TIME":
            if time_value is not None:
                raise ValueError("TIME may appear only once")
            time_value = _parse_quoted(raw_value, "TIME")
        elif keyword == "LIMIT":
            if saw_limit:
                raise ValueError("LIMIT may appear only once")
            try:
                limit = int(raw_value)
            except ValueError as exc:
                raise ValueError("LIMIT must be an integer") from exc
            if not 1 <= limit <= 10:
                raise ValueError("LIMIT must be between 1 and 10")
            saw_limit = True

    if target is None:
        raise ValueError("TARGET is required")

    return SonarProbe(
        mode=mode,
        target=target,
        must=tuple(must),
        should=tuple(should),
        must_not=tuple(must_not),
        time=time_value,
        limit=limit,
    )


_MODE_GUIDANCE = {
    "LITERAL": "Prioritize exact names or phrases from the target and required anchors.",
    "SEMANTIC": "Recover the same information need by meaning even when the wording differs.",
    "FUNCTIONAL": "Recover the target by its process or function; do not rely on its headline wording unless required anchors contain it.",
    "RELATIONAL": "Recover the target through its distinctive relations, roles, or authority structure.",
}


def _joined(values: tuple[str, ...]) -> str:
    return "; ".join(values)


def render_personal_context_query(probe: SonarProbe) -> str:
    parts = [
        f"Find past context about: {probe.target}.",
        f"Probe mode: {probe.mode}. {_MODE_GUIDANCE[probe.mode]}",
    ]
    if probe.must:
        parts.append(f"Require: {_joined(probe.must)}.")
    if probe.should:
        parts.append(f"Prefer: {_joined(probe.should)}.")
    if probe.time:
        parts.append(f"Time constraint: {probe.time}.")
    parts.append(
        f"Return at most {probe.limit} distinct relevant past conversations or context records. "
        "Keep separate sources distinct, avoid treating repeated fragments as corroboration, "
        "and treat a miss as unknown rather than proof of absence."
    )
    return "\n".join(parts)
