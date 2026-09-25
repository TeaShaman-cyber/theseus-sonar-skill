# Contributing

This repository is a public experimental implementation line. Small, reviewable, evidence-backed changes are preferred over broad speculative rewrites.

## Before changing behavior

1. Find or open the narrow issue that covers the change.
2. Confirm the intended invariant and acceptance criteria.
3. Keep private account data, conversation exports, credentials, and local retrieval state out of the repository.
4. Prefer the smallest change that can be independently verified.

Issue #1 currently covers the initial Sonar skill prototype.

## Development flow

Create a bounded branch, make the change, then run:

```bash
tools/dev/check
```

A pull request should state:

- the covering issue;
- the behavior or invariant changed;
- the exact validation performed;
- any intentionally unverified boundary;
- whether the change affects permissions, authority, publication, or upstream compatibility.

Do not optimize a metric merely to make CI green. A negative or unresolved fixture may correctly remain `UNKNOWN`.

## Review and promotion

Before merge:

- base/currentness and exact head must be known;
- repository-native QA must pass;
- no known blocker may remain;
- the change must stay within the issue scope;
- external publication or release must not be smuggled into an implementation PR.

After merge, verify the authoritative remote state rather than relying only on executor self-report.

## External upstream work

An upstream feature issue or repository link is evidence and coordination, not standing authority to publish code or comments externally. Upstream submissions are reviewed and authorized separately.
