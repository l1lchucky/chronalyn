# Testing record

## Deterministic suite

Final artifact result: **62 tests passed** with **89.47% branch-aware deterministic-core coverage**. Python compilation, shell syntax, wheel build, and a clean-virtual-environment wheel smoke test also passed.


The repository's tests use fake backends to verify behavior without depending
on network services:

- primary/fallback recall routing;
- automatic primary-only writes;
- dual checkpoint delivery;
- durable retry after failure;
- mapped deletion and deletion retry;
- idempotency under concurrency;
- namespace isolation;
- secret redaction and rejection;
- context exclusion;
- Hindsight request construction;
- provider failure behavior.

## Live test limitations

The artifact-building environment did not provide installable Hindsight or
Mnemosyne packages and did not run a Hermes gateway. Therefore no claim is made
that live backend or plugin discovery testing was completed here.

Production activation requires `scripts/live-smoke-test.sh` plus the isolation,
backup, and failure-recovery tests documented in the repository.


## Quality-tool availability

The artifact environment did not provide Ruff or mypy and its package mirror
could not install them. They are therefore optional maintainer checks, not part
of the claimed local validation. The required CI gate uses the checks completed
here: compilation, shell parsing, tests with coverage, distribution build,
clean-wheel installation, plugin-resource installation, and dependency
consistency.
