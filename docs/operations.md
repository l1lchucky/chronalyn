# Operations runbook

## Daily

- Check failed delivery count.
- Check Hindsight and Mnemosyne health.
- Confirm disk space and backup completion.

## Before deployment

- Ensure outbox has no failed deliveries.
- Back up all three data stores.
- Record version, config checksum, and rollback command.
- Run a unique isolation marker.

## After deployment

- Run `memory_router_status`.
- Create and recall a non-sensitive checkpoint.
- Delete the test checkpoint and confirm both delete deliveries complete.
- Review gateway logs for memory errors.

## Alert thresholds

- any failed deletion: urgent;
- failed retains older than 15 minutes: warning;
- router DB integrity failure: critical;
- cross-environment marker recall: critical and immediate shutdown;
- disk usage above 80%: warning.
