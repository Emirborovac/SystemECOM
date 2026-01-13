from collections.abc import Iterable

ROLE_WAREHOUSE_ADMIN = "WAREHOUSE_ADMIN"
ROLE_WAREHOUSE_SUPERVISOR = "WAREHOUSE_SUPERVISOR"
ROLE_WAREHOUSE_WORKER = "WAREHOUSE_WORKER"
ROLE_DRIVER = "DRIVER"
ROLE_CLIENT_USER = "CLIENT_USER"

WAREHOUSE_ROLES: set[str] = {ROLE_WAREHOUSE_ADMIN, ROLE_WAREHOUSE_SUPERVISOR, ROLE_WAREHOUSE_WORKER, ROLE_DRIVER}


def is_warehouse_role(role: str) -> bool:
    return role in WAREHOUSE_ROLES


def require_roles(user_role: str, allowed: Iterable[str]) -> None:
    allowed_set = set(allowed)
    if user_role not in allowed_set:
        raise PermissionError(f"Role '{user_role}' is not allowed")


