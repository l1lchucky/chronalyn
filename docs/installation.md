# Installation

Chronalyn 1.0 is a stable release for Hermes Agent. The recommended way to
install it is from inside Hermes.

## Requirements

- Python 3.11, 3.12, or 3.13;
- a supported Hermes Agent installation;
- a reachable Hindsight API;
- `mnemosyne-memory>=3.15,<4` only if you enable dual mode.

## Recommended: install from Hermes

```bash
hermes plugins install l1lchucky/chronalyn
hermes memory setup
```

`hermes plugins install` clones the Chronalyn repository into
`$HERMES_HOME/plugins/chronalyn` and Hermes discovers it as a memory provider.
`hermes memory setup` then lets you choose **Chronalyn**; the Chronalyn wizard
runs inside the same flow and activates `memory.provider = chronalyn` when it
finishes.

The wizard offers two architectures:

- **Hindsight only** — Hindsight handles every memory operation.
- **Dual memory** — Mnemosyne additionally keeps verified checkpoints, with
  bounded fallback when Hindsight has no answer.

In dual mode the wizard also asks how Hindsight should be provided:

- **Lightweight local Hindsight (managed)** — Chronalyn installs and starts a
  local Hindsight API for you (see
  [Managed Hindsight](managed-hindsight.md)). You only supply an
  OpenAI-compatible base URL, API key, LLM model, and embedding model.
- **Self-hosted / existing Hindsight** — connect to a Hindsight API you
  already run; Chronalyn only connects and never manages its process.
- **Hindsight Cloud** — connect to the hosted Hindsight Cloud service.

In dual mode with remote embeddings, the wizard also configures a
provider-neutral embedding backend (OpenAI-compatible API) for Mnemosyne
semantic recall.

Verify with:

```bash
hermes memory status
```

## Python package (manual / developer install)

```bash
python -m pip install chronalyn
chronalyn install-plugin
chronalyn setup
```

Installing the package alone does not configure Hermes: `chronalyn
install-plugin` writes the provider entry Hermes discovers, and `chronalyn
setup` launches the guided wizard. The recommended Hermes flow above performs
both steps for you.

If you manage Hermes' environment yourself, install into that interpreter
explicitly:

```bash
"$HERMES_HOME/hermes-agent/venv/bin/python" -m pip install chronalyn
"$HERMES_HOME/hermes-agent/venv/bin/python" -m chronalyn.cli install-plugin
```

## Scripted bootstrap (advanced)

For a machine that may not have Hermes yet, `scripts/install-dual.sh` downloads
the release wheel, verifies its SHA-256 against the published checksum file,
optionally verifies GitHub build provenance with `gh`, and then launches the
guided setup interface. It never pipes remote content into a shell, never calls
`sudo` itself, and never enables telemetry.

Read [Trusted bootstrap](trusted-bootstrap.md) before using it on an important
machine.

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
chronalyn status
chronalyn doctor
```
