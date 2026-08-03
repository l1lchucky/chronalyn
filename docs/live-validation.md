# Live validation matrix

The deterministic suite cannot prove behavior of a live Hermes process,
Hindsight deployment, or installed Mnemosyne runtime. Complete this matrix on a
non-production server before production activation.

## 1. Install and discovery

```bash
python -m pip install ./hermes_memory_router-0.1.0a1-py3-none-any.whl
hermes-memory-router install-plugin
hermes-memory-router init --namespace test-project --environment staging
hermes config set memory.provider hermes_memory_router
hermes memory status
```

Pass condition: Hermes reports the router as active and exposes only the
`memory_router_*` tools.

## 2. Backend health

```bash
hermes-memory-router validate
hermes-memory-router status
```

Pass condition: Hindsight and Mnemosyne both report healthy, and the SQLite
control plane reports no failed or dead deliveries.

## 3. Primary recall and automatic retention

Create a unique non-sensitive marker in a normal primary Hermes turn. Complete
the turn, drain the outbox, start a new session, and recall the marker.

Pass condition: the turn is present in Hindsight and absent from the Mnemosyne
checkpoint bank.

## 4. Verified checkpoint dual write

Use `memory_router_checkpoint` with a unique marker and evidence.

Pass condition:

```text
hindsight:retain = complete
mnemosyne:retain = complete
```

Then search for the marker through `memory_router_recall`.

## 5. Fallback

Temporarily make Hindsight unreachable without deleting data. Recall the
checkpoint marker.

Pass condition: Mnemosyne returns checkpoint-only context, the response states
that fallback was used, and the result respects `fallback_max_chars`.

## 6. Retry

Make one backend unavailable, create a checkpoint, restore the backend, then run:

```bash
hermes-memory-router retry
hermes-memory-router drain --limit 100
```

Pass condition: the failed delivery becomes complete without creating duplicate
backend records.

## 7. Deletion

Call `memory_router_forget` for the test checkpoint and drain the outbox.

Pass condition:

```text
hindsight:delete = complete
mnemosyne:delete = complete
```

Neither backend may recall the marker afterward.

## 8. Forget/write race

Pause one backend while a checkpoint retain is processing, request forget, then
allow the retain to finish.

Pass condition: the router automatically schedules deletion and the memory does
not survive.

## 9. Context exclusion

Generate activity through cron, flush, and subagent contexts.

Pass condition: none is automatically retained unless explicitly checkpointed.

## 10. Secret policy

In a disposable isolated test bank, attempt a checkpoint containing a fake API
key.

Pass condition:

- `redaction.mode=redact`: the fake secret is replaced;
- `redaction.mode=reject`: the write is rejected;
- no raw secret appears in router, Hindsight, Mnemosyne, or logs.

Never use a real credential for this test.

## 11. Environment isolation

Use unique markers:

```text
STAGING-ONLY-<random>
PRODUCTION-ONLY-<random>
```

Pass condition: each environment recalls only its own marker. Any cross-recall is
a critical failure; disable the provider immediately and inspect bank IDs,
configuration paths, and restored databases.

## 12. Backup and restore

Back up the router DB, Mnemosyne data, and Hindsight database. Restore them into
a disposable environment with identical namespace and bank configuration.

Pass condition: checkpoints, backend mappings, and delivery states remain
consistent, and no staging data appears in a production restore.
