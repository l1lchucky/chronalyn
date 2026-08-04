# Staying compatible with Hermes

The router is designed to fit inside Hermes' memory-provider interface, not work
around it.

## One provider from Hermes' point of view

Hermes should have one active external provider:

```yaml
memory:
  provider: chronalyn
```

Hindsight and Mnemosyne are internal router backends. Do not also list them as
separate active Hermes memory providers. The router checks for that conflict and
refuses to start rather than risk duplicate writes and duplicate context.

## No silent activation

Installing a Python package is not permission to change memory behavior.

The router may detect an existing Hindsight setup or an installed Mnemosyne
package, but detection is read-only. It shows a plan, asks for approval, backs up
configuration, applies the change, and provides a rollback path.

It will not activate a backend, migrate data, restart Hermes, or send data to a
remote service just because a package is present.

## No Hermes patching

The plugin uses the public `MemoryProvider` interface. It does not patch
`MemoryManager`, edit `run_agent.py`, import Hermes' bundled Hindsight provider,
or replace built-in Hermes memory files.

## Keep the tool list small

The default tool profile exposes router-level actions rather than every native
operation from both backends. Backend administration stays in the CLI.

This keeps tool selection understandable and avoids recreating the schema bloat
that a composite provider is meant to prevent.

## Hermes owns context fencing

`prefetch()` returns plain recalled text. Hermes wraps it in its own
`<memory-context>` block. The router does not add a second wrapper or pretend
recalled memory is a new user message.

## Non-blocking turn writes

`sync_turn()` records the sanitized turn in the local outbox and returns. A
background worker sends it to Hindsight. Slow memory services should not hold up
a completed Hermes turn.

## Profile-scoped files

All router paths start from the `hermes_home` value supplied by Hermes. The
router database also records its profile path, namespace, and environment. A
mismatch stops startup and requires an explicit operator decision.

## Future Hermes multi-provider support

If Hermes later supports several external providers natively, the router remains
one provider. Users should still choose either the router or its child providers,
not both at once.
