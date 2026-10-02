# QA lanes

The repository keeps deterministic local QA separate from external independent
witnesses.

## Deterministic baseline

`tools/dev/check` is the blocking local and CI gate. It includes unit tests,
repository contract checks, Python syntax, whitespace checks, and executable
Lark parser/grammar differential validation.

## Wolfram independent witness

`tools/research/wolfram-witness` calls the official Wolfram MCP through the
workspace-pinned mcporter transport and evaluates
`QA/wolfram/sonar-decision.wl`.

Typical MarcoPolo invocation:

```sh
./tools/research/wolfram-witness --out /tmp/sonar-wolfram-witness.json
```

The receipt records the witness SHA-256, mcporter version, transport metadata,
payload, and one of these statuses:

- `VERIFIED` — Wolfram returned a structured payload with `pass=true`.
- `FAIL_ASSERTION` — transport succeeded but the independent assertions failed.
- `DEGRADED_EXTERNAL_WITNESS` — transport or payload parsing was unavailable.

The external witness is not part of `tools/dev/check`; network/provider
availability must not make deterministic repository QA flaky. A missing witness
is degraded external evidence, never a local PASS.

The witness exports the actual Python navigation behavior as a compact exhaustive
16,384-state decision table, then Wolfram independently checks that table against
the typed Sonar navigation invariants over the presence-state space for STRONG, DRIFT, and CONFLICT evidence across
LITERAL, SEMANTIC, FUNCTIONAL, and RELATIONAL modes with bounded probe budget.
It verifies decision totality, LOCATED safety invariants, budget termination, and
reachability for the personal_context.search navigation stage. LOCATED is not
authority resolution or verification. It does not verify PCA retrieval quality or model-side receipt
classification.

## Targeted mutation witness

The decision-core mutation lane is change-targeted heavy QA, not part of
`tools/dev/check`. It mutates only `scripts/sonar_decision.py` and runs only
the deterministic decision regression tests. Property/Hypothesis suites are
deliberately excluded from the mutation loop.

A surviving mutant is a classification lead, not score debt. Treat the receipt
as evidence bound to the exact source SHA and classify useful survivors as
REAL_TEST_GAP, EQUIVALENT, DIAGNOSTIC_ONLY, or IRRELEVANT before deciding on
any regression or follow-up.
