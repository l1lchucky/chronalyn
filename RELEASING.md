# Releasing Hermes Memory Router

## Pre-release gate

1. Confirm the working tree contains no credentials, local databases, build
   output, or private deployment configuration.
2. Run:

   ```bash
   make check
   bash -n scripts/*.sh
   ```

3. Build and inspect distributions:

   ```bash
   python -m build
   python -m pip install twine
   twine check dist/*
   ```

4. Install the wheel in a clean virtual environment.
5. Run the full live validation matrix in `docs/live-validation.md`.
6. Update `CHANGELOG.md`, `docs/compatibility.md`, and the version in:
   - `pyproject.toml`
   - `plugin.yaml`
   - `src/hermes_memory_router/__init__.py`
   - `src/hermes_memory_router/resources/plugin.yaml`
7. Create a signed tag:

   ```bash
   git tag -s v0.1.0-alpha.1 -m "Hermes Memory Router v0.1.0-alpha.1"
   git push origin v0.1.0-alpha.1
   ```

## GitHub repository settings

Before making the repository public:

- enable private vulnerability reporting;
- enable secret scanning and push protection;
- enable Dependabot alerts and security updates;
- enable CodeQL;
- protect `main`;
- require CI and security checks;
- require CODEOWNER review for security-sensitive paths;
- disallow force pushes and branch deletion;
- enable signed-commit vigilance where practical.

## PyPI

The alpha release should remain GitHub-only until the live staging matrix passes.
When publishing to PyPI, use Trusted Publishing from the GitHub release workflow
rather than a long-lived PyPI token.
