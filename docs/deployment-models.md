# Deployment models

The router runs inside Hermes. Hindsight can be local or remote. Mnemosyne stays
local in the current release.

## Separate self-hosted stacks

```text
Staging server
├── Hermes and router
├── self-hosted Hindsight
└── local Mnemosyne

Production server
├── Hermes and router
├── separate self-hosted Hindsight
└── separate local Mnemosyne
```

Best for: sensitive production data and strong staging/production isolation.

Advantages:

- each environment has a separate failure and trust boundary;
- memory databases remain under your control;
- a wrong bank name cannot reach the other server unless networking also allows
  it.

Costs:

- two Hindsight installations to update and monitor;
- more memory, disk, and database work;
- a language-model provider is still needed for Hindsight extraction and
  reflection unless your Hindsight setup handles it locally.

## Hindsight Cloud with local Mnemosyne

```text
Hermes host
├── router and SQLite control database
├── Hindsight Cloud over HTTPS
└── local Mnemosyne checkpoints
```

Best for: small hosts and teams that prefer managed Hindsight infrastructure.

Advantages:

- no local Hindsight service to operate;
- local checkpoints remain available during a cloud outage;
- router retries survive temporary network failures.

Costs:

- sanitized automatic memory leaves the host;
- internet availability affects primary recall;
- isolation relies on separate credentials and bank IDs rather than separate
  Hindsight servers.

## Central self-hosted Hindsight

```text
Private memory server
└── Hindsight
    ├── staging bank
    └── production bank

Each Hermes host
├── router
└── local Mnemosyne
```

Best for: a private VPS or internal network where one Hindsight service is easier
to maintain.

Advantages:

- one Hindsight installation;
- central backup and monitoring;
- local checkpoint fallback on each Hermes host.

Costs:

- one outage affects every environment;
- bank configuration errors have a wider impact;
- logical separation is weaker than separate servers.

A home Raspberry Pi can be useful for backups and monitoring. It is a weaker
choice for the only production Hindsight service because home power and internet
become production dependencies.

## Self-hosted Hindsight with an external model API

```text
Your server
├── Hindsight data and API
├── router
└── local Mnemosyne

External model API
└── Hindsight extraction and reflection
```

This keeps the memory database under your control while using an OpenAI-compatible
model endpoint for Hindsight's model work. Content sent for extraction still
leaves the server, so review that provider's privacy and retention terms.

## Mnemosyne sync

Mnemosyne can be backed up or synchronized separately. That sync is outside the
router's delivery transaction. Use different sync identities, keys, and stores
for staging and production.

## Practical recommendations

- strongest isolation: separate self-hosted stacks;
- easiest maintenance: Hindsight Cloud plus local Mnemosyne;
- balanced private setup: central Hindsight on a reliable private VPS, local
  Mnemosyne on each Hermes host;
- start on staging, then choose production hosting after real load and memory
  quality are understood.
