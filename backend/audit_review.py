"""Bounded, read-only review of audit metadata for clinic administrators."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AuditEvent


AuditEventType = Literal[
    "login_success", "login_failure", "logout", "clinical_read",
    "clinical_write", "access_denied",
]


class AuditEventRead(BaseModel):
    """Only the deliberately minimal columns stored in the audit table."""

    id: int
    occurred_at: datetime
    event_type: AuditEventType
    route_template: str
    http_method: str
    status_code: int
    actor_user_id: int | None
    subject_patient_id: int | None
    resource_id: int | None

    model_config = ConfigDict(from_attributes=True)


def list_audit_events(
    session: Session,
    *,
    limit: int = 50,
    before_id: int | None = None,
    event_type: AuditEventType | None = None,
) -> list[AuditEvent]:
    """Return a stable newest-first page without loading unbounded audit history."""
    query = select(AuditEvent)
    if before_id is not None:
        query = query.where(AuditEvent.id < before_id)
    if event_type is not None:
        query = query.where(AuditEvent.event_type == event_type)
    return list(session.scalars(query.order_by(AuditEvent.id.desc()).limit(limit)).all())
