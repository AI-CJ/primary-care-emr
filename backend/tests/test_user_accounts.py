"""Database constraints for synthetic staff and patient identities."""

import unittest
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Base, Patient, UserAccount


class UserAccountTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            patient = Patient(
                first_name="Avery", last_name="Sample",
                date_of_birth=date(1990, 5, 12), sex_at_birth="unknown",
            )
            session.add(patient)
            session.flush()
            self.patient_id = patient.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def add_account(self, **overrides):
        fields = {
            "username": "test.staff", "password_hash": "synthetic-hash",
            "account_type": "staff", "staff_role": "clinician",
        }
        fields.update(overrides)
        with Session(self.engine) as session:
            account = UserAccount(**fields)
            session.add(account)
            session.commit()
            return account.id

    def test_staff_and_patient_are_separate_identities(self):
        staff_id = self.add_account()
        patient_login_id = self.add_account(
            username="sample.patient", account_type="patient",
            staff_role=None, patient_id=self.patient_id,
        )
        with Session(self.engine) as session:
            accounts = session.scalars(select(UserAccount).order_by(UserAccount.id)).all()
            self.assertEqual([a.id for a in accounts], [staff_id, patient_login_id])
            self.assertIsNone(accounts[0].patient_id)
            self.assertEqual(accounts[1].patient_id, self.patient_id)
            self.assertTrue(accounts[0].is_active)
            self.assertIsNotNone(accounts[1].created_at)

    def test_username_must_be_unique_and_lowercase(self):
        self.add_account()
        for username in ("test.staff", "Test.Staff"):
            with self.subTest(username=username):
                with self.assertRaises(IntegrityError):
                    self.add_account(username=username)

    def test_patient_cannot_have_two_portal_accounts(self):
        self.add_account(
            username="patient.1", account_type="patient", staff_role=None,
            patient_id=self.patient_id,
        )
        with self.assertRaises(IntegrityError):
            self.add_account(
                username="patient.2", account_type="patient", staff_role=None,
                patient_id=self.patient_id,
            )

    def test_role_rules_are_checked_by_database(self):
        invalid = (
            {"account_type": "staff", "staff_role": None},
            {"account_type": "staff", "staff_role": "unknown"},
            {"account_type": "staff", "patient_id": self.patient_id},
            {"account_type": "patient", "staff_role": None, "patient_id": None},
            {"account_type": "patient", "staff_role": "clinician", "patient_id": self.patient_id},
            {"account_type": "invalid"},
        )
        for fields in invalid:
            with self.subTest(fields=fields):
                with self.assertRaises(IntegrityError):
                    self.add_account(**fields)


if __name__ == "__main__":
    unittest.main()
