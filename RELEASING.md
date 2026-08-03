# Releasing Hermes Memory Router

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
6. Update `CHANGELOG.md`, `docs/compatibility.md`, and the version in:

   - `pyproject.toml`
   - `plugin.yaml`
   - `src/hermes_memory_router/__init__.py`
   - `src/hermes_memory_router/resources/plugin.yaml`
   - `CITATION.cff`

7. Create and push a signed tag:

   ```bash
   git tag -s v0.2.0-beta.1 -m "Hermes Memory Router v0.2.0-beta.1"
   git push origin v0.2.0-beta.1
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

Keep the beta on GitHub Releases until the live staging checklist passes. When
PyPI publishing is enabled, use GitHub Trusted Publishing instead of a
long-lived PyPI token.
