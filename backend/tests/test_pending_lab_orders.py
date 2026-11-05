"""Pending lab requests remain visible until cancelled or resulted."""

import unittest
from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.lab_orders import (
    cancel_lab_order,
    list_pending_lab_orders,
    record_lab_result,
)
from backend.models import Base, Encounter, LabOrder, Patient
from backend.schemas import (
    LabOrderCancel,
    LabOrderRead,
    LabResultCreate,
    PendingLabOrderRead,
)


class PendingLabOrderTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            avery = Patient(
                first_name="Avery", last_name="Example",
                date_of_birth=date(1986, 4, 3), sex_at_birth="unknown",
            )
            morgan = Patient(
                first_name="Morgan", preferred_name="Mo", last_name="Sample",
                date_of_birth=date(1993, 2, 10), sex_at_birth="unknown",
            )
            session.add_all([avery, morgan])
            session.flush()
            first_visit = Encounter(
                patient_id=avery.id,
                visit_date=date(2026, 11, 2),
                reason_for_visit="Synthetic visit",
                assessment="Fictional assessment",
            )
            second_visit = Encounter(
                patient_id=morgan.id,
                visit_date=date(2026, 11, 3),
                reason_for_visit="Synthetic follow-up",
                assessment="Fictional assessment",
                finalized_at=datetime(2026, 11, 3, 15, tzinfo=timezone.utc),
            )
            session.add_all([first_visit, second_visit])
            session.flush()

            routine = LabOrder(
                encounter_id=first_visit.id,
                test_name="Synthetic routine panel",
                priority="routine", status="ordered",
                ordered_at=datetime(2026, 11, 3, 9, tzinfo=timezone.utc),
            )
            urgent = LabOrder(
                encounter_id=second_visit.id,
                test_name="Synthetic urgent test",
                priority="urgent", status="ordered",
                ordered_at=datetime(2026, 11, 3, 10, tzinfo=timezone.utc),
            )
            cancelled = LabOrder(
                encounter_id=first_visit.id,
                test_name="Cancelled synthetic test",
                priority="urgent", status="cancelled",
                ordered_at=datetime(2026, 11, 2, 9, tzinfo=timezone.utc),
            )
            resulted = LabOrder(
                encounter_id=second_visit.id,
                test_name="Resulted synthetic test",
                priority="urgent", status="resulted",
                ordered_at=datetime(2026, 11, 2, 8, tzinfo=timezone.utc),
            )
            session.add_all([routine, urgent, cancelled, resulted])
            session.flush()
            self.routine_id = routine.id
            self.urgent_id = urgent.id
            self.avery_id = avery.id
            self.morgan_id = morgan.id
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_pending_only_and_urgent_first(self):
        with Session(self.engine) as session:
            rows = list_pending_lab_orders(session)
            self.assertEqual([order.id for order, _, _ in rows],
                             [self.urgent_id, self.routine_id])
            self.assertEqual([patient.id for _, _, patient in rows],
                             [self.morgan_id, self.avery_id])
            self.assertEqual(rows[0][1], date(2026, 11, 3))
            self.assertEqual(rows[1][1], date(2026, 11, 2))

    def test_patient_identity_and_response_are_consistent(self):
        with Session(self.engine) as session:
            order, visit_date, patient = list_pending_lab_orders(session)[0]
            response = PendingLabOrderRead(
                **LabOrderRead.model_validate(order).model_dump(),
                patient_id=patient.id,
                patient_name=f"{patient.preferred_name or patient.first_name} {patient.last_name}",
                visit_date=visit_date,
            )
            self.assertEqual(response.patient_name, "Mo Sample")
            self.assertEqual(response.patient_id, self.morgan_id)
            self.assertEqual(response.encounter_id, order.encounter_id)
            self.assertEqual(response.status, "ordered")
            self.assertEqual(response.priority, "urgent")

    def test_items_disappear_after_cancellation_and_resulting(self):
        with Session(self.engine) as session:
            cancel_lab_order(
                session, self.routine_id,
                LabOrderCancel(reason="No longer needed for fictional patient"),
            )
            record_lab_result(
                session, self.urgent_id,
                LabResultCreate(
                    collected_on=date(2026, 11, 3),
                    result_text="Synthetic finding",
                ),
            )
            session.commit()

        with Session(self.engine) as session:
            self.assertEqual(list_pending_lab_orders(session), [])

    def test_newly_ordered_item_is_included(self):
        with Session(self.engine) as session:
            original = list_pending_lab_orders(session)
            encounter_id = original[1][0].encounter_id
            order = LabOrder(
                encounter_id=encounter_id,
                test_name="Later synthetic test",
                priority="urgent", status="ordered",
                ordered_at=datetime(2026, 11, 4, 12, tzinfo=timezone.utc),
            )
            session.add(order)
            session.commit()
            new_id = order.id

        with Session(self.engine) as session:
            ids = [row[0].id for row in list_pending_lab_orders(session)]
            self.assertEqual(ids, [self.urgent_id, new_id, self.routine_id])


if __name__ == "__main__":
    unittest.main()
