"""Short-lived, revocable bearer sessions for synthetic accounts."""

from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Patient, UserAccount, UserSession


SESSION_LIFETIME = timedelta(hours=12)
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z")


def _utc(value: datetime) -> datetime:
    # SQLite test databases do not retain timezone information.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _lookup_session(session: Session, token: str) -> UserSession | None:
    if not isinstance(token, str) or not _TOKEN_PATTERN.fullmatch(token):
        return None
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    return session.scalar(select(UserSession).where(UserSession.token_digest == digest))


def create_session(session: Session, account: UserAccount) -> tuple[str, UserSession]:
    if account.id is None or not account.is_active:
        raise ValueError("An active account is required")
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    record = UserSession(
        user_id=account.id,
        token_digest=hashlib.sha256(token.encode("ascii")).hexdigest(),
        created_at=now,
        expires_at=now + SESSION_LIFETIME,
    )
    session.add(record)
    session.flush()
    return token, record


def get_session_account(session: Session, token: str) -> UserAccount | None:
    record = _lookup_session(session, token)
    if record is None or record.revoked_at is not None:
        return None
    if _utc(record.expires_at) <= datetime.now(timezone.utc):
        return None
    account = session.get(UserAccount, record.user_id)
    if account is None or not account.is_active:
        return None
    if account.account_type == "patient":
        patient = session.get(Patient, account.patient_id)
        if patient is None or patient.archived_at is not None:
            return None
    return account


def revoke_session(session: Session, token: str) -> bool:
    record = _lookup_session(session, token)
    if record is None or record.revoked_at is not None:
        return False
    record.revoked_at = datetime.now(timezone.utc)
    return True
