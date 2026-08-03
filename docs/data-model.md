# Data model

## `records`

One sanitized logical memory record. A checksum uniqueness constraint provides
idempotency within namespace, environment, and kind.

## `deliveries`

One backend operation for a record:

- backend;
- retain or delete;
- pending, processing, failed, or complete;
- external backend identifier;
- attempts and next retry time;
- last error and receipt.

## `audit_events`

Append-only operational events. This is an operational audit trail, not a legal
compliance log.

## Deletion lifecycle

```text
record retained
  ├── Hindsight receipt: document ID
  └── Mnemosyne receipt: memory ID

forget requested
  ├── Hindsight document deletion delivery
  └── Mnemosyne forget delivery
```


## Delivery terminal states

- `complete`: backend operation confirmed.
- `cancelled`: retain was prevented because forget was requested first.
- `dead`: automatic attempts reached the configured maximum; manual retry can
  return it to `pending`.
