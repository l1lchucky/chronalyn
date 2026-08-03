# Architecture

## Components

```text
Hermes MemoryManager
        │
        ▼
HermesMemoryRouterProvider
        │
        ├── policy and redaction
        ├── SQLite control plane
        │   ├── records
        │   ├── backend deliveries
        │   ├── retries
        │   └── audit events
        │
        ├── Hindsight REST adapter
        └── Mnemosyne Python adapter
```

Hermes sees one provider and one compact tool set. The provider implements the
current Hermes lifecycle: initialization, prompt block, prefetch, turn sync,
tools, session switch, pre-compression, backup paths, and shutdown.

## Authority

1. Repository, runtime, database, service, and deployment evidence.
2. Hindsight automatic memory.
3. Mnemosyne verified checkpoints.
4. Conversation inference.

Memory never overrides directly observed state.

## Write path

Automatic turns are sanitized, deduplicated, committed to SQLite, and queued
only for Hindsight. Checkpoints are queued for both backends. The caller is not
blocked on backend latency.

## Read path

Hindsight is queried first. Mnemosyne is queried only when Hindsight returns no
hits or raises an error and the matching fallback option is enabled. Fallback
content has a strict character budget.

## Control-plane durability

Each record has a stable `mr_<uuid>` identifier. Each backend operation has its
own delivery row with attempts, next retry time, external ID, receipt, and last
error. Deletion is generated from successful retain receipts, preventing the
router from claiming a backend deletion it cannot identify.

## Concurrency

SQLite runs in WAL mode with a 30-second busy timeout. Record creation uses an
immediate transaction and a uniqueness constraint over namespace, environment,
kind, and content checksum. This makes repeated checkpoint submissions
idempotent under concurrent gateway sessions.
