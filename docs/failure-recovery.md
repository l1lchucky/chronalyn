# Failure recovery

## Start with status

```bash
chronalyn validate
chronalyn status
chronalyn doctor
chronalyn db check
journalctl --user -u hermes-gateway.service -n 200 --no-pager
```

`status` separates backend health from queued delivery state. `doctor` classifies
warning, degraded, and unsafe conditions. Database integrity failure is unsafe.

## Retry failed work

Retry everything marked failed or dead:

```bash
chronalyn retry
chronalyn drain --limit 500
```

Retry one logical record:

```bash
chronalyn retry --record-id mr_...
```

## Hindsight is down

New automatic writes stay in SQLite. Dual-mode recall may fall back to
Mnemosyne checkpoints when configured. Restore Hindsight, then drain the outbox.

## Mnemosyne is down

Normal Hindsight memory continues. Dual-mode checkpoints remain pending for
Mnemosyne. Repair the package or data path, then retry.

## A record was forgotten while a write was pending

Pending writes are cancelled. If a write was already processing and finishes
late, its receipt creates a delete job automatically.

## A delete is incomplete

A record is fully deleted only when every backend delete is complete. Repair the
failed backend and retry the record. Keep the audit history until both sides are
confirmed.

## Restore the router database

Stop Hermes first:

```bash
systemctl --user stop hermes-gateway.service
```

Prefer a verified online backup created with `db backup`; it already includes
committed WAL content. Follow `database-operations.md`, verify its SHA-256 manifest
and SQLite integrity, and match profile, namespace, environment, and schema before
restarting. Never restore a staging router database into production.

## Return to direct Hindsight

```bash
hermes config set memory.provider hindsight
systemctl --user restart hermes-gateway.service
```

Keep the router database and Mnemosyne bank while investigating. Disabling the
router should not destroy recovery evidence.

## Back up together

A complete recovery set includes:

- `$HERMES_HOME/memory-router/`;
- Mnemosyne data;
- Hindsight data and configuration;
- the Hermes profile configuration;
- the secret store used by the profile.

Encrypt backups and test a restore on a disposable host.
