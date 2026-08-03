# Why use Hermes Memory Router?

Hermes Memory Router is not a replacement for Hindsight or Mnemosyne. It is a
control and reliability layer that assigns each system a narrow role.

## The problem with connecting both MCP servers directly

A user can expose Hindsight MCP and Mnemosyne MCP to the same agent. That is
useful for manual experimentation, but it leaves the model responsible for
operational policy:

- deciding which system is authoritative;
- deciding whether to write to one or both;
- avoiding duplicate memories;
- resolving conflicting recall results;
- retrying partial writes;
- remembering backend IDs for deletion;
- deleting a logical record from both systems;
- keeping staging and production namespaces separate;
- keeping fallback context within a prompt budget.

MCP gives the model tools. It does not create a transaction or consistency
boundary across independent memory systems.

## What the router adds

The router presents one Hermes memory provider and one compact tool surface.
It applies policy before the model sees or writes memory.

### One authority for automatic memory

Hindsight owns normal automatic retention, recall, and reflection. Mnemosyne is
not queried unless Hindsight is empty or unavailable and fallback is enabled.
This avoids automatic result merging and duplicate prompt injection.

### Evidence-backed checkpointing

Mnemosyne receives only explicit checkpoints with a verification level and
supporting evidence. It becomes a compact recovery ledger rather than another
copy of every conversation.

### Durable outbox

Backend writes happen through a SQLite outbox. A failed Hindsight or Mnemosyne
write remains visible and retryable after the Hermes process restarts.

### Logical IDs and coordinated deletion

Each router record has one `mr_...` identifier. The router maps that logical ID
to the Hindsight document ID and Mnemosyne memory ID. Forgetting the logical
record schedules deletion from every backend that accepted it.

### Race protection

Pending retains are cancelled when forget is requested. When a retain finishes
at the same time as forget, the successful receipt automatically creates a
delete delivery so the forgotten record is not resurrected.

### Environment policy

Namespace and environment are part of the router's uniqueness boundary. The
recommended deployment additionally uses different Hindsight banks,
Mnemosyne banks, SQLite databases, hosts, and credentials.

## When direct Hindsight is better

Use Hindsight alone when:

- you want the simplest supported Hermes setup;
- Hindsight is sufficient as the only memory authority;
- you do not need an independent checkpoint ledger;
- you do not need coordinated cross-backend deletion or retry;
- lower component count matters more than redundancy.

## When direct Mnemosyne is better

Use Mnemosyne alone when:

- you want one local SQLite database;
- zero external service dependencies are the priority;
- MCP support across many coding clients is more important than Hindsight's
  deeper reflection and entity/temporal processing;
- you want the lowest operational overhead.

## When both MCP servers are better

Expose both MCP servers directly when:

- a human is supervising every memory operation;
- experimentation is the goal;
- duplicate writes and manual cleanup are acceptable;
- there is no requirement for atomic logical records or automatic retries.

## When the router is better

Use the router when:

- Hindsight should remain the automatic intelligence layer;
- Mnemosyne should be an independently searchable checkpoint ledger;
- partial backend failures must survive restarts;
- one logical delete must reach every backend;
- prompt and tool-schema duplication must be controlled;
- staging and production require explicit memory policy.

The router's value is policy, consistency, recovery, and observability—not a
claim that two memory engines are always better than one.
