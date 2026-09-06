"""Default governance roles that ship with the product.

Single source of truth consumed by the alembic migration that seeds
governance_roles (real deployments) and by tests/conftest.py, which builds
its schema with Base.metadata.create_all and so needs the same rows
inserted directly.

Chief AI Governance Officer is the root of the org chart; the rest report
to it by default (an admin can reparent any of them afterwards).
"""

DEFAULT_ROLES: list[tuple[str, str, int | None]] = [
    (
        "Chief AI Governance Officer",
        "Managing and approving.",
        1,
    ),
    (
        "Data Owner",
        "Manage datasets.",
        None,
    ),
    (
        "AI System Owner",
        "Responsible for managing the assigned AI system across lifecycle stages.",
        None,
    ),
    (
        "Risk Owner",
        "Responsible for specific risk treatment and monitoring.",
        None,
    ),
    (
        "Implementation Team",
        "Responsible for creating documentation, impact and risk assessments, "
        "and implementing controls. Includes engineers, data scientists, and DevOps.",
        None,
    ),
]
