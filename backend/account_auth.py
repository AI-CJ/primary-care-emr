"""Password and identity operations; HTTP session handling is separate."""

import base64
import hashlib
import hmac
import re
import secrets
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Patient, UserAccount


_PASSWORD_ITERATIONS = 600_000
_PASSWORD_SCHEME = "pbkdf2_sha256"
_USERNAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{2,79}\Z")
_STAFF_ROLES = frozenset({"admin", "clinician", "front_desk"})


def normalize_username(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Username must be text")
    username = value.strip().lower()
    if not _USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Username must be 3–80 characters using letters, numbers, dots, dashes, or underscores")
    return username


def _derive_password(raw: bytes, salt: bytes) -> bytes:
    # Pyodide does not bundle OpenSSL-backed hashlib.pbkdf2_hmac.
    # Use the same algorithm and work factor in the browser.
    if sys.platform == "emscripten" and not hasattr(hashlib, "pbkdf2_hmac"):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        return PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=salt,
            iterations=_PASSWORD_ITERATIONS,
        ).derive(raw)
    return hashlib.pbkdf2_hmac("sha256", raw, salt, _PASSWORD_ITERATIONS)


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValueError("Password must be 12–128 characters")
    raw = password.encode("utf-8")
    if len(raw) > 1024:
        raise ValueError("Password is too long")
    salt = secrets.token_bytes(16)
    digest = _derive_password(raw, salt)
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{_PASSWORD_SCHEME}${_PASSWORD_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not isinstance(password, str) or not isinstance(stored_hash, str):
        return False
    raw = password.encode("utf-8")
    if len(raw) > 1024 or len(stored_hash) > 255:
        return False
    try:
        scheme, rounds, salt_text, digest_text = stored_hash.split("$")
        if scheme != _PASSWORD_SCHEME or int(rounds) != _PASSWORD_ITERATIONS:
            return False
        salt = base64.b64decode(salt_text, altchars=b"-_", validate=True)
        expected = base64.b64decode(digest_text, altchars=b"-_", validate=True)
        if len(salt) != 16 or len(expected) != 32:
            return False
    except (ValueError, TypeError):
        return False
    actual = _derive_password(raw, salt)
    return hmac.compare_digest(actual, expected)


def _lock_portal_patient(session: Session, patient_id: int) -> Patient | None:
    # Coordinate account creation and successful login with chart archival.
    return session.scalar(
        select(Patient).where(Patient.id == patient_id).with_for_update()
        .execution_options(populate_existing=True)
    )


def create_user_account(
    session: Session,
    *,
    username: str,
    password: str,
    account_type: str,
    staff_role: str | None = None,
    patient_id: int | None = None,
) -> UserAccount:
    username = normalize_username(username)
    password_hash = hash_password(password)

    if account_type == "staff":
        if staff_role not in _STAFF_ROLES or patient_id is not None:
            raise ValueError("Staff accounts need a valid staff role and no patient link")
    elif account_type == "patient":
        if staff_role is not None or patient_id is None:
            raise ValueError("Patient accounts need one patient link and no staff role")
        patient = _lock_portal_patient(session, patient_id)
        if patient is None:
            raise ValueError("Patient does not exist")
        if patient.archived_at is not None:
            raise ValueError("Archived patient charts cannot receive portal accounts")
    else:
        raise ValueError("Unsupported account type")

    if session.scalar(select(UserAccount.id).where(UserAccount.username == username)) is not None:
        raise ValueError("Username is already in use")

    account = UserAccount(
        username=username,
        password_hash=password_hash,
        account_type=account_type,
        staff_role=staff_role,
        patient_id=patient_id,
    )
    session.add(account)
    session.flush()
    return account


def authenticate_user(session: Session, username: str, password: str) -> UserAccount | None:
    try:
        username = normalize_username(username)
    except ValueError:
        return None
    account = session.scalar(select(UserAccount).where(UserAccount.username == username))
    if account is None or not account.is_active:
        return None
    if not verify_password(password, account.password_hash):
        return None
    if account.account_type == "patient":
        # The login route commits the new session while this lock is held.
        patient = _lock_portal_patient(session, account.patient_id)
        if patient is None or patient.archived_at is not None:
            return None
    return account
