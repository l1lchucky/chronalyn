# Installation

Chronalyn `v1.0.0-rc.1` is a **release candidate**. Install it on staging first
and read [RC limitations](rc-limitations.md).

## Requirements

- Python 3.11, 3.12, or 3.13;
- a supported Hermes Agent installation;
- a reachable Hindsight API;
- `mnemosyne-memory>=3.15,<4` only if you enable dual mode.

Chronalyn must be installed into **the same Python environment as Hermes**, so
Hermes can import the provider. The scripted installers below handle this for
you by locating Hermes' own interpreter.

## Option 1 — scripted install (recommended, Linux/macOS/WSL)

From a source checkout, into an existing Hermes installation:

```bash
./scripts/install.sh
chronalyn setup
```

`install.sh` finds Hermes' interpreter, installs Chronalyn into it, writes the
provider entries, and links both console commands onto Hermes' PATH.

## Option 2 — guided bootstrap with checksum verification

For a machine that may not have Hermes yet, `scripts/install-dual.sh` downloads
the release wheel, verifies its SHA-256 against the published checksum file,
optionally verifies GitHub build provenance with `gh`, and then launches the
guided setup interface. It never pipes remote content into a shell, never calls
`sudo` itself, and never enables telemetry.

Read [Trusted bootstrap](trusted-bootstrap.md) before using it on an important
machine.

## Option 3 — manual install

```bash
python -m pip install chronalyn
chronalyn install-plugin
chronalyn setup
```

If you manage Hermes' environment yourself, install into that interpreter
explicitly:

```bash
"$HERMES_HOME/hermes-agent/venv/bin/python" -m pip install chronalyn
"$HERMES_HOME/hermes-agent/venv/bin/python" -m chronalyn.cli install-plugin
```

Because Chronalyn `1.0.0rc1` is a pre-release, pip requires an explicit opt-in
when installing by version range:

```bash
python -m pip install --pre chronalyn
```

## What gets written

```text
$HERMES_HOME/
├── config.yaml                              # memory.provider set on activation
├── plugins/chronalyn/                       # provider entry Hermes discovers
├── plugins/hermes_memory_router/            # compatibility alias (legacy id)
├── memory-router/config.json                # Chronalyn configuration
├── memory-router/router.db                  # local control database
├── memory-router/backups/<timestamp>/       # pre-change configuration backups
└── .env                                     # secrets only, owner-only mode
```

`memory-router/` is a **durable path** kept from the previous name so existing
installations continue to work without migrating data.

## Verify the install

```bash
chronalyn --version
chronalyn validate
chronalyn status
chronalyn doctor
hermes memory status
```

`status` and `doctor` verify Hermes' `MemoryProvider` contract, so run them with
the interpreter that has Hermes installed. The `db` subcommands do not need
Hermes:

```bash
chronalyn db info
chronalyn db check
```

Expected healthy result: `chronalyn` is the only active external memory provider,
the database binding matches your namespace/environment/profile, and no
deliveries are stuck in `failed` or `dead`.

## Fresh install versus adopting Hindsight

- **Fresh install.** `chronalyn setup` creates configuration from your answers.
- **Existing direct Hindsight user.** Setup detects your endpoint, bank, and
  mode, and adopts them in place. Your Hindsight configuration is preserved,
  including settings Chronalyn does not manage. No memories are copied,
  recreated, or reindexed.

Non-interactive adoption is also available:

```bash
chronalyn adopt \
  --namespace my-project \
  --environment staging \
  --policy hindsight-only \
  --dry-run
```

Review the printed plan, then rerun without `--dry-run`.

## Optional Mnemosyne

Mnemosyne stays opt-in. Installing the package does not enable it:

```bash
python -m pip install 'chronalyn[mnemosyne]'
chronalyn provider add mnemosyne --dry-run
chronalyn provider add mnemosyne
```

Only new verified checkpoints go to Mnemosyne. Existing Hindsight data stays
where it is.

## Upgrading from Hermes Memory Router

See [Migration](migration.md). The short version: install Chronalyn, run
`chronalyn setup`, review the plan, confirm. Your old CLI, provider id, and
import path keep working in the meantime.

## Uninstalling

Package removal and data deletion are separate actions:

```bash
./scripts/uninstall.sh
```

See [Uninstall and data retention](uninstall-and-data-retention.md).
