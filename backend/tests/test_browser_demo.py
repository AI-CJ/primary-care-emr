"""Exercise real ASGI handlers against independent browser databases."""
import json
import unittest
from unittest.mock import patch

from backend.browser_demo import BROWSER_PASSWORD, create_browser_engine, dispatch, seed_browser_database, _validated_demo_hashes
from backend.account_auth import hash_password, verify_password, authenticate_browser_user, verify_browser_password, _derive_password
from backend.models import UserAccount
from sqlalchemy import select
from sqlalchemy.orm import Session
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

    async def test_native_seed_hashes_are_browser_only_and_preserve_authentication(self):
        hashes = {name: hash_password(BROWSER_PASSWORD) for name in
                  ("admin", "clinician", "jordan.lee", "maria.thompson")}
        raw = json.dumps(hashes)
        with self.assertRaises(RuntimeError):
            _validated_demo_hashes(raw)
        engine = create_browser_engine()
        try:
            with patch("backend.browser_demo.sys.platform", "emscripten"):
                self.assertEqual(_validated_demo_hashes(raw), hashes)
                self.assertIsNone(_validated_demo_hashes(json.dumps(dict.fromkeys(hashes, hashes["admin"]))))
                self.assertIsNone(_validated_demo_hashes(json.dumps({"admin": hashes["admin"]})))
                self.assertIsNone(_validated_demo_hashes(raw.replace("600000", "1")))
                seed_browser_database(engine, demo_hashes_json=raw)
            with Session(engine) as session:
                accounts = session.scalars(select(UserAccount)).all()
                self.assertEqual({a.username: a.password_hash for a in accounts}, hashes)
                self.assertTrue(all(verify_password(BROWSER_PASSWORD, a.password_hash) for a in accounts))
            with patch("backend.main.engine", engine):
                token = await self.login("clinician")
                status, account = await self.request("GET", "/auth/me", token)
                self.assertEqual(status, 200)
                self.assertEqual(account["staff_role"], "clinician")
                status, _ = await self.request("POST", "/auth/login", data={
                    "username": "clinician", "password": "Wrong fictional password",
                })
                self.assertEqual(status, 401)
        finally:
            engine.dispose()

    async def test_browser_verifier_uses_same_digest_and_rejects_wrong_identity(self):
        engine = create_browser_engine()
        try:
            seed_browser_database(engine)
            async def native(raw, salt):
                return _derive_password(raw, salt)
            with Session(engine) as session:
                with self.assertRaises(RuntimeError):
                    await authenticate_browser_user(session, "admin", BROWSER_PASSWORD)
                with patch("backend.account_auth.sys.platform", "emscripten"), patch(
                    "backend.account_auth._derive_browser_password", side_effect=native
                ) as derive:
                    account = await authenticate_browser_user(session, " ADMIN ", BROWSER_PASSWORD)
                    self.assertEqual(account.staff_role, "admin")
                    self.assertIsNone(await authenticate_browser_user(session, "admin", "wrong password"))
                    self.assertIsNone(await authenticate_browser_user(session, "missing", BROWSER_PASSWORD))
                    self.assertFalse(await verify_browser_password(BROWSER_PASSWORD, "invalid"))
                    account.is_active = False
                    session.flush()
                    self.assertIsNone(await authenticate_browser_user(session, "admin", BROWSER_PASSWORD))
                    self.assertEqual(derive.await_count, 2)
        finally:
            engine.dispose()
