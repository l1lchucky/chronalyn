# Configuration

The profile-scoped file lives at:

```text
$HERMES_HOME/memory-router/config.json
```

The guided setup writes this file. Manual editing is supported, but run
`hermes-memory-router validate` afterward.

## Identity

- `namespace`: the project or organization name used to separate records.
- `environment`: the deployment boundary, such as `staging` or `production`.
- `state_db`: optional custom path for the router SQLite database.

The database is bound to the active Hermes profile path, namespace, and
environment.

## Policy

- `hindsight-only`
- `hindsight-primary-mnemosyne-checkpoints`

The policy chooses the backend roles. Individual low-level routing fields are
validated against that policy and cannot be used to create equal automatic
fan-out.

## Hindsight

- `api_url`: Hindsight HTTP or HTTPS endpoint.
- `api_key_env`: environment variable containing the API key.
- `bank_id`: bank dedicated to this project and environment.
- `timeout_seconds`: request timeout.
- `recall_budget`: `low`, `mid`, or `high`.
- `recall_max_tokens`: upper bound for recall and reflect output.
- `recall_types`: preferred Hindsight memory types.
- `tags`: tags added to router writes.
- `verify_tls`: keep enabled outside a controlled local test.

## Mnemosyne

- `enabled`: true only in dual mode.
- `bank`: checkpoint bank dedicated to this project and environment.
- `data_dir`: optional external data directory.
- `top_k`: fallback result limit.

## Privacy

- `redaction.mode`: `redact`, `reject`, or `off`.
- `redaction.replacement`: replacement text used in redact mode.
- `redaction.max_record_chars`: maximum size stored per field.
- `redaction.custom_patterns`: deployment-specific regular expressions.
- `include_tool_messages`: must remain false in this release.

## Tools

- `profile`: `minimal` or `standard`.
- `destructive_model_tools`: enables the two-step forget tools when true.
- `confirmation_ttl_seconds`: lifetime of a forget confirmation token.

## Worker and retry settings

The routing section controls worker polling, batch size, retry timing, fallback
conditions, and fallback character budget. The setup defaults are appropriate
for most installations.

See `examples/staging.json` and `examples/production.json` for complete files.
