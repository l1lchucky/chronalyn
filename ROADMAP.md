# Roadmap

This is a working plan, not a promise of dates or features. Priorities may move
when upstream APIs change, testing uncovers a problem, or users report a better
need.

## Shipped in 1.0

- Hermes-native plugin installation (`hermes plugins install l1lchucky/chronalyn`).
- Hindsight-only and dual-memory modes.
- Hindsight-first recall with bounded Mnemosyne fallback.
- Verified checkpoint routing to Mnemosyne in dual mode.
- Provider-neutral semantic embedding configuration.
- Mnemosyne LLM disabled by default.
- Durable SQLite control state with retries and an outbox.
- Safe two-step deletion flow.
- Backup and rollback.
- Native plugin lifecycle with data retention (update and remove never delete
  durable memory).
- Hermes' one-external-provider rule preserved.

## Near-term improvements

- Test against supported Hermes releases in CI.
- Add database integrity and migration commands.
- Add a guided backup-and-restore check.
- Expose simple metrics without requiring a monitoring stack.
- Add repair tools for orphaned backend records.
- Improve error messages using real staging feedback.

## Future direction

These are ideas, not commitments:

- **Chronalyn → Skill candidate bridge** — surface repeated, verified successes
  as candidate procedures for Hermes' skill review. Chronalyn remembers what
  happened; Skills remember how to do it again. The bridge would propose, not
  auto-write.
- **Deterministic verification framework** — a framework that verifies actual
  functionality after a repair, instead of trusting a command exit code.
- **Safe diagnostic/self-healing tools** — read-only diagnosis first, explicit
  repair actions only with operator consent.
- **Observability** — optional metrics and traces for the control plane.
- **Knowledge promotion** — explicit, user-approved promotion of local history
  to shared knowledge; never automatic.
- **Chronalyn Console** — a dashboard for the control plane.
- **Chronalyn Intelligence** — change intelligence and deployment analysis.

## Other memory backends

A new adapter needs a clear job. It must document its IDs, retry behavior,
delete behavior, privacy boundary, and failure policy. Provider count by itself
is not a project goal.
