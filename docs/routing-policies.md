# Routing policies

The initial release intentionally supports one safe policy set.

## Automatic writes: `primary_only`

Normal completed turns go only to Hindsight. Mnemosyne is not a second raw
conversation archive.

## Checkpoints: `primary_and_checkpoint`

A checkpoint is written to Hindsight and Mnemosyne. It must contain a declared
verification level and evidence.

## Recall: `primary_then_fallback`

Hindsight remains authoritative for automatic recall. Mnemosyne is a fallback
only when:

- Hindsight returns no hits and `fallback_on_empty` is true; or
- Hindsight fails and `fallback_on_error` is true.

## Context restrictions

Only `primary` agent context is written automatically by default. Subagent,
cron, and flush contexts are excluded because their system prompts and
intermediate outputs can pollute durable memory.

## Deletion

`memory_router_forget` deletes only router-managed records. It schedules a
backend deletion for every completed retain delivery. A failed deletion stays
in the outbox until retried.

## Why equal multi-provider routing is not supported

Equal automatic providers create duplicated memories, conflicting ranking,
larger prompts, more tool schemas, double extraction cost, and unclear deletion
semantics. This project offers explicit asymmetric policy instead.
