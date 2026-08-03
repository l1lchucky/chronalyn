# Failure recovery

## Inspect

```bash
hermes-memory-router validate
hermes-memory-router status
journalctl --user -u hermes-gateway.service -n 200 --no-pager
```

The status output separates backend health from durable delivery state.

## Retry failed deliveries

```bash
hermes-memory-router retry
hermes-memory-router drain --limit 500
```

Or retry one router record:

```bash
hermes-memory-router retry --record-id mr_...
```

## Hindsight unavailable

Automatic writes remain in SQLite. Recall may use Mnemosyne checkpoints when
configured. Restore Hindsight, then drain the outbox.

## Mnemosyne unavailable

Normal Hindsight memory continues. Checkpoints remain pending for Mnemosyne.
Repair the Python package or SQLite path, then retry.

## Router database recovery

Stop Hermes first:

```bash
systemctl --user stop hermes-gateway.service
```

Back up the damaged files, restore `router.db` together with its WAL/SHM files
when present, run `PRAGMA integrity_check`, then restart. Never restore a staging
database into production.

## Partial deletion

A record is fully deleted only when every `backend:delete` delivery is complete.
Repair the failed backend and retry. Preserve the audit trail until confirmed.

## Rollback to direct Hindsight

```bash
hermes memory off
hermes config set memory.provider hindsight
systemctl --user restart hermes-gateway.service
```

The router and Mnemosyne data remain untouched for later recovery.

## Backup set

Back up:

- `$HERMES_HOME/memory-router/`
- Mnemosyne data directory
- Hindsight database according to its deployment documentation
- non-secret configuration files

Encrypt backups and test restoration.


## Forgotten records with pending writes

Forget cancels pending, failed, and dead retain deliveries. If a retain was
already processing and completes concurrently, the control plane automatically
creates a delete delivery from its receipt. A forgotten record therefore cannot
be resurrected by a later retry.
