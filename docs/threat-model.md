# Threat model

## Assets

- User and project memories
- Hindsight API credentials
- Mnemosyne SQLite data
- Router mapping/outbox database
- Environment isolation boundaries
- Audit and deletion state

## Trust boundaries

1. Hermes process to router provider
2. Router to Hindsight over HTTP(S)
3. Router to local Mnemosyne Python package
4. Router and Mnemosyne SQLite files
5. Operators editing configuration and restoring backups

## Threats and controls

### Secret exfiltration

Threat: credentials appear in prompts, tool output, signed URLs, or environment
files and are retained.

Controls:

- built-in credential, JWT, private-key, DSN, signed-URL, and entropy detection;
- configurable redact or reject mode;
- raw tool messages excluded;
- no secret values stored in JSON configuration;
- production example defaults to rejection.

Residual risk: pattern detection is not perfect. Operators must still avoid
feeding secrets to memory tools.

### Prompt or memory poisoning

Threat: untrusted tool, subagent, cron, or imported content becomes authoritative.

Controls:

- only primary context is automatically retained;
- checkpoints require verification level and evidence;
- Mnemosyne writes use external-write trust classification when supported;
- system prompt states that runtime evidence overrides memory.

### Cross-environment leakage

Threat: production recalls staging facts.

Controls:

- distinct bank names;
- profile-scoped configuration;
- separate router databases;
- validated namespace/environment identifiers;
- deployment guidance recommends physically separate servers;
- isolation smoke tests use unique markers.

### Backend compromise

Threat: a remote Hindsight service reads or alters memory.

Controls:

- TLS verification on by default;
- API key supplied through environment;
- local Hindsight recommended for sensitive deployments;
- backend responses are context, never operational authority.

### Availability failure

Threat: one backend is unavailable.

Controls:

- durable outbox;
- exponential retries;
- bounded fallback;
- agent continues without blocking on writes;
- status exposes backend and delivery health.

### Data deletion inconsistency

Threat: one backend deletes while another does not.

Controls:

- per-backend delete deliveries;
- mapped external identifiers;
- retryable failures;
- audit trail;
- no claim of global deletion until all deliveries complete.

## Out of scope

- Compromise of the host operating system or Python interpreter
- Malicious dependency code with host-level access
- Cryptographic backup tooling
- Hindsight or Mnemosyne internal correctness
- Legal classification of retained data
