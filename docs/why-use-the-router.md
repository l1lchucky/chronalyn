# Why use the router?

The router is not a replacement for Hindsight or Mnemosyne. It gives each one a
clear role and adds the operational glue between them.

## Using both MCP servers directly

Connecting both MCP servers gives the model two sets of tools. A person can then
decide where each memory belongs and clean up mistakes manually.

What is still missing:

- one automatic memory authority;
- protection from duplicate writes and duplicate recall;
- retry after a partial failure;
- one logical ID that maps to both backends;
- coordinated deletion;
- a durable record of pending work;
- an environment-isolation check.

That can be acceptable for experimentation. It is harder to operate unattended.

## What the router adds

### Hindsight remains the main memory

Normal completed turns, primary recall, and reflection go to Hindsight. The
router does not dilute that role by querying both systems on every turn.

### Mnemosyne becomes a checkpoint ledger

Only deliberate milestones are written to Mnemosyne. Examples include a tested
release, a migration result, a confirmed root cause, or a rollback point.

### Writes survive restarts

The router saves work in SQLite before contacting a backend. A failed delivery
is still there after Hermes restarts and can be retried.

### One ID controls both copies

The router maps one `mr_...` ID to the Hindsight document ID and the Mnemosyne
memory ID. That mapping is used for status, retry, and deletion.

### Delete races are handled

If a pending write is forgotten, it is cancelled. If the write was already in
flight and finishes late, the receipt creates a follow-up delete.

### The prompt stays smaller

Hermes sees a small router tool set. It does not receive every Hindsight and
Mnemosyne administration tool or a merged recall result on each turn.

## When Hindsight alone is better

Use Hindsight directly when you want the simplest setup and do not need a second
checkpoint store, coordinated deletion, or the router's outbox.

## When Mnemosyne alone is better

Use Mnemosyne directly when a local SQLite memory and broad MCP access matter
more than Hindsight's extraction and reflection features.

## When both MCP servers are better

Use both directly when the goal is hands-on experimentation and a person will
review every memory action.

## When the router is a good fit

Use the router when Hindsight should stay automatic, Mnemosyne should preserve
important checkpoints, and failed writes or deletes must remain visible until
they finish.
