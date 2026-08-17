# Limitations

Current, real limitations of Chronalyn 1.0.

## Supported environments

- Python 3.11, 3.12, and 3.13.
- Hermes Agent versions supporting the memory-provider contract used here
  (see [Compatibility](compatibility.md)).
- Hindsight and Mnemosyne backend version boundaries are documented in
  [Compatibility](compatibility.md).

## Platform caveats

- The interactive setup wizard is a terminal UI (curses). It is tested on
  Linux, macOS, and WSL; behavior on other platforms follows the terminal
  capabilities available.
- Mouse support in the wizard is best-effort; number keys, arrows, SPACE, and
  ENTER always work.

## Compatibility aliases

These legacy identities remain for existing installations and are scheduled
for removal in a future major release:

- the `hermes-memory-router` CLI command (deprecation warning to stderr);
- the `hermes_memory_router` Python import shim;
- the `hermes_memory_router` Hermes provider id;
- the `setup-dual` command alias.

The `$HERMES_HOME/memory-router/` on-disk path is a durable compatibility path
and is not renamed.

## Not implemented in 1.0

These are roadmap items, not current features:

- automatically turning repeated successful memories into Hermes Skills;
- automatically rewriting Skills from Chronalyn memory;
- a deterministic self-healing/repair verifier;
- unrestricted system repair;
- automatic knowledge sharing between installations;
- Chronalyn Console;
- Chronalyn Intelligence.

Chronalyn stores checkpoint fields such as verification level and evidence
according to its implemented API. A command exit code of 0 does not by itself
prove a repair succeeded; verification semantics are the caller's responsibility
until a deterministic verification framework is built.

## Backend boundaries

- Mnemosyne is optional and only active in dual mode.
- Mnemosyne's LLM features are disabled by default; Chronalyn's checkpoint flow
  does not require an LLM.
- Hindsight embedding backend changes on an existing bank require an explicit
  migration (equal dimensions do not imply compatible vector spaces).
