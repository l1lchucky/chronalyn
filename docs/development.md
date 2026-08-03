# Development

## Set up a local environment

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Run checks

```bash
make check
```

Optional style and type checks:

```bash
make quality
make audit
```

## Design rules

- Hermes sees one external provider.
- Normal turns are never written to both backends.
- Failed writes remain visible and retryable.
- Secrets do not belong in normal configuration files.
- Profile and environment bindings cannot be bypassed silently.
- Backend-specific code stays behind `MemoryBackend`.
- Database changes are forward-only and include recovery tests.
- New routing behavior needs a failure-path test and a threat-model update.

## Adding a backend

Implement `MemoryBackend` and document:

- the backend's role;
- retain idempotency;
- recall normalization;
- stable external IDs;
- deletion behavior;
- health and retry behavior;
- privacy boundary;
- supported versions.

A new backend is not automatically eligible for normal-turn writes.

## Release work

1. Update the version and changelog.
2. Run local checks and release-tree hygiene checks.
3. Test a clean wheel installation.
4. Complete live staging validation.
5. Create a signed tag.
6. Let GitHub Actions build and attest the release artifacts.
7. Publish to PyPI only after the beta is proven in live use.
