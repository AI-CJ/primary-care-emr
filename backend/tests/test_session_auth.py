"""Opaque session lifecycle with fictional identities."""

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Base, UserAccount, UserSession
from backend.session_auth import create_session, get_session_account, revoke_session


class SessionAuthTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            user = UserAccount(
                username="test.clinician", password_hash="synthetic-hash",
                account_type="staff", staff_role="clinician",
            )
            session.add(user)
            session.flush()
            self.user_id = user.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def issue(self):
        with Session(self.engine) as session:
            token, record = create_session(session, session.get(UserAccount, self.user_id))
            record_id = record.id
            session.commit()
        return token, record_id

    def test_token_is_not_stored_and_resolves_account(self):
        token, record_id = self.issue()
        self.assertEqual(len(token), 43)
        with Session(self.engine) as session:
            record = session.get(UserSession, record_id)
            self.assertNotEqual(record.token_digest, token)
            self.assertEqual(len(record.token_digest), 64)
            self.assertEqual(get_session_account(session, token).id, self.user_id)
            for invalid in ("", "wrong", token + "!", "a" * 1024):
                with self.subTest(token=invalid[:12]):
                    self.assertIsNone(get_session_account(session, invalid))

    def test_revocation_only_affects_target_session(self):
        first, _ = self.issue()
        second, _ = self.issue()
        with Session(self.engine) as session:
            self.assertTrue(revoke_session(session, first))
            self.assertFalse(revoke_session(session, first))
            session.commit()
        with Session(self.engine) as session:
            self.assertIsNone(get_session_account(session, first))
            self.assertIsNotNone(get_session_account(session, second))
            self.assertFalse(revoke_session(session, "not-a-token"))

    def test_expiry_and_account_deactivation(self):
        token, record_id = self.issue()
        with Session(self.engine) as session:
            session.get(UserSession, record_id).expires_at = (
                datetime.now(timezone.utc) - timedelta(minutes=1)
            )
            session.commit()
        with Session(self.engine) as session:
            self.assertIsNone(get_session_account(session, token))
            session.get(UserAccount, self.user_id).is_active = False
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(ValueError):
                create_session(session, session.get(UserAccount, self.user_id))
            session.get(UserSession, record_id).expires_at = (
                datetime.now(timezone.utc) + timedelta(hours=1)
            )
            session.commit()
        with Session(self.engine) as session:
            self.assertIsNone(get_session_account(session, token))


if __name__ == "__main__":
    unittest.main()
