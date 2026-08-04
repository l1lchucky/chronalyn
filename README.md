# Chronalyn

[![CI](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/ci.yml/badge.svg)](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/ci.yml)
[![Security](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/security.yml/badge.svg)](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Chronalyn is an open-source AI agent memory orchestration layer and memory
provider for Hermes Agent. It coordinates Hindsight for persistent memory,
recall, and reflection with Mnemosyne for verified checkpoints and bounded
fallback, backed by durable SQLite delivery, retry, and deletion controls.

**What is implemented today:** this release candidate delivers one thing —
reliable memory orchestration for Hermes Agent, shipped as **Chronalyn for
Hermes**. Chronalyn gives Hindsight and Mnemosyne separate jobs instead of
letting them compete for every turn.

Hermes sees one external memory provider. Behind that provider:

- **Hindsight** handles normal automatic memory, recall, and reflection.
- **Mnemosyne** keeps deliberate, evidence-backed checkpoints and can act as a
  small fallback when Hindsight is unavailable or has no answer.
- A local **SQLite control database** tracks writes, retries, backend IDs,
  deletions, and the active environment.

> **Current release:** `1.0.0rc1` (`v1.0.0-rc.1`) — a **release candidate**.
> Local tests do not prove production readiness. Live Hindsight and Mnemosyne
> testing plus a staging soak are still required. See
> [RC limitations](docs/rc-limitations.md) and
> [Live validation](docs/live-validation.md).

### Roadmap, not yet built

Chronalyn Console (dashboard), Chronalyn Intelligence (change intelligence),
bug discovery, and deployment analysis are **future modules**. They are not part
of this release candidate and are not implemented. See [ROADMAP.md](ROADMAP.md).

### Renamed from Hermes Memory Router

Chronalyn was previously released as Hermes Memory Router. Existing
installations keep working: the old CLI, the old Hermes provider id, and the old
import path all remain available as temporary compatibility aliases. Nothing is
migrated without your explicit confirmation, and no memories are ever copied,
recreated, or reindexed. See [Migration](docs/migration.md).

## The policy in one screen

```text
NORMAL TURN   -> HINDSIGHT only
CHECKPOINT    -> HINDSIGHT + MNEMOSYNE
FAILOVER      -> bounded MNEMOSYNE checkpoints
MERGED RECALL -> never
```

That policy is intentionally narrow and is **unchanged** by the rename:

- normal conversations are not copied into both systems;
- recall results are not merged into one large prompt;
- installing Mnemosyne does not activate it;
- existing Hindsight memories are not copied or rewritten;
- cron, flush, and subagent output are not automatically retained;
- raw tool messages are never retained;
- destructive model-requested operations are disabled by default;
- Chronalyn never patches Hermes core.

See [Routing policies](docs/routing-policies.md) for the exact rules.

## How Hermes loads Chronalyn

Chronalyn uses Hermes' public memory-provider contract. Nothing here relies on a
private Hermes API, an invented entry-point group, or a modified Hermes core.

```text
$HERMES_HOME/plugins/chronalyn/            <- provider entry Hermes discovers
$HERMES_HOME/plugins/hermes_memory_router/ <- compatibility alias (legacy id)
```

- Hermes discovers user-installed memory providers by scanning
  `$HERMES_HOME/plugins/<provider-id>/`.
- Each entry declares `kind: exclusive` in `plugin.yaml`, so Hermes' generic
  plugin manager records the manifest without importing it and leaves activation
  to the memory category.
- Activation is a single supported config write: `memory.provider`.

Details, including the exact discovery rules verified against a real Hermes
installation, are in [Hermes integration](docs/hermes-integration.md).

## Install

Requirements:

- Python 3.11, 3.12, or 3.13;
- a supported Hermes Agent installation;
- a reachable Hindsight API;
- `mnemosyne-memory` only when dual mode is selected.

```bash
python -m pip install chronalyn
chronalyn setup
```

`chronalyn setup` is guided and non-destructive until you confirm. It detects
your Hermes installation and any existing direct Hindsight configuration,
previews every change, backs up configuration, activates Chronalyn as the single
external memory provider, then validates provider discovery and health.

Full walkthrough: [Installation](docs/installation.md) and
[Guided setup](docs/guided-setup.md).

## Commands

```bash
chronalyn --version
chronalyn setup
chronalyn validate
chronalyn status
chronalyn doctor
chronalyn db info
chronalyn db check
chronalyn db backup --output /secure/path/router.sqlite
chronalyn db verify-backup --path /secure/path/router.sqlite
```

Also available: `detect`, `adopt`, `provider add|remove mnemosyne`, `retry`,
`drain`, `forget`, `rollback`, `upgrade-config`, `install-plugin`, and
`uninstall-plugin`. Most support `--json`:

```bash
chronalyn --json status
```

The deprecated `hermes-memory-router` command still works. It invokes Chronalyn
and prints a deprecation warning to stderr, so `--json` output on stdout stays
machine-readable.

## Hermes tools

The standard tool profile stays small and the tool names are unchanged:

- `memory_router_retain`
- `memory_router_checkpoint`
- `memory_router_recall`
- `memory_router_reflect`
- `memory_router_status`

Model-requested deletion is off by default. When an operator enables it, deletion
uses a two-step plan/apply flow with a short-lived confirmation token:

- `memory_router_forget_plan`
- `memory_router_forget_apply`

Administrative retry, direct deletion, provider changes, configuration adoption,
and rollback remain command-line operations.

## Generic projects, profiles, and environments

Chronalyn is project-agnostic. Namespaces, profiles, and environments are yours
to choose; nothing about any specific product is baked into routing, provider,
database, or CLI logic. `examples/` holds optional, removable sample
configurations.

Use separate Hermes profiles, bank names, databases, credentials, and backups
per environment:

```text
Staging server
├── Hindsight bank: my-project-staging
├── Mnemosyne bank: my-project-staging-checkpoints
└── database bound to the staging Hermes profile

Production server
├── Hindsight bank: my-project-production
├── Mnemosyne bank: my-project-production-checkpoints
└── database bound to the production Hermes profile
```

Chronalyn records the profile path, namespace, and environment in its database
and refuses to open that database under a different binding.

## Uninstall and data retention

Removing the package and deleting data are **separate actions**. Uninstalling
never deletes backend data:

```bash
./scripts/uninstall.sh   # removes package + provider entries only
```

Router configuration, the state database, backups, Hindsight data, and Mnemosyne
data are all retained. See
[Uninstall and data retention](docs/uninstall-and-data-retention.md).

## Testing

```bash
python -m pip install -e '.[test]'
make check
```

The suite uses local fake backends for routing and failure scenarios. It is not
a substitute for testing a real Hermes, Hindsight, and Mnemosyne deployment.
Complete [Live validation](docs/live-validation.md) before production use.

## Documentation

- [Installation](docs/installation.md)
- [Hermes integration](docs/hermes-integration.md)
- [Migration](docs/migration.md)
- [Upgrading](docs/upgrading.md)
- [Rollback](docs/rollback.md)
- [Uninstall and data retention](docs/uninstall-and-data-retention.md)
- [RC limitations](docs/rc-limitations.md)
- [Architecture](docs/architecture.md)
- [Routing policies](docs/routing-policies.md)
- [Hermes compatibility rules](docs/strict-compatibility.md)
- [Guided setup](docs/guided-setup.md)
- [Configuration](docs/configuration.md)
- [Database operations](docs/database-operations.md)
- [Operations](docs/operations.md)
- [Deployment models](docs/deployment-models.md)
- [Threat model](docs/threat-model.md)
- [Privacy](docs/privacy.md)
- [Failure recovery](docs/failure-recovery.md)
- [Live validation](docs/live-validation.md)
- [Rename migration matrix](docs/rename-migration-matrix.md)
- [Roadmap](ROADMAP.md)

## Project status and affiliation

This is an independent community project. It is not maintained or endorsed by
Nous Research, Vectorize, Hindsight, or the Mnemosyne maintainers.

The code is available under the [MIT License](LICENSE).
