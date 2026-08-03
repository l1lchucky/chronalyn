# ADR 0001: Asymmetric memory routing

- Status: Accepted
- Date: 2026-08-03

## Context

Hermes deliberately activates one external memory provider. Running multiple
equal providers would duplicate tool schemas, prompt context, extraction work,
and deletion state.

## Decision

Expose one composite Hermes provider:

- Hindsight owns automatic turn retention, primary recall, and reflection.
- Mnemosyne owns verified checkpoint storage and bounded fallback.
- A local SQLite control plane owns logical IDs, idempotency, retries, deletion
  mapping, and audit events.

## Consequences

Benefits:

- one authoritative automatic backend;
- no duplicate normal-turn writes;
- deterministic fallback;
- recoverable partial failure;
- backend-independent logical record IDs.

Costs:

- another SQLite database;
- custom adapter maintenance;
- eventual consistency between checkpoint backends;
- live compatibility testing after backend upgrades.

## Rejected alternatives

- Equal automatic fan-out to every provider.
- Automatic merging of both recall result sets.
- Mnemosyne-only or Hindsight-only checkpoint handling.
- Importing Hermes' private bundled Hindsight provider implementation.
