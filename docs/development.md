# Development

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Quality gate

```bash
make check
```

## Design rules

- Never expose both full backend tool sets.
- Never automatically write ordinary turns to both backends.
- Never silently drop failed writes.
- Never store API keys in configuration.
- Never merge environment namespaces.
- Keep adapters behind `MemoryBackend`.
- Preserve forward-only SQLite migrations.
- Add failure-path tests before adding new routing behavior.

## Adding a backend

Implement `MemoryBackend`, then document:

- retain semantics and idempotency;
- recall result normalization;
- stable external identifier;
- deletion semantics;
- health behavior;
- privacy boundary;
- compatibility range.

A backend cannot become automatic without a routing-policy review and threat
model update.

## Release process

1. update version, changelog, and compatibility matrix;
2. run local checks;
3. test against live staging;
4. create a signed tag;
5. let GitHub Actions build artifacts;
6. publish a GitHub pre-release;
7. publish to PyPI only after beta stability.
