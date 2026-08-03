# Routing policies

The router ships with two policies. Both keep Hindsight as the automatic memory
system.

## Hindsight only

Use this when you want the router's outbox, redaction, logical IDs, and upgrade
path without adding Mnemosyne.

```text
Normal turn     -> Hindsight
Explicit retain -> Hindsight
Checkpoint      -> Hindsight
Recall          -> Hindsight
Reflect         -> Hindsight
Fallback        -> off
```

## Hindsight with Mnemosyne checkpoints

Use this when important milestones need a second local record.

```text
Normal turn     -> Hindsight
Explicit retain -> Hindsight
Checkpoint      -> Hindsight and Mnemosyne
Recall          -> Hindsight first
Fallback        -> Mnemosyne checkpoints only
Reflect         -> Hindsight
Merged recall   -> off
```

A checkpoint includes a verification level and evidence. Typical checkpoints are
releases, migrations, incident conclusions, rollback points, and tested project
milestones.

## Context rules

Only the primary Hermes context is written automatically. Cron output, flush
work, and subagent results are ignored unless a person or the main agent creates
an explicit checkpoint.

Raw tool messages are not retained by default because they can contain file
paths, command output, signed URLs, or secrets.

## Delete rules

Each router record has one logical ID and one delivery per backend. A delete is
complete only after every backend that accepted the record confirms deletion.

If a write and delete happen at the same time, the successful write receipt is
used to schedule a follow-up delete. A late write should not bring a forgotten
record back.

## Why the policies are fixed

The model does not invent routing rules during a conversation. Policy changes
are operator actions because they change where data is stored and how recall
works.
