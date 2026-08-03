# Architecture

```text
Hermes MemoryManager
        │
        ▼
HermesMemoryRouterProvider
        │
        ├── routing policy and redaction
        ├── SQLite control database
        │   ├── logical records
        │   ├── backend deliveries
        │   ├── retries and errors
        │   └── audit events
        │
        ├── Hindsight REST adapter
        └── optional Mnemosyne adapter
```

## What Hermes sees

Hermes sees one provider, one prompt contribution, and one small tool set. The
provider follows the normal Hermes lifecycle: initialize, prefetch, sync a turn,
handle tools, switch sessions, prepare for compression, report backup paths, and
shut down.

## What counts as truth

Current repository, database, service, and deployment state always outrank a
memory result. Hindsight is the main long-term memory. Mnemosyne checkpoints are
a recovery aid. Neither backend is allowed to overrule direct evidence.

## Write flow

1. The router sanitizes and bounds the content.
2. It writes a logical record and delivery jobs to SQLite.
3. `sync_turn()` returns to Hermes.
4. The background worker sends each due job to its backend.
5. The receipt and backend ID are saved for retry and deletion.

Normal turns create one Hindsight delivery. Dual-mode checkpoints create one
Hindsight delivery and one Mnemosyne delivery.

## Read flow

Hindsight is queried first. Mnemosyne is queried only when the policy allows
fallback and Hindsight either fails or returns no result. Fallback content has a
small character budget and contains checkpoints only.

## SQLite control database

Each logical record receives an `mr_...` ID. Delivery rows track:

- backend and operation;
- pending, processing, failed, dead, cancelled, or complete state;
- attempt count and next retry time;
- backend ID and receipt;
- last error.

SQLite uses WAL mode, foreign keys, full synchronization, and a busy timeout.
Record creation uses a unique checksum within the active namespace and
environment so repeated checkpoint submissions are idempotent.
