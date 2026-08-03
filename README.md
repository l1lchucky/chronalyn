# Hermes Memory Router

[![CI](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/ci.yml/badge.svg)](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/ci.yml)
[![Security](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/security.yml/badge.svg)](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Hermes Memory Router gives Hindsight and Mnemosyne separate jobs instead of
letting them compete for every turn.

Hermes still sees one external memory provider. Behind that provider:

- **Hindsight** handles normal automatic memory, recall, and reflection.
- **Mnemosyne** keeps deliberate, evidence-backed checkpoints and can act as a
  small fallback when Hindsight is unavailable or has no answer.
- A local **SQLite control database** tracks writes, retries, backend IDs,
  deletions, and the active environment.

The result is not “two memories are always better than one.” It is a practical
way to keep Hindsight as the main memory system while giving important project
milestones a second, portable home.

> **Current release:** `0.2.0-beta.1`. Use it on staging first. The automated
> test suite covers the router itself, but a real installation still needs the
> live checks in [docs/live-validation.md](docs/live-validation.md).

## The policy in one screen

```text
NORMAL TURN   -> HINDSIGHT only
CHECKPOINT    -> HINDSIGHT + MNEMOSYNE
FAILOVER      -> bounded MNEMOSYNE checkpoints
MERGED RECALL -> never
```

That policy is intentionally narrow:

- normal conversations are not copied into both systems;
- recall results are not merged into one large prompt;
- installing Mnemosyne does not activate it;
- existing Hindsight memories are not copied or rewritten;
- the router never patches Hermes core.

See [Routing policies](docs/routing-policies.md) for the exact rules.

## Why not connect both MCP servers?

You can connect Hindsight MCP and Mnemosyne MCP directly. That is useful when a
person is supervising every memory action.

What MCP does not provide is a shared operating policy. It does not decide which
system owns automatic memory, retry a half-completed write after a restart, map
one logical record to two backend IDs, or make sure one delete reaches both
systems.

The router handles those jobs while keeping the model-facing tool list small.
A fuller comparison is in [Why use the router?](docs/why-use-the-router.md).

## One-command dual setup

The release includes a lightweight, monochrome terminal installer for Linux,
macOS, and WSL. It supports arrow keys, number keys, Space, Enter, and mouse
clicks when the terminal reports mouse events.

After `v0.2.0-beta.1` is published as a GitHub Release:

```bash
curl --proto '=https' --tlsv1.2 -fsSLo /tmp/install-hmr-dual.sh \
  https://raw.githubusercontent.com/l1lchucky/hermes-memory-router/v0.2.0-beta.1/scripts/install-dual.sh \
  && bash /tmp/install-hmr-dual.sh
```

The command downloads the installer to a file before running it. It does not
pipe remote content straight into a shell.

A more cautious path is to review the script first:

```bash
curl --proto '=https' --tlsv1.2 -fsSLo install-hmr-dual.sh \
  https://raw.githubusercontent.com/l1lchucky/hermes-memory-router/v0.2.0-beta.1/scripts/install-dual.sh
less install-hmr-dual.sh
bash install-hmr-dual.sh
```

The bootstrap will:

1. reuse an existing Hermes installation when possible;
2. offer the official Nous Research Hermes installer when Hermes is missing;
3. show the downloaded installer source, size, and SHA-256 before it runs;
4. verify the router wheel against the release checksum file;
5. install the router inside Hermes' own Python environment;
6. open the **Dual Memory Router Setup** interface;
7. back up existing configuration before activation;
8. test both memory backends before making the router active.

It does not call `sudo` itself, enable telemetry, move historical memories, or
modify Hermes source files. The official Hermes installer is a separate upstream
script and may ask for system-package permissions on some platforms.

The base setup keeps Hermes lightweight. Browser automation is optional:

```bash
bash /tmp/install-hmr-dual.sh --with-browser
```

Read [Trusted bootstrap](docs/trusted-bootstrap.md) before using the one-command
installer on an important machine.

## The setup interface

The interface was made specifically for this dual-memory policy. It is built
with Python's standard `curses` module, so it does not install Rich, Textual,
Node.js, Electron, or a local web server.

```text
┌──────────────────────────────────────────────────────────────────────┐
│ DUAL MEMORY ROUTER                                      4 / 7       │
│ STRICT HINDSIGHT + MNEMOSYNE SETUP                                  │
├──────────────────────────────────────────────────────────────────────┤
│ Hindsight remains the only automatic memory authority.              │
│ Mnemosyne receives verified checkpoints, not every conversation.    │
│                                                                      │
│ 1  Reuse the Hindsight connection already configured                │
│ 2  Connect to a self-hosted Hindsight API                            │
│ 3  Connect to Hindsight Cloud                                        │
│                                                                      │
│ C  * * * *  Checking the selected backend                           │
├──────────────────────────────────────────────────────────────────────┤
│ ARROWS move  1-9 choose  SPACE select  ENTER continue  MOUSE click  │
└──────────────────────────────────────────────────────────────────────┘
```

Controls:

```text
ARROWS    move through choices
1-9       select a numbered choice
SPACE     select or toggle
ENTER     continue
MOUSE     click choices where supported
B         go back
Q / ESC   cancel without applying the plan
```

Run the interface again with:

```bash
hermes-memory-router setup-dual
```

Disable mouse reporting while keeping all keyboard controls:

```bash
hermes-memory-router setup-dual --no-mouse
```

See [Dual setup UI](docs/dual-setup-ui.md) for every screen and safety check.

## Manual installation

Requirements:

- Python 3.11, 3.12, or 3.13;
- a supported Hermes Agent installation;
- a reachable Hindsight API;
- `mnemosyne-memory` only when dual mode is selected.

From a source checkout:

```bash
git clone https://github.com/l1lchucky/hermes-memory-router.git
cd hermes-memory-router
python -m pip install .
hermes-memory-router install-plugin
```

Adopt an existing Hindsight setup without adding Mnemosyne:

```bash
hermes-memory-router adopt \
  --namespace my-project \
  --environment staging \
  --policy hindsight-only \
  --dry-run
```

Review the plan, then rerun without `--dry-run`.

Add Mnemosyne later:

```bash
python -m pip install '.[mnemosyne]'
hermes-memory-router provider add mnemosyne --dry-run
hermes-memory-router provider add mnemosyne
```

Only new verified checkpoints are written to Mnemosyne. Existing Hindsight data
stays where it is.

## Hindsight choices

The guided setup supports three clear paths:

- reuse the Hindsight connection already configured for the Hermes profile;
- connect to an existing self-hosted Hindsight API;
- connect to Hindsight Cloud over HTTPS.

When a remote endpoint is selected, the setup explains that sanitized memory
content leaves the machine and asks for separate consent. `--yes` does not count
as cloud consent by itself.

The router manages memory routing. It does not manage a self-hosted Hindsight
server process or silently start an embedded daemon.

## Loading animation

Waiting steps use a small Pac-Man-style line in interactive terminals:

```text
C  * * * *  Checking backend health
```

It is automatically disabled in CI, JSON output, redirected logs, and
non-interactive terminals.

Disable it manually with either form:

```bash
hermes-memory-router --no-animation status
HMR_NO_ANIMATION=1 hermes-memory-router status
```

## Hermes tools

The standard tool profile stays small:

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

## Useful commands

```bash
hermes-memory-router detect
hermes-memory-router validate
hermes-memory-router status
hermes-memory-router retry
hermes-memory-router drain --limit 500
hermes-memory-router rollback --yes
```

All commands support JSON output where it makes sense:

```bash
hermes-memory-router --json status
```

## Keeping staging and production separate

Use separate Hermes profiles, bank names, router databases, credentials, and
backups:

```text
Staging server
├── Hindsight bank: my-project-staging
├── Mnemosyne bank: my-project-staging-checkpoints
└── router database bound to the staging Hermes profile

Production server
├── Hindsight bank: my-project-production
├── Mnemosyne bank: my-project-production-checkpoints
└── router database bound to the production Hermes profile
```

The router records the profile path, namespace, and environment in its database.
It refuses to open that database under a different binding.

## Testing

```bash
python -m pip install -e '.[test]'
make check
```

The test suite uses local fake backends for routing and failure scenarios. It is
not a substitute for testing a real Hermes, Hindsight, and Mnemosyne deployment.
Complete [Live validation](docs/live-validation.md) before production use.

## Documentation

- [Architecture](docs/architecture.md)
- [Routing policies](docs/routing-policies.md)
- [Hermes compatibility rules](docs/strict-compatibility.md)
- [Guided setup](docs/guided-setup.md)
- [Dual setup UI](docs/dual-setup-ui.md)
- [Trusted bootstrap](docs/trusted-bootstrap.md)
- [Configuration](docs/configuration.md)
- [Deployment models](docs/deployment-models.md)
- [Why use the router?](docs/why-use-the-router.md)
- [Threat model](docs/threat-model.md)
- [Privacy](docs/privacy.md)
- [Failure recovery](docs/failure-recovery.md)
- [Upgrading](docs/upgrading.md)
- [Roadmap](ROADMAP.md)

## Project status and affiliation

This is an independent community project. It is not maintained or endorsed by
Nous Research, Vectorize, Hindsight, or the Mnemosyne maintainers.

The code is available under the [MIT License](LICENSE).
