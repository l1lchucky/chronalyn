# ADR 0001: Asymmetric memory routing

- Status: Accepted
- Date: 2026-08-03

## Context

Hermes currently treats external memory as a single-provider choice. Running two
independent providers equally would duplicate tool schemas, recalled context,
normal-turn writes, and delete state.

## Decision

Ship one Hermes provider with fixed internal roles:

- Hindsight owns automatic retention, primary recall, and reflection.
- Mnemosyne stores verified checkpoints and optional fallback context.
- SQLite owns logical IDs, idempotency, retry state, backend mappings, and audit
  events.

## Benefits

- one clear automatic memory authority;
- no normal-turn duplication;
- small model-facing tool list;
- failed checkpoint writes survive restarts;
- one logical record can be deleted from both backends;
- the router remains compatible with Hermes' single-provider model.

## Costs

- one additional SQLite database;
- adapter maintenance when upstream APIs change;
- checkpoint copies are eventually consistent rather than atomic;
- every supported release combination needs live testing.

## Alternatives considered

- expose both providers directly and let the model choose;
- merge both recall result sets on every turn;
- write every normal turn to both backends;
- import Hermes' bundled Hindsight provider implementation;
- use Mnemosyne as the automatic primary backend.

These alternatives either weaken compatibility, increase prompt/tool size, or
make failure and deletion behavior harder to reason about.
