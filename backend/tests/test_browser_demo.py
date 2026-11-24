"""Exercise real ASGI handlers against independent browser databases."""
import json
import unittest
from unittest.mock import patch

from backend.browser_demo import BROWSER_PASSWORD, create_browser_engine, dispatch, seed_browser_database
from backend.main import app


class BrowserDemoTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, method, path, token=None, data=None):
        headers = [("content-type", "application/json")]
        if token:
            headers.append(("authorization", f"Bearer {token}"))
        reply = await dispatch(app, {
            "url": f"http://emr.local{path}", "method": method,
            "headers": headers, "body": json.dumps(data) if data is not None else "",
        })
        return reply["status"], json.loads(reply["body"]) if reply["body"] else None

    async def login(self, username):
        status, response = await self.request("POST", "/auth/login", data={
            "username": username, "password": BROWSER_PASSWORD,
        })
        self.assertEqual(status, 200)
        return response["access_token"]

    async def test_changes_are_private_and_reset_to_seed(self):
        engines = [create_browser_engine(), create_browser_engine()]
        try:
            for engine in engines:
                seed_browser_database(engine)
            with patch("backend.main.engine", engines[0]):
                token = await self.login("admin")
                status, patients = await self.request("GET", "/patients", token)
                self.assertEqual(status, 200)
                self.assertEqual(len(patients), 3)
                status, patient = await self.request("POST", "/patients", token, {
                    "first_name": "Avery", "last_name": "Reed",
                    "date_of_birth": "1990-01-01", "sex_at_birth": "unknown",
                })
                self.assertEqual(status, 201)
                self.assertEqual(patient["first_name"], "Avery")
                status, records = await self.request("GET", "/patients?search=Avery", token)
                self.assertEqual(len(records), 1)
                patient_token = await self.login("jordan.lee")
                status, _ = await self.request("GET", "/patients", patient_token)
                self.assertEqual(status, 403)
                status, meds = await self.request("GET", "/portal/medications", patient_token)
                self.assertEqual(status, 200)
                self.assertTrue(meds)
                status, _ = await self.request("PUT", "/portal/communication-preferences",
                                               patient_token, {
                    "preferred_channel": "email", "appointment_reminders": True,
                    "care_updates": False,
                })
                self.assertEqual(status, 200)
                status, _ = await self.request("POST", "/auth/logout", patient_token)
                self.assertEqual(status, 204)
                patient_token = await self.login("jordan.lee")
                status, preferences = await self.request("GET", "/portal/communication-preferences",
                                                         patient_token)
                self.assertEqual(preferences["preferred_channel"], "email")
            with patch("backend.main.engine", engines[1]):
                status, _ = await self.request("GET", "/auth/me", token)
                self.assertEqual(status, 401)
                fresh = await self.login("admin")
                status, patients = await self.request("GET", "/patients", fresh)
                self.assertEqual(len(patients), 3)
                patient_token = await self.login("jordan.lee")
                status, preferences = await self.request("GET", "/portal/communication-preferences",
                                                         patient_token)
                self.assertEqual(preferences["preferred_channel"], "portal")
        finally:
            for engine in engines:
                engine.dispose()
