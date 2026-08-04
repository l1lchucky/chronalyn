# Router database operations

These commands operate only on the database selected by the validated router configuration. They do not contact Hindsight or Mnemosyne and do not read or print memory contents.

## Information

```bash
chronalyn db info
chronalyn --json db info
```

The output includes the database schema version, namespace/environment/profile binding, delivery counts, oldest incomplete delivery, and database/WAL/SHM sizes.

## Integrity check

```bash
chronalyn db check
```

This runs SQLite `integrity_check` without starting backends. Exit code `0` means SQLite returned `ok`; exit code `3` means the database is unsafe to use. Stop Hermes and investigate before modifying a database that fails this check.

## Online backup

```bash
chronalyn db backup --output /secure/path/router.sqlite
chronalyn db verify-backup --path /secure/path/router.sqlite
```

The backup uses SQLite's online backup API, so committed WAL data is included consistently. Existing destinations are never overwritten. A sibling file named `router.sqlite.manifest.json` is created.

Manifest format:

```json
{
  "format_version": 1,
  "created_at": "UTC ISO-8601 timestamp",
  "database": "router.sqlite",
  "sha256": "64 lowercase hexadecimal characters",
  "size_bytes": 12345,
  "schema_version": 2,
  "binding": {
    "namespace": "project",
    "environment": "staging",
    "profile": "profile fingerprint"
  }
}
```

The manifest contains no credentials or memory contents. `verify-backup` checks both SHA-256 and SQLite integrity.

## Safe restore

1. Stop the Hermes gateway and any router processes.
2. Keep the damaged database and its WAL/SHM files as recovery evidence.
3. Copy the backup and manifest to a disposable host first.
4. Run `db verify-backup` and confirm the binding matches the target profile, namespace, and environment.
5. Open the backup with SQLite and run `PRAGMA integrity_check`.
6. Restore only into the same bound profile/environment. Never restore staging into production.
7. Start Hermes, run `validate`, `doctor`, and the staging checks in `live-validation.md`.
8. Keep the previous database until the restored system has completed a soak period.

A router database backup does not include Hindsight data, Mnemosyne data, profile configuration, or secrets. Back up and restore those systems using their supported procedures as one coordinated recovery set.

## Vacuum

```bash
chronalyn db vacuum --yes
```

Vacuum rewrites the disposable/configured database and can require temporary disk space and an exclusive lock. It requires `--yes`. Take and verify a backup first, stop active router processes, and never point a test at a live production database.
