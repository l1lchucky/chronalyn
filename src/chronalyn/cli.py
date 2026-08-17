from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import identity
from .compatibility import discover, profile_fingerprint, require_strict_hermes_compatibility
from .config import load_config, write_config, write_default_config
from .exceptions import ConfigurationError
from .factory import build_router
from .operations import (
    add_mnemosyne,
    apply_plan,
    build_plan,
    config_for_adoption,
    confirm,
    recommended_policy,
    remove_mnemosyne,
    require_cloud_approval,
    rollback_latest,
)
from .plugin_entry import entry_dir, install_plugin_entries, uninstall_plugin_entries
from .policy import HINDSIGHT_MNEMOSYNE, HINDSIGHT_ONLY
from .store import RouterStore
from .ui import PacmanLoader


def _home(value: str | None) -> Path:
    return Path(value or os.environ.get("HERMES_HOME") or (Path.home() / ".hermes")).expanduser()


def _install_plugin(home: Path) -> Path:
    """Install provider entries at Hermes' real discovery root.

    Returns the canonical entry directory. Both the canonical and legacy
    provider ids are installed so an existing configuration keeps loading.
    """
    install_plugin_entries(home)
    return entry_dir(home, identity.PROVIDER_ID)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog=identity.CLI_COMMAND,
        description=f"{identity.BRAND} — {identity.TAGLINE}",
    )
    root.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"{identity.BRAND} {identity.RELEASE_NAME} (python {identity.VERSION})",
    )
    root.add_argument("--hermes-home")
    root.add_argument("--json", action="store_true", help="Machine-readable output")
    root.add_argument("--no-animation", action="store_true", help="Disable Pac-Man animation")
    sub = root.add_subparsers(dest="command", required=True)

    # `setup` is the RC command name; `setup-dual` remains a deprecated alias.
    for setup_name, setup_help in (
        ("setup", "Guided setup: detect, preview, back up, activate, and validate"),
        ("setup-dual", "Deprecated alias for `setup`"),
    ):
        setup_parser = sub.add_parser(setup_name, help=setup_help)
        setup_parser.add_argument(
            "--package-source",
            default=os.environ.get("CHRONALYN_PACKAGE_SOURCE")
            or os.environ.get("HMR_PACKAGE_SOURCE", ""),
            help="Wheel, source directory, or package URL installed into Hermes' runtime",
        )
        setup_parser.add_argument(
            "--no-mouse",
            action="store_true",
            help="Disable terminal mouse handling; keyboard navigation remains available",
        )
        setup_parser.add_argument(
            "--with-browser",
            action="store_true",
            help="Include Playwright/Chromium when the setup must install Hermes",
        )

    init = sub.add_parser("init", help="Create a strict Hindsight-first config")
    init.add_argument("--namespace", required=True)
    init.add_argument("--environment", required=True)
    init.add_argument(
        "--policy",
        choices=[HINDSIGHT_ONLY, HINDSIGHT_MNEMOSYNE],
        default=HINDSIGHT_ONLY,
    )
    init.add_argument("--force", action="store_true")

    sub.add_parser("detect", help="Read-only provider and compatibility discovery")
    sub.add_parser("validate", help="Validate configuration without network calls")
    sub.add_parser("status", help="Show router and backend status")
    sub.add_parser("doctor", help="Check configuration, database, queue, and backend health")
    db = sub.add_parser("db", help="Safely inspect and maintain the router database")
    db_sub = db.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("info", help="Show database identity, queue counts, and file sizes")
    db_sub.add_parser("check", help="Run SQLite integrity_check without opening backends")
    backup = db_sub.add_parser("backup", help="Create an online SQLite backup and manifest")
    backup.add_argument("--output", required=True)
    verify_backup = db_sub.add_parser(
        "verify-backup", help="Verify backup manifest SHA-256 and integrity"
    )
    verify_backup.add_argument("--path", required=True)
    vacuum = db_sub.add_parser("vacuum", help="Run VACUUM after explicit confirmation")
    vacuum.add_argument("--yes", action="store_true")
    sub.add_parser("install-plugin", help="Install the Hermes memory-provider entry")
    sub.add_parser("uninstall-plugin", help="Remove only the Hermes plugin entry")

    adopt = sub.add_parser("adopt", help="Adopt an existing Hindsight setup safely")
    adopt.add_argument("--namespace", required=True)
    adopt.add_argument("--environment", required=True)
    adopt.add_argument(
        "--policy",
        choices=["auto", HINDSIGHT_ONLY, HINDSIGHT_MNEMOSYNE],
        default="auto",
    )
    adopt.add_argument("--dry-run", action="store_true")
    adopt.add_argument("--yes", action="store_true")
    adopt.add_argument("--allow-cloud", action="store_true")

    provider = sub.add_parser("provider", help="Add or remove a managed child backend")
    provider_sub = provider.add_subparsers(dest="provider_command", required=True)
    add = provider_sub.add_parser("add")
    add.add_argument("name", choices=["mnemosyne"])
    add.add_argument("--dry-run", action="store_true")
    add.add_argument("--yes", action="store_true")
    remove = provider_sub.add_parser("remove")
    remove.add_argument("name", choices=["mnemosyne"])
    remove.add_argument("--dry-run", action="store_true")
    remove.add_argument("--yes", action="store_true")

    rollback = sub.add_parser("rollback", help="Restore the latest pre-change configuration")
    rollback.add_argument("--yes", action="store_true")

    upgrade = sub.add_parser("upgrade-config", help="Persist an older config in schema v2")
    upgrade.add_argument("--yes", action="store_true")

    retry = sub.add_parser("retry", help="Retry failed deliveries")
    retry.add_argument("--record-id")

    drain = sub.add_parser("drain", help="Drain the durable outbox")
    drain.add_argument("--limit", type=int, default=100)

    forget = sub.add_parser("forget", help="Administrative deletion of a router record")
    forget.add_argument("--record-id", required=True)
    forget.add_argument("--yes", action="store_true")

    return root


def _loader(args: argparse.Namespace, label: str) -> PacmanLoader:
    return PacmanLoader(label, enabled=False if args.no_animation or args.json else None)


def _print(args: argparse.Namespace, payload: Any, *, human: str | None = None) -> None:
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    elif human is not None:
        print(human)
    elif isinstance(payload, str):
        print(payload)
    else:
        print(json.dumps(payload, indent=2, default=str))


def _status_human(payload: dict[str, Any]) -> str:
    versions = payload["versions"]
    deliveries = payload["deliveries"]
    database = payload["database"]
    lines = [
        f"Health: {payload['state']}",
        f"Router: {versions['router']} "
        f"(config schema {versions['configuration_schema']}, "
        f"database schema {versions['database_schema']})",
        f"Runtime: Python {versions['python']}, SQLite {versions['sqlite']}",
        f"Policy: {payload['policy']}",
        f"Binding: namespace={payload['namespace']} environment={payload['environment']} "
        f"profile={payload['binding']['database']['profile'] or 'unbound'}",
        "Deliveries: "
        + ", ".join(
            f"{state}={deliveries.get(state, 0)}" for state in ("pending", "failed", "dead")
        ),
        f"Database: {database['size_bytes']} B "
        f"(WAL {database['wal_size_bytes']} B, SHM {database['shm_size_bytes']} B)",
    ]
    oldest = payload.get("oldest_incomplete_delivery")
    if oldest:
        lines.append(
            f"Oldest incomplete delivery: {oldest['state']} {oldest['backend']} "
            f"{oldest['operation']} ({oldest['age_seconds']:.0f}s old)"
        )
    managed = payload.get("managed_hindsight")
    if isinstance(managed, dict) and managed.get("configured"):
        if managed.get("healthy"):
            status = "healthy"
        elif managed.get("running"):
            status = "running"
        else:
            status = "stopped"
        lines.append(f"Managed Hindsight: {status} ({managed.get('api_url', '')})")
    for category in ("warnings", "degraded", "unsafe"):
        lines.extend(f"{category[:-1].upper()}: {message}" for message in payload.get(category, []))
    return "\n".join(lines)


def _require_apply_confirmation(args: argparse.Namespace, prompt: str) -> None:
    if not confirm(prompt, assume_yes=args.yes):
        raise ConfigurationError("Operation cancelled; no configuration was changed")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    home = _home(args.hermes_home)
    config_path = home / identity.STATE_DIRNAME / identity.CONFIG_FILENAME

    try:
        if args.command in {"setup", "setup-dual"}:
            if args.json:
                raise ConfigurationError(
                    f"{args.command} is an interactive terminal UI and cannot use --json"
                )
            if args.command == "setup-dual":
                print(
                    f"WARNING: `{identity.CLI_COMMAND} setup-dual` is deprecated; "
                    f"use `{identity.CLI_COMMAND} setup`.",
                    file=sys.stderr,
                )
            from .setup_tui import run_dual_setup

            return run_dual_setup(
                hermes_home=home,
                package_source=args.package_source,
                mouse=not args.no_mouse,
                with_browser=args.with_browser,
            )

        if args.command == "init":
            if config_path.exists() and not args.force:
                raise ConfigurationError(f"Config already exists: {config_path}; use --force")
            with _loader(args, "Creating strict configuration"):
                write_default_config(
                    config_path,
                    namespace=args.namespace,
                    environment=args.environment,
                    policy=args.policy,
                )
            _print(
                args, {"config": str(config_path), "policy": args.policy}, human=str(config_path)
            )
            return 0

        if args.command == "install-plugin":
            with _loader(args, "Installing Hermes provider entry"):
                installed = install_plugin_entries(home)
            plugin_dir = entry_dir(home, identity.PROVIDER_ID)
            _print(
                args,
                {"plugin_dir": str(plugin_dir), "provider_ids": list(installed)},
                human=str(plugin_dir),
            )
            return 0

        if args.command == "uninstall-plugin":
            with _loader(args, "Removing Hermes provider entry"):
                removed = uninstall_plugin_entries(home)
            _print(
                args,
                {
                    "removed": list(removed),
                    "data_retained": True,
                    "note": (
                        "Provider entries removed. Router configuration, database, "
                        "backups, Hindsight and Mnemosyne data were NOT deleted."
                    ),
                },
                human=(
                    f"Removed provider entries: {', '.join(removed) or '(none)'}. "
                    "No backend or router data was deleted."
                ),
            )
            return 0

        if args.command == "detect":
            with _loader(args, "Inspecting Hermes memory configuration"):
                state = discover(home)
            _print(args, state.to_dict())
            return 0

        if args.command == "adopt":
            with _loader(args, "Inspecting existing Hindsight configuration"):
                state = discover(home)
            if state.conflicts:
                raise ConfigurationError(" ".join(state.conflicts))
            allowed_current = {"", "hindsight", "chronalyn"}
            current = state.active_provider if len(state.active_providers) <= 1 else ""
            if current not in allowed_current:
                raise ConfigurationError(
                    "Adoption supports an empty, Hindsight, or existing router configuration only"
                )
            policy = recommended_policy(state) if args.policy == "auto" else args.policy
            if policy == HINDSIGHT_MNEMOSYNE and not state.mnemosyne_installed:
                raise ConfigurationError("The dual policy requires mnemosyne-memory>=3.15,<4")
            config = config_for_adoption(
                home,
                state,
                namespace=args.namespace,
                environment=args.environment,
                policy=policy,
            )
            plan = build_plan(state, policy=policy, existing_config=config)
            _print(args, plan.to_dict(), human=plan.render())
            if args.dry_run:
                return 0
            require_cloud_approval(
                plan,
                allow_cloud=args.allow_cloud,
                assume_yes=args.yes,
            )
            _require_apply_confirmation(args, "Apply this configuration? [y/N] ")
            with _loader(args, "Backing up and activating the router"):
                _install_plugin(home)
                backup = apply_plan(
                    home,
                    config=config,
                    reason=f"adopt {policy}",
                    activate_provider=True,
                )
            _print(
                args,
                {"applied": True, "policy": policy, "backup": str(backup)},
                human=f"Applied {policy}. Backup: {backup}",
            )
            return 0

        if args.command == "provider":
            existing = load_config(config_path)
            state = discover(home)
            if state.conflicts:
                raise ConfigurationError(" ".join(state.conflicts))
            if args.provider_command == "add":
                with _loader(args, "Checking Mnemosyne compatibility"):
                    proposed = add_mnemosyne(home, existing=existing)
                plan = build_plan(state, policy=proposed.policy, existing_config=proposed)
                _print(args, plan.to_dict(), human=plan.render())
                if args.dry_run:
                    return 0
                _require_apply_confirmation(args, "Apply this configuration? [y/N] ")
                with _loader(args, "Enabling verified Mnemosyne checkpoints"):
                    backup = apply_plan(
                        home,
                        config=proposed,
                        reason="add mnemosyne checkpoint backend",
                        activate_provider=False,
                    )
                _print(
                    args,
                    {"applied": True, "policy": proposed.policy, "backup": str(backup)},
                )
                return 0
            if args.provider_command == "remove":
                proposed = remove_mnemosyne(existing)
                plan = build_plan(state, policy=proposed.policy, existing_config=proposed)
                _print(args, plan.to_dict(), human=plan.render())
                if args.dry_run:
                    return 0
                _require_apply_confirmation(args, "Apply this configuration? [y/N] ")
                with _loader(args, "Disabling Mnemosyne routing"):
                    backup = apply_plan(
                        home,
                        config=proposed,
                        reason="remove mnemosyne checkpoint backend",
                        activate_provider=False,
                    )
                _print(
                    args,
                    {"applied": True, "policy": proposed.policy, "backup": str(backup)},
                )
                return 0

        if args.command == "rollback":
            _require_apply_confirmation(
                args, "Restore the latest router configuration backup? [y/N] "
            )
            with _loader(args, "Restoring configuration backup"):
                backup, restored = rollback_latest(home)
            _print(
                args,
                {"backup": str(backup), "restored": restored},
                human=f"Restored {backup}: {', '.join(restored)}",
            )
            return 0

        if args.command == "upgrade-config":
            config = load_config(config_path)
            _require_apply_confirmation(args, "Back up and persist config schema v2? [y/N] ")
            with _loader(args, "Upgrading configuration schema"):
                from .compatibility import backup_configuration

                backup = backup_configuration(home, reason="upgrade config schema")
                write_config(config_path, config)
            _print(args, {"upgraded": True, "backup": str(backup)})
            return 0

        config = load_config(config_path)
        if args.command == "validate":
            state = discover(home)
            payload = {
                "config": config.to_safe_dict(),
                "discovery": state.to_dict(),
                "strict_contract": not state.conflicts,
            }
            _print(args, payload)
            return 0

        if args.command == "db":
            db_path = config.resolved_state_db(home)
            if args.db_command == "check":
                payload = RouterStore.check_database(db_path)
                _print(args, payload)
                return 0 if payload.get("ok") else 3
            if args.db_command == "verify-backup":
                payload = RouterStore.verify_backup_manifest(Path(args.path))
                _print(args, payload)
                return 0 if payload.get("ok") else 3
            if not db_path.exists():
                raise ConfigurationError(f"Router database does not exist: {db_path}")
            store = RouterStore(
                db_path,
                namespace=config.namespace,
                environment=config.environment,
                profile_fingerprint=profile_fingerprint(home),
                strict_binding=True,
            )
            try:
                if args.db_command == "info":
                    payload = store.database_info()
                elif args.db_command == "backup":
                    payload = store.backup_database(Path(args.output))
                elif args.db_command == "vacuum":
                    payload = store.vacuum_database(confirm=args.yes)
                else:
                    raise ConfigurationError(f"Unknown database command: {args.db_command}")
            finally:
                store.close()
            _print(args, payload)
            return 0

        require_strict_hermes_compatibility(home)
        with _loader(args, "Starting memory backends"):
            router = build_router(config=config, hermes_home=home, session_id="router-cli")
        try:
            if args.command in {"status", "doctor"}:
                with _loader(args, "Checking backend health"):
                    integrity = (
                        RouterStore.check_database(config.resolved_state_db(home))
                        if args.command == "doctor"
                        else None
                    )
                    payload = router.status(integrity=integrity)
                    # Report the Chronalyn-managed Hindsight service when the
                    # current configuration uses managed_local mode.
                    try:
                        if config.hindsight.api_url.startswith("http://127.0.0.1"):
                            from .managed import managed_state

                            mstate = managed_state(home)
                            payload["managed_hindsight"] = {
                                "configured": mstate.installed,
                                "installed": mstate.installed,
                                "running": mstate.running,
                                "healthy": mstate.healthy,
                                "api_url": mstate.api_url,
                                "error": mstate.error or None,
                            }
                    except Exception:
                        # Status reporting must never crash on managed-state
                        # inspection problems.
                        payload["managed_hindsight"] = {
                            "configured": False,
                            "installed": False,
                            "running": False,
                            "healthy": False,
                            "api_url": config.hindsight.api_url,
                            "error": "managed state unavailable",
                        }
                _print(args, payload, human=_status_human(payload))
                if args.command == "doctor":
                    exit_code = payload.get("exit_code")
                    return exit_code if isinstance(exit_code, int) else 2
            elif args.command == "retry":
                with _loader(args, "Retrying failed deliveries"):
                    retried = router.retry(args.record_id)
                    processed = router.drain_outbox(args.limit if hasattr(args, "limit") else 100)
                _print(args, {"retried": retried, "processed": processed})
            elif args.command == "drain":
                with _loader(args, "Pac-Man is eating pending deliveries"):
                    processed = router.drain_outbox(args.limit)
                _print(args, {"processed": processed})
            elif args.command == "forget":
                if not args.yes:
                    raise ConfigurationError("Administrative deletion requires --yes")
                with _loader(args, "Deleting mapped backend records"):
                    payload = router.forget_cli(args.record_id)
                    processed = router.drain_outbox(100)
                _print(args, {**payload, "processed": processed})
            return 0
        finally:
            router.close(flush=args.command not in {"status", "doctor"})
    except ConfigurationError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
