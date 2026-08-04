def drain_all(router, loops=10):
    for _ in range(loops):
        if not router.drain_outbox(100):
            break


def test_automatic_turn_writes_primary_only(router):
    instance, primary, checkpoint = router
    record_id = instance.retain_turn(
        user_content="hello",
        assistant_content="world",
        session_id="s1",
        agent_context="primary",
    )
    drain_all(instance)
    assert record_id
    assert len(primary.retained) == 1
    assert checkpoint.retained == {}


def test_non_primary_context_is_not_retained(router):
    instance, primary, _checkpoint = router
    result = instance.retain_turn(
        user_content="cron",
        assistant_content="noise",
        session_id="s1",
        agent_context="cron",
    )
    drain_all(instance)
    assert result is None
    assert not primary.retained


def test_checkpoint_dual_writes(router):
    instance, primary, checkpoint = router
    result = instance.checkpoint_record(
        content="Verified release candidate passed.",
        verification_level="tested",
        evidence="pytest: 42 passed",
    )
    drain_all(instance)
    states = instance.store.delivery_states(result.record_id)
    assert states == {
        "hindsight:retain": "complete",
        "mnemosyne:retain": "complete",
    }
    assert len(primary.retained) == 1
    assert len(checkpoint.retained) == 1


def test_duplicate_checkpoint_is_idempotent(router):
    instance, primary, checkpoint = router
    args = dict(
        content="Same verified checkpoint.",
        verification_level="tested",
        evidence="same evidence",
    )
    first = instance.checkpoint_record(**args)
    second = instance.checkpoint_record(**args)
    assert first.record_id == second.record_id
    assert second.duplicate
    drain_all(instance)
    assert len(primary.retained) == 1
    assert len(checkpoint.retained) == 1


def test_failed_delivery_retries(router):
    instance, _primary, checkpoint = router
    checkpoint.fail_retain = 1
    result = instance.checkpoint_record(
        content="Retry this verified checkpoint.",
        verification_level="tested",
        evidence="controlled failure test",
    )
    instance.drain_outbox(100)
    assert instance.store.delivery_states(result.record_id)["mnemosyne:retain"] == "failed"
    assert instance.retry(result.record_id) == 1
    instance.drain_outbox(100)
    assert instance.store.delivery_states(result.record_id)["mnemosyne:retain"] == "complete"


def test_forget_schedules_both_backends(router):
    instance, primary, checkpoint = router
    result = instance.checkpoint_record(
        content="Checkpoint to remove.",
        verification_level="environment-verified",
        evidence="deletion test",
    )
    drain_all(instance)
    instance.forget(result.record_id)
    drain_all(instance)
    states = instance.store.delivery_states(result.record_id)
    assert states["hindsight:delete"] == "complete"
    assert states["mnemosyne:delete"] == "complete"
    assert primary.deleted
    assert checkpoint.deleted


def test_failed_delete_is_retryable(router):
    instance, _primary, checkpoint = router
    result = instance.checkpoint_record(
        content="Checkpoint delete retry.",
        verification_level="environment-verified",
        evidence="delete failure test",
    )
    drain_all(instance)
    checkpoint.fail_delete = 1
    instance.forget(result.record_id)
    instance.drain_outbox(100)
    assert instance.store.delivery_states(result.record_id)["mnemosyne:delete"] == "failed"
    instance.retry(result.record_id)
    instance.drain_outbox(100)
    assert instance.store.delivery_states(result.record_id)["mnemosyne:delete"] == "complete"


def test_status_reports_outbox(router):
    instance, _, _ = router
    instance.checkpoint_record(
        content="Status checkpoint.",
        verification_level="tested",
        evidence="status test",
    )
    status = instance.status()
    assert status["store"]["deliveries"]["pending"] == 2
    assert status["routing"]["automatic_write"] == "hindsight-only"
    assert status["versions"]["router"]
    assert status["versions"]["configuration_schema"] == 2
    assert status["versions"]["database_schema"] == 2
    assert status["versions"]["python"]
    assert status["versions"]["sqlite"]
    assert status["deliveries"]["pending"] == 2
    assert status["oldest_incomplete_delivery"]["state"] == "pending"
    assert status["database"]["size_bytes"] > 0
    assert status["health"]["state"] == "warning"


def test_status_does_not_deliver_pending_work(router):
    instance, primary, _ = router
    instance.checkpoint_record(
        content="Status must not deliver.",
        verification_level="tested",
        evidence="status is read-only",
    )
    instance.status()
    assert primary.retained == {}


def test_forget_before_delivery_cancels_retains(router):
    instance, primary, checkpoint = router
    result = instance.checkpoint_record(
        content="Forget before backend delivery.",
        verification_level="environment-verified",
        evidence="pre-delivery cancellation test",
    )
    instance.forget(result.record_id)
    drain_all(instance)
    states = instance.store.delivery_states(result.record_id)
    assert states["hindsight:retain"] == "cancelled"
    assert states["mnemosyne:retain"] == "cancelled"
    assert primary.retained == {}
    assert checkpoint.retained == {}


def test_max_attempts_becomes_dead_and_manual_retry_recovers(router):
    instance, _primary, checkpoint = router
    instance.config.routing.max_attempts = 1
    checkpoint.fail_retain = 1
    result = instance.checkpoint_record(
        content="Dead-letter retry checkpoint.",
        verification_level="tested",
        evidence="max attempt test",
    )
    instance.drain_outbox(100)
    assert instance.store.delivery_states(result.record_id)["mnemosyne:retain"] == "dead"
    assert instance.retry(result.record_id) == 1
    instance.drain_outbox(100)
    assert instance.store.delivery_states(result.record_id)["mnemosyne:retain"] == "complete"


def test_checkpoint_metadata_is_sanitized_before_backend_delivery(router):
    instance, primary, checkpoint = router
    result = instance.checkpoint_record(
        content="Metadata sanitation checkpoint.",
        verification_level="tested",
        evidence="metadata test",
        metadata={"api_key": "plain-value", "nested": {"safe": "ok"}},
    )
    drain_all(instance)
    assert result.record_id
    for backend in (primary, checkpoint):
        retained = next(iter(backend.retained.values()))
        assert retained["metadata"]["api_key"] == "[REDACTED]"
        assert retained["metadata"]["nested"]["safe"] == "ok"


def test_backend_error_is_redacted_before_store(router):
    instance, _primary, checkpoint = router
    checkpoint.fail_retain = 1
    original = checkpoint.retain

    fake_bearer = "-".join(("demo", "token", "not", "secret")) * 2

    def secret_failure(**kwargs):
        raise RuntimeError("Authorization: Bearer " + fake_bearer)

    checkpoint.retain = secret_failure
    result = instance.checkpoint_record(
        content="Error redaction checkpoint.",
        verification_level="tested",
        evidence="controlled backend error",
    )
    instance.drain_outbox(100)
    row = (
        instance.store._connection()
        .execute(
            "SELECT last_error FROM deliveries WHERE record_id=? AND backend='mnemosyne'",
            (result.record_id,),
        )
        .fetchone()
    )
    assert fake_bearer not in row["last_error"]
    assert "[REDACTED]" in row["last_error"]
    checkpoint.retain = original
