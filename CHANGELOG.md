# Changelog

The project follows Semantic Versioning and the Keep a Changelog format.

## [Unreleased]

## [1.1.0] - unreleased

Managed lightweight Hindsight for fresh installations.

### Added

- **Lightweight local Hindsight (managed)** — a new option in the guided setup
  that installs, configures, and starts a local Hindsight API automatically:
  isolated venv under `$HERMES_HOME/hindsight-managed/`, `hindsight-api-slim`
  with embedded PostgreSQL + pgvector, remote OpenAI-compatible LLM and
  embeddings, one API worker, access log off, loopback-only.
- **Four-input setup** — for managed mode the wizard asks only for the
  OpenAI-compatible base URL, API key, LLM model, and embedding model.
- **Automatic embedding-dimension detection** — the installer probes the
  embedding endpoint before starting Hindsight.
- **Managed service lifecycle** — systemd `--user` service (auto-start,
  restart on failure) when available, launcher-script fallback otherwise;
  never requires sudo; never touches external Hindsight processes.
- **`chronalyn status` / `chronalyn doctor`** now report the managed Hindsight
  service state (running / stopped / unhealthy).
- **Mnemosyne wiring** — same remote embedding provider/model as Hindsight,
  LLM disabled, `top_k=5`, separate checkpoint bank.

### Changed

- Version 1.1.0.

### Unchanged

- Routing policy is unchanged: normal/retain/reflect reach Hindsight only,
  checkpoint reaches Hindsight + Mnemosyne, recall is Hindsight-first with
  bounded Mnemosyne fallback, merged recall remains prohibited.
- Existing external Hindsight configurations are never started, stopped, or
  modified by Chronalyn.
- No automatic memory migration or re-embedding.

## [1.0.0] - 2026-08-17

First stable release.

### Added

- **Native Hermes plugin installation.** Chronalyn can be installed from inside
  Hermes with `hermes plugins install l1lchucky/chronalyn`, then
  selected in `hermes memory setup`. The Chronalyn wizard runs inside the Hermes
  flow via the provider's `post_setup` hook — no separate CLI step is required.
- **Hindsight-only mode** — Hindsight handles every memory operation; Mnemosyne
  is neither installed nor configured.
- **Dual memory mode** — Hindsight for normal memory; Mnemosyne for verified
  checkpoints and bounded fallback.
- **Provider-neutral embedding configuration** — an OpenAI-compatible embedding
  backend can be configured for Mnemosyne semantic recall; Mnemosyne's LLM is
  disabled by default.
- **Hindsight embedding-backend guidance** — embedding providers are
  interchangeable as long as the target vector index is rebuilt (equal
  dimensions do not imply compatible vector spaces).
- **Hindsight 0.9 metadata compatibility** — outbound Hindsight metadata is
  normalized to `dict[str, str]` deterministically, without mutating caller
  metadata.
- **Verified Mnemosyne checkpoints** with durable delivery, retry, and safe
  deletion.
- **Backup and rollback** for configuration and the control database.
- **Native Hermes coexistence** — three complementary memory layers: Hermes
  native memory, Chronalyn (Hindsight + Mnemosyne), and Skills.

### Changed

- README recommended installation path is the Hermes-native flow; the
  Python package path (`pip install chronalyn`) remains supported.
- Public repository renamed to `l1lchucky/chronalyn`.
- Release artifacts (wheel, sdist, SBOM, checksums) are named from the release
  tag instead of a hard-coded version.

## [1.0.0-rc.1] - 2026-08-04

This is a **release candidate**. Local tests do not prove production readiness.
Live Hindsight and Mnemosyne testing plus a staging soak are still required
before a stable 1.0.0. See `docs/rc-limitations.md`.

### Changed — project renamed to Chronalyn

The project is renamed from Hermes Memory Router to **Chronalyn**, a persistent
engineering-intelligence layer for AI agents and software teams. This release
candidate implements memory orchestration for Hermes Agent only.

- Distribution renamed `hermes-memory-router` → `chronalyn`.
- Python package renamed `hermes_memory_router` → `chronalyn`.
- Primary CLI renamed `hermes-memory-router` → `chronalyn`.
- Preferred Hermes provider id renamed `hermes_memory_router` → `chronalyn`.
- Guided setup command renamed `setup-dual` → `setup`.
- Version is `1.0.0rc1` (Python) / `v1.0.0-rc.1` (human).

Durable on-disk identities are deliberately **unchanged** so existing
installations keep working without data migration: `$HERMES_HOME/memory-router/`
still holds configuration, the state database, and backups; namespaces,
environments, profile bindings, bank ids, routing policy values, and
`memory_router_*` tool names are untouched.

### Fixed — Hermes provider installation (RC blocker)

Two defects were found by probing the installed Hermes runtime directly. Either
one alone prevented Hermes from discovering the provider.

- **Wrong installation root.** Entries were written to
  `$HERMES_HOME/plugins/memory/<id>/`, which Hermes never scans for
  user-installed providers. Entries now install to `$HERMES_HOME/plugins/<id>/`,
  the path `plugins/memory/__init__.py::_iter_provider_dirs` actually reads.
- **Entry file failed the discovery heuristic.** Hermes gates user provider
  directories on the literal substring `register_memory_provider` or
  `MemoryProvider` in `__init__.py`. The previous entry exported
  `HermesMemoryRouterProvider` — which contains neither — so the directory was
  skipped even at the correct path. Entries now call
  `ctx.register_memory_provider(...)` explicitly.

Manifests now declare `kind: exclusive`, so Hermes' generic plugin manager
records the manifest without importing the module and leaves activation to
memory-category discovery via `memory.provider`.

### Added — backward compatibility

- `hermes-memory-router` remains an installed console command. It invokes
  Chronalyn and prints a deprecation warning to **stderr**, so `--json` output
  on stdout stays machine-readable. Exit codes are propagated unchanged.
- The legacy provider id `hermes_memory_router` is installed as a compatibility
  entry and stays loadable, so an existing `memory.provider:
  hermes_memory_router` configuration keeps working.
- `import hermes_memory_router` still works via a shim that aliases submodules
  to the identical `chronalyn` module objects, preserving class identity and
  `isinstance` checks. It emits a `DeprecationWarning`.
- `HermesMemoryRouterProvider` remains an alias of `ChronalynMemoryProvider`.
- `setup-dual` remains a deprecated alias of `setup`.
- Conflict detection recognises the legacy provider id, so a pre-rename install
  paired with another provider is still reported as a conflict.
- Configuration backups now cover provider entries for **both** provider ids at
  the real discovery root, so rollback restores whichever entry was installed.

### Security and data safety

- Provider installation refuses to overwrite a directory it does not own,
  detected via a `.chronalyn-managed` marker; all targets are validated before
  any write, so a refusal cannot leave a half-installed state.
- Uninstall removes only Chronalyn-managed provider entries and the package.
  Router configuration, the state database, backups, Hindsight data and
  Mnemosyne data are retained. Deleting data remains a separate explicit action.
- Routing policy is unchanged: normal turns write to Hindsight only; verified
  checkpoints write to Hindsight and Mnemosyne; recall is Hindsight-first with
  bounded checkpoint fallback and is never merged; cron, flush and subagent
  output are not automatically retained; raw tool messages stay disabled; and
  destructive model-requested operations remain disabled by default.

### Removed

- `src/chronalyn/resources/` templates. Provider entries and manifests are now
  generated from a single source of truth in `chronalyn.plugin_entry`, removing a
  second, drifting copy of the manifest.

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
