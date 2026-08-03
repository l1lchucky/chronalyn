from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

try:
    from agent.memory_provider import MemoryProvider
except ImportError:  # Allows package tests outside Hermes.
    class MemoryProvider:  # type: ignore[no-redef]
        pass

from .config import RouterConfig, load_config
from .factory import build_router
from .router import MemoryRouter
from .tools import TOOL_SCHEMAS, VERIFICATION_LEVELS

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
        try:
            import mnemosyne  # noqa: F401
        except Exception:
            return False
        home = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
        return (home / "memory-router" / "config.json").exists()

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
        self._router = build_router(
            config=self._config,
            hermes_home=self._hermes_home,
            session_id=session_id,
        )

    def system_prompt_block(self) -> str:
        if not self._config:
            return ""
        return (
            "<memory_router>\n"
            f"Namespace: {self._config.namespace}\n"
            f"Environment: {self._config.environment}\n"
            "Hindsight is the primary automatic backend. Mnemosyne stores "
            "verified checkpoints and is used only as configured fallback.\n"
            "Repository and runtime evidence override recalled memory.\n"
            "Never store secrets, signed URLs, raw environment files, or "
            "private customer data in memory.\n"
            "</memory_router>"
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        if not self._router:
            return ""
        result = self._router.recall(query=query, limit=5)
        if not result.hits:
            return ""
        lines = [
            "<memory_router_context>",
            f"Backend: {result.backend}",
            f"Fallback used: {str(result.fallback_used).lower()}",
        ]
        if result.primary_error:
            lines.append("Primary backend was unavailable; treat fallback as checkpoint-only context.")
        for index, hit in enumerate(result.hits, start=1):
            lines.append(f"{index}. {hit.content}")
        lines.append("</memory_router_context>")
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
                # Raw tool messages are deliberately excluded by default.
                "tool_messages_included": False,
            },
        )

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return list(TOOL_SCHEMAS)

    def handle_tool_call(
        self, tool_name: str, args: dict[str, Any], **kwargs
    ) -> str:
        if not self._router:
            return _json({"ok": False, "error": "Memory router is not initialized"})
        try:
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
                return _json({
                    "ok": True,
                    "result": self._router.reflect(query=str(args.get("query", ""))),
                })
            if tool_name == "memory_router_forget":
                return _json({
                    "ok": True,
                    **self._router.forget(str(args.get("record_id", ""))),
                })
            if tool_name == "memory_router_retry":
                record_id = str(args.get("record_id") or "") or None
                return _json({"ok": True, "retried": self._router.retry(record_id)})
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
            "Preserve verified memory-router checkpoint IDs, exact environment, "
            "Git/deployment state, failed delivery state, and unresolved risks."
        )

    def on_session_end(self, messages: list[dict[str, Any]]) -> None:
        # Normal turn writes are already queued. No full transcript duplication.
        return None

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        # Built-in MEMORY.md writes are intentionally not mirrored automatically.
        return None

    def on_delegation(
        self,
        task: str,
        result: str,
        *,
        child_session_id: str = "",
        **kwargs,
    ) -> None:
        # Subagent outputs are not automatically retained to avoid memory poisoning.
        return None

    def shutdown(self) -> None:
        if self._router:
            self._router.close()
            self._router = None

    def backup_paths(self) -> list[str]:
        home = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
        # Hermes already backs up HERMES_HOME. Declare only explicit external
        # Mnemosyne storage so it is not silently omitted.
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
