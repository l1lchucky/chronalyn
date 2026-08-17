# Migration from Hermes Memory Router

Chronalyn was previously released as Hermes Memory Router. This guide covers
upgrading an existing installation.

**Nothing is migrated silently.** Existing configuration is detected, backed up,
shown to you as a plan, and changed only after you confirm.

## What is guaranteed not to happen

Migration never:

- recreates memories;
- copies historical memories between backends;
- reindexes data;
- changes namespaces;
- changes environments;
- changes profile bindings;
- renames durable database identifiers;
- deletes Hindsight or Mnemosyne data.

## What actually changes

| Surface | Before | After |
|---|---|---|
| Distribution | `hermes-memory-router` | `chronalyn` |
| Python package | `hermes_memory_router` | `chronalyn` |
| CLI | `hermes-memory-router` | `chronalyn` |
| Setup command | `setup-dual` | `setup` |
| Hermes provider id | `hermes_memory_router` | `chronalyn` |
| Version | `0.2.0b1` | `1.0.0` |

## What deliberately does not change

These are durable identities. Renaming them would strand existing data, so they
are kept exactly as they were:

- `$HERMES_HOME/memory-router/` — configuration, state database, backups;
- namespaces, environments, profile bindings, and Hindsight/Mnemosyne bank ids;
- routing policy values `hindsight-only` and
  `hindsight-primary-mnemosyne-checkpoints`;
- `memory_router_*` Hermes tool names;
- `HERMES_HOME`, `HERMES_PYTHON`, and `HINDSIGHT_API_KEY`.

Your existing database keeps working with no schema change and no reindex.

## Steps

1. **Back up first**, independently of the automatic backup:

   ```bash
   hermes-memory-router db backup --output /secure/path/pre-chronalyn.sqlite
   hermes-memory-router db verify-backup --path /secure/path/pre-chronalyn.sqlite
   ```

2. **Install Chronalyn** into Hermes' Python environment. It replaces the old
   distribution; the old import path keeps working through a shim.

   ```bash
   python -m pip install chronalyn
   ```

3. **Review the plan without applying it:**

   ```bash
   chronalyn detect
   chronalyn adopt --namespace my-project --environment staging --dry-run
   ```

   The plan shows the current provider (`hermes_memory_router`), the proposed
   provider (`chronalyn`), the banks, the routing policy, and states explicitly
   that existing Hindsight memories are preserved and migration is `None`.

4. **Apply it** with `chronalyn setup` (guided) or by rerunning `adopt` without
   `--dry-run`. Configuration is backed up before anything is written.

5. **Validate:**

   ```bash
   chronalyn validate
   chronalyn status
   chronalyn db check
   hermes memory status
   ```

   Expect `chronalyn` as the only active external memory provider and a database
   binding identical to before the migration.

## Compatibility during and after migration

You can migrate at your own pace. Until you do, and for a period afterwards:

- **Old CLI works.** `hermes-memory-router …` invokes Chronalyn and prints a
  deprecation warning to stderr. Exit codes are unchanged, and `--json` output on
  stdout stays clean and machine-readable.
- **Old provider id works.** A compatibility entry is installed at
  `$HERMES_HOME/plugins/hermes_memory_router/`, so an unmodified
  `memory.provider: hermes_memory_router` still loads Chronalyn.
- **Old import path works.** `import hermes_memory_router` resolves to the same
  module objects as `chronalyn`, preserving class identity and `isinstance`
  checks. It raises a `DeprecationWarning`.
- **Old class name works.** `HermesMemoryRouterProvider` is an alias of
  `ChronalynMemoryProvider`.
- **Old setup command works.** `setup-dual` is a deprecated alias of `setup`.
- **Conflict detection still applies** to the legacy id, so a pre-rename install
  paired with another memory provider is still reported as a conflict.

These aliases are **temporary** and will be removed in a future major release.
Move to the `chronalyn` names when convenient.

## If a provider entry directory already exists

Chronalyn refuses to overwrite a plugin directory it does not own, identified by
a `.chronalyn-managed` marker file. If you previously created a directory with
one of these names by hand, move or remove it, then rerun setup. All targets are
validated before anything is written, so a refusal cannot leave a half-installed
state behind.

## Rollback

If anything looks wrong, roll back before investigating further:

```bash
chronalyn rollback --yes
```

See [Rollback](rollback.md). Rollback restores configuration only; it never
deletes memory data.
