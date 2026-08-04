from __future__ import annotations

import pytest

from chronalyn.exceptions import ConfigurationError


def _checkpoint(instance):
    result = instance.checkpoint_record(
        content="Delete me safely.",
        verification_level="tested",
        evidence="deletion confirmation test",
    )
    instance.drain_outbox(10)
    return result.record_id


def test_two_stage_delete(router):
    instance, primary, checkpoint = router
    record_id = _checkpoint(instance)
    plan = instance.plan_forget(record_id)
    assert plan["confirmation_token"]
    result = instance.apply_forget(record_id, plan["confirmation_token"])
    instance.drain_outbox(10)
    assert result["record_id"] == record_id
    assert primary.deleted
    assert checkpoint.deleted


def test_delete_token_is_one_time(router):
    instance, _, _ = router
    record_id = _checkpoint(instance)
    token = instance.plan_forget(record_id)["confirmation_token"]
    instance.apply_forget(record_id, token)
    with pytest.raises(ConfigurationError, match="already used"):
        instance.apply_forget(record_id, token)


def test_invalid_delete_token_is_rejected(router):
    instance, _, _ = router
    record_id = _checkpoint(instance)
    instance.plan_forget(record_id)
    with pytest.raises(ConfigurationError, match="Invalid"):
        instance.apply_forget(record_id, "wrong-token")
