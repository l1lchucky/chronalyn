<p align="center">
  <img src="docs/assets/chronalyn-logo.png" alt="Chronalyn" width="320">
</p>

<p align="center">
  <strong>Give Hermes a past it can actually use.</strong>
</p>

<p align="center">
  Long-term memory for Hermes Agent, with Hindsight recall and verified
  Mnemosyne checkpoints.
</p>

<p align="center">
  <a href="https://github.com/l1lchucky/chronalyn/actions/workflows/ci.yml"><img src="https://github.com/l1lchucky/chronalyn/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/l1lchucky/chronalyn/actions/workflows/security.yml"><img src="https://github.com/l1lchucky/chronalyn/actions/workflows/security.yml/badge.svg" alt="Security"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

Hermes already keeps important facts close. Chronalyn handles the deeper
history behind them: what happened, what failed, what worked, and which states
were verified.

- **Hindsight** handles long-term semantic memory and recall.
- **Mnemosyne** keeps verified checkpoints and provides bounded fallback.

Chronalyn is a Hermes memory plugin. Install it from inside Hermes and pick it
as your memory provider:

```bash
hermes plugins install l1lchucky/chronalyn
hermes memory setup
```

## How it works

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
Mnemosyne are internal Chronalyn backends; Hermes' memory manager allows the
built-in provider plus at most one external provider.

Chronalyn uses Hermes' public memory-provider contract. It does not patch
Hermes core, invent entry-point groups, or rely on private APIs. Details are in
[Hermes integration](docs/hermes-integration.md).

## Install

Requirements: Python 3.11–3.13, a supported Hermes Agent installation, a
reachable Hindsight API, and `mnemosyne-memory` only when you select dual mode.

### Recommended: from Hermes

```bash
hermes plugins install l1lchucky/chronalyn
hermes memory setup
```

Choose **Chronalyn** in the memory provider picker. The wizard detects your
Hermes installation and any existing Hindsight configuration, previews every
change, backs up configuration, activates Chronalyn as the single external
memory provider, then validates discovery and backend health. When it finishes,
`memory.provider` is set to `chronalyn`.

Two modes are available:

- **Hindsight only** — Hindsight handles every memory operation.
- **Dual memory** — Mnemosyne also keeps verified checkpoints, with bounded
  fallback when Hindsight has no answer.

Verify with `hermes memory status`.

### Python package (direct install)

```bash
python -m pip install chronalyn
chronalyn setup
```

This gives you the `chronalyn` CLI and the importable package. Installing the
package alone does not configure Hermes; `chronalyn setup` runs the same guided
wizard as the Hermes flow when you are ready. Hermes users should prefer the
recommended Hermes installation above, which installs the provider entry and
drives the wizard from `hermes memory setup`.

Full walkthrough: [Installation](docs/installation.md) and
[Guided setup](docs/guided-setup.md).

## Memory policy

Chronalyn gives Hindsight and Mnemosyne separate jobs instead of letting them
compete for every turn:

```text
NORMAL TURN        -> Hindsight
EXPLICIT RETAIN    -> Hindsight
REFLECTION         -> Hindsight
CHECKPOINT (dual)  -> Hindsight + Mnemosyne
RECALL             -> Hindsight first
FALLBACK           -> bounded Mnemosyne checkpoints
MERGED RECALL      -> never
```

The policy is intentionally narrow: normal conversations are not copied into
both systems, installing Mnemosyne does not activate it, existing Hindsight
memories are never rewritten, and merged recall is never produced. Exact rules
are in [Routing policies](docs/routing-policies.md).

## Commands

The everyday commands:

```bash
chronalyn status
chronalyn validate
chronalyn doctor
chronalyn db check
chronalyn db backup --output /secure/path/router.sqlite
```

`chronalyn setup` runs the same guided wizard as the Hermes flow. Most commands
support `--json` (`chronalyn --json status`). The full CLI, including the
legacy `hermes-memory-router` alias, is documented in
[Operations](docs/operations.md).

## Safety and data

- Model-requested deletion is **off by default**; when enabled it uses a
  two-step plan/apply flow with a short-lived confirmation token
  (`memory_router_forget_plan` / `memory_router_forget_apply`).
- Every configuration change is backed up first and can be rolled back.
- Removing the package **never deletes memory**: router config, the state
  database, backups, Hindsight data, and Mnemosyne data are all retained.
- Cron, flush, and subagent output are not automatically retained; raw tool
  messages are never retained.

See [Uninstall and data retention](docs/uninstall-and-data-retention.md) and
[Rollback](docs/rollback.md).

## Skills

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

Chronalyn does not automatically create or rewrite Skills. Hermes' own skill
review and its Curator (an auxiliary-model task that reviews, pins, archives,
and consolidates agent-created skills) maintain the Skills library
independently.

## What is not in Chronalyn 1.0

Future ideas, not current features: automatic promotion of memories into
Skills, a deterministic self-healing verifier, unrestricted system repair,
automatic knowledge sharing between installations, Chronalyn Console, and
Chronalyn Intelligence. See [ROADMAP.md](ROADMAP.md).

## Documentation

- [Installation](docs/installation.md) · [Guided setup](docs/guided-setup.md)
- [Architecture](docs/architecture.md) · [Configuration](docs/configuration.md)
- [Routing policies](docs/routing-policies.md) · [Operations](docs/operations.md)
- [Hermes integration](docs/hermes-integration.md) · [Compatibility](docs/compatibility.md)
- [Live validation](docs/live-validation.md) · [Limitations](docs/limitations.md)
- [Migration](docs/migration.md) · [Failure recovery](docs/failure-recovery.md)
- [Privacy](docs/privacy.md) · [Threat model](docs/threat-model.md)
- [Database operations](docs/database-operations.md) · [Deployment models](docs/deployment-models.md)
- [Rollback](docs/rollback.md) · [Upgrading](docs/upgrading.md)
- [Uninstall and data retention](docs/uninstall-and-data-retention.md)
- [Rename migration matrix](docs/rename-migration-matrix.md) · [Roadmap](ROADMAP.md)

## Project status

An independent community project, not maintained or endorsed by Nous Research,
Vectorize, Hindsight, or the Mnemosyne maintainers. MIT licensed — see
[LICENSE](LICENSE).
