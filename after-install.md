# Chronalyn installed

Chronalyn is a dual-memory orchestration provider for Hermes:

- **Hindsight** — automatic memory, recall, and reflect
- **Mnemosyne** (optional) — verified checkpoints and bounded fallback

## Configure it from Hermes

Run:

    hermes memory setup

Then choose:

    Chronalyn

The Chronalyn wizard will guide you through the architecture (Hindsight-only or
dual memory), endpoints, embeddings, and routing. When it finishes, Chronalyn is
activated as Hermes' memory provider.

## Verify

    hermes memory status

## Notes

- Hindsight and Mnemosyne remain internal Chronalyn backends; Hermes only sees
  Chronalyn as its one external memory provider.
- Removing this plugin never deletes your memory data (router state, Hindsight
  memories, Mnemosyne checkpoints, or backups).
