# Repository Rules

These rules apply to `TeaShaman-cyber/theseus-sonar-skill`.

## Authority and scope

- `main` is accepted repository state.
- Issues coordinate live work; they are not implementation authority.
- Pull requests are candidate changes until merged and read back.
- Upstream feature request `openai/codex#48166` motivates the work but does not grant permission for later upstream publication or contribution.
- Current implementation coordination lives in issue #1 until it is closed or superseded.

## Epistemic boundaries

Preserve these distinctions in code, fixtures, tests, documentation, and review:

```text
retrieval result != truth
search miss != historical absence
semantic-region hit != exact locator
repeated fragment != independent corroboration
historical evidence != current authority
attractor recovery != recovery of corrections / boundaries
```

When evidence is insufficient, retain an explicit UNKNOWN state instead of manufacturing absence or certainty.

## Public-data boundary

Do not commit:

- private conversation corpora or account exports;
- credentials, tokens, cookies, private URLs, or account-specific identifiers;
- local search databases or private retrieval caches;
- raw diagnostic exports that may contain user data.

Public fixtures must be synthetic or explicitly sanitized public evidence. Sanitization is part of acceptance, not an afterthought.

## Change control

Use one narrow issue for material implementation, architecture, durable automation, or cross-cutting repository changes. Reuse a covering issue when one already exists.

Prefer small reversible changes and one obvious next step. Do not broaden an implementation slice merely because a related capability is available.

Normal flow:

```text
Issue
-> bounded branch
-> implementation
-> tools/dev/check
-> reviewable PR
-> required CI/review
-> merge
-> exact remote readback
-> issue disposition
```

Routine maintenance that changes no behavior or authority may remain narrower.

## Verification

`tools/dev/check` is the canonical local pre-review gate.

Keep fast deterministic checks in `tools/dev/check`. Model-based evals, repeated stochastic runs, live link checks, and cross-harness comparisons belong in explicit acceptance/heavy QA paths unless a concrete regression justifies promoting one into the fast gate.

External validators are differential evidence, not repository authority. If two validators disagree, preserve the disagreement and inspect the exact rule rather than voting by tool count.

A successful command or green CI proves only the postconditions encoded by that check. Claims about external tools, upstream behavior, or current remote state require their own observable readback.

Important writes require exact remote readback when an independent read route is available.

## Upstream boundary

This repository may prepare evidence or candidate packages for OpenAI or other external projects. External issue comments, pull requests, releases, package publication, or other upstream mutations are separate consequential actions and require explicit current authorization.

Capability is not permission.
