"""Custom exception hierarchy for NetworkingAgent."""


class NetworkingAgentError(Exception):
    """Base exception for all networking agent errors."""


class SecurityViolationError(NetworkingAgentError):
    """Raised when an operation violates security policies."""


class CommandInjectionError(SecurityViolationError):
    """Raised when an intent or command attempts CLI / command injection."""


class BlastRadiusViolationError(SecurityViolationError):
    """Raised when an operation targets a protected or non-whitelisted resource."""


class DeviceConnectionError(NetworkingAgentError):
    """Raised when communication with a network device fails."""


class VerificationFailedError(NetworkingAgentError):
    """Raised when a post-change health verification fails."""


class RollbackFailedError(NetworkingAgentError):
    """Raised when an automated configuration rollback fails."""


class AIAnalysisError(NetworkingAgentError):
    """Raised when an AI provider fails to return a valid structured intent."""
