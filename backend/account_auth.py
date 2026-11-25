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
    # The server uses the standard library. The browser has its own async
    # Web Crypto verifier because its WASM stdlib lacks OpenSSL-backed PBKDF2.
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


def _password_parts(password: str, stored_hash: str) -> tuple[bytes, bytes, bytes] | None:
    if not isinstance(password, str) or not isinstance(stored_hash, str):
        return None
    raw = password.encode("utf-8")
    if len(raw) > 1024 or len(stored_hash) > 255:
        return None
    try:
        scheme, rounds, salt_text, digest_text = stored_hash.split("$")
        if scheme != _PASSWORD_SCHEME or int(rounds) != _PASSWORD_ITERATIONS:
            return None
        salt = base64.b64decode(salt_text, altchars=b"-_", validate=True)
        expected = base64.b64decode(digest_text, altchars=b"-_", validate=True)
        if len(salt) != 16 or len(expected) != 32:
            return None
    except (ValueError, TypeError):
        return None
    return raw, salt, expected


def verify_password(password: str, stored_hash: str) -> bool:
    parts = _password_parts(password, stored_hash)
    if parts is None:
        return False
    raw, salt, expected = parts
    return hmac.compare_digest(_derive_password(raw, salt), expected)


async def _derive_browser_password(raw: bytes, salt: bytes) -> bytes:
    # Registered only by the private, serialized browser worker. No digest,
    # salt, or password is accepted from an HTTP request as a verifier.
    from emr_crypto import derivePassword
    from pyodide.ffi import to_js

    digest = await derivePassword(to_js(list(raw)), to_js(list(salt)))
    return bytes(digest.to_py())


async def verify_browser_password(password: str, stored_hash: str) -> bool:
    if sys.platform != "emscripten":
        raise RuntimeError("Browser authentication is not a server operation")
    parts = _password_parts(password, stored_hash)
    if parts is None:
        return False
    raw, salt, expected = parts
    return hmac.compare_digest(await _derive_browser_password(raw, salt), expected)


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
    return _create_user_account_with_hash(
        session, username=username, password_hash=hash_password(password),
        account_type=account_type, staff_role=staff_role, patient_id=patient_id,
    )


def _create_user_account_with_hash(
    session: Session,
    *,
    username: str,
    password_hash: str,
    account_type: str,
    staff_role: str | None = None,
    patient_id: int | None = None,
) -> UserAccount:
    """Shared account invariants; pre-derived hashes are internal, never API input."""
    username = normalize_username(username)
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


def _active_account(session: Session, username: str) -> UserAccount | None:
    try:
        username = normalize_username(username)
    except ValueError:
        return None
    account = session.scalar(select(UserAccount).where(UserAccount.username == username))
    if account is None or not account.is_active:
        return None
    return account


def _authenticated_account(session: Session, account: UserAccount) -> UserAccount | None:
    if account.account_type == "patient":
        # The login route commits the new session while this lock is held.
        patient = _lock_portal_patient(session, account.patient_id)
        if patient is None or patient.archived_at is not None:
            return None
    return account

def authenticate_user(session: Session, username: str, password: str) -> UserAccount | None:
    account = _active_account(session, username)
    if account is None or not verify_password(password, account.password_hash):
        return None
    return _authenticated_account(session, account)


async def authenticate_browser_user(session: Session, username: str, password: str) -> UserAccount | None:
    if sys.platform != "emscripten":
        raise RuntimeError("Browser authentication is not a server operation")
    account = _active_account(session, username)
    if account is None or not await verify_browser_password(password, account.password_hash):
        return None
    return _authenticated_account(session, account)
