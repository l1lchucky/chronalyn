"""Version and release-identity consistency for the stable 1.0 tree.

These tests guard the next release: every source of release identity must
agree, and no stale release-candidate identity may leak into the stable tree.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from chronalyn import identity

REPO_ROOT = Path(__file__).resolve().parent.parent


def _pyproject() -> dict[str, object]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)


def test_identity_version_matches_pyproject() -> None:
    project = _pyproject()["project"]
    assert project["version"] == identity.VERSION == "1.0.0"
    assert identity.RELEASE_NAME == "v1.0.0"
    assert identity.IS_RELEASE_CANDIDATE is False


def test_plugin_manifest_version_matches_identity() -> None:
    manifest = (REPO_ROOT / "plugin.yaml").read_text(encoding="utf-8")
    assert f"version: {identity.VERSION}" in manifest


def test_install_script_version_matches_identity() -> None:
    script = (REPO_ROOT / "scripts" / "install-dual.sh").read_text(encoding="utf-8")
    assert f'VERSION="{identity.RELEASE_NAME.lstrip("v")}"' in script
    assert f'PY_VERSION="{identity.VERSION}"' in script


def test_release_identity_is_stable_not_rc() -> None:
    # The stable tree must not carry release-candidate version strings.
    assert "rc" not in identity.VERSION.lower()
    assert "rc" not in identity.RELEASE_NAME.lower()
    assert identity.SBOM == "chronalyn-v1.0.0.spdx.json"
    assert identity.CHECKSUMS == "SHA256SUMS-chronalyn-v1.0.0.txt"


def test_repository_identity_uses_canonical_slug() -> None:
    assert identity.REPOSITORY == "l1lchucky/chronalyn"
    assert identity.RELEASE_BASE.startswith("https://github.com/l1lchucky/chronalyn/")
