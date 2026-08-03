# Changelog

The project follows Semantic Versioning and the Keep a Changelog format.

## [0.2.0-beta.1] - 2026-08-03

### Added

- Hindsight-only mode alongside the dual checkpoint policy.
- Read-only discovery and guided adoption of existing Hindsight setups.
- Explicit add/remove flow for Mnemosyne with no historical migration.
- Profile, namespace, and environment binding for router databases.
- Strict conflict detection when the router and child providers are both active.
- Two-stage, short-lived confirmation for model-requested deletion.
- Configuration backup, rollback, and schema upgrade commands.
- Lightweight monochrome dual-setup interface with arrows, number keys, Space,
  Enter, optional mouse support, and Pac-Man progress animation.
- One-command trusted bootstrap with checksum checks and official Hermes install
  handoff when Hermes is missing.
- Cloud transmission acknowledgement and owner-only secret writes.

### Changed

- Mnemosyne is now an optional dependency and is installed only for dual mode.
- Prefetch returns plain text so Hermes owns memory-context fencing.
- The default Hermes tool set is smaller and administrative actions stay in the
  CLI.
- Public documentation was rewritten for clearer setup, privacy, recovery, and
  deployment guidance.

### Removed

- Automatic assumption that Mnemosyne is always present.
- Direct model access to one-step destructive deletion.

## [0.1.0-alpha.1] - 2026-08-03

### Added

- Initial Hindsight-primary and Mnemosyne-checkpoint router.
- Hindsight REST adapter and Mnemosyne Python adapter.
- SQLite outbox, backend mappings, retry state, audit events, and deletion
  tracking.
- Secret redaction and rejection.
- Primary-context-only automatic retention.
- Initial CLI, examples, tests, and project documentation.
