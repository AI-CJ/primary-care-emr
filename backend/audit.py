"""Write minimal persistent audit metadata without credentials or clinical text."""

from sqlalchemy.orm import Session

from backend.models import AuditEvent


_EVENT_TYPES = frozenset({
    "login_success", "login_failure", "logout", "clinical_read",
    "clinical_write", "access_denied",
})


def record_audit_event(
    session: Session,
    *,
    event_type: str,
    route_template: str,
    http_method: str,
    status_code: int,
    actor_user_id: int | None = None,
    subject_patient_id: int | None = None,
    resource_id: int | None = None,
) -> None:
    """Stage one event; the caller commits it with the associated operation."""
    if event_type not in _EVENT_TYPES:
        raise ValueError("Unsupported audit event")
    if not route_template.startswith("/") or len(route_template) > 160:
        raise ValueError("Invalid audit route template")
    if http_method not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}:
        raise ValueError("Unsupported audit method")
    if not 100 <= status_code <= 599:
        raise ValueError("Invalid audit status")
    session.add(AuditEvent(
        event_type=event_type,
        route_template=route_template,
        http_method=http_method,
        status_code=status_code,
        actor_user_id=actor_user_id,
        subject_patient_id=subject_patient_id,
        resource_id=resource_id,
    ))
