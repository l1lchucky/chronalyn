# Chronalyn Documentation

Chronalyn is an AI agent memory orchestration layer and **Hermes Agent memory
provider**: Hindsight for persistent memory, recall, and reflection; Mnemosyne
for verified checkpoints and bounded fallback; one provider visible to Hermes.

## Getting started

- [Installation](installation.md) — install Chronalyn for Hermes Agent
- [Guided setup](guided-setup.md) — the interactive setup wizard
- [Why use the router?](why-use-the-router.md) — the problem Chronalyn solves

## Architecture and concepts

- [Architecture](architecture.md) — Hermes, Chronalyn, Hindsight, Mnemosyne
- [Routing policies](routing-policies.md) — normal, checkpoint, recall, fallback
- [Data model](data-model.md) — records, deliveries, metadata
- [Deployment models](deployment-models.md) — external vs managed backends
- [Dual-memory setup UI](dual-setup-ui.md) — the in-terminal wizard

## Configuration

- [Configuration](configuration.md) — namespaces, environments, routing
- [Hermes integration](hermes-integration.md) — the Hermes memory-provider contract
- [Strict compatibility](strict-compatibility.md) — Hermes compatibility policy

## Operations

- [Operations](operations.md) — status, health, day-to-day management
- [Database operations](database-operations.md) — safe SQLite administration
- [Backup and rollback](rollback.md) — restore previous configuration
- [Migration](migration.md) — upgrading from Hermes Memory Router
- [Rename migration matrix](rename-migration-matrix.md) — old vs new identity
- [Failure recovery](failure-recovery.md) — handling backend failures
- [Uninstall and data retention](uninstall-and-data-retention.md) — what is kept

## Security and privacy

- [Privacy](privacy.md) — what is stored and where
- [Threat model](threat-model.md) — trust boundaries
- [Trusted bootstrap](trusted-bootstrap.md) — first-run trust chain

## Validation and development

- [Live validation](live-validation.md) — real-backend test results
- [Limitations](limitations.md) — current limitations
- [Release candidate limitations (historical)](rc-limitations.md)
- [Upgrading](upgrading.md) — version upgrade paths
- [Compatibility](compatibility.md) — Python and Hermes support
- [Development](development.md) — build, test, lint, release
