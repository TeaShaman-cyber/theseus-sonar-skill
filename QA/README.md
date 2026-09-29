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

The current Wolfram model independently checks the typed Sonar decision guard
over the presence-state space for STRONG, DRIFT, and CONFLICT evidence across
LITERAL, SEMANTIC, FUNCTIONAL, and RELATIONAL modes with bounded probe budget.
It verifies decision totality, READY safety invariants, budget termination, and
reachability. It does not verify PCA retrieval quality or model-side receipt
classification.
