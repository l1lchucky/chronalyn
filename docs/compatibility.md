# Compatibility

## Supported target

| Component | Supported/tested boundary |
|---|---|
| Python | 3.11, 3.12, 3.13 |
| Hermes Agent | 2026 `MemoryProvider` contract with one external provider |
| Hindsight API | Source-verified against generated OpenAPI 0.8.6 v1 endpoints |
| Mnemosyne | Source-verified against 3.15.2; supported range `>=3.15,<4` |
| OS | Linux is the production target |

## Verification levels

- **Core tested here:** router policy, idempotency, SQLite outbox, retry,
  deletion mapping, fallback, redaction, context exclusion, adapter request
  construction.
- **Source-verified:** current Hermes provider lifecycle and current public
  backend APIs.
- **Requires live environment:** plugin discovery, Hindsight endpoint behavior,
  real Mnemosyne embeddings, gateway concurrency, backup/restore.

## Upgrade policy

Patch releases may expand tested dependency ranges. Minor releases may add
routing policies. Breaking configuration or database changes require a major
release after `1.0`.

Before upgrading production:

1. back up router, Mnemosyne, and Hindsight;
2. test the new version on staging;
3. run the full live smoke test;
4. verify cross-environment marker isolation;
5. confirm failed delivery count is zero.
