# Chronalyn rename migration matrix

> **Historical note (2026-08-17):** the repository rename described below as
> "future" has since been completed: `l1lchucky/hermes-memory-router` is now
> `l1lchucky/chronalyn` (same repository, redirects preserved). This matrix is
> retained as the historical record of the brand/compatibility migration.

This matrix was created from the clean `rename-and-prepare-rc` baseline at
`7587737f623c6d05cf84ac077eec2d40e762654e` before implementation changes.
It distinguishes public identity from durable compatibility identities; it is
not a global-search replacement plan.

| Surface | Existing identity | RC identity | Migration and compatibility treatment |
|---|---|---|---|
| Brand | Hermes Memory Router | Chronalyn | Rename user-facing product copy. Describe the implemented RC as memory orchestration for Hermes; keep dashboard and intelligence capabilities on the roadmap. |
| GitHub repository/remote | `l1lchucky/hermes-memory-router` | future `l1lchucky/chronalyn` | Do not rename the remote in this task. Existing repository URLs remain valid until the repository is renamed; release docs distinguish current and future names. |
| PyPI distribution | `hermes-memory-router` | `chronalyn` | Build only the `chronalyn` distribution at `1.0.0rc1`. Upgrade documentation explains the distribution-name change. |
| Python implementation package | `hermes_memory_router` | `chronalyn` | Move implementation to `chronalyn`. Ship a temporary `hermes_memory_router` import shim for source compatibility. Do not duplicate implementation or data. |
| Primary CLI | `hermes-memory-router` | `chronalyn` | Add `chronalyn`; retain `hermes-memory-router` as a temporary alias that emits a deprecation warning to stderr and invokes the same command implementation. |
| CLI setup command | `setup-dual` | `setup` | Make `setup` the guided setup command. Retain `setup-dual` as a deprecated command alias during the compatibility window. |
| Hermes provider ID | `hermes_memory_router` | `chronalyn` | Install/discover the canonical `$HERMES_HOME/plugins/chronalyn` provider. Also install a legacy `$HERMES_HOME/plugins/hermes_memory_router` adapter so existing `memory.provider: hermes_memory_router` configurations remain loadable. Migration to `chronalyn` is previewed, backed up, and applied only after confirmation. |
| Hermes provider mechanism | nested `$HERMES_HOME/plugins/memory/hermes_memory_router` copied files | standalone user memory plugin at `$HERMES_HOME/plugins/<provider-id>/` | Correct the installer to the current public Hermes discovery contract. A provider directory contains `__init__.py` with `register(ctx)`/`MemoryProvider` and optional `plugin.yaml`; activation uses `hermes config set memory.provider <id>`. No Hermes core edits or invented entry-point group. |
| Router configuration path | `$HERMES_HOME/memory-router/config.json` | unchanged for RC | Preserve as a durable compatibility path so upgrades open the same config without copying or migration. New docs identify it as the legacy-stable Chronalyn state location. |
| Router state database path | configured path, default under `$HERMES_HOME/memory-router/` | unchanged for RC | Preserve path, schema, namespace, environment, and profile fingerprint. No memory copy, recreation, reindex, or durable-identity rename. |
| Backup path | `$HERMES_HOME/memory-router/backups/` | unchanged for RC | Preserve and extend backup coverage to canonical and legacy plugin entries. Rollback restores exact pre-change files and removes entries absent at backup time. |
| Hindsight configuration | `$HERMES_HOME/hindsight/config.json`, `HINDSIGHT_API_KEY` | unchanged | Detect and adopt in place. Preserve unknown Hindsight settings, bank IDs, endpoint, mode, and secrets. Never copy or delete Hindsight data. |
| Mnemosyne configuration/data | optional `mnemosyne-memory`, configured bank/data directory | unchanged | Remains opt-in. Setup must not silently install or enable it. Preserve bank and data directory; uninstall never deletes backend data. |
| Routing policy IDs | `hindsight-only`, `hindsight-primary-mnemosyne-checkpoints` | unchanged | Durable policy values and semantics remain unchanged to avoid behavioral migration. |
| Tool names | `memory_router_*` | unchanged for RC | Preserve model/tool compatibility and routing safety. Branding can change later through a separately versioned migration. |
| Environment variables | `HERMES_HOME`, `HERMES_PYTHON`, `HINDSIGHT_API_KEY`, `HMR_PACKAGE_SOURCE`, `HMR_NO_ANIMATION` | preserve existing; add `CHRONALYN_*` only where needed | Existing variables remain accepted. New variables must not carry durable identity or secrets unnecessarily. Secrets remain in `$HERMES_HOME/.env`. |
| Installer/release artifacts | `hermes_memory_router-0.2.0b1-*`, old checksum/SBOM names | `chronalyn-1.0.0rc1-*`, `SHA256SUMS-chronalyn-v1.0.0-rc.1.txt`, `chronalyn-v1.0.0-rc.1.spdx.json` | Update build/release naming consistently. Keep current repository download origin until a later remote rename. |
| User-Agent | `hermes-memory-router/0.2.0-beta.1` | `chronalyn/1.0.0-rc.1` | Safe protocol metadata rename; no backend identity or data migration. |
| Uninstall | removes router package/plugin | removes Chronalyn package and both plugin adapters only | Backend data, state database, config, backups, Hindsight, and Mnemosyne data are retained unless the user runs a separate explicit data-deletion action. |

## Invariants during migration

- No namespace, environment, profile binding, bank ID, database schema identity,
  record ID, or backend data path is renamed by the brand migration.
- Existing configuration is detected and presented as a plan before mutation.
- Every activation/configuration mutation is preceded by a backup and explicit
  confirmation.
- Rollback restores direct Hindsight or the exact previously configured provider.
- Hermes sees exactly one configured external memory provider.
- Normal turns write only to Hindsight; verified checkpoints may write to both;
  recall is Hindsight-first with bounded checkpoint fallback and never merged.
- Cron, flush, subagent output, and raw tool messages are not automatically retained.
- Destructive model-requested operations remain disabled by default.

## Audited baseline

- Root: `C:/Users/LENOVO/hermes-memory-router`
- Branch: `rename-and-prepare-rc`
- Commit: `7587737f623c6d05cf84ac077eec2d40e762654e`
- Remote: `origin https://github.com/l1lchucky/hermes-memory-router.git`
- Working tree: clean before this matrix was added
- Distribution/version: `hermes-memory-router 0.2.0b1`
- CLI entry point: `hermes-memory-router = hermes_memory_router.cli:main`
- Provider ID: `hermes_memory_router`
- Previous integration implementation: copied a provider entry under
  `$HERMES_HOME/plugins/memory/hermes_memory_router`.

## Integration defects found by probing the installed Hermes

Both defects below were reproduced against the installed Hermes at
`C:/Users/LENOVO/AppData/Local/hermes/hermes-agent` using a temporary
`HERMES_HOME`, not inferred from documentation.

1. **Wrong installation root.** User-installed memory providers are discovered by
   `plugins/memory/__init__.py::_iter_provider_dirs`, which scans
   `$HERMES_HOME/plugins/<name>/` only. A directory installed at
   `$HERMES_HOME/plugins/memory/<name>/` is never discovered
   (`find_provider_dir` returned `None`). The RC installs to
   `$HERMES_HOME/plugins/<provider-id>/`.
2. **Entry file failed the discovery heuristic.** For user-installed
   directories, `_is_memory_provider_dir` requires the literal substring
   `register_memory_provider` or `MemoryProvider` in the first 8 KiB of
   `__init__.py`. The old entry exported `HermesMemoryRouterProvider`, which does
   not contain `MemoryProvider` as a substring, and did not mention
   `register_memory_provider`, so the directory was skipped even when placed at
   the correct root. The RC entry file calls
   `ctx.register_memory_provider(...)` explicitly.

Additionally, `plugin.yaml` must declare `kind: exclusive` so the generic plugin
manager records the manifest but does not import the module
(`hermes_cli/plugins.py`), leaving activation to memory-category discovery via
`memory.provider`. Without an explicit kind, Hermes auto-coerces to `exclusive`
using the same text heuristic; the RC declares it explicitly rather than relying
on inference.
