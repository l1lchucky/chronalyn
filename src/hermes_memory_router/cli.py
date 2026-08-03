from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .config import load_config, write_default_config
from .factory import build_router


def _home(value: str | None) -> Path:
    return Path(
        value or os.environ.get("HERMES_HOME") or (Path.home() / ".hermes")
    ).expanduser()


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="hermes-memory-router")
    root.add_argument("--hermes-home")
    sub = root.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a safe default config")
    init.add_argument("--namespace", required=True)
    init.add_argument("--environment", required=True)
    init.add_argument("--force", action="store_true")

    sub.add_parser("validate", help="Validate configuration")
    sub.add_parser("status", help="Show router and backend status")
    sub.add_parser("install-plugin", help="Install the Hermes plugin entry")
    sub.add_parser("uninstall-plugin", help="Remove only the Hermes plugin entry")

    retry = sub.add_parser("retry", help="Retry failed deliveries")
    retry.add_argument("--record-id")

    drain = sub.add_parser("drain", help="Drain the durable outbox")
    drain.add_argument("--limit", type=int, default=100)

    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    home = _home(args.hermes_home)
    config_path = home / "memory-router" / "config.json"

    if args.command == "init":
        if config_path.exists() and not args.force:
            raise SystemExit(f"Config already exists: {config_path}; use --force")
        write_default_config(
            config_path,
            namespace=args.namespace,
            environment=args.environment,
        )
        print(config_path)
        return 0

    if args.command == "install-plugin":
        from importlib.resources import files

        plugin_dir = home / "plugins" / "memory" / "hermes_memory_router"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        resource_root = files("hermes_memory_router.resources")
        (plugin_dir / "__init__.py").write_text(
            resource_root.joinpath("plugin_entry.py.txt").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (plugin_dir / "plugin.yaml").write_text(
            resource_root.joinpath("plugin.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        print(plugin_dir)
        return 0

    if args.command == "uninstall-plugin":
        import shutil

        plugin_dir = home / "plugins" / "memory" / "hermes_memory_router"
        shutil.rmtree(plugin_dir, ignore_errors=True)
        print(plugin_dir)
        return 0

    config = load_config(config_path)
    if args.command == "validate":
        print(json.dumps(config.to_safe_dict(), indent=2))
        return 0

    # CLI status/retry requires real backends.
    router = build_router(config=config, hermes_home=home, session_id="router-cli")
    try:
        if args.command == "status":
            print(json.dumps(router.status(), indent=2, default=str))
        elif args.command == "retry":
            print(json.dumps({"retried": router.retry(args.record_id)}))
        elif args.command == "drain":
            print(json.dumps({"processed": router.drain_outbox(args.limit)}))
        return 0
    finally:
        router.close()


if __name__ == "__main__":
    raise SystemExit(main())
