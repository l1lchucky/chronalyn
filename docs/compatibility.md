# Compatibility

Chronalyn is the public product identity. `1.0.0rc1` (`v1.0.0-rc.1`) is a
release candidate, not a production-readiness claim.

## Public and temporary compatibility names

| Surface | Primary name | Temporary compatibility name |
|---|---|---|
| Product / distribution / Python package | Chronalyn / `chronalyn` / `chronalyn` | `import hermes_memory_router` remains a deprecated shim |
| CLI | `chronalyn` | `hermes-memory-router` invokes the same implementation and warns on stderr |
| Hermes memory-provider id | `chronalyn` | `hermes_memory_router` loads the same provider implementation |

The compatibility command propagates Chronalyn's exit status and keeps stdout
machine-readable. The compatibility provider and import path are temporary and
will be removed in a future major release; new configuration should use
`chronalyn`.

## Exact Hermes provider contract

Hermes discovers user memory providers in the flat directory:

```text
$HERMES_HOME/plugins/<provider-id>/
├── __init__.py
└── plugin.yaml
```

Chronalyn therefore installs both `$HERMES_HOME/plugins/chronalyn/` and
`$HERMES_HOME/plugins/hermes_memory_router/`. It does **not** install under the
older, incorrect `$HERMES_HOME/plugins/memory/` path.

The installed Hermes runtime was probed with a disposable `HERMES_HOME` to
confirm that its user-provider discovery heuristic scans the first 8 KiB of
`__init__.py` for the literal `register_memory_provider` or `MemoryProvider`.
Chronalyn's entry satisfies that heuristic and exposes the supported
`MemoryProvider` implementation. Both manifests declare `kind: exclusive`.
Hermes selects one external provider through `memory.provider`; the two ids are
aliases, not two simultaneously active provider modules.

See [Hermes integration](hermes-integration.md) for the detailed mechanism and
[Migration](migration.md) for the compatibility window.

## Adoption, planning, backup, and rollback

An existing direct Hindsight installation can be adopted without copying,
reindexing, or renaming its memories. Chronalyn detects the current provider and
Hindsight connection, displays current and proposed configuration before any
mutation, and requires confirmation. Configuration files and both flat plugin
entries are included in the pre-change backup.

`chronalyn rollback --yes` restores the saved configuration and previous active
provider, including direct `hindsight`, without deleting Hindsight, Mnemosyne, or
Chronalyn database data. See [Rollback](rollback.md).

## Uninstall and retained data

Uninstall removes the Chronalyn distribution and Chronalyn-owned provider
entries. It does not remove the control database, configuration backups,
Hindsight data, Mnemosyne data, or credentials shared with Hermes. Data deletion
is a separate explicit operation; backend deletes should be propagated before
removing local state. See [Uninstall and data retention](uninstall-and-data-retention.md).

## Supported range and limits

| Component | RC compatibility statement |
|---|---|
| Python | 3.11, 3.12, and 3.13 are configured in CI; this continuation validates the installed local version only |
| Hermes Agent | Installed-runtime discovery is validated against the current local Hermes runtime; other Hermes versions require staging validation |
| Hindsight API | Code targets v1 retain, recall, reflect, health, version, and document-delete endpoints |
| Mnemosyne | Optional package constraint is `mnemosyne-memory>=3.15,<4` |
| Production operating system | Linux is the intended production platform |

Compatibility is intentionally limited to the documented aliases. Chronalyn
does not promise compatibility with private Hermes APIs, arbitrary third-party
memory providers, unknown Hindsight/Mnemosyne versions, or future host discovery
changes.

### Windows

Windows is suitable for local development and tests, but it is not the declared
production platform. Curses may be unavailable in the host Python, so the guided
setup TUI can require WSL or the non-interactive commands. Device Guard / WDAC
may block newly generated console-script `.exe` launchers; package metadata and
`python -m chronalyn.cli` can validate the entry point, but that is not proof the
blocked executable ran.

### POSIX and live backends

Local `bash -n` checks shell syntax only. Linux GitHub Actions remain responsible
for unrestricted POSIX execution, permissions, symlinks, and console-script
behavior. The automated suite uses fake Hindsight and Mnemosyne backends. It does
not prove live retain/recall/reflect/delete behavior, a staging soak, coordinated
restore, throughput, or production failure recovery.

See [Release-candidate limitations](rc-limitations.md) and
[Live validation](live-validation.md).

## Upgrade rule

Test every Chronalyn, Hermes, Hindsight, or Mnemosyne upgrade on staging first.
Back up the Chronalyn database and all backend stores before changing production.
