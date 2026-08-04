class MemoryRouterError(RuntimeError):
    """Base router error."""


class ConfigurationError(MemoryRouterError):
    """Invalid or unsafe configuration."""


class BackendUnavailable(MemoryRouterError):
    """Backend is unavailable or failed a health check."""


class BackendOperationError(MemoryRouterError):
    """Backend request failed."""


class SecretDetected(MemoryRouterError):
    """Configured policy rejected content containing a likely secret."""
