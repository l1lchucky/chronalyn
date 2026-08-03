# Privacy

Hermes Memory Router is self-hosted software and does not operate a hosted
service. The project maintainers do not receive memory content.

## Data stored locally

The router database stores:

- sanitized record content;
- namespace and environment;
- record kind and metadata;
- backend external identifiers;
- delivery state, attempts, errors, and receipts;
- audit events.

Mnemosyne stores checkpoint content in its configured SQLite bank.

## Data sent remotely

When Hindsight uses a remote API, sanitized automatic turns and checkpoints are
sent to that API. Hindsight may use a configured language-model provider during
extraction or reflection. Review the Hindsight deployment's privacy terms and
model-provider configuration.

## Minimization defaults

- normal turns are not copied to Mnemosyne;
- raw tool messages are excluded;
- subagent and scheduled contexts are excluded;
- fallback injection is character-bounded;
- only router-managed records can be deleted through router tools.

## Operator responsibilities

Operators are data controllers for their deployment. They must define retention,
backup, deletion, user-consent, and access-control policies appropriate to their
jurisdiction and data.

## Telemetry

This project contains no telemetry, analytics, crash reporting, or automatic
network update check.
