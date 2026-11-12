"""Clinic worklist for lab results awaiting release."""

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.lab_orders import list_unreleased_lab_results, release_lab_result
from backend.main import read_unreleased_lab_results
from backend.models import Base, Encounter, LabOrder, LabResult, Patient


class UnreleasedLabResultsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        base = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)

        with Session(self.engine) as session:
            avery = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1988, 2, 12), sex_at_birth="unknown",
            )
            morgan = Patient(
                first_name="Morgan", preferred_name="Mo", last_name="Sample",
                date_of_birth=date(1992, 6, 9), sex_at_birth="unknown",
            )
            session.add_all([avery, morgan])
            session.flush()
            signed = Encounter(
                patient_id=morgan.id, visit_date=date(2026, 11, 9),
                reason_for_visit="Fictional follow-up", finalized_at=base,
            )
            second_signed = Encounter(
                patient_id=avery.id, visit_date=date(2026, 11, 10),
                reason_for_visit="Synthetic appointment", finalized_at=base,
            )
            draft = Encounter(
                patient_id=avery.id, visit_date=date(2026, 11, 11),
                reason_for_visit="Unfinalized synthetic visit",
            )
            session.add_all([signed, second_signed, draft])
            session.flush()

            def add_order(visit, name, priority, status, offset, released=False, with_result=True):
                order = LabOrder(
                    encounter_id=visit.id, test_name=name, priority=priority,
                    status=status, ordered_at=base + timedelta(hours=offset),
                )
                session.add(order)
                session.flush()
                if status == "resulted" and with_result:
                    session.add(LabResult(
                        lab_order_id=order.id,
                        collected_on=visit.visit_date,
                        result_text=f"Private synthetic result for {name}",
                        reported_at=base + timedelta(hours=offset + 1),
                        released_at=base if released else None,
                    ))
                return order.id

            self.first_urgent = add_order(signed, "Urgent first", "urgent", "resulted", 0)
            self.second_urgent = add_order(second_signed, "Urgent second", "urgent", "resulted", 2)
            self.routine = add_order(signed, "Routine result", "routine", "resulted", -2)
            add_order(signed, "Already released", "urgent", "resulted", -3, released=True)
            add_order(draft, "Draft only", "urgent", "resulted", -4)
            add_order(signed, "Request still pending", "urgent", "ordered", -5)
            add_order(signed, "Missing result", "urgent", "resulted", -6, with_result=False)
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_unreleased_results_from_finalized_visits_only(self):
        with Session(self.engine) as session:
            rows = list_unreleased_lab_results(session)

        self.assertEqual(
            [order.id for order, _, _, _ in rows],
            [self.first_urgent, self.second_urgent, self.routine],
        )
        self.assertEqual(rows[0][2], date(2026, 11, 9))
        self.assertEqual(rows[0][3].preferred_name, "Mo")

    def test_endpoint_excludes_result_text_and_note_details(self):
        with patch("backend.main.engine", self.engine):
            response = read_unreleased_lab_results()

        self.assertEqual([item.order_id for item in response],
                         [self.first_urgent, self.second_urgent, self.routine])
        self.assertEqual(response[0].patient_name, "Mo Sample")
        self.assertEqual(response[0].priority, "urgent")
        self.assertEqual(
            set(response[0].model_dump()),
            {"order_id", "patient_id", "patient_name", "test_name",
             "priority", "visit_date", "ordered_at", "reported_at"},
        )
        self.assertNotIn("Private synthetic result", repr(response))
        self.assertNotIn("Fictional follow-up", repr(response))

    def test_released_result_leaves_worklist(self):
        with Session(self.engine) as session:
            release_lab_result(session, self.first_urgent)
            session.commit()
        with Session(self.engine) as session:
            ids = [order.id for order, _, _, _ in list_unreleased_lab_results(session)]
        self.assertEqual(ids, [self.second_urgent, self.routine])

    def test_draft_result_enters_only_after_finalization(self):
        with Session(self.engine) as session:
            draft = session.query(Encounter).filter(
                Encounter.reason_for_visit == "Unfinalized synthetic visit"
            ).one()
            draft.finalized_at = datetime(2026, 11, 12, tzinfo=timezone.utc)
            session.commit()
        with Session(self.engine) as session:
            names = [order.test_name for order, _, _, _ in list_unreleased_lab_results(session)]
        self.assertIn("Draft only", names)
        self.assertNotIn("Already released", names)


if __name__ == "__main__":
    unittest.main()
