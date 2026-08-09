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
