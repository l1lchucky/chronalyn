# Privacy

Chronalyn is self-hosted software. The project maintainer does not
receive your memories, configuration, or usage data.

## What the router stores

The local router database contains:

- sanitized memory content;
- namespace and environment;
- record type and metadata;
- backend IDs and delivery receipts;
- retry state and errors;
- audit events for router operations.

Mnemosyne stores checkpoint content in its configured local bank.

## What may leave the machine

When Hindsight points to a remote service, sanitized normal turns and
checkpoints are sent to that endpoint. A self-hosted Hindsight installation may
also send content to the language-model provider it uses for extraction or
reflection.

The setup shows the selected endpoint before activation. Cloud use requires a
separate acknowledgement. Raw tool messages are off by default.

## Data minimization

The default policy keeps the amount of copied data small:

- normal turns are sent only to Hindsight;
- Mnemosyne receives verified checkpoints, not full conversations;
- fallback context is bounded;
- subagent, cron, and flush contexts are not automatically stored;
- telemetry and automatic update checks are not included.

## Redaction

Redaction catches common API keys, authorization headers, private keys, database
passwords, signed URLs, JWTs, and high-entropy tokens. Production can use reject
mode so a suspected secret stops the write instead of being replaced.

Pattern matching is a safety net, not a guarantee. Do not intentionally place
credentials or private customer data in memory.

## Operator responsibility

The person running the software decides retention, access, backups, deletion,
and consent. Check the privacy terms of every remote Hindsight or model service
you configure.
