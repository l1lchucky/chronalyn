from __future__ import annotations

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

TOOL_SCHEMAS = [
    {
        "name": "memory_router_checkpoint",
        "description": (
            "Store one evidence-backed milestone in Hindsight and Mnemosyne. "
            "Use only after verifying the stated engineering status."
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
    },
    {
        "name": "memory_router_recall",
        "description": (
            "Recall through the configured policy: Hindsight first, then "
            "Mnemosyne checkpoints only when configured fallback conditions apply."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_router_reflect",
        "description": "Ask Hindsight to synthesize an answer from primary memory.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "memory_router_forget",
        "description": (
            "Schedule deletion of a router-managed record from every backend "
            "that successfully retained it."
        ),
        "parameters": {
            "type": "object",
            "properties": {"record_id": {"type": "string"}},
            "required": ["record_id"],
        },
    },
    {
        "name": "memory_router_retry",
        "description": "Retry failed backend deliveries.",
        "parameters": {
            "type": "object",
            "properties": {"record_id": {"type": "string"}},
        },
    },
    {
        "name": "memory_router_status",
        "description": "Show routing, outbox, isolation, worker, and backend health.",
        "parameters": {"type": "object", "properties": {}},
    },
]
