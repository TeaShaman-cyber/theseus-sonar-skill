---
name: sonar
description: Use when a task materially depends on prior chats, decisions, corrections, or references and the exact historical source is unknown, ambiguous, or likely phrased differently; also when nearby historical episodes could be mistaken for the intended one.
---

# Sonar

Sonar is a navigator over an available historical/context retrieval surface. It is not a memory backend and not an authority layer.

Use `personal_context.search` to locate likely historical context. Resolve exact claims through the appropriate authority before calling them verified.

## Non-negotiable boundaries

```text
retrieval result != truth
search miss != historical absence
semantic-region hit != exact locator
repeated fragment != independent corroboration
source metadata != proposition provenance
historical evidence != current authority
personal_context.search <= LOCATED
VERIFIED requires authority + exact object + readback
```

Do not bulk-crawl history. Keep probes bounded. A transport or tool failure is DEGRADED, not a retrieval miss.

## Trigger contract

```text
DISCOVERY != AUTO_TRIGGER

TRIGGER when:
  - the user explicitly asks to recall, recover, compare with, or continue
    something from prior chats/history and the exact source is not already known;
  - the current task materially depends on an earlier decision, correction,
    constraint, reference, or episode that is missing from current context;
  - competing historical episodes or wording drift make a direct remembered
    answer unsafe without retrieval.

DO_NOT_TRIGGER when:
  - current-conversation context is already sufficient;
  - the exact historical object/source locator is already known and can be
    read directly;
  - the task only needs current authoritative state, not historical
    reconstruction;
  - the question is generic and does not materially depend on user/project
    history.
```

When a TRIGGER condition holds, load Sonar before guessing from remembered context or asking the user to reconstruct the missing history manually.

Do not copy Superpowers' broad "1% chance means invoke" rule. Sonar has explicit adjacent negative controls: trigger only when historical reconstruction is materially required and the exact source is unknown or ambiguous.

`DISCOVERY` means the host exposes this skill's metadata so it can be selected. `AUTO_TRIGGER` means a matching clean-session request actually causes the host/model to load Sonar before unsupported reconstruction. A discoverable skill is not automatically proven to auto-trigger.

Never claim AUTO_TRIGGER from the contents of this file alone. Prove it with clean-session positive cases plus adjacent negative controls on the target host. If the host cannot expose or auto-trigger skills, report that capability as host-limited rather than simulating it.

## Probe slots

The model-facing skill uses structural slots, not arithmetic counters.

```text
PROBE_SLOTS
  LIGHT_LITERAL     OPTIONAL  UNUSED
  LIGHT_FUNCTIONAL  PRIMARY   UNUSED
  LIGHT_RELATIONAL  PRIMARY   UNUSED
  FULL_EXTRA        ESCALATE  LOCKED
```

Slot transitions are monotonic:

```text
LIGHT_*   UNUSED -> USED
FULL_EXTRA LOCKED -> UNUSED -> USED
```

A slot may be used at most once. Do not maintain or subtract a numeric probe counter in model text.

Rules:

- `LIGHT_LITERAL` may be skipped when no genuine exact historical anchor exists.
- Use `LIGHT_FUNCTIONAL` as the primary discriminating probe.
- Use `LIGHT_RELATIONAL` when another independent relation is needed.
- Stop immediately when the evidence is sufficient for `LOCATED`; unused slots do not need to be consumed.
- Unlock `FULL_EXTRA` only when LIGHT_SONAR is insufficient and a specific escalation mechanic is justified.
- `FULL_EXTRA` permits exactly one additional probe using one selected FULL_SONAR mechanic.
- If the next required slot is already USED, or no eligible UNUSED slot remains, terminate as `UNKNOWN`.
- Transport/provider failure terminates as `DEGRADED`.

When a deterministic helper is available, it may represent the same finite control with an integer or enum internally. The model-facing skill must not rely on free-form arithmetic. Wolfram or another external verifier may check invariants, but is not required as a runtime counter.

## LIGHT_SONAR control block

Use the smallest probe family that can discriminate the target.

```text
LIGHT_SONAR
  LITERAL?      -> exact name / phrase when one is available
  FUNCTIONAL    -> recover by process or function without the headline attractor
  RELATIONAL    -> recover by distinctive relations, roles, or authority structure

LOCATE only when:
  - at least two distinct probe modes carry STRONG evidence;
  - those STRONG receipts belong to at least two distinct correlation groups;
  - at least one STRONG mode is FUNCTIONAL or RELATIONAL;
  - no unresolved DRIFT or CONFLICT remains.

Otherwise:
  - use one eligible UNUSED slot for the next discriminating probe;
  - no eligible slot remains -> UNKNOWN;
  - transport/provider unavailable -> DEGRADED.
```

Assign the same `correlation_id` to propositions that come from the same retrieved fragment or context group. Do not count repeated retrieval of one correlation group as independent evidence, even when different probe modes or wording returned it. A correlation identity is a navigation/deduplication label, not an authority locator.

SEMANTIC may recover a useful region, but LITERAL + SEMANTIC alone is not sufficient to declare LOCATED.

## Probe DSL

Generate probes in this canonical form. This is the normative Sonar query IR.

```text
PROBE <LITERAL|SEMANTIC|FUNCTIONAL|RELATIONAL>
TARGET "<operator-side target label>"
MUST "<required retrieval anchor>"
MUST "<optional second required anchor>"
SHOULD "<supporting relation or clue>"
SHOULD "<optional second supporting clue>"
MUST_NOT "<known distractor>"
MUST_NOT "<optional second distractor>"
TIME "<optional time constraint>"
LIMIT <1..10>
```

Rules:

- `TARGET` is required operator metadata. Never copy it into the rendered retrieval query.
- At least one `MUST` or `SHOULD` clause is required.
- Use at most two clauses of each repeated kind.
- Keep clause order canonical: TARGET, MUST, SHOULD, MUST_NOT, TIME, LIMIT.
- Default `LIMIT` is 5; keep it small.
- `MUST_NOT` is routing control, never positive evidence. Its text can itself become an attractor.
- Keep probe families independent. Do not pack every known anchor into one query.

### Probe mechanics

**LITERAL**

Use exact names or phrases only when they are genuine historical anchors. Do not treat a literal hit as proof that the intended episode was found.

**FUNCTIONAL**

Describe what happened or what the object did without repeating the operator-side target label or headline attractor. Prefer this as the main discriminating probe.

**RELATIONAL**

Search by distinctive relationships: actor -> object, problem -> workaround, issue -> repository, decision -> consequence, authority -> reference. Prefer this when FUNCTIONAL returns an adjacent cluster.

**SEMANTIC**

Use meaning-based paraphrase to recover a broader semantic region. Treat a broad region hit as candidate evidence until discriminated.

## Proposition provenance admission

Classify each displayed proposition separately from the metadata of the container that carried it.

```text
RETRIEVED_HISTORY
  proposition is supported as historical retrieved content

QUERY_CONSTRAINT
  proposition is restated or injected from the current query/instruction

SYNTHESIZED_CONTEXT
  proposition is assembled, summarized, inferred, or generated by the
  retrieval/context layer rather than directly established as historical text

UNKNOWN
  proposition origin cannot be established
```

Historical timestamps, labels such as USER_FACT / USER_CONSTRAINT, or a historical-looking source group do not by themselves establish the provenance of the exact displayed proposition.

Admission rule:

```text
RETRIEVED_HISTORY + STRONG      -> STRONG

QUERY_CONSTRAINT + STRONG       -> WEAK
SYNTHESIZED_CONTEXT + STRONG    -> WEAK
UNKNOWN + STRONG                -> WEAK
```

Never use query-derived, synthesized, or unknown propositions as independent corroboration for LOCATED.

## Evidence classification

Classify the admitted evidence from each probe:

```text
STRONG
  distinctive evidence identifies the intended historical episode well enough
  to justify authority resolution

WEAK
  relevant or adjacent evidence, but identity is partial or ambiguous

DRIFT
  retrieval moved to a nearby but materially different episode/entity

CONFLICT
  retrieved evidence materially conflicts with another candidate or known
  constraint

NONE
  no useful historical evidence was recovered
```

Rank is not confidence. A result moving to the top across repeated calls does not make it stronger evidence.

## Attractor and correction mechanics

When a strong attractor keeps dominating:

1. Do not repeat the same query with cosmetic wording changes.
2. Add a FUNCTIONAL or RELATIONAL probe that omits the attractor.
3. If a known distractor is contaminating results, place it in `MUST_NOT`.
4. Treat the negative instruction as QUERY_CONSTRAINT, never evidence.
5. If the recovered episode has a later correction, probe the correction separately.
6. Preserve both the original claim and correction until authority resolution.
7. If evidence remains conflicting, return UNKNOWN rather than averaging it into confidence.

## Temporal mechanic

Use `TIME` only when time disambiguates competing episodes.

Newer adjacent context may outrank an older intended target. Recency is a routing clue, not evidence that the newer episode is the requested one.

## Falsifier mechanic

When a candidate appears strong, ask what observation would show that it is the wrong episode.

Prefer a falsifier that changes identity, relation, correction state, or time window. Do not use a merely synonymous re-query as a falsifier.

A failed falsifier does not prove truth; it only increases confidence that the candidate region is worth resolving through authority.

## Authority handoff

Once navigation reaches LOCATED, stop broad probing and resolve the exact object.

Prefer the authority that owns the claim:

```text
historical chat/message claim  -> Session Search or exact history store
repository/current Git state   -> GitHub / canonical repository
durable memory claim           -> memory provider with provider readback
file/document claim            -> Files or the owning document provider
other external claim           -> the smallest authoritative source available
```

If the needed authority is unavailable, report DEGRADED. Do not promote a `personal_context.search` result to RESOLVED or VERIFIED.

Resolution states:

```text
ROUTED
  authority selected, exact object not yet found

RESOLVED
  exact object found, readback not yet verified

VERIFIED
  exact object found and authority readback verified

DEGRADED
  required authority unavailable or execution failed
```

## FULL_SONAR escalation

Do not enter FULL_SONAR automatically after an ordinary miss.

Escalate only when LIGHT_SONAR is insufficient and the task materially depends on deeper reconstruction.

FULL_SONAR reuses the same Probe DSL. Add only the mechanic needed by the failure:

```text
SEMANTIC             -> broader meaning-based region recovery
RELATIONAL/AUTHORITY -> distinctive role or ownership relation
TEMPORAL             -> competing episodes separated by time
CORRECTION           -> later correction or reversal
FALSIFIER            -> evidence that would disconfirm the candidate
EPISTEMIC_BOUNDARY   -> recover uncertainty, caveat, or explicit non-claim
SOURCE               -> recover the likely authority route
```

Use exactly one selected FULL_SONAR mechanic through the single `FULL_EXTRA` slot. Stop when that slot is USED, when the next probe would only repeat the same attractor or fragment, or when no eligible slot remains. Terminate as UNKNOWN rather than opening another probe.

## Evaluation trace

For tests, debugging, or explicit requests for a Sonar trace, emit a compact receipt:

```text
SONAR_TRACE v0
STATE <UNLOCATED|LOCATED|ROUTED|RESOLVED|VERIFIED|DEGRADED|UNKNOWN>
SLOT <LIGHT_LITERAL|LIGHT_FUNCTIONAL|LIGHT_RELATIONAL|FULL_EXTRA> <UNUSED|USED|LOCKED>
PROBE <MODE> <EVIDENCE> <PROVENANCE> GROUP <correlation_id>
PROBE <MODE> <EVIDENCE> <PROVENANCE> GROUP <correlation_id>
AUTHORITY <SESSION_SEARCH|GITHUB|MEMORY_PROVIDER|FILES|OTHER|UNKNOWN>
NEXT <PROBE|RESOLVE_AUTHORITY|VERIFY_READBACK|NONE>
BOUNDARY "<short reason>"
```

For ordinary user-facing answers, do not dump the trace unless it helps. State uncertainty and degraded routes plainly.

## Execution discipline

When this repository's helper implementation is available:

- use the repository Query DSL semantics rather than inventing another query format;
- treat `sonar/sonar_query.lark` and `scripts/sonar_query.py` as the executable probe grammar/renderer;
- treat `scripts/sonar_decision.py` as the typed navigation/provenance admission and authority-state implementation;
- keep private historical corpus content out of public repository artifacts;
- preserve exact receipts for behavioral evals without copying private retrieved text into Git.
