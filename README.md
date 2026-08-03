# Hermes Memory Router

[![CI](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/ci.yml/badge.svg)](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/ci.yml)
[![Security](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/security.yml/badge.svg)](https://github.com/l1lchucky/hermes-memory-router/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A policy-based composite memory provider for Hermes Agent:

- **Hindsight** is the primary automatic recall and retention backend.
- **Mnemosyne** stores evidence-backed checkpoints and acts as a bounded fallback.
- A local **SQLite control plane** provides idempotency, backend mappings,
  durable retries, deletion tracking, and an audit trail.

This project does not enable two equal automatic memory providers. Its asymmetric
routing avoids duplicate context, duplicate writes, tool-schema bloat, and
unclear authority.

> **Release status:** `0.1.0-alpha.1`. The core routing, redaction, outbox,
> retry, deletion, and isolation logic is tested. A live deployment must still
> pass the documented Hermes/Hindsight/Mnemosyne smoke test before production use.

## Routing

| Event | Destination |
|---|---|
| Automatic turn recall | Hindsight |
| Hindsight empty/error | Mnemosyne checkpoint fallback, when enabled |
| Automatic completed turn | Hindsight only |
| Verified milestone checkpoint | Hindsight and Mnemosyne |
| Reflect request | Hindsight only |
| Router-managed deletion | Every backend that retained the record |

## Installation

Requirements:

- Python 3.11–3.13
- Hermes Agent with the current `MemoryProvider` plugin contract
- Hindsight API reachable over HTTP(S)
- `mnemosyne-memory>=3.15,<4`

The alpha is installed from a source checkout or a GitHub Release wheel; it is
not yet published to PyPI.

```bash
git clone https://github.com/l1lchucky/hermes-memory-router.git
cd hermes-memory-router
./scripts/install.sh
```

After a GitHub Release exists, the attached wheel can be installed with
`python -m pip install ./hermes_memory_router-<version>-py3-none-any.whl`, then
`hermes-memory-router install-plugin`.

Create a profile-scoped configuration:

```bash
hermes-memory-router init \
  --namespace my-project \
  --environment staging
```

Edit:

```text
~/.hermes/memory-router/config.json
```

Set the Hindsight API key only when required:

```bash
printf '\nHINDSIGHT_API_KEY=replace-me\n' >> ~/.hermes/.env
chmod 600 ~/.hermes/.env
```

Activate:

```bash
hermes config set memory.provider hermes_memory_router
hermes memory status
```

Restart the gateway when applicable:

```bash
systemctl --user restart hermes-gateway.service
```

## Strict environment isolation

Run separate configurations and storage for staging and production:

```text
Staging server
├── Hindsight bank: my-project-staging
├── Mnemosyne bank: my-project-staging-checkpoints
└── Router SQLite DB: staging server only

Production server
├── Hindsight bank: my-project-production
├── Mnemosyne bank: my-project-production-checkpoints
└── Router SQLite DB: production server only
```

Never sync these banks or copy their databases across environment boundaries.

## Tools

- `memory_router_checkpoint`
- `memory_router_recall`
- `memory_router_reflect`
- `memory_router_forget`
- `memory_router_retry`
- `memory_router_status`

## Verification

Local deterministic test suite:

```bash
python -m pip install -e ".[test]"
make check
```

Live integration test:

```bash
./scripts/live-smoke-test.sh
```

See [Why use the router?](docs/why-use-the-router.md),
[Deployment models](docs/deployment-models.md), [Upgrade path](docs/upgrade-path.md),
[Compatibility](docs/compatibility.md), [Live validation](docs/live-validation.md),
and [Failure recovery](docs/failure-recovery.md) before production activation.

## Security posture

- Secrets are redacted or rejected before router-managed writes.
- Raw tool messages are not retained by default.
- Cron, flush, and subagent contexts are not automatically written.
- SQLite uses WAL, foreign keys, full synchronization, and durable outbox state.
- Backend failures fail open for the agent but remain visible and retryable.
- Repository/runtime evidence always overrides recalled memory.

See [Threat model](docs/threat-model.md), [Privacy](docs/privacy.md), and
[Security policy](SECURITY.md).

## Non-affiliation

This is an independent community project. It is not affiliated with, endorsed
by, or maintained by Nous Research, Vectorize, Hindsight, or the Mnemosyne
maintainers.
