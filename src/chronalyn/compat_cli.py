"""Deprecated ``hermes-memory-router`` console entry point.

Chronalyn was previously published as Hermes Memory Router. This shim keeps the
old command working for existing installations while making the rename visible.

Design constraints, each covered by a test:

* The warning is written to **stderr**, so ``--json`` consumers parsing stdout
  are unaffected.
* Arguments are forwarded verbatim and the delegated exit code is returned
  unchanged, so scripts keep observing the same behaviour.
* No behaviour is reimplemented here: it is a thin delegation to
  :func:`chronalyn.cli.main`.
"""

from __future__ import annotations

import sys

from . import identity
from .cli import main as chronalyn_main


def main(argv: list[str] | None = None) -> int:
    """Warn about the rename, then delegate to the Chronalyn CLI."""
    print(f"WARNING: {identity.DEPRECATION_NOTICE}", file=sys.stderr)
    return chronalyn_main(argv)


if __name__ == "__main__":  # pragma: no cover - console-script parity
    raise SystemExit(main())
