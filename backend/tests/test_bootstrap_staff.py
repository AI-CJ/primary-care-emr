"""Local staff account bootstrap tests."""

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.bootstrap_staff import main
from backend.account_auth import authenticate_user
from backend.models import Base, UserAccount


class BootstrapStaffTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_creates_clinician_without_storing_plaintext_password(self):
        with (
            patch("backend.bootstrap_staff.engine", self.engine),
            patch("backend.bootstrap_staff.getpass", side_effect=["Synthetic password 123!", "Synthetic password 123!"]),
            patch("builtins.print"),
        ):
            main(["--username", " Demo.Clinician ", "--role", "clinician"])
        with Session(self.engine) as session:
            user = session.scalar(select(UserAccount))
            self.assertEqual(user.username, "demo.clinician")
            self.assertNotIn("Synthetic password 123!", user.password_hash)
            self.assertIsNotNone(authenticate_user(session, "demo.clinician", "Synthetic password 123!"))

    def test_rejects_mismatch_without_creating_account(self):
        with (
            patch("backend.bootstrap_staff.engine", self.engine),
            patch("backend.bootstrap_staff.getpass", side_effect=["Synthetic password 123!", "Different password 123!"]),
        ):
            with self.assertRaises(SystemExit):
                main(["--username", "demo.clinician"])
        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(UserAccount)))


if __name__ == "__main__":
    unittest.main()
