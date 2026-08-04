# Operations

## Status and doctor

`chronalyn status` is a quick operational snapshot. It reports versions,
the active policy and binding, backend health, delivery counts and age, database
file sizes, and an overall state. It does not run SQLite integrity checking.

`chronalyn doctor` performs the same bounded backend checks and maps the
result to an exit code suitable for monitoring:

| State | Meaning | Exit code |
| --- | --- | --- |
| `healthy` | Required components are healthy and no work is incomplete. | 0 |
| `warning` | The router is safe, but an optional component is absent or work is pending. | 0 |
| `degraded` | A backend, worker, failed delivery, or dead delivery needs attention. | 1 |
| `unsafe` | Binding or database integrity is unsafe. Stop and investigate. | 3 |

Configuration/usage errors remain exit code `2`. Use global `--json` for stable,
machine-readable objects. Output contains no memory text or secrets.

Automatic checks are deliberately bounded. They do not prove recall quality,
backup restorability, backend data compatibility, isolation under real traffic,
or production capacity. See [database operations](database-operations.md) and
[live validation](live-validation.md).

## Regular checks

- review failed and dead deliveries;
- check Hindsight and Mnemosyne health;
- watch disk space;
- confirm backups completed;
- keep staging and production markers separate.

## Before a deployment

1. Drain the outbox.
2. Confirm there are no failed deletes.
3. Back up the router, Mnemosyne, Hindsight, and Hermes profile.
4. Record the current versions and rollback command.
5. Run a unique isolation marker on staging.

## Production-readiness checklist

- all local compilation, lint, format, type, test, coverage, build, and audit gates pass;
- the built wheel installs and its CLI works in a clean environment;
- `validate`, `doctor`, and `db check` pass on staging;
- an online database backup was restored and verified on a disposable host;
- supported Hindsight and optional Mnemosyne versions were tested with real services;
- automatic writes, checkpoint dual writes, fallback bounds, retries, coordinated deletion,
  and late-write deletion were validated in staging;
- namespace, environment, credentials, banks, and profile paths are isolated;
- staging completed an agreed soak with queue, disk, and backend monitoring;
- rollback ownership, commands, and preserved recovery evidence are documented.

Passing local tests alone does not prove production readiness. Do not call a
deployment production-ready until live compatibility testing, restoration, and a
staging soak have actually completed.

## After a deployment

1. Run `chronalyn status`.
2. Create a harmless test checkpoint.
3. Recall it.
4. Delete it and confirm both backend deletes finish.
5. Review the gateway log for memory errors.

## Suggested alerts

- any failed delete: urgent;
- a retain failure older than 15 minutes: warning;
- router database integrity failure: critical;
- a staging marker recalled in production: critical, disable immediately;
- disk usage above 80 percent: warning.
