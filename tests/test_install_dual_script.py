import re
import shutil
import subprocess
from pathlib import Path

import pytest

from chronalyn import identity


def test_dual_installer_is_safety_first_and_branded():
    script = Path("scripts/install-dual.sh").read_text()
    assert "CHRONALYN" in script
    assert "HINDSIGHT PRIMARY + MNEMOSYNE CHECKPOINTS" in script
    assert "curl | bash" not in script
    assert "--proto '=https'" in script
    assert "sha256" in script.lower()
    # The installer must launch the RC command name, not the deprecated alias.
    assert "setup --package-source" in script
    assert "-m chronalyn.cli" in script
    assert re.search(r"(?m)^\s*sudo\s", script) is None
    assert "telemetry" in script.lower()
    assert "--non-interactive" in script
    assert "--with-browser" in script
    assert "--skip-browser" in script
    assert "hermes-agent/.venv/bin/python" in script


def test_installer_version_matches_package_identity():
    """Installer artifact names must not drift from the packaged version."""
    script = Path("scripts/install-dual.sh").read_text()
    assert f'VERSION="{identity.RELEASE_NAME.lstrip("v")}"' in script
    assert f'PY_VERSION="{identity.VERSION}"' in script
    assert identity.WHEEL.replace(identity.VERSION, "${PY_VERSION}") in script


def test_release_workflow_publishes_installer_and_checksums():
    workflow = Path(".github/workflows/release.yml").read_text()
    assert "cp scripts/install-dual.sh dist/install-dual.sh" in workflow
    # Artifact names derive from the release tag, not a hard-coded version.
    assert "TAG=${GITHUB_REF_NAME}" in workflow
    assert "SHA256SUMS-chronalyn-${TAG}.txt" in workflow
    assert "chronalyn-${TAG}.spdx.json" in workflow or "${SBOM_FILE}" in workflow
    assert "actions/attest@v4" in workflow
    assert 'subject-path: "dist/*"' in workflow
    # The RC-era hard-coded artifact name must be gone.
    assert "v1.0.0-rc.1" not in workflow


def test_workflows_use_only_checkout_v6_and_ci_checks_wheel_import_shim():
    workflows = list(Path(".github/workflows").glob("*.yml"))
    checkout_uses = [
        line.strip()
        for workflow in workflows
        for line in workflow.read_text(encoding="utf-8").splitlines()
        if "actions/checkout@" in line
    ]

    assert checkout_uses
    assert all("actions/checkout@v6" in use for use in checkout_uses)
    assert not any("actions/checkout@v7" in use for use in checkout_uses)
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert (
        "import hermes_memory_router, chronalyn; "
        "assert hermes_memory_router.provider is chronalyn.provider"
    ) in ci


def test_posix_installers_use_the_real_hermes_plugin_root():
    """Installers must not resurrect the undiscoverable plugins/memory path."""
    for name in ("install.sh", "uninstall.sh", "install-dual.sh"):
        script = Path("scripts") / name
        text = script.read_text()
        assert "plugins/memory/" not in text, name


def test_uninstaller_separates_package_removal_from_data_deletion():
    script = Path("scripts/uninstall.sh").read_text()
    # Both distributions are removed, but no data path is ever deleted.
    assert "pip uninstall -y chronalyn" in script
    assert "pip uninstall -y hermes-memory-router" in script
    assert "hermes-agent/.venv/bin/python" in script
    assert "/usr/local/lib/hermes-agent/.venv/bin/python" in script
    assert "Could not locate a Hermes Python environment" in script
    assert 'if [ "$provider_removed" = true ] && [ "$packages_removed" = true ]; then' in script
    assert 'echo "Removed Chronalyn package and Hermes provider entries."' in script
    assert "Preserved router state" in script
    for destructive in ("rm -rf", "hindsight/config.json", "router.db"):
        assert destructive not in script


def test_uninstaller_does_not_claim_removal_without_hermes_python(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("Bash is required to exercise the POSIX uninstaller")

    state = tmp_path / identity.STATE_DIRNAME
    state.mkdir()
    database = state / identity.STATE_DB_FILENAME
    database.write_bytes(b"durable-router-state")
    hindsight = tmp_path / "hindsight" / "config.json"
    hindsight.parent.mkdir()
    hindsight.write_text('{"bank_id": "keep-me"}', encoding="utf-8")

    result = subprocess.run(  # noqa: S603 -- executes the resolved trusted Bash binary.
        [bash, "scripts/uninstall.sh"],
        capture_output=True,
        check=False,
        env={"HOME": str(tmp_path), "HERMES_HOME": str(tmp_path), "PATH": ""},
        text=True,
    )

    assert result.returncode == 0
    assert "Could not locate a Hermes Python environment" in result.stderr
    assert "Removed Chronalyn package and Hermes provider entries." not in result.stdout
    assert database.read_bytes() == b"durable-router-state"
    assert hindsight.read_text(encoding="utf-8") == '{"bank_id": "keep-me"}'


def test_smoke_test_uses_the_new_command():
    script = Path("scripts/live-smoke-test.sh").read_text()
    assert "chronalyn validate" in script
    assert "chronalyn status" in script
