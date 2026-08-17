# Contributing

Thanks for taking the time to improve the project.

By submitting a contribution, you agree to license it under the MIT License.

## Before opening a pull request

1. Open an issue first for changes to routing, storage, deletion, privacy, or
   compatibility.
2. Keep the branch focused on one problem.
3. Add tests for the normal path and the failure path.
4. Run `make check`.
5. Update the relevant documentation and changelog.
6. Explain the security, privacy, compatibility, and rollback impact in the pull
   request.

A change will not be accepted if it silently drops writes, weakens environment
isolation, stores secrets in normal configuration, or turns both providers into
equal automatic memory backends without an approved design change.

## Environment setup

Chronalyn targets Python 3.11, 3.12, and 3.13.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

The package has no required runtime dependencies. Mnemosyne is an optional
extra used only when dual-memory mode is selected:

```bash
python -m pip install -e '.[mnemosyne]'
```

## Tests

```bash
pytest
```

The suite must stay green. The Hermes-provider integration tests
(`tests/test_hermes_native_integration.py`) exercise the real Hermes
memory-provider discovery contract when a Hermes source tree is importable on
the machine (see `docs/hermes-integration.md`); they skip cleanly otherwise, so
CI and contributor machines without Hermes still pass.

Coverage is enforced at 80%:

```bash
pytest --cov --cov-report=term-missing
```

## Lint and type checking

```bash
ruff check src tests
ruff format --check src tests
mypy src
```

## Hermes integration testing

To verify the native Hermes installation experience against a clean
`HERMES_HOME`:

```bash
hermes plugins install <local-or-git Chronalyn source>
hermes memory setup
hermes memory status
```

Chronalyn must appear as a selectable memory provider, its `post_setup` hook
must run the Chronalyn wizard in-flow, and activation must set
`memory.provider = chronalyn`. See `docs/hermes-integration.md` for the exact
contract.
