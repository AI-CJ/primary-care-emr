"""Clinical reference, medication and immunization access regression checks."""
from datetime import date, timedelta
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.browser_demo import BROWSER_PASSWORD, create_browser_engine, seed_browser_database
from backend.clinical_reference import reference_search
from backend.main import app


REFERENCES = {
    "rxnorm": ("test-rx", {
        "29046": {"code": "29046", "name": "lisinopril", "kind": "IN"},
        "314076": {"code": "314076", "name": "lisinopril 10 MG Oral Tablet", "kind": "SCD"},
        "83367": {"code": "83367", "name": "atorvastatin", "kind": "IN"},
    }),
    "cvx": ("test-cvx", {
        "115": {"code": "115", "name": "Tdap", "kind": "Active", "short_name": "Tdap"},
        "88": {"code": "88", "name": "Influenza, unspecified formulation", "kind": "Inactive", "short_name": "Influenza"},
    }),
    "mvx": ("test-mvx", {
        "PMC": {"code": "PMC", "name": "Sanofi Pasteur", "kind": "Active"},
    }),
}


class ClinicalReferenceTests(TestCase):
    def setUp(self):
        self.engine = create_browser_engine()
        seed_browser_database(self.engine)
        self.addCleanup(self.engine.dispose)
        for target, options in (
            ("backend.main.engine", {"new": self.engine}),
            ("backend.clinical_reference.load_reference", {"side_effect": REFERENCES.__getitem__}),
        ):
            fixture = patch(target, **options)
            fixture.start()
            self.addCleanup(fixture.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.staff = self.login("admin")
        self.patient = self.login("jordan.lee")
        self.other = self.login("maria.thompson")

    def login(self, username):
        response = self.client.post("/auth/login", json={"username": username, "password": BROWSER_PASSWORD})
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def request(self, method, path, payload=None, *, headers=None, expected=200):
        result = self.client.request(method, path, json=payload, headers=self.staff if headers is None else headers)
        self.assertEqual(result.status_code, expected, result.text)
        self.assertEqual(result.headers.get("cache-control"), "no-store")
        return result.json()

    def test_reference_lookup_rank_and_access(self):
        self.assertEqual(reference_search("rxnorm", "lisinopril")["results"][0]["code"], "29046")
        self.assertEqual(reference_search("rxnorm", "lisinopril tablet")["results"][0]["code"], "314076")
        self.assertEqual(reference_search("rxnorm", "unknown")["results"], [])
        path = "/clinical-reference/cvx/search"
        self.request("POST", path, {"query": "115"}, headers={}, expected=401)
        self.request("POST", path, {"query": "115"}, headers=self.patient, expected=403)
        self.assertEqual(self.request("POST", path, {"query": "115"})["results"][0]["code"], "115")

    def test_coded_medications_preserve_history(self):
        path = "/patients/1/medications"
        self.request("POST", path, {"name": "wrong", "rxnorm_cui": "29046"}, expected=422)
        self.request("POST", path, {"name": "lisinopril", "rxnorm_cui": "999999999"}, expected=422)
        med = self.request("POST", path, {"name": "lisinopril", "rxnorm_cui": "29046",
                                        "strength": "10 mg"}, expected=201)
        self.assertEqual(med["rxnorm_cui"], "29046")
        self.assertEqual(med["rxnorm_release"], "test-rx")
        edit = f"/medications/{med['id']}"
        self.assertEqual(self.request("PUT", edit, {"name": "lisinopril", "strength": "20 mg"})["rxnorm_cui"], "29046")
        self.request("PUT", edit, {"name": "Changed without reconciliation"}, expected=422)
        self.assertIsNone(self.request("PUT", edit, {"name": "Historical entry", "rxnorm_cui": None})["rxnorm_cui"])
        self.assertTrue(all("rxnorm_cui" not in row for row in self.request("GET", "/portal/medications", headers=self.patient)))

    def test_immunizations_ownership_duplicates_and_correction(self):
        path = "/patients/1/immunizations"
        payload = {"cvx_code": "115", "source": "historical_record",
                   "administered_on": (date.today() - timedelta(days=10)).isoformat(),
                   "manufacturer_code": "PMC", "dose_number": 1, "route": "Intramuscular"}
        self.request("POST", path, payload, headers=self.patient, expected=403)
        self.request("POST", path, dict(payload, administered_on="1900-01-01"), expected=422)
        self.request("POST", path, dict(payload, administered_on=(date.today() + timedelta(days=1)).isoformat()), expected=422)
        self.request("POST", path, dict(payload, cvx_code="88", source="clinic"), expected=422)
        row = self.request("POST", path, payload, expected=201)
        self.assertEqual(row["manufacturer_name"], "Sanofi Pasteur")
        self.request("POST", path, payload, expected=409)
        own = self.request("GET", "/portal/immunizations", headers=self.patient)
        self.assertEqual([r["id"] for r in own], [row["id"]])
        self.assertNotIn("patient_id", own[0])
        self.assertEqual(self.request("GET", "/portal/immunizations", headers=self.other), [])
        self.request("GET", "/patients/1/portal-preview/immunizations", headers=self.other, expected=403)
        self.request("GET", "/portal/immunizations", headers=self.staff, expected=403)
        correction = f"/immunizations/{row['id']}/void"
        self.request("POST", correction, {"reason": " "}, expected=422)
        self.request("POST", correction, {"reason": "Duplicate external record"}, headers=self.patient, expected=403)
        self.request("POST", correction, {"reason": "Duplicate external record"})
        self.assertEqual(self.request("GET", "/portal/immunizations", headers=self.patient), [])
        self.assertTrue(self.request("GET", path)[0]["voided_at"])
        replacement = self.request("POST", path, payload, expected=201)
        self.assertNotEqual(replacement["id"], row["id"])

    def test_demographic_correction_preserves_vaccination_chronology(self):
        demographics = {"first_name": "Synthetic", "last_name": "Fixture",
                        "sex_at_birth": "unknown", "date_of_birth": "1990-01-01"}
        patient = self.request("POST", "/patients", demographics, expected=201)
        path = f"/patients/{patient['id']}"
        row = self.request("POST", path + "/immunizations", {
            "cvx_code": "115", "source": "historical_record",
            "administered_on": "2010-01-01",
        }, expected=201)
        corrected = dict(demographics, date_of_birth="2011-01-01")
        self.request("PUT", path, corrected, expected=409)
        self.assertEqual(self.request("GET", path)["date_of_birth"], "1990-01-01")
        self.request("PUT", path, dict(demographics, preferred_name="Test"))
        self.request("POST", f"/immunizations/{row['id']}/void",
                     {"reason": "Synthetic fixture correction"})
        self.assertEqual(self.request("PUT", path, corrected)["date_of_birth"], "2011-01-01")
        self.assertTrue(self.request("GET", path + "/immunizations")[0]["voided_at"])

    def test_front_desk_cannot_read_or_write_clinical_reference_records(self):
        from backend.account_auth import create_user_account
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            create_user_account(session, username="fixture.frontdesk",
                                password=BROWSER_PASSWORD, account_type="staff",
                                staff_role="front_desk")
            session.commit()
        front_desk = self.login("fixture.frontdesk")
        clinician = self.login("clinician")
        for path, payload in (
            ("/diagnosis-codes/search", {"query": "I10"}),
            ("/clinical-reference/rxnorm/search", {"query": "lisinopril"}),
            ("/clinical-reference/cvx/search", {"query": "115"}),
            ("/clinical-reference/mvx/search", {"query": "PMC"}),
        ):
            self.request("POST", path, payload, headers=front_desk, expected=403)
            self.request("POST", path, payload, headers=self.patient, expected=403)
        self.request("GET", "/patients/1/immunizations", headers=front_desk, expected=403)
        self.request("POST", "/patients/1/immunizations", {
            "cvx_code": "115", "source": "historical_record",
            "administered_on": "2020-01-01",
        }, headers=front_desk, expected=403)
        self.request("GET", "/patients/1/immunizations", headers=clinician)
        self.request("POST", "/clinical-reference/rxnorm/search",
                     {"query": "lisinopril"}, headers=clinician)
