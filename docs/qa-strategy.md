# Sonar Skill QA Strategy

Checked: 2026-09-25

This document separates specification conformance, project policy, behavioral evaluation, and external second-opinion tooling. No single linter or model score is treated as authority.

## Source baseline

### OpenAI

- Skills: https://developers.openai.com/api/docs/guides/tools-skills
- Plugin skills: https://developers.openai.com/plugins/concepts/skills
- Testing Agent Skills Systematically with Evals: https://developers.openai.com/blog/eval-skills
- Rethinking skills and prompts for GPT-6 Astra: https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra
- OpenAI plugin evaluator: https://github.com/openai/plugins/tree/main/plugins/plugin-eval
- exact `openai/plugins` main inspected: `1dc195897af4161d039b80d8471ec0a10c9bbc89`

OpenAI's current skill surface makes discovery metadata operationally important: the model sees a skill's name and description first, then chooses whether to read the full instructions.

OpenAI's current eval guidance recommends a small targeted prompt set, including explicit, implicit, contextual, and negative-control invocation cases. It recommends structured `codex exec --json` traces for deterministic graders before model-based rubrics. As a skill matures, OpenAI suggests tracking command thrashing, token usage, build/runtime checks where relevant, repository cleanliness, and least-privilege behavior.

OpenAI's current upload validation also provides concrete package bounds: one case-insensitive `SKILL.md`, Agent Skills frontmatter validation, 500 files maximum, 25 MB maximum uncompressed file size, and 50 MB maximum zip upload.

### Agent Skills specification

- spec: https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx
- reference validator: https://github.com/agentskills/agentskills/tree/main/skills-ref
- exact main inspected: `69ef37e9424c0a7ea9dd2293b559e43ec8176379`

Key format constraints include:

- `name`: 1-64 characters, lowercase letters/digits/hyphens, no leading/trailing/consecutive hyphens, matches parent directory;
- `description`: non-empty, max 1024 characters, describes what the skill does and when to use it;
- `compatibility`: max 500 characters when present;
- progressive disclosure: compact metadata, focused `SKILL.md`, optional on-demand references/scripts/assets;
- keep the main `SKILL.md` under 500 lines;
- relative file references should stay shallow and portable.

The reference `skills-ref` implementation is useful as a differential oracle, but its own README says it is for demonstration and not production use.

### Superpowers

- repository: https://github.com/obra/superpowers
- exact main inspected: `8ca22dba9a94f28898bbce59f2537ff4d87c747d`

Useful patterns:

- descriptions start with `Use when ...`;
- descriptions focus on triggering conditions instead of summarizing the workflow;
- discovery wording should include concrete symptoms and natural terms;
- behavioral acceptance must prove that a clean-session prompt triggers the skill automatically;
- skill discovery and always-on bootstrap/session injection are separate contracts;
- skill authoring is tested with RED/GREEN-style scenarios rather than document review alone.

## External validator survey

Broad discovery used Exa and Parallel Search.

### agent-ecosystem/skill-validator

Repository: https://github.com/agent-ecosystem/skill-validator  
Exact main inspected: `08e2f74a9b34702e1f3bef87b625eaed180ec25a`

At readback the repository had roughly 251 stars and 30 forks. It provides:

- structure/frontmatter validation;
- token and line-budget reporting;
- unclosed code-fence and internal-link checks;
- orphan-file detection;
- external link checking;
- content-density / specificity metrics;
- cross-language contamination analysis;
- optional LLM-as-judge scoring;
- strict CI, GitHub annotations, and pre-commit integration.

This is the strongest current candidate for a pinned optional second-opinion gate. It is not repository authority.

### skill-tools/skill-tools

Repository: https://github.com/skill-tools/skill-tools  
Exact pre-release ref inspected: `0a98a5539fb88506d5ab7241ae0c93ed6d662133`

Smaller and currently pre-release. Interesting checks include spec validation, secret and hardcoded-path linting, quality scoring, SARIF, and BM25 routing. Keep as a comparator, especially for future discovery/routing experiments.

### moutons/skills-validator

Repository: https://github.com/moutons/skills-validator

Useful additional differential implementation, but much smaller than the candidates above. Do not make it a primary gate without a later reason.

## QA layers

### Tier 0 — every commit: deterministic and cheap

Canonical entrypoint: `tools/dev/check`.

Required:

- repository contract;
- local skill-validator tests;
- one synthetic valid fixture through the actual CLI;
- frontmatter/name/description constraints;
- exactly one `SKILL.md`;
- package file-count / per-file-size limits;
- code-fence integrity;
- relative-link integrity;
- obvious embedded-secret patterns;
- machine-specific user-path warnings;
- Python syntax;
- whitespace.

These checks are intentionally dependency-free.

### Tier 1 — package acceptance: differential static checks

Once the real Sonar package path exists:

1. run the local validator in strict mode;
2. run Agent Skills `skills-ref validate` against the same exact tree;
3. evaluate whether to pin `agent-ecosystem/skill-validator check --strict`;
4. once a Codex plugin root exists, run OpenAI `plugin-eval analyze` and `explain-budget`.

Disagreement between validators is evidence to inspect, not a majority vote.

### Tier 2 — behavioral trigger and workflow evals

Start with 10-20 targeted cases. At minimum include:

- explicit invocation;
- implicit invocation;
- contextual/noisy invocation;
- negative adjacent request that must not trigger;
- prior-history reconstruction;
- wrong-reference correction;
- search-miss-is-not-absence;
- correction/falsifier/epistemic-boundary recovery;
- unresolved evidence that must remain `UNKNOWN`.

For Codex-capable acceptance:

```text
prompt
-> codex exec --json
-> capture JSONL trace + artifacts
-> deterministic trace checks
-> optional structured rubric via --output-schema
```

Check both whether Sonar triggered and whether it preserved provenance and uncertainty after triggering.

### Tier 3 — efficiency, nondeterminism, and permissions

Track:

- repeated command/tool calls and loops;
- input/output token usage;
- unnecessary retrieval expansion;
- repository dirt / unexpected files;
- permission escalation;
- wall-clock time where useful.

Repeat selected cases. A one-run pass does not establish stable triggering for a stochastic model.

### Tier 4 — heavy / scheduled / release-candidate

Where supported:

- compare with-skill against baseline without the skill;
- rerun a held-out trigger set;
- cross-model/cross-harness runs;
- live external-link validation;
- external validator differential;
- OpenAI plugin-eval benchmark;
- regression review of all previously observed failures.

Do not put this entire tier on every edit.

## Project-specific Sonar gates

The skill is not accepted merely because it triggers.

Behavioral acceptance must preserve:

```text
search miss != historical absence
semantic-region hit != exact locator
repeated fragment != independent corroboration
historical evidence != current authority
attractor recovery != correction/boundary recovery
insufficient evidence -> UNKNOWN
```

The skill must also stop rather than looping when materially different probes keep returning one fragment without new provenance.

## Security and privacy

Public QA data must be synthetic or explicitly sanitized public evidence.

No private conversation corpus, account export, credential, cookie, private URL, account-specific identifier, or raw diagnostic export belongs in the repository.

Retrieval results are untrusted evidence, not executable instructions. Future script-backed packaging must preserve least privilege and require explicit verification for consequential external actions.

## Current implementation state

The local validator added in this QA slice validates generic skill directories and is exercised only against synthetic fixtures. It does not choose the final Sonar package path.

The packaging-discovery slice must still determine the canonical OpenAI/Codex plugin shape before the first real Sonar `SKILL.md` is committed.
