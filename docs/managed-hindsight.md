# Managed lightweight Hindsight

Chronalyn 1.1 can install, configure, start, and manage a local Hindsight API
for you. This is the **Lightweight local Hindsight** option in the guided
setup, and it removes the need to install or operate Hindsight yourself.

```bash
hermes plugins install l1lchucky/chronalyn
hermes memory setup
```

Then choose:

```text
Chronalyn
→ Dual Memory
→ Lightweight local Hindsight (managed)
```

The wizard asks for four things only:

1. OpenAI-compatible base URL
2. API key
3. LLM model
4. embedding model

## What Chronalyn does

1. Creates an isolated venv under `$HERMES_HOME/hindsight-managed/venv`.
2. Installs `hindsight-api-slim` with the embedded PostgreSQL + pgvector
   backend (`pg0`). Heavyweight local ML dependencies are **not** installed.
3. Detects the embedding dimensions by probing the remote endpoint.
4. Writes a generated env file (owner-readable only) configuring:

   - the remote OpenAI-compatible LLM;
   - the remote OpenAI-compatible embeddings (batch size 64);
   - embedded PostgreSQL + pgvector persistence;
   - one API worker, access log off;
   - neural reranking disabled and RRF/text-search passthrough enabled;
   - loopback binding only (`127.0.0.1:8888`).

5. Starts Hindsight and waits until it is healthy.
6. Registers the service lifecycle: a **systemd `--user` service** when
   available (auto-start, restart on failure), otherwise a launcher-script
   fallback. No root or sudo is required.
7. Installs and configures Mnemosyne for dual mode, using the **same remote
   embedding provider/model**, with its LLM disabled.
8. Validates both backends and runs a functional routing check before
   activating `memory.provider = chronalyn`. If validation fails, the
   configuration is rolled back and Chronalyn is not left partially activated.

## Service lifecycle

The lifecycle behavior applies only to the **managed** Hindsight instance that
Chronalyn owns.

- With `systemd --user` available, the `chronalyn-hindsight` service starts
  automatically at login and restarts on unexpected failure.
- Without `systemd --user`, the managed service still runs for the current
  session; automatic start after reboot is unavailable, and this is reported
  clearly.
- For **existing / hosted Hindsight**, Chronalyn only connects. It never
  starts, stops, restarts, or creates services for an external Hindsight.

## Checking the service

```bash
chronalyn status
chronalyn doctor
```

Both report whether the managed Hindsight service is running, stopped,
unhealthy, or unreachable.

## Security

- Hindsight binds to `127.0.0.1` only; nothing is exposed to the network.
- No local LLM and no local embedding model are installed by default.
- No sudo is required.
- Secrets live only in the owner-readable env file
  (`$HERMES_HOME/hindsight-managed/.env`); they are never written to
  `config.json` or logs.
- No telemetry and no raw tool-message retention.
