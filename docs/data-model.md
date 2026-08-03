# Data model

The router uses one SQLite database as its control plane.

## `bindings`

Records the Hermes profile path, namespace, and environment that own the
database. A different binding cannot open it accidentally.

## `records`

Stores one sanitized logical memory record with an `mr_...` ID. A checksum makes
repeated submissions idempotent within the same namespace, environment, and
record type.

## `deliveries`

Stores one backend operation for one record:

- backend;
- retain or delete;
- state;
- backend ID;
- attempt count and retry time;
- last error;
- receipt metadata.

Delivery states:

- `pending`: waiting for the worker;
- `processing`: currently running;
- `failed`: retry is scheduled;
- `dead`: automatic attempts stopped and an operator must retry;
- `cancelled`: a pending write was stopped because the record was forgotten;
- `complete`: the backend confirmed the operation.

## `audit_events`

Keeps a small operational history of router actions. It is useful for debugging
but is not intended as a legal compliance log.

## Delete flow

```text
mr_123
├── Hindsight receipt -> document ID
└── Mnemosyne receipt -> memory ID

forget mr_123
├── delete Hindsight document
└── forget Mnemosyne memory
```

A delete is finished only when every required delivery is complete.
