"""Configuration regressions for local and hosted synthetic instances."""
import unittest

from sqlalchemy.engine import make_url

from backend.settings import build_database_url, cors_origins


class SettingsTests(unittest.TestCase):
    def test_defaults_and_password_escaping(self):
        env = {
            "POSTGRES_USER": "synthetic",
            "POSTGRES_PASSWORD": "a@b:%/c",
            "POSTGRES_DB": "demo",
        }
        url = build_database_url(env)
        self.assertEqual(url.host, "localhost")
        self.assertEqual(url.port, 5432)
        self.assertEqual(make_url(url.render_as_string(hide_password=False)).password,
                         env["POSTGRES_PASSWORD"])

    def test_hosted_settings(self):
        url = build_database_url({
            "POSTGRES_USER": "synthetic", "POSTGRES_PASSWORD": "local-only",
            "POSTGRES_DB": "demo", "POSTGRES_HOST": "db.example.test",
            "POSTGRES_PORT": "6432", "POSTGRES_SSLMODE": "verify-full",
        })
        self.assertEqual(url.host, "db.example.test")
        self.assertEqual(url.port, 6432)
        self.assertEqual(url.query["sslmode"], "verify-full")

    def test_invalid_database_settings(self):
        env = {"POSTGRES_USER": "u", "POSTGRES_PASSWORD": "p", "POSTGRES_DB": "d"}
        for extra in ({"POSTGRES_PORT": "0"}, {"POSTGRES_PORT": "abc"},
                      {"POSTGRES_SSLMODE": "invalid"}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                build_database_url({**env, **extra})

    def test_cors_defaults_and_explicit_origins(self):
        self.assertEqual(cors_origins({}), [
            "http://localhost:5173", "http://127.0.0.1:5173"
        ])
        self.assertEqual(cors_origins({"EMR_CORS_ORIGINS": ""}), [])
        self.assertEqual(cors_origins({
            "EMR_CORS_ORIGINS": " https://app.example.test/, https://app.example.test "
        }), ["https://app.example.test"])

    def test_reject_wildcards_credentials_and_paths(self):
        for origin in ("*", "https://*.example.test", "https://u:p@example.test",
                       "https://example.test/path", "https://example.test?x=1",
                       "https://example.test:99999", "file:///tmp/demo"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                cors_origins({"EMR_CORS_ORIGINS": origin})
