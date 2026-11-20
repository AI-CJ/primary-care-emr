"""Password verification and account creation with fictional identities."""

import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.account_auth import (
    authenticate_user, create_user_account, hash_password,
    normalize_username, verify_password,
)
from backend.models import Base, Patient, UserAccount


class AccountAuthTests(unittest.TestCase):
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

    def test_salted_password_hashes_and_invalid_attempts(self):
        password = "A synthetic passphrase 12!"
        first = hash_password(password)
        second = hash_password(password)
        self.assertNotEqual(first, second)
        self.assertNotIn(password, first)
        self.assertTrue(verify_password(password, first))
        self.assertFalse(verify_password("Wrong synthetic passphrase", first))
        for malformed in ("", "plain-text", "pbkdf2_sha256$999999999$abc$def", "pbkdf2_sha256$600000$bad$bad"):
            with self.subTest(malformed=malformed):
                self.assertFalse(verify_password(password, malformed))

    def test_password_length_bounds(self):
        for value in ("short", "A" * 129):
            with self.subTest(length=len(value)):
                with self.assertRaises(ValueError):
                    hash_password(value)
        self.assertFalse(verify_password("A" * 1025, hash_password("A" * 12)))

    def test_username_normalization(self):
        self.assertEqual(normalize_username("  ExAmPle.Staff  "), "example.staff")
        for value in ("a", "has space", "../bad", "é", "a" * 81):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_username(value)

    def test_create_and_authenticate_staff_and_patient(self):
        with Session(self.engine) as session:
            staff = create_user_account(
                session, username="  STAFF.Sample ", password="Synthetic staff pass!",
                account_type="staff", staff_role="clinician",
            )
            portal = create_user_account(
                session, username="Portal.Sample", password="Synthetic portal pass!",
                account_type="patient", patient_id=self.patient_id,
            )
            self.assertEqual(staff.username, "staff.sample")
            self.assertEqual(portal.patient_id, self.patient_id)
            self.assertNotEqual(staff.password_hash, "Synthetic staff pass!")
            session.commit()

        with Session(self.engine) as session:
            staff = authenticate_user(session, "STAFF.SAMPLE", "Synthetic staff pass!")
            self.assertEqual(staff.account_type, "staff")
            self.assertEqual(staff.staff_role, "clinician")
            patient = authenticate_user(session, "portal.sample", "Synthetic portal pass!")
            self.assertEqual(patient.patient_id, self.patient_id)
            self.assertIsNone(authenticate_user(session, "staff.sample", "not the password"))
            self.assertIsNone(authenticate_user(session, "absent.user", "Synthetic staff pass!"))
            self.assertIsNone(authenticate_user(session, "invalid user", "Synthetic staff pass!"))
            staff.is_active = False
            session.commit()
            self.assertIsNone(authenticate_user(session, "staff.sample", "Synthetic staff pass!"))

    def test_invalid_account_types_and_uniqueness(self):
        with Session(self.engine) as session:
            invalid = (
                {"account_type": "staff"},
                {"account_type": "staff", "staff_role": "clinician", "patient_id": self.patient_id},
                {"account_type": "patient"},
                {"account_type": "patient", "patient_id": 999999},
                {"account_type": "patient", "patient_id": self.patient_id, "staff_role": "clinician"},
                {"account_type": "other"},
            )
            for fields in invalid:
                with self.subTest(fields=fields):
                    with self.assertRaises(ValueError):
                        create_user_account(
                            session, username="example", password="Synthetic password!", **fields
                        )
            create_user_account(
                session, username="staff.one", password="Synthetic password!",
                account_type="staff", staff_role="front_desk",
            )
            with self.assertRaises(ValueError):
                create_user_account(
                    session, username="STAFF.ONE", password="Synthetic password!",
                    account_type="staff", staff_role="front_desk",
                )
            session.commit()

    def test_patient_identity_is_unique_under_database_constraint(self):
        with Session(self.engine) as session:
            create_user_account(
                session, username="portal.one", password="Synthetic password!",
                account_type="patient", patient_id=self.patient_id,
            )
            session.commit()
        with Session(self.engine) as session:
            with self.assertRaises(IntegrityError):
                create_user_account(
                    session, username="portal.two", password="Synthetic password!",
                    account_type="patient", patient_id=self.patient_id,
                )


if __name__ == "__main__":
    unittest.main()
