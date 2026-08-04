# Releasing Chronalyn

## Before tagging a release

1. Confirm the working tree contains no credentials, local databases, generated
   reports, build output, or private deployment settings.
2. Run the full local gate:

   ```bash
   make check
   make quality
   make audit
   ```

3. Build and inspect the distributions:

   ```bash
   python -m build
   python -m pip install twine
   twine check dist/*
   ```

4. Install the wheel in a clean virtual environment and run the CLI/plugin smoke
   test.
5. Complete `docs/live-validation.md` on staging.
6. Update `CHANGELOG.md`, `docs/compatibility.md`, and the version. The Python
   version and human release name live in one place:

   - `src/chronalyn/identity.py` (`VERSION`, `RELEASE_NAME`) — the single source
     of truth consumed by the CLI, health output, bootstrap, and User-Agent

   Then mirror it in the files that cannot import it:

   - `pyproject.toml`
   - `plugin.yaml` — the root manifest is retained for this RC as a public
     plugin release input; its name and version must match canonical identity
   - `CITATION.cff`
   - `scripts/install-dual.sh` (`VERSION`, `PY_VERSION`)
   - `.github/workflows/release.yml` (SBOM and checksum file names)

   `tests/test_install_dual_script.py` asserts the installer and workflow names,
   while `tests/test_plugin_entry.py` asserts the root manifest public identity,
   match `identity.py`. A missed release input therefore fails the suite rather
   than shipping another source of truth.

7. Create and push a signed tag:

   ```bash
   git tag -s v1.0.0-rc.1 -m "Chronalyn v1.0.0-rc.1"
   git push origin v1.0.0-rc.1
   ```

## GitHub settings

Before making the repository public:

- enable private vulnerability reporting;
- enable secret scanning and push protection;
- enable Dependabot alerts and security updates;
- enable CodeQL;
- protect `main`;
- require CI and security checks;
- require CODEOWNER review for security-sensitive paths;
- disallow force pushes and branch deletion.

## PyPI

Keep the release candidate on GitHub Releases until the live staging checklist
passes. When PyPI publishing is enabled, use GitHub Trusted Publishing instead
of a long-lived PyPI token.
