# Release-candidate limitations

Chronalyn `1.0.0rc1` (`v1.0.0-rc.1`) is a **release candidate**, not a stable
release. Read this before installing it anywhere that matters.

## This is an RC

- The version is deliberately a pre-release. Package managers treat `1.0.0rc1`
  as a pre-release and will not install it without an explicit opt-in.
- Interfaces may still change before the stable `1.0.0`.

## Local tests do not prove production readiness

The automated suite runs against **local fake backends** for routing, retry, and
failure scenarios. It proves the router's internal logic and the Hermes
discovery contract; it does **not** prove that your Hindsight or Mnemosyne
deployment behaves correctly under real load.

What the suite does cover:

- routing policy (normal turn, checkpoint, recall, fallback, no merged recall);
- write/delete ordering, including a delete racing an in-flight write;
- configuration detection, migration planning, backup, and rollback;
- provider discovery against Hermes' real contract, verified against an
  installed Hermes rather than from documentation;
- both CLI commands, the deprecation warning, and the legacy provider id;
- a fresh install of the built wheel into a clean virtual environment;
- Windows path handling and POSIX installer syntax.

## Still required before production

1. **Live Hindsight testing.** Point Chronalyn at a real Hindsight API and
   confirm retain, recall, reflect, health, and delete against live data.
2. **Live Mnemosyne testing.** If you enable dual mode, confirm checkpoint
   writes, bounded fallback recall, and delete propagation.
3. **A staging soak.** Run a representative workload on staging for long enough
   to exercise restarts, retries, queue drain, and backup/restore. A short smoke
   test is not a soak.
4. **Restore rehearsal.** Practise `db backup` → `db verify-backup` → restore on
   staging before you need it.

Follow [Live validation](live-validation.md) step by step and do not skip the
failure-injection sections.

## Known environment-specific notes

- **Windows console-script stubs and Device Guard / WDAC.** On a host with an
  application-control policy, a freshly generated `.exe` console-script launcher
  can be blocked by policy. During RC validation on Windows,
  `chronalyn.exe` ran normally while the `hermes-memory-router.exe`
  compatibility stub was blocked by local Device Guard policy. This is a host
  policy artifact, not a packaging defect: the entry point is declared correctly
  in the wheel and works when invoked as
  `python -m chronalyn.cli` or via the module entry point. If you hit this,
  either allow the launcher in your policy or use `python -m chronalyn.cli`.
- **Hermes must be importable for `status` and `doctor`.** Those commands verify
  Hermes' `MemoryProvider` contract, so run them with the Python environment
  that has Hermes installed. Chronalyn is normally installed *into* Hermes' own
  runtime, where this is automatic. The `db` subcommands do not require Hermes.

## Not implemented in this release candidate

These are roadmap items. They are **not** present in this release, and no part
of the RC should be read as delivering them:

- Chronalyn Console (dashboard / web UI)
- Chronalyn Intelligence (change intelligence)
- automated bug discovery
- deployment analysis

## Scope of the rename

The rename to Chronalyn is deliberately conservative. Durable on-disk
identities are unchanged, so no data migration is required:

- `$HERMES_HOME/memory-router/` still holds configuration, the state database,
  and backups;
- namespaces, environments, profile bindings, and bank ids are untouched;
- routing policy values (`hindsight-only`,
  `hindsight-primary-mnemosyne-checkpoints`) are unchanged;
- `memory_router_*` tool names are unchanged.

Compatibility aliases (old CLI, old provider id, old import path) are
**temporary** and will be removed in a future major release.
