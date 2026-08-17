# Chronalyn

[![CI](https://github.com/l1lchucky/chronalyn/actions/workflows/ci.yml/badge.svg)](https://github.com/l1lchucky/chronalyn/actions/workflows/ci.yml)
[![Security](https://github.com/l1lchucky/chronalyn/actions/workflows/security.yml/badge.svg)](https://github.com/l1lchucky/chronalyn/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Give Hermes a past it can actually use.**

Hermes already keeps important facts close. Chronalyn handles the deeper
history behind them: what happened, what failed, what worked, and which states
were verified.

- **Hindsight** handles long-term semantic memory and recall.
- **Mnemosyne** keeps verified checkpoints and provides bounded fallback.

Chronalyn is a Hermes memory plugin — install it from inside Hermes and pick it
as your memory provider:

```bash
hermes plugins install l1lchucky/chronalyn
hermes memory setup
```

## Three complementary memory layers

Chronalyn does not replace Hermes' own memory. They sit side by side:

```text
Hermes Agent
├── Native memory        important facts kept close (MEMORY.md / USER.md)
├── Chronalyn
│   ├── Hindsight        deeper history and semantic recall
│   └── Mnemosyne        verified checkpoints / bounded fallback
└── Skills               reusable procedures
```

- **Hermes native memory** keeps the facts you want close: preferences, stable
  facts about the user and the project.
- **Chronalyn** remembers what happened: the deeper history behind those facts.
- **Skills** remember how to do it again: reusable procedures.

Hermes sees **one** external memory provider — Chronalyn. Hindsight and
Mnemosyne are internal Chronalyn backends. Hermes' memory manager orchestrates
the built-in provider plus at most one external provider.

## What Chronalyn does

Chronalyn gives Hindsight and Mnemosyne separate jobs instead of letting them
compete for every turn:

```text
NORMAL TURN   -> HINDSIGHT only
CHECKPOINT    -> HINDSIGHT + MNEMOSYNE (dual mode)
FAILOVER      -> bounded MNEMOSYNE checkpoints
MERGED RECALL -> never
```

That policy is intentionally narrow:

- normal conversations are not copied into both systems;
- recall results are not merged into one large prompt;
- installing Mnemosyne does not activate it;
- existing Hindsight memories are not copied or rewritten;
- cron, flush, and subagent output are not automatically retained;
- raw tool messages are never retained;
- destructive model-requested operations are disabled by default;
- Chronalyn never patches Hermes core.

Two modes are available: **Hindsight-only** (Hindsight handles every memory
operation) and **dual memory** (Mnemosyne also keeps verified checkpoints).

See [Routing policies](docs/routing-policies.md) for the exact rules.

## Install

Requirements:

- Python 3.11, 3.12, or 3.13;
- a supported Hermes Agent installation;
- a reachable Hindsight API;
- `mnemosyne-memory` only when dual mode is selected.

### Recommended: install from Hermes

```bash
hermes plugins install l1lchucky/chronalyn
hermes memory setup
```

Then choose **Chronalyn** in the memory provider picker. The Chronalyn wizard
runs inside the same flow: it detects your Hermes installation and any existing
direct Hindsight configuration, previews every change, backs up configuration,
activates Chronalyn as the single external memory provider, then validates
provider discovery and health. When it finishes, `memory.provider` is set to
`chronalyn`.

Verify with:

```bash
hermes memory status
```

### Python package (manual / developer install)

```bash
python -m pip install chronalyn
chronalyn setup
```

`chronalyn setup` is guided and non-destructive until you confirm, and is the
same wizard the Hermes flow runs.

Full walkthrough: [Installation](docs/installation.md) and
[Guided setup](docs/guided-setup.md).

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

## Skills and Curator

Chronalyn remembers what happened. Hermes Skills remember how to do it again.

A checkpoint may record:

```text
Problem X occurred.
Attempt A failed.
Repair Y worked.
Verification passed.
```

A Hermes Skill may encode the reusable procedure:

```text
Recover from Problem X
1. Check prerequisite A.
2. Confirm symptom B.
3. Apply Y.
4. Verify C.
5. Stop if verification fails.
```

Chronalyn does not automatically create or rewrite Skills today. Hermes' own
skill review and its Curator (an auxiliary-model task that periodically
reviews, pins, archives, and consolidates agent-created skills) handle the
Skills library independently.

## What is not in Chronalyn 1.0

These are future ideas, not current features:

- automatically turning repeated successful memories into Hermes Skills;
- automatically rewriting Skills from Chronalyn memory;
- a deterministic self-healing/repair verifier;
- unrestricted system repair;
- automatic knowledge sharing between installations;
- Chronalyn Console;
- Chronalyn Intelligence.

See [ROADMAP.md](ROADMAP.md) for the future direction.

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
See [Live validation](docs/live-validation.md) for the operator checklist.

## Documentation

- [Installation](docs/installation.md)
- [Hermes integration](docs/hermes-integration.md)
- [Migration](docs/migration.md)
- [Upgrading](docs/upgrading.md)
- [Rollback](docs/rollback.md)
- [Uninstall and data retention](docs/uninstall-and-data-retention.md)
- [Limitations](docs/limitations.md)
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
