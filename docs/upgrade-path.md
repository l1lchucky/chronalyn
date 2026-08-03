# Upgrade path

## Current phase: 0.1 alpha

The alpha establishes the safety model:

- Hindsight-first recall;
- Hindsight-only automatic writes;
- Hindsight plus Mnemosyne checkpoints;
- durable SQLite outbox;
- retry and dead-letter states;
- logical IDs and coordinated deletion;
- redaction/rejection;
- primary-context-only retention.

The release is suitable for controlled staging evaluation. It is not presented
as production-certified until the live validation matrix passes against the
specific Hermes, Hindsight, and Mnemosyne versions being deployed.

## 0.2 beta goals

- complete live Hermes integration fixtures in CI;
- version-probe both backends and expose compatibility warnings;
- add database migration command and schema backup command;
- add structured metrics for Prometheus/OpenTelemetry;
- add configurable health/readiness endpoints or command output;
- improve backend receipt normalization;
- add a repair command for orphaned backend records;
- add Hindsight scoped-tag filtering in recall;
- add optional write approval for checkpoints;
- publish signed GitHub release artifacts.

## 0.3 release-candidate goals

- repeated staging soak tests;
- controlled production canary;
- backup/restore and disaster-recovery test evidence;
- dependency upgrade matrix across Python 3.11–3.13;
- documented Hermes upgrade tests;
- confirmed behavior during concurrent gateway shutdown and restart;
- operator dashboards and alert examples;
- stable configuration schema.

## 1.0 requirements

- no known data-loss or cross-environment isolation defects;
- backward-compatible configuration and database migration policy;
- live integration CI or published compatibility test evidence;
- stable deletion semantics for both backends;
- documented security-response process;
- at least one tested self-hosted deployment and one tested Hindsight Cloud
  deployment;
- release signing, provenance, SBOM, and verified installation instructions.

## Future optional adapters

A generic adapter interface exists, but new backends should not be added merely
to increase the provider count. A new adapter must define:

- its exact routing role;
- stable external identifiers;
- idempotent retain behavior;
- deletion behavior;
- health and retry behavior;
- privacy boundary;
- failure and conflict policy.

Potential future adapters include Honcho or a remote Mnemosyne service, but each
requires a separate architectural decision record and threat-model update.

## Upgrade procedure for operators

1. Stop automatic upgrades in production.
2. Record the current router, Hermes, Hindsight, and Mnemosyne versions.
3. Drain the router outbox and verify zero failed/dead deliveries.
4. Back up router SQLite, Mnemosyne, and Hindsight.
5. Upgrade staging first.
6. Run unit checks and the full live validation matrix.
7. Run unique staging/production isolation markers.
8. Canary the new version on one non-critical Hermes profile.
9. Upgrade production during a rollback-capable window.
10. Verify status, checkpoint dual write, recall, deletion, and logs.

## Rollback

The quickest functional rollback is to disable the router and return Hermes to
direct Hindsight. Preserve the router database and Mnemosyne bank so pending
operations can be investigated rather than discarded.
