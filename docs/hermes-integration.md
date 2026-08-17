# Hermes integration

Chronalyn integrates with Hermes Agent through Hermes' **public**
memory-provider mechanism. This document records the exact contract Chronalyn
relies on, and how that contract was verified.

Chronalyn does not:

- modify Hermes core;
- import a private Hermes API;
- invent an entry-point group, provider menu, configuration field, or lifecycle
  callback.

## The mechanism

Hermes discovers external memory providers as **directories**:

```text
$HERMES_HOME/plugins/<provider-id>/
├── __init__.py     # must expose register(ctx) or a MemoryProvider subclass
└── plugin.yaml     # manifest; declares kind: exclusive
```

Three rules govern discovery. All three were confirmed by probing an installed
Hermes with a temporary `HERMES_HOME`, not inferred from documentation:

1. **Discovery root.** `plugins/memory/__init__.py::_iter_provider_dirs` scans
   `$HERMES_HOME/plugins/<name>/` for user-installed providers. A nested
   `$HERMES_HOME/plugins/memory/<name>/` directory is **never** discovered.
2. **Text heuristic.** For user directories,
   `_is_memory_provider_dir` requires the literal substring
   `register_memory_provider` or `MemoryProvider` within the first 8 KiB of
   `__init__.py`. A provider whose entry mentions neither is skipped even when
   placed at the correct root.
3. **Manifest kind.** `hermes_cli/plugins.py` skips manifests declaring
   `kind: exclusive`: the generic plugin manager records the manifest but does
   not import the module, leaving activation to memory-category discovery. Both
   Chronalyn entries declare `kind: exclusive` explicitly rather than relying on
   Hermes' auto-coercion heuristic.

Activation is a single supported configuration write:

```yaml
memory:
  provider: chronalyn
```

Hermes loads exactly one external memory provider, read from `memory.provider`.
Chronalyn is designed for that model: it presents one provider, one prompt
contribution, and one small tool set, and it multiplexes Hindsight and Mnemosyne
internally.

### Provider ids

| Provider id | Status | Purpose |
|---|---|---|
| `chronalyn` | preferred | The canonical provider id. |
| `hermes_memory_router` | temporary alias | Keeps an existing `memory.provider: hermes_memory_router` configuration loadable. Delegates to the same implementation. |

Both entries are installed by default. The alias exists so upgrading Chronalyn
does not break a Hermes profile that still names the old provider. Migrating to
`chronalyn` is previewed and confirmed, never silent.

### Lifecycle methods used

Chronalyn implements the documented `MemoryProvider` surface:

`name`, `is_available`, `initialize`, `system_prompt_block`, `prefetch`,
`queue_prefetch`, `sync_turn`, `get_tool_schemas`, `handle_tool_call`,
`on_session_switch`, `on_pre_compress`, `on_session_end`, `on_memory_write`,
`shutdown`, `backup_paths`, `get_config_schema`, `save_config`.

`is_available()` performs local configuration checks only and never makes a
network call, as the contract requires.

## Installation and activation flow

There are two equivalent entry points into the same wizard:

- **Native Hermes flow (recommended):**

  ```bash
  hermes plugins install l1lchucky/chronalyn
  hermes memory setup        # choose Chronalyn
  ```

  `hermes memory setup` detects the provider's `post_setup(hermes_home, config)`
  hook and delegates the whole wizard to it, so the user never leaves the Hermes
  flow. Chronalyn's `post_setup` calls the same `run_dual_setup()` engine the
  standalone CLI uses, with a **setup origin** of `HERMES_PLUGIN` so the wizard
  treats Chronalyn as already installed by Hermes:

  - no Chronalyn package/wheel reinstall;
  - no provider-entry creation (the Hermes-managed Git clone is the entry);
  - no replacement of `$HERMES_HOME/plugins/chronalyn`;
  - configuration backup, backend/embedding setup, and
    `memory.provider=chronalyn` activation still run.

  The standalone flow uses `SetupOrigin.STANDALONE` and may still install
  provider entries where required.

- **Standalone flow (manual / developer):**

  ```bash
  python -m pip install chronalyn
  chronalyn setup
  ```

Both flows run the same logical phases in order. Nothing is mutated before the
preview is shown and confirmed. Installation actions differ by origin:

1. **Ensure Chronalyn is available** — the native flow skips this (Hermes
   already installed the plugin); the standalone flow installs Chronalyn into
   Hermes' own Python runtime and writes the provider entries.
2. **Detect the Hermes installation** — command path, runtime interpreter, and
   `MemoryProvider` contract availability.
3. **Detect existing configuration** — the active `memory.provider`, any direct
   Hindsight configuration (endpoint, bank, mode), and whether Mnemosyne is
   installed.
4. **Configure optional Mnemosyne** — offered explicitly in dual mode only.
   Installing `mnemosyne-memory` does not enable it; enabling requires an
   explicit choice.
5. **Preview every change** — current versus proposed provider, banks, routing
   policy, and an explicit statement that existing memories are preserved and no
   migration occurs. Remote endpoints require separate consent.
6. **Back up configuration** — `config.yaml`, router config, Hindsight config,
   `.env`, and provider entries for both provider ids.
7. **Activate** — the native flow sets `memory.provider` through the Hermes CLI
   without touching the Hermes-managed plugin directory; the standalone flow
   writes provider entries and then sets `memory.provider`.
8. **Validate** — re-read discovery and confirm Chronalyn is the sole active
   external provider; verify backend health before declaring success.
9. **Roll back automatically** on any failure during activation.

## Verifying discovery yourself

With Hermes installed, this reports what Hermes actually sees:

```bash
hermes memory status
hermes doctor
chronalyn status
chronalyn validate
```

To inspect discovery directly against a disposable profile:

```bash
HERMES_HOME=/tmp/chronalyn-check chronalyn --hermes-home /tmp/chronalyn-check install-plugin
HERMES_HOME=/tmp/chronalyn-check hermes memory status
```

Expected result: Hermes lists `chronalyn` as an available external memory
provider, and `chronalyn` is the only active one.

## Conflicts

Chronalyn must be the **only** active external memory provider. If Hermes is
configured with Chronalyn *and* another provider — including `hindsight` or
`mnemosyne` directly — discovery reports a conflict and Chronalyn refuses to
proceed rather than competing for the same turns. Conflict detection recognises
the legacy provider id too, so a pre-rename installation does not silently lose
this protection.

## Rollback to direct Hindsight

Chronalyn never becomes load-bearing without a documented exit:

```bash
chronalyn rollback --yes
```

This restores the most recent pre-change backup, removing provider entries that
did not exist at backup time and restoring the previous `memory.provider`. To
return to direct Hindsight manually:

```bash
hermes config set memory.provider hindsight
```

No memory data is deleted by rollback. See [Rollback](rollback.md).
