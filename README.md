# Theseus Sonar Skill

Public implementation and validation repository for a bounded model-facing retrieval skill.

Upstream feature request: [openai/codex#48166](https://github.com/openai/codex/issues/48166)  
Implementation coordination: [#1](https://github.com/TeaShaman-cyber/theseus-sonar-skill/issues/1)

**Status:** PUBLIC PROTOTYPE / IMPLEMENTATION TRACK OPEN / NO UPSTREAM PLUGIN PR YET

## Purpose

The project prototypes a provider-agnostic retrieval discipline for models that already have access to a historical or contextual search surface.

The skill is intended to improve query formulation, provenance handling, uncertainty, and exact-reference verification without claiming knowledge of a provider's hidden retrieval implementation.

## Core boundaries

```text
retrieval result != truth
search miss != historical absence
semantic-region hit != exact locator
repeated fragment != independent corroboration
historical evidence != current authority
```

Real private conversation corpora, account exports, credentials, private URLs, and account-specific identifiers are not committed here. Public fixtures must be synthetic or explicitly sanitized public evidence.

## Working flow

```text
Issue
-> bounded branch
-> implementation / fixture
-> repo-native QA
-> reviewable PR
-> exact remote readback
-> disposition
```

The current implementation track is [issue #1](https://github.com/TeaShaman-cyber/theseus-sonar-skill/issues/1).

## Development

Run the canonical local pre-review check from the repository root:

```bash
tools/dev/check
```

The fast gate is dependency-free and validates the repository contract, exercises the generic Agent Skill validator against a synthetic reference fixture, runs unit/regression tests, compiles Python verification code, and rejects whitespace errors.

Validate any candidate skill directory directly with:

```bash
python3 scripts/verify_skill.py --strict path/to/skill
```

The project deliberately separates fast deterministic QA from slower behavioral/model evals. See [Sonar Skill QA Strategy](docs/qa-strategy.md) for the OpenAI, Agent Skills, Superpowers, and external-validator baseline plus the planned trigger/negative-control eval layers.

Repository operating rules are in [RULES.md](RULES.md). Contribution mechanics are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Research lineage

- [Theseus research #11 — retrieval/Sonar calibration](https://github.com/TeaShaman-cyber/theseus-research/issues/11)
- [Theseus research #81 — upstream retrieval proposals](https://github.com/TeaShaman-cyber/theseus-research/issues/81)
- [Theseus Session Search Lab](https://github.com/TeaShaman-cyber/theseus-session-search-lab)

This repository is an implementation line under the wider Theseus public research program. It does not define the Theseus program contract.
