from __future__ import annotations

import io
from dataclasses import replace

import pytest

from hermes_memory_router.compatibility import HermesDiscovery
from hermes_memory_router.exceptions import ConfigurationError
from hermes_memory_router.operations import (
    build_plan,
    confirm,
    recommended_policy,
    require_cloud_approval,
)
from hermes_memory_router.policy import HINDSIGHT_MNEMOSYNE, HINDSIGHT_ONLY


def state(**changes):
    base = HermesDiscovery(
        hermes_home="/tmp/home",
        config_path="/tmp/home/config.yaml",
        config_exists=True,
        active_providers=("hindsight",),
        active_provider="hindsight",
        hermes_command="/usr/bin/hermes",
        hermes_version="1.0",
        contract_available=True,
        contract_missing_methods=(),
        hindsight_config_path="/tmp/home/hindsight/config.json",
        hindsight_config_exists=True,
        hindsight_api_url="http://127.0.0.1:8888",
        hindsight_bank_id="syncost-staging",
        hindsight_mode="local_external",
        hindsight_is_cloud=False,
        hindsight_is_remote=False,
        mnemosyne_installed=False,
        mnemosyne_version=None,
        router_config_exists=False,
        conflicts=(),
    )
    return replace(base, **changes)


def test_recommendation_uses_dual_only_when_mnemosyne_installed():
    assert recommended_policy(state()) == HINDSIGHT_ONLY
    assert recommended_policy(state(mnemosyne_installed=True)) == HINDSIGHT_MNEMOSYNE


def test_plan_matches_strict_user_visible_flow():
    plan = build_plan(state(mnemosyne_installed=True), policy=HINDSIGHT_MNEMOSYNE)
    rendered = plan.render()
    assert "Active Hermes provider: hindsight" in rendered
    assert "Hindsight bank: syncost-staging" in rendered
    assert "Primary backend: hindsight" in rendered
    assert "Checkpoint backend: mnemosyne" in rendered
    assert "Existing Hindsight memories:\n  Preserved" in rendered
    assert "Migration:\n  None" in rendered


def test_noninteractive_confirmation_requires_yes():
    stream = io.StringIO("yes\n")
    with pytest.raises(ConfigurationError, match="--yes"):
        confirm("Apply?", assume_yes=False, input_stream=stream)
    assert confirm("Apply?", assume_yes=True, input_stream=stream)


def test_noninteractive_cloud_requires_explicit_flag():
    plan = build_plan(
        state(
            hindsight_api_url="https://cloud.example.test",
            hindsight_is_cloud=True,
        ),
        policy=HINDSIGHT_ONLY,
    )
    with pytest.raises(ConfigurationError, match="--allow-cloud"):
        require_cloud_approval(plan, allow_cloud=False, assume_yes=True)
    require_cloud_approval(plan, allow_cloud=True, assume_yes=True)
