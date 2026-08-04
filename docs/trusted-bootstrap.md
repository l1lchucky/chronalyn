# Trusted bootstrap

A one-command installer is convenient, but it should still be understandable.
The bootstrap is deliberately small and leaves the important choices to the full
terminal interface.

## Recommended command

```bash
curl --proto '=https' --tlsv1.2 -fsSLo /tmp/install-hmr-dual.sh \
  https://raw.githubusercontent.com/l1lchucky/chronalyn/v1.0.0-rc.1/scripts/install-dual.sh \
  && bash /tmp/install-hmr-dual.sh
```

The script is downloaded first. You can inspect it before running:

```bash
less /tmp/install-hmr-dual.sh
```

## What it downloads

- the router wheel from the matching GitHub Release;
- the release checksum file;
- the official Hermes installer only when a suitable Hermes/Python runtime is
  not already available.

The Hermes installer source is:

```text
https://hermes-agent.nousresearch.com/install.sh
```

The bootstrap validates basic installer identity markers, shows the SHA-256,
and asks before running it.

## What it verifies

- HTTPS is required;
- the router wheel must match the published SHA-256;
- GitHub build provenance is checked when `gh` is installed;
- downloaded files use owner-only permissions;
- the wheel is imported and its version checked inside Hermes' Python;
- the plugin entry is installed before activation;
- both backends are checked before the router becomes active.

## What it does not do

- no direct `curl | bash` flow in the documented command;
- no hidden `sudo` call;
- no Hermes source patch;
- no telemetry;
- no historical-memory migration;
- no provider activation before review and verification;
- no root execution unless `--allow-root` is supplied.

The upstream Hermes installer is outside this repository. It may request system
package privileges depending on the operating system. Its output is captured in
the setup log.

By default, the bootstrap passes `--skip-browser` to the official installer so
Playwright and Chromium are not installed. Use `--with-browser` when browser
automation is required.

## Logs and temporary files

Setup logs are written under:

```text
$HERMES_HOME/memory-router/logs/
```

They are created owner-readable. The bootstrap removes downloaded files at exit
unless `--keep-downloads` is used.

## Local wheel installation

For offline review or an internal release mirror:

```bash
./scripts/install-dual.sh --wheel /path/to/chronalyn-1.0.0rc1-py3-none-any.whl
```

Verify the wheel through your own release process before using this option.
