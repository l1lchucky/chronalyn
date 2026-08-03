# Live validation

The local tests use fake backends. Complete this checklist on a staging host
before production use.

## 1. Install and discover the plugin

```bash
python -m pip install ./hermes_memory_router-0.2.0b1-py3-none-any.whl
hermes-memory-router install-plugin
hermes-memory-router setup-dual
hermes memory status
```

Pass: Hermes reports `hermes_memory_router` as the only external memory provider
and exposes only the expected router tools.

## 2. Check backend health

```bash
hermes-memory-router validate
hermes-memory-router status
```

Pass: the configured backends are healthy and no delivery is failed or dead.

## 3. Check automatic Hindsight retention

Use a unique harmless marker in a normal Hermes conversation. Finish the turn,
drain the outbox, start a new session, and recall the marker.

Pass: Hindsight recalls it and the Mnemosyne checkpoint bank does not contain it.

## 4. Check dual checkpoint delivery

Create a verified checkpoint with a different marker.

Pass:

```text
hindsight:retain = complete
mnemosyne:retain = complete
```

Recall the marker through the router.

## 5. Check fallback

Temporarily make Hindsight unreachable without deleting its data. Recall the
checkpoint marker.

Pass: Mnemosyne returns checkpoint-only context, fallback is reported, and the
result stays inside `fallback_max_chars`.

## 6. Check retry

Make one backend unavailable, create a checkpoint, restore the backend, then run:

```bash
hermes-memory-router retry
hermes-memory-router drain --limit 100
```

Pass: the failed delivery completes without a duplicate record.

## 7. Check deletion

Delete the test checkpoint through the administrative CLI or the enabled
two-step tool flow.

Pass:

```text
hindsight:delete = complete
mnemosyne:delete = complete
```

Neither backend recalls the marker afterward.

## 8. Check the write/delete race

Pause one backend while a checkpoint write is processing, request deletion, then
allow the write to finish.

Pass: a delete is scheduled from the late receipt and the memory does not remain.

## 9. Check excluded contexts

Generate cron, flush, and subagent activity.

Pass: it is not automatically retained unless explicitly checkpointed.

## 10. Check secret handling

Use a fake credential in a disposable test bank.

Pass:

- redact mode replaces it;
- reject mode blocks it;
- the original fake value does not appear in router, Hindsight, Mnemosyne, or
  logs.

Never use a real credential for this test.

## 11. Check staging and production isolation

Use different random markers in each environment.

Pass: each environment recalls only its own marker. Any crossover is a critical
failure. Disable the provider and inspect profile paths, bank IDs, credentials,
and restored databases.

## 12. Check backup restoration

Restore the router database, Mnemosyne data, and Hindsight data into a disposable
host with matching identity settings.

Pass: checkpoint IDs, backend mappings, delivery states, and recall remain
consistent.
