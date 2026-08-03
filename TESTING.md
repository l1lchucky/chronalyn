# Testing

The repository has two kinds of tests.

## Local automated tests

The normal test suite uses fake Hindsight and Mnemosyne adapters. That makes
failure cases repeatable without needing network services.

The suite covers:

- Hindsight-first recall and Mnemosyne fallback;
- Hindsight-only automatic writes;
- dual checkpoint writes;
- retries, dead deliveries, and restart-safe outbox state;
- logical IDs and coordinated deletion;
- delete/write race handling;
- profile, namespace, and environment binding;
- secret redaction and rejection;
- provider conflict detection;
- guided setup and rollback;
- terminal controls and Pac-Man animation behavior;
- bootstrap download and permission checks;
- package and plugin installation paths.

Run it with:

```bash
python -m pip install -e '.[test]'
make check
```

## Live checks

Fake backends cannot prove that a particular Hermes, Hindsight, and Mnemosyne
combination works on a real server. Before using the router in production, run
the checklist in [docs/live-validation.md](docs/live-validation.md) on staging.

The live check covers installation, automatic retention, fallback, retry,
delete behavior, environment isolation, and backup restoration.

## Optional maintainer checks

Ruff, mypy, and `pip-audit` are available through the `quality` and `dev`
extras. They are useful release checks but are not required to run the basic
test suite.
