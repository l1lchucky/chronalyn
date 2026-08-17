# Markdown audit manifest — Chronalyn 1.0 stable release preparation

Date: 2026-08-17
Branch: release/chronalyn-1.0
Base: main @ cd0af3440560d24eefb4d6fdb8c7e94055ee2964

44 Markdown files audited (root + docs + docs/adr + .github + after-install.md).

## Classification

UPDATED (rewritten for stable 1.0 identity/accuracy):
- README.md — new tagline, three complementary memory layers, current-vs-future
  separation, canonical install command, Skills/Curator section
- docs/installation.md — Hermes-native primary, RC/--pre removed
- docs/live-validation.md — validated-against list + operator checklist,
  native install flow
- docs/rc-limitations.md — converted to historical note
- docs/limitations.md — NEW: current real limitations
- docs/hermes-integration.md — origin-specific phases (native never
  reinstalls), canonical URL
- docs/compatibility.md — stable wording
- docs/migration.md — target version 1.0.0
- docs/architecture.md — canonical provider class name
- docs/trusted-bootstrap.md — v1.0.0 references
- docs/rename-migration-matrix.md — historical completion note added
- docs/README.md — limitations index entry, canonical link
- ROADMAP.md — shipped-in-1.0 / near-term / future direction
- RELEASING.md — v1.0.0 tag, tag-derived artifact names, PyPI status
- CHANGELOG.md — [1.0.0] entry added; rc.1 entry retained as history
- after-install.md — both modes, canonical install

REVIEWED_CURRENT (accurate as-is, no changes needed):
- docs/adr/0001-asymmetric-memory-routing.md
- docs/data-model.md
- docs/database-operations.md
- docs/deployment-models.md
- docs/development.md
- docs/dual-setup-ui.md
- docs/failure-recovery.md
- docs/guided-setup.md
- docs/operations.md
- docs/privacy.md
- docs/rollback.md
- docs/routing-policies.md
- docs/strict-compatibility.md
- docs/threat-model.md
- docs/uninstall-and-data-retention.md
- docs/upgrading.md
- docs/why-use-the-router.md
- AUTHORS.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, GOVERNANCE.md,
  SECURITY.md, SUPPORT.md, TESTING.md, THIRD_PARTY_NOTICES.md,
  .github/pull_request_template.md

HISTORICAL_KEEP (retained for history/compatibility; may reference old names):
- CHANGELOG.md (1.0.0-rc.1 entry)
- docs/rename-migration-matrix.md (completed-rename record)
- docs/rc-limitations.md (historical note)
- docs/migration.md (old-name migration table)

## Checks

- one H1 per doc: PASS
- internal markdown links: PASS
- stale RC sweep: only historical/test-guard references remain
- old repository slug: only rename-migration-matrix (historical)
- old product name: only compatibility/deprecation contexts
- privacy scan: PASS (no private deployment data)
