# Upgrading

## Before every upgrade

1. Record the router, Hermes, Hindsight, Mnemosyne, and Python versions.
2. Run `chronalyn status`.
3. Drain failed and dead deliveries.
4. Back up all memory stores and the Hermes profile.
5. Upgrade staging first.
6. Run the live validation checklist.
7. Upgrade production only when rollback is available.

## From 0.1 alpha to 0.2 beta

The 0.2 loader can read a 0.1 configuration. Persist the new schema with:

```bash
chronalyn upgrade-config --yes
```

The command creates a timestamped backup before writing schema version 2. The
old dual behavior becomes the fixed
`hindsight-primary-mnemosyne-checkpoints` policy. No memories are copied.

## Roll back configuration

```bash
chronalyn rollback --yes
```

This restores the latest router configuration backup, including removal of a
new file when the file did not exist before the backed-up change.

## Roll back the active provider

The quickest operational rollback is direct Hindsight:

```bash
hermes config set memory.provider hindsight
systemctl --user restart hermes-gateway.service
```

Keep the router database and Mnemosyne bank for investigation and later retry.
