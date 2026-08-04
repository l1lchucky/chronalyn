from __future__ import annotations

import pytest

from chronalyn.exceptions import ConfigurationError
from chronalyn.store import RouterStore


def test_store_binding_reopens_with_same_identity(tmp_path):
    path = tmp_path / "router.db"
    first = RouterStore(
        path,
        namespace="project",
        environment="staging",
        profile_fingerprint="profile-a",
        strict_binding=True,
    )
    first.close()
    second = RouterStore(
        path,
        namespace="project",
        environment="staging",
        profile_fingerprint="profile-a",
        strict_binding=True,
    )
    assert second.stats()["binding"]["environment"] == "staging"
    second.close()


@pytest.mark.parametrize(
    "namespace,environment,profile",
    [
        ("other", "staging", "profile-a"),
        ("project", "production", "profile-a"),
        ("project", "staging", "profile-b"),
    ],
)
def test_store_binding_refuses_mismatch(tmp_path, namespace, environment, profile):
    path = tmp_path / "router.db"
    first = RouterStore(
        path,
        namespace="project",
        environment="staging",
        profile_fingerprint="profile-a",
        strict_binding=True,
    )
    first.close()
    with pytest.raises(ConfigurationError, match="binding mismatch"):
        RouterStore(
            path,
            namespace=namespace,
            environment=environment,
            profile_fingerprint=profile,
            strict_binding=True,
        )
