"""Regression coverage for diagnosis selections and historical indication snapshots."""
import unittest
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.browser_demo import BROWSER_PASSWORD, create_browser_engine, seed_browser_database
from backend.icd10_catalog import DiagnosisCode, search_index
from backend.main import app


class DiagnosisIndicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_browser_engine()
        seed_browser_database(self.engine)
        self.addCleanup(self.engine.dispose)
        engine_patch = patch("backend.main.engine", self.engine)
        engine_patch.start()
        self.addCleanup(engine_patch.stop)
        catalog_patch = patch("backend.icd10_catalog.load_catalog", return_value={
            "I10": DiagnosisCode("I10", "Essential (primary) hypertension"),
            "E119": DiagnosisCode("E11.9", "Type 2 diabetes mellitus without complications"),
        })
        catalog_patch.start()
        self.addCleanup(catalog_patch.stop)
        search_index.cache_clear()
        self.addCleanup(search_index.cache_clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.staff = self.login("admin")
        self.patient = self.login("jordan.lee")

    def login(self, username):
        response = self.client.post("/auth/login", json={"username": username, "password": BROWSER_PASSWORD})
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def request(self, method, path, data=None, expected=200, headers=None):
        response = self.client.request(method, path, json=data, headers=self.staff if headers is None else headers)
        self.assertEqual(response.status_code, expected, response.text)
        return response

    def test_search_roles_and_validated_codes(self):
        path = "/diagnosis-codes/search"
        self.request("POST", path, {"query": "I10"}, 401, {})
        self.request("POST", path, {"query": "I10"}, 403, self.patient)
        response = self.request("POST", path, {"query": "hypertension"})
        self.assertEqual(response.json()["results"][0]["code"], "I10")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.request("POST", "/patients/1/problems", {"name": "Unknown code", "icd10_code": "I99ZZZZ"}, 422)
        problem = self.request("POST", "/patients/1/problems", {"name": "Diabetes", "icd10_code": "e119"}, 201).json()
        self.assertEqual(problem["icd10_code"], "E11.9")
        self.assertEqual(problem["icd10_release"], "FY2027")
        self.request("PUT", f"/problems/{problem['id']}", {"name": "Renamed without confirmation"}, 422)
        portal = self.request("GET", "/portal/problems", headers=self.patient).json()
        self.assertTrue(any(item["id"] == problem["id"] for item in portal))
        self.assertTrue(all("icd10_code" not in item for item in portal))

    def test_medication_selections_are_scoped_and_preserved(self):
        path = "/patients/1/medications"
        problems = self.request("GET", "/patients/1/problems").json()
        ids = [item["id"] for item in problems[:2]]
        other = self.request("POST", "/patients/2/problems", {"name": "Other condition", "icd10_code": "I10"}, 201).json()
        self.request("POST", path, {"name": "Wrong chart", "problem_ids": [other["id"]]}, 404)
        self.request("POST", path, {"name": "Duplicate", "problem_ids": [ids[0], ids[0]]}, 422)
        self.request("POST", path, {"name": "Bad selection", "problem_ids": [True]}, 422)
        medication = self.request("POST", path, {"name": "Example medication", "problem_ids": ids}, 201).json()
        self.assertEqual({item["problem_id"] for item in medication["indications"]}, set(ids))
        edit = f"/medications/{medication['id']}"
        self.assertEqual(self.request("PUT", edit, {"name": "Example medication"}).json()["indications"], medication["indications"])
        self.assertEqual(self.request("PUT", edit, {"name": "Example medication", "problem_ids": []}).json()["indications"], [])

    def test_finalized_lab_and_visit_snapshot(self):
        problem = self.request("POST", "/patients/1/problems", {"name": "Blood pressure", "icd10_code": "I10"}, 201).json()
        visit = self.request("POST", "/patients/1/encounters", {"visit_date": date.today().isoformat(), "reason_for_visit": "Example review", "assessment": "Chart reviewed.", "plan": "Follow-up planned."}, 201).json()
        root = f"/encounters/{visit['id']}"
        self.request("POST", root + "/problems", {"problem_id": problem["id"]}, 201)
        order = self.request("POST", root + "/lab-orders", {"test_name": "Example panel", "problem_ids": [problem["id"]]}, 201).json()
        self.assertEqual(order["indications"][0]["icd10_code"], "I10")
        path = f"/lab-orders/{order['id']}/indications"
        self.request("POST", root + "/finalize", expected=200)
        self.request("PUT", path, {"problem_ids": []}, 409)
        self.request("PUT", f"/problems/{problem['id']}", {"name": "Diabetes", "icd10_code": "E11.9"})
        self.assertEqual(self.request("GET", root + "/problems").json()[0]["icd10_code_at_link"], "I10")
        self.assertEqual(self.request("GET", root + "/lab-orders").json()[0]["indications"], order["indications"])
        portal = self.request("GET", "/portal/lab-orders", headers=self.patient).json()
        self.assertTrue(all("indications" not in item for item in portal))
