from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

try:
    from agent.memory_provider import MemoryProvider
except ImportError:  # Keeps package tests usable when Hermes is not installed.
    class MemoryProvider:  # type: ignore[no-redef]
        pass

from .compatibility import require_strict_hermes_compatibility
from .config import RouterConfig, load_config
from .factory import build_router
from .router import MemoryRouter
from .tools import VERIFICATION_LEVELS, tool_schemas_for

logger = logging.getLogger(__name__)


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


class HermesMemoryRouterProvider(MemoryProvider):
    def __init__(self) -> None:
        self._router: MemoryRouter | None = None
        self._config: RouterConfig | None = None
        self._hermes_home: Path | None = None
        self._session_id = ""
        self._agent_context = "primary"
        self._platform = "cli"

    @property
    def name(self) -> str:
        return "hermes_memory_router"

    def is_available(self) -> bool:
        """Perform only local package/config checks; never make a network call."""
        home = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
        config_path = home / "memory-router" / "config.json"
        if not config_path.exists():
            return False
        try:
            config = load_config(config_path)
        except Exception:
            return False
        if config.policy.endswith("mnemosyne-checkpoints"):
            try:
                import mnemosyne  # noqa: F401
            except Exception:
                return False
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        self._hermes_home = Path(
            kwargs.get("hermes_home")
            or os.environ.get("HERMES_HOME")
            or (Path.home() / ".hermes")
        ).expanduser()
        self._session_id = session_id
        self._agent_context = str(kwargs.get("agent_context") or "primary")
        self._platform = str(kwargs.get("platform") or "cli")
        config_path = self._hermes_home / "memory-router" / "config.json"
        self._config = load_config(config_path)
        if self._config.compatibility.require_supported_contract:
            require_strict_hermes_compatibility(self._hermes_home)
        self._router = build_router(
            config=self._config,
            hermes_home=self._hermes_home,
            session_id=session_id,
        )

    def system_prompt_block(self) -> str:
        if not self._config:
            return ""
        return (
            "Hermes Memory Router policy\n"
            f"Namespace: {self._config.namespace}\n"
            f"Environment: {self._config.environment}\n"
            f"Policy: {self._config.policy}\n"
            "Hindsight is the only automatic memory authority. Mnemosyne, when "
            "configured, receives verified checkpoints and is only a bounded fallback.\n"
            "Never merge backend recall sets. Current repository and runtime evidence "
            "override recalled memory. Never retain secrets, signed URLs, raw environment "
            "files, or private customer data."
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Return plain provider content; Hermes owns memory-context fencing."""
        if not self._router:
            return ""
        result = self._router.recall(query=query, limit=5)
        if not result.hits:
            return ""
        lines = [
            f"Memory backend: {result.backend}",
            f"Fallback used: {str(result.fallback_used).lower()}",
        ]
        if result.primary_error:
            lines.append(
                "Primary backend was unavailable; the following is checkpoint-only fallback context."
            )
        for index, hit in enumerate(result.hits, start=1):
            lines.append(f"{index}. {hit.content}")
        return "\n".join(lines)

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        return None

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: list[dict[str, Any]] | None = None,
    ) -> None:
        if not self._router:
            return
        self._router.retain_turn(
            user_content=user_content,
            assistant_content=assistant_content,
            session_id=session_id or self._session_id,
            agent_context=self._agent_context,
            metadata={
                "platform": self._platform,
                "tool_messages_included": False,
            },
        )

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        if not self._config:
            return []
        return tool_schemas_for(self._config)

    def handle_tool_call(
        self, tool_name: str, args: dict[str, Any], **kwargs
    ) -> str:
        if not self._router or not self._config:
            return _json({"ok": False, "error": "Memory router is not initialized"})
        allowed = {schema["name"] for schema in tool_schemas_for(self._config)}
        if tool_name not in allowed:
            return _json({"ok": False, "error": f"Tool is disabled by strict profile: {tool_name}"})
        try:
            if tool_name == "memory_router_retain":
                result = self._router.retain_memory(
                    content=str(args.get("content", "")),
                    context=str(args.get("context", "")),
                    metadata=dict(args.get("metadata") or {}),
                )
                return _json({"ok": True, **result.to_dict()})
            if tool_name == "memory_router_checkpoint":
                level = str(args.get("verification_level", ""))
                if level not in VERIFICATION_LEVELS:
                    return _json({"ok": False, "error": "Invalid verification_level"})
                result = self._router.checkpoint_record(
                    content=str(args.get("content", "")),
                    verification_level=level,
                    evidence=str(args.get("evidence", "")),
                    metadata=dict(args.get("metadata") or {}),
                )
                return _json({"ok": True, **result.to_dict()})
            if tool_name == "memory_router_recall":
                result = self._router.recall(
                    query=str(args.get("query", "")),
                    limit=max(1, min(int(args.get("limit", 5)), 20)),
                )
                return _json({"ok": True, **result.to_dict()})
            if tool_name == "memory_router_reflect":
                return _json(
                    {
                        "ok": True,
                        "result": self._router.reflect(query=str(args.get("query", ""))),
                    }
                )
            if tool_name == "memory_router_forget_plan":
                return _json(
                    {
                        "ok": True,
                        **self._router.plan_forget(str(args.get("record_id", ""))),
                    }
                )
            if tool_name == "memory_router_forget_apply":
                return _json(
                    {
                        "ok": True,
                        **self._router.apply_forget(
                            str(args.get("record_id", "")),
                            str(args.get("confirmation_token", "")),
                        ),
                    }
                )
            if tool_name == "memory_router_status":
                return _json({"ok": True, **self._router.status()})
            return _json({"ok": False, "error": f"Unknown tool: {tool_name}"})
        except Exception as exc:
            logger.exception("Memory router tool failed: %s", tool_name)
            return _json({"ok": False, "error": str(exc)})

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        rewound: bool = False,
        **kwargs,
    ) -> None:
        self._session_id = new_session_id

    def on_pre_compress(self, messages: list[dict[str, Any]]) -> str:
        return (
            "Preserve verified checkpoint IDs, exact environment, Git/deployment state, "
            "failed delivery state, and unresolved risks."
        )

    def on_session_end(self, messages: list[dict[str, Any]]) -> None:
        return None

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        return None

    def shutdown(self) -> None:
        if self._router:
            self._router.close()
            self._router = None

    def backup_paths(self) -> list[str]:
        home = self._hermes_home or Path(
            os.environ.get("HERMES_HOME") or (Path.home() / ".hermes")
        )
        try:
            config = load_config(home / "memory-router" / "config.json")
            if config.mnemosyne.data_dir:
                return [str(Path(config.mnemosyne.data_dir).expanduser())]
        except Exception:
            pass
        return []

    def get_config_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "key": "namespace",
                "description": "Project or organization namespace",
                "required": True,
                "default": "my-project",
            },
            {
                "key": "environment",
                "description": "Environment boundary, e.g. staging or production",
                "required": True,
                "default": "development",
            },
        ]

    def save_config(self, values: dict[str, Any], hermes_home: str) -> None:
        from .config import write_default_config

        home = Path(hermes_home).expanduser()
        write_default_config(
            home / "memory-router" / "config.json",
            namespace=str(values.get("namespace") or "my-project"),
            environment=str(values.get("environment") or "development"),
        )


def register(ctx) -> None:
    ctx.register_memory_provider(HermesMemoryRouterProvider())
