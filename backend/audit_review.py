"""Bounded, read-only review of audit metadata for clinic administrators."""

from csv import writer
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
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


class AuditActivitySummary(BaseModel):
    """Counts of audit metadata in one bounded, recent UTC window."""

    hours: int
    since: datetime
    total_events: int
    failed_logins: int
    access_denials: int
    server_errors: int


def summarize_audit_activity(
    session: Session, *, hours: int, now: datetime | None = None,
) -> AuditActivitySummary:
    """Aggregate recent events in SQL; do not expose accounts or clinical identifiers."""
    if not 1 <= hours <= 168:
        raise ValueError("Audit review window must be between 1 and 168 hours")
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=hours)
    counts = dict(session.execute(
        select(AuditEvent.event_type, func.count(AuditEvent.id))
        .where(AuditEvent.occurred_at >= cutoff)
        .group_by(AuditEvent.event_type)
    ).all())
    server_errors = session.scalar(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.occurred_at >= cutoff,
            AuditEvent.status_code >= 500,
        )
    ) or 0
    return AuditActivitySummary(
        hours=hours,
        since=cutoff,
        total_events=sum(counts.values()),
        failed_logins=counts.get("login_failure", 0),
        access_denials=counts.get("access_denied", 0),
        server_errors=server_errors,
    )


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



def export_audit_csv(events: list[AuditEvent]) -> str:
    """Export only the same allowlisted metadata available in admin review."""
    buffer = StringIO(newline="")
    output = writer(buffer)
    columns = tuple(AuditEventRead.model_fields)
    output.writerow(columns)
    for event in events:
        safe = AuditEventRead.model_validate(event).model_dump(mode="json")
        output.writerow(safe[column] for column in columns)
    return buffer.getvalue()
