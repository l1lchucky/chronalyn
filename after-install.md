# Chronalyn installed

Chronalyn is a memory orchestration provider for Hermes:

- **Hindsight** — automatic memory, recall, and reflect
- **Mnemosyne** (optional) — verified checkpoints and bounded fallback

## Configure it inside Hermes

Run:

    hermes memory setup

Then choose:

    Chronalyn

Available modes:

- **Dual memory** — Hindsight plus Mnemosyne verified checkpoints
- **Hindsight only** — Hindsight handles every memory operation

The wizard also configures a provider-neutral embedding backend (when dual
memory is selected) and routing. When it finishes, Chronalyn is activated as
Hermes' memory provider.

## Verify

    hermes memory status

## Notes

- Hindsight and Mnemosyne remain internal Chronalyn backends; Hermes only sees
  Chronalyn as its one external memory provider.
- Removing this plugin never deletes your memory data (router state, Hindsight
  memories, Mnemosyne checkpoints, or backups).
