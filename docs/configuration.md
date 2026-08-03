# Configuration

Path:

```text
$HERMES_HOME/memory-router/config.json
```

## Top level

- `namespace`: project or organization boundary.
- `environment`: deployment boundary.
- `state_db`: optional router SQLite path.
- `primary_backend`: must be `hindsight` in this release.
- `checkpoint_backend`: must be `mnemosyne` in this release.

## Hindsight

- `api_url`: Hindsight HTTP(S) endpoint.
- `api_key_env`: environment variable containing its API key.
- `bank_id`: isolated Hindsight bank.
- `timeout_seconds`: request timeout.
- `recall_budget`: `low`, `mid`, or `high`.
- `recall_max_tokens`: recall and reflect response budget.
- `recall_types`: preferred memory types.
- `tags`: tags added to retained documents.
- `verify_tls`: keep true outside controlled development.

## Mnemosyne

- `bank`: isolated checkpoint bank.
- `data_dir`: optional external data root.
- `top_k`: fallback result limit.

## Redaction

- `mode`: `redact`, `reject`, or `off`.
- `replacement`: substituted secret marker.
- `max_record_chars`: per-field bound.
- `custom_patterns`: deployment-specific regular expressions.

Production should use `reject` unless operational experience demonstrates that
redaction is required.

## Routing

- `fallback_on_empty`
- `fallback_on_error`
- `fallback_max_chars`
- `automatic_write_contexts`
- `include_tool_messages`: currently intentionally ignored and must remain false.
- worker and retry tuning.

See `examples/staging.json` and `examples/production.json`.
