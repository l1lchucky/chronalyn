# Operations

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

## After a deployment

1. Run `hermes-memory-router status`.
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
