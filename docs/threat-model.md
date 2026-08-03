# Threat model

This document describes the problems the router is designed to reduce. It does
not claim to protect a machine after the operating system or Python runtime has
been compromised.

## Assets

- memory content;
- Hindsight credentials;
- Mnemosyne data;
- the router database and audit trail;
- staging and production boundaries;
- backup copies.

## Trust boundaries

1. Hermes calls the router plugin.
2. The router calls Hindsight over HTTP or HTTPS.
3. The router calls the installed Mnemosyne Python package.
4. SQLite files are read and written on the host.
5. Operators edit configuration and restore backups.

## Main risks

### Secrets stored as memory

A prompt, command result, or signed URL may contain a credential.

Controls:

- common secret patterns are redacted or rejected;
- raw tool messages are off;
- configuration contains environment-variable names, not secret values;
- production examples use reject mode.

Remaining risk: no pattern list catches every secret.

### Memory poisoning

Untrusted content may be saved as if it were a confirmed fact.

Controls:

- subagent, cron, and flush output is not written automatically;
- checkpoints require a verification level and evidence;
- direct runtime evidence outranks recalled memory;
- the model cannot change routing policy during a conversation.

### Staging data appearing in production

Controls:

- distinct bank names and credentials;
- profile, namespace, and environment binding in the router database;
- separate server deployments are recommended for strong isolation;
- live validation includes unique cross-environment markers.

Any cross-environment recall is a critical failure. Disable the provider and
inspect configuration and restored databases before continuing.

### Remote-service compromise or interception

Controls:

- TLS verification is on by default;
- API keys come from environment storage;
- remote endpoints require explicit consent;
- local Hindsight is recommended for sensitive workloads.

A backend response is memory context, not permission to deploy, delete data, or
change infrastructure.

### Backend outage

Controls:

- writes enter a durable local outbox first;
- retries use backoff;
- failed operations remain visible;
- Mnemosyne fallback is bounded and optional;
- a slow backend does not block `sync_turn()`.

### Incomplete deletion

Controls:

- each backend has its own delete delivery;
- backend IDs are saved from successful writes;
- failed deletes are retryable;
- a write/delete race schedules a follow-up delete.

### Installer supply-chain risk

Controls:

- HTTPS-only downloads;
- release checksums;
- optional GitHub attestation verification;
- no direct `curl | bash` path in the documentation;
- no hidden `sudo` call in the router bootstrap;
- downloaded sources and logs are shown to the user.

## Outside this threat model

- a compromised host or Python interpreter;
- malicious code in an installed dependency;
- physical access to an unlocked machine;
- backup encryption tooling;
- bugs inside Hindsight or Mnemosyne;
- legal classification of stored data.
