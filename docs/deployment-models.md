# Deployment models

The router always runs inside the Hermes environment. Hindsight may be local or
hosted. Mnemosyne is local to the router in the initial release.

## Model A: fully self-hosted and physically isolated

```text
Staging server
├── Hermes + router
├── local Hindsight API/database
├── local Mnemosyne checkpoint bank
└── local router SQLite control plane

Production server
├── Hermes + router
├── separate local Hindsight API/database
├── separate local Mnemosyne checkpoint bank
└── separate local router SQLite control plane
```

### Advantages

- strongest staging/production boundary;
- memory remains available without home connectivity or a third-party cloud;
- full control of retention, backups, database, and LLM provider;
- Hindsight can use an OpenAI-compatible API while embeddings and storage stay
  on the server.

### Costs

- two Hindsight deployments to patch and monitor;
- database, disk, backup, and resource requirements on both servers;
- self-hosted Hindsight still needs an LLM provider for extraction and reflect
  unless a suitable local model is configured.

### Recommended for

Sensitive production environments, strict isolation, and teams with reliable
server operations.

## Model B: Hindsight Cloud plus local Mnemosyne

```text
Hermes server
├── router
├── Hindsight Cloud bank through HTTPS
├── local Mnemosyne checkpoint bank
└── local router SQLite control plane
```

### Advantages

- Hindsight operations, scaling, upgrades, and availability are managed;
- local Mnemosyne still provides an independent checkpoint/fallback copy;
- the router continues to provide retries, mappings, and coordinated deletion;
- fastest route to a dependable deployment.

### Costs

- automatic conversation memory is sent to Hindsight Cloud after router
  redaction/rejection policy;
- usage and long-term storage are billed;
- availability depends on network and vendor service;
- bank and API-key configuration becomes the main isolation boundary.

### Recommended for

Most users who value low maintenance more than keeping all Hindsight content on
their own infrastructure.

## Model C: one central self-hosted Hindsight API plus local Mnemosyne per host

```text
Central private Hindsight service
├── bank: staging
└── bank: production

Staging server: Hermes + router + local Mnemosyne
Production server: Hermes + router + local Mnemosyne
```

### Advantages

- only one Hindsight deployment to maintain;
- local checkpoint ledgers remain available during a Hindsight outage;
- lower total RAM and database administration than two Hindsight installations.

### Costs

- central Hindsight is a shared dependency;
- a wrong URL, key, or bank ID can weaken environment isolation;
- central outage affects automatic memory in both environments;
- network latency is added to every primary recall.

### Recommended for

A private network with competent access control where operational simplicity is
more important than physical isolation.

## Model D: Hindsight Cloud plus a self-hosted Mnemosyne sync server

The initial router writes to a local Mnemosyne bank. Mnemosyne Sync may then
replicate that local bank to a VPS or backup server.

### Advantages

- managed Hindsight;
- local checkpoint reads;
- encrypted Mnemosyne synchronization can provide off-host recovery;
- no shared writable SQLite file over a network filesystem.

### Costs

- the sync server is another service to secure and monitor;
- synchronization is eventual, not part of the router transaction;
- staging and production must use different sync identities, keys, and stores.

### Important clarification

The official Mnemosyne project documents a self-hosted sync service for VPS,
Docker, bare metal, and Fly.io deployments. Do not assume the existence of a
first-party managed Mnemosyne Cloud product unless the maintainers publish one.

## Model E: laptop or Raspberry Pi hosted backends

This is suitable for development, personal agents, backup, or monitoring. It is
not the preferred dependency for a customer-facing production server because
home power, sleep, storage, and internet become part of production memory
availability.

## Recommended security controls for every remote model

- HTTPS with certificate verification;
- bank-scoped or least-privilege Hindsight API keys;
- separate keys for staging and production;
- no API keys in JSON configuration or Git;
- production `redaction.mode=reject`;
- firewall or private network restrictions;
- encrypted backups with tested restoration;
- alerts for failed or dead router deliveries;
- unique cross-environment isolation markers during deployment.
