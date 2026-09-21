class NotFoundError(Exception):
    def __init__(self, entity: str, entity_id: int) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} {entity_id} not found")


class ConflictError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidStatusTransitionError(ConflictError):
    pass


class ValidationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class AuthenticationError(Exception):
    """Bad credentials, or a missing/expired/invalid session -- always
    surfaced as 401, and deliberately vague to callers (never reveals
    whether an email exists)."""

    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message)


class AuthorizationError(Exception):
    """A real, authenticated user whose role doesn't permit the action --
    403, distinct from AuthenticationError's 401 (who you are vs what
    you're allowed to do)."""

    def __init__(self, message: str = "Not permitted") -> None:
        super().__init__(message)


class RateLimitedError(Exception):
    """Too many attempts in a short window -- 429, distinct from bad
    credentials so a client backs off instead of retrying immediately."""

    def __init__(self, message: str = "Too many attempts. Try again later.") -> None:
        super().__init__(message)


class ServiceUnavailableError(Exception):
    """A feature that depends on something not configured or not reachable --
    AI assistance with no provider set, say. Distinct from ValidationError
    because the caller did nothing wrong; the deployment isn't set up."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
