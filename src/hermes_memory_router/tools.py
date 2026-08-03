from __future__ import annotations

from .config import RouterConfig

VERIFICATION_LEVELS = [
    "investigated",
    "planned",
    "edited",
    "tested",
    "committed",
    "pushed",
    "deployed",
    "migrated",
    "service-restarted",
    "environment-verified",
]


def _retain_schema() -> dict:
    return {
        "name": "memory_router_retain",
        "description": (
            "Store an explicit durable memory in Hindsight through the router's "
            "redaction, idempotency, and retry controls."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "context": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["content"],
        },
    }


def _checkpoint_schema() -> dict:
    return {
        "name": "memory_router_checkpoint",
        "description": (
            "Store one evidence-backed milestone using the fixed policy. Normal turns "
            "are never duplicated to the checkpoint backend."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "verification_level": {
                    "type": "string",
                    "enum": VERIFICATION_LEVELS,
                },
                "evidence": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["content", "verification_level", "evidence"],
        },
    }


def _recall_schema() -> dict:
    return {
        "name": "memory_router_recall",
        "description": (
            "Recall through the configured fixed policy. Results are never merged from "
            "multiple automatic memory providers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["query"],
        },
    }


def _reflect_schema() -> dict:
    return {
        "name": "memory_router_reflect",
        "description": "Ask Hindsight to synthesize an answer from primary memory.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    }


def _status_schema() -> dict:
    return {
        "name": "memory_router_status",
        "description": "Show policy, isolation binding, outbox, worker, and backend health.",
        "parameters": {"type": "object", "properties": {}},
    }


def _forget_plan_schema() -> dict:
    return {
        "name": "memory_router_forget_plan",
        "description": (
            "Create a short-lived one-time confirmation token for deleting one "
            "router-managed record. This step does not delete data."
        ),
        "parameters": {
            "type": "object",
            "properties": {"record_id": {"type": "string"}},
            "required": ["record_id"],
        },
    }


def _forget_apply_schema() -> dict:
    return {
        "name": "memory_router_forget_apply",
        "description": (
            "Apply a previously planned deletion using its one-time confirmation token."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "record_id": {"type": "string"},
                "confirmation_token": {"type": "string"},
            },
            "required": ["record_id", "confirmation_token"],
        },
    }


def tool_schemas_for(config: RouterConfig) -> list[dict]:
    schemas = [_recall_schema(), _reflect_schema(), _status_schema()]
    if config.tools.profile == "standard":
        schemas.insert(0, _checkpoint_schema())
        schemas.insert(0, _retain_schema())
    if config.tools.destructive_model_tools:
        schemas.extend([_forget_plan_schema(), _forget_apply_schema()])
    return schemas


# Kept for tests and callers that inspect the default surface without configuration.
TOOL_SCHEMAS = tool_schemas_for(RouterConfig())
