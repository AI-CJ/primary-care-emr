"""Local patient account bootstrap tests."""

import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.account_auth import authenticate_user
from backend.bootstrap_patient import main
from backend.models import Base, Patient, UserAccount


class BootstrapPatientTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Alex", last_name="Example",
                date_of_birth=date(1985, 2, 3), sex_at_birth="unknown",
            )
            session.add(patient)
            session.commit()
            self.patient_id = patient.id

    def tearDown(self):
        self.engine.dispose()

    def test_links_login_to_one_patient_with_hashed_password(self):
        with (
            patch("backend.bootstrap_patient.engine", self.engine),
            patch("backend.bootstrap_patient.getpass", side_effect=[
                "Synthetic password 123!", "Synthetic password 123!",
            ]),
            patch("builtins.print"),
        ):
            main(["--username", " Alex.Portal ", "--patient-id", str(self.patient_id)])

        with Session(self.engine) as session:
            account = session.scalar(select(UserAccount))
            self.assertEqual(account.username, "alex.portal")
            self.assertEqual(account.account_type, "patient")
            self.assertIsNone(account.staff_role)
            self.assertEqual(account.patient_id, self.patient_id)
            self.assertNotIn("Synthetic password 123!", account.password_hash)
            self.assertIsNotNone(
                authenticate_user(session, "alex.portal", "Synthetic password 123!")
            )

    def test_rejects_missing_patient_without_creating_account(self):
        with (
            patch("backend.bootstrap_patient.engine", self.engine),
            patch("backend.bootstrap_patient.getpass", side_effect=[
                "Synthetic password 123!", "Synthetic password 123!",
            ]),
        ):
            with self.assertRaises(SystemExit):
                main(["--username", "alex.portal", "--patient-id", "99999"])
        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(UserAccount)))

    def test_rejects_password_mismatch_without_creating_account(self):
        with (
            patch("backend.bootstrap_patient.engine", self.engine),
            patch("backend.bootstrap_patient.getpass", side_effect=[
                "Synthetic password 123!", "Different password 123!",
            ]),
        ):
            with self.assertRaises(SystemExit):
                main(["--username", "alex.portal", "--patient-id", str(self.patient_id)])
        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(UserAccount)))


if __name__ == "__main__":
    unittest.main()
