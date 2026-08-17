# Uninstall and data retention

**Removing Chronalyn and deleting your data are two separate actions.**
Uninstalling never deletes backend data. Nothing in this project deletes
Hindsight or Mnemosyne memories automatically, at any point.

## Uninstall the software

```bash
./scripts/uninstall.sh
```

That script:

1. disables the external memory provider (`hermes memory off`);
2. removes the Chronalyn provider entries from `$HERMES_HOME/plugins/`;
3. uninstalls the `chronalyn` distribution, and the older
   `hermes-memory-router` distribution if it is still present;
4. removes the `chronalyn` and `hermes-memory-router` command symlinks it
   created.

Equivalent manual steps:

```bash
hermes memory off
chronalyn uninstall-plugin
python -m pip uninstall -y chronalyn
```

`chronalyn uninstall-plugin` removes only directories Chronalyn owns, identified
by a `.chronalyn-managed` marker file. A directory Chronalyn did not create is
left alone.

## What is retained

After uninstalling, all of this is still on disk, untouched:

```text
$HERMES_HOME/
├── memory-router/config.json          # Chronalyn configuration
├── memory-router/router.db            # control database (records, queue, audit)
├── memory-router/backups/             # configuration backups
├── memory-router/logs/                # setup and bootstrap logs
├── hindsight/config.json              # Hindsight configuration
└── .env                               # secrets
```

Also retained, because Chronalyn never owned it:

- everything in your **Hindsight** bank;
- everything in your **Mnemosyne** bank and its data directory;
- Hermes' own sessions, memory files, and configuration.

This is deliberate. Reinstalling Chronalyn over a retained
`$HERMES_HOME/memory-router/` resumes with the same namespace, environment,
profile binding, and queue state — no reindex, no data loss.

## Deleting data, when you actually mean it

Do these only when you intend permanent loss. Take a verified backup first.

### 1. Back up before deleting anything

```bash
chronalyn db backup --output /secure/path/final.sqlite
chronalyn db verify-backup --path /secure/path/final.sqlite
```

### 2. Delete Chronalyn's local state

This removes the control database, configuration, backups, and logs. It does
**not** touch Hindsight or Mnemosyne contents.

```bash
rm -rf "$HERMES_HOME/memory-router"
```

Consequences: local record IDs, the delivery queue, backend ID mappings, and the
audit trail are gone. Memories already written to Hindsight or Mnemosyne remain
in those systems, but Chronalyn can no longer map or delete them for you.

### 3. Delete individual memories before removing local state

Deleting local state first orphans backend copies. If you want backend content
removed, delete the records **while Chronalyn is still installed**, so it can
propagate deletes to both backends:

```bash
chronalyn forget --record-id mr_… --yes
chronalyn drain --limit 500
chronalyn status
```

Confirm `…:delete = complete` for every backend before removing local state.

### 4. Delete backend data directly

Hindsight and Mnemosyne own their storage. Use their own tools to delete a bank
or its contents. Chronalyn has no command that wipes a whole bank, by design.

## Order of operations that avoids orphans

```text
1. chronalyn db backup + verify-backup
2. chronalyn forget … / drain      # propagate deletes to backends
3. chronalyn status                # confirm delete deliveries completed
4. ./scripts/uninstall.sh          # remove software
5. rm -rf $HERMES_HOME/memory-router   # only if you want local state gone
6. delete banks with Hindsight/Mnemosyne tooling, if desired
```

Skipping step 2 leaves memories in the backends with no local mapping.

## Secrets

`$HERMES_HOME/.env` is written with owner-only permissions and is retained on
uninstall, because Hermes and other providers may also use it. If you are
decommissioning a machine, remove or rotate `HINDSIGHT_API_KEY` explicitly —
uninstalling Chronalyn does not revoke credentials.

## Reinstalling later

```bash
python -m pip install chronalyn
chronalyn install-plugin
chronalyn validate
chronalyn status
```

Because `memory-router/` was retained, this resumes the previous configuration
and binding. Chronalyn refuses to open a database whose recorded namespace,
environment, or profile does not match the current one, so a mismatched restore
fails loudly instead of cross-contaminating environments.
