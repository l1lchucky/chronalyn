from pathlib import Path
import re


def test_dual_installer_is_safety_first_and_branded():
    script = Path("scripts/install-dual.sh").read_text()
    assert "DUAL MEMORY ROUTER" in script
    assert "HINDSIGHT PRIMARY + MNEMOSYNE CHECKPOINTS" in script
    assert "curl | bash" not in script
    assert "--proto '=https'" in script
    assert "sha256" in script.lower()
    assert "setup-dual" in script
    assert re.search(r"(?m)^\s*sudo\s", script) is None
    assert "telemetry" in script.lower()
    assert "--non-interactive" in script
    assert "--with-browser" in script
    assert "--skip-browser" in script
    assert "hermes-agent/.venv/bin/python" in script


def test_release_workflow_publishes_installer_and_checksums():
    workflow = Path(".github/workflows/release.yml").read_text()
    assert "cp scripts/install-dual.sh dist/install-dual.sh" in workflow
    assert "SHA256SUMS-hermes-memory-router-0.2.0-beta.1.txt" in workflow
    assert "actions/attest@v4" in workflow
