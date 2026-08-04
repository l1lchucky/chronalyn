# Guided setup

The CLI can adopt an existing Hindsight setup or add Mnemosyne later without
silently changing memory behavior.

## Read-only discovery

```bash
chronalyn detect
```

The command reports:

- the active Hermes memory provider;
- the Hindsight endpoint and bank, when found;
- whether the endpoint is local or remote;
- whether Mnemosyne is installed;
- any provider conflict.

Discovery does not write configuration, contact a backend, or restart Hermes.

## Adopt Hindsight

Preview the change:

```bash
chronalyn adopt \
  --namespace my-project \
  --environment staging \
  --policy hindsight-only \
  --dry-run
```

The plan shows the current provider, proposed provider, bank names, routing
policy, remote-data warning, backup action, and rollback path.

Apply it by rerunning without `--dry-run`.

## Add Mnemosyne

Install the optional dependency, preview the plan, then apply it:

```bash
python -m pip install '.[mnemosyne]'
chronalyn provider add mnemosyne --dry-run
chronalyn provider add mnemosyne
```

This changes future checkpoint routing. It does not copy old Hindsight memories.

Remove Mnemosyne routing with:

```bash
chronalyn provider remove mnemosyne --dry-run
chronalyn provider remove mnemosyne
```

The Mnemosyne database is preserved unless the operator removes it separately.

## Cloud consent

A remote Hindsight endpoint means sanitized memory content leaves the host.
Setup requires explicit cloud consent. General `--yes` confirmation does not
also grant permission for cloud transmission.

## Backups and rollback

Before a configuration change, the router copies relevant profile files into a
timestamped backup directory.

Restore the newest backup with:

```bash
chronalyn rollback --yes
```

Rollback restores configuration. It does not delete Hindsight or Mnemosyne data.
