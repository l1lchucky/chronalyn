# Compatibility

## Supported range

| Component | Supported range |
|---|---|
| Python | 3.11, 3.12, 3.13 |
| Hermes Agent | the current public `MemoryProvider` contract with one external provider |
| Hindsight API | v1 retain, recall, reflect, health, version, and document-delete endpoints |
| Mnemosyne | `mnemosyne-memory>=3.15,<4` |
| Production operating system | Linux |

The source code was reviewed against the current upstream Hermes provider guide,
Hindsight API shape, and Mnemosyne public Python interface. A source review is
not the same as a live compatibility test.

## What the automated suite proves

The local suite checks routing, retries, deletion mapping, database binding,
redaction, setup plans, terminal controls, and request construction using fake
backends.

## What must be tested live

A staging installation must still verify:

- Hermes discovers and activates the plugin;
- the selected Hindsight endpoint accepts the requests;
- Mnemosyne can create, recall, and forget a real checkpoint;
- gateway shutdown and restart leave the outbox consistent;
- backups restore all three data stores together.

See [Live validation](live-validation.md).

## Upgrade rule

Test every router, Hermes, Hindsight, or Mnemosyne upgrade on staging first.
Back up the router database and both memory stores before changing production.
