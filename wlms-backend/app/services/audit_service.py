import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def audit_log(
    db: Session,
    *,
    tenant_id: int,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=before,
            after_json=after,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
    db.flush()


