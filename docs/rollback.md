# Rollback

Rollback restores the most recent pre-change configuration backup. It is a
**configuration** operation: it never deletes, moves, or rewrites memory data in
Hindsight or Mnemosyne, and it never touches the Chronalyn state database.

## When a backup is created

Chronalyn writes a backup automatically before any operation that changes
configuration or provider entries:

- `chronalyn setup` (before installing entries or writing configuration);
- `chronalyn adopt` (before applying a plan);
- `chronalyn provider add|remove mnemosyne`;
- `chronalyn upgrade-config`.

Backups live under a timestamped directory:

```text
$HERMES_HOME/memory-router/backups/<UTC timestamp>/
├── backup.json                              # manifest: reason, copied, absent
├── config.yaml                              # Hermes configuration
├── memory-router/config.json                # Chronalyn configuration
├── hindsight/config.json                    # Hindsight configuration
├── .env                                     # secrets, owner-only mode
├── plugins/chronalyn/…                      # provider entry
└── plugins/hermes_memory_router/…           # compatibility alias entry
```

The manifest records both which files were **copied** and which were **absent**
at backup time. That second list is what makes rollback able to undo an
installation: a file that did not exist before is removed on restore.

## Roll back

```bash
chronalyn rollback --yes
```

This selects the most recent backup, restores every copied file in place, and
removes files that were absent when the backup was taken — including provider
entries created during a failed or unwanted activation.

To confirm the result:

```bash
chronalyn detect
hermes memory status
```

## Roll back to direct Hindsight

If you want Hermes to use Hindsight directly again, without Chronalyn in the
path:

```bash
chronalyn rollback --yes                      # restore prior configuration
hermes config set memory.provider hindsight   # or set it explicitly
```

Optionally remove the provider entries as well. This deletes only the entry
directories Chronalyn owns:

```bash
chronalyn uninstall-plugin
```

Your Hindsight bank, endpoint, credentials, and memories are untouched by all of
the above.

## Automatic rollback during setup

`chronalyn setup` rolls back on its own if activation fails. The sequence is:

1. take a backup;
2. install provider entries and write configuration;
3. verify backend health;
4. activate `memory.provider` and re-read discovery;
5. if any step in 2–4 raises, restore the backup taken in step 1.

That means a failed setup does not leave a half-activated Hermes profile behind.

## What rollback does not do

- It does not delete Hindsight or Mnemosyne data.
- It does not delete or truncate `memory-router/router.db`.
- It does not remove backups.
- It does not change namespaces, environments, or profile bindings.
- It does not uninstall the Python package. Use
  [uninstall](uninstall-and-data-retention.md) for that.

## Recovering pending writes after a rollback

Rolling back configuration does not discard queued deliveries. If writes failed
while you were investigating, drain them once the backend is healthy again:

```bash
chronalyn status
chronalyn retry
chronalyn drain --limit 500
```

See [Failure recovery](failure-recovery.md) for the full procedure.

## If no backup exists

`rollback` fails loudly rather than guessing:

```text
ERROR: No router configuration backup exists
```

In that case restore from your own backup, or reset the provider selection
manually with `hermes config set memory.provider hindsight`.
