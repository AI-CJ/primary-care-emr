"""Offline regressions for the dependency inventory and advisory gate."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.audit_python_dependencies import assess_report, browser_inventory, pinned_requirements
from scripts.build_browser_runtime import PACKAGES, WHEEL_OVERRIDES, effective_runtime_lock


class PythonDependencyAuditTests(unittest.TestCase):
    def test_browser_closure_includes_transitive_wheels_and_runtime_modules(self):
        digest = "a" * 64
        lock = {"packages": {
            "root": {"file_name": "root-1.0-py3-none-any.whl", "version": "1.0", "sha256": digest,
                     "depends": ["dep", "sqlite3"]},
            "dep": {"file_name": "my_dep-2.0-py3-none-any.whl", "version": "2.0", "sha256": digest,
                    "depends": ["sqlite3"]},
            "sqlite3": {"file_name": "sqlite3.zip", "version": "3.0", "sha256": digest},
            "unrelated": {"file_name": "unrelated.whl", "version": "1", "sha256": digest},
        }}
        records = browser_inventory(lock, roots=("root",))
        self.assertEqual([r["lock_key"] for r in records], ["dep", "root", "sqlite3"])
        self.assertEqual(records[0]["name"], "my-dep")
        self.assertFalse(records[-1]["pypi_wheel"])
        lock["packages"]["dep"]["sha256"] = ""
        with self.assertRaises(ValueError):
            browser_inventory(lock, roots=("root",))

    def test_effective_lock_replaces_wheel_bytes_and_expands_real_dependency_closure(self):
        digest = "a" * 64
        upstream = {"packages": {
            "anyio": {"version": "4.13.0", "file_name": "anyio-old.whl", "sha256": digest,
                      "depends": ["sniffio"]},
            "starlette": {"version": "1.0.0", "file_name": "starlette-old.whl", "sha256": digest},
            "idna": {"version": "3.11", "file_name": "idna-3.11-py3-none-any.whl", "sha256": digest},
            "sniffio": {"version": "1.3.1", "file_name": "sniffio-1.3.1-py3-none-any.whl", "sha256": digest},
        }}
        effective = effective_runtime_lock(upstream)
        self.assertEqual(upstream["packages"]["anyio"]["version"], "4.13.0")
        for name, override in WHEEL_OVERRIDES.items():
            for field in ("version", "file_name", "sha256"):
                self.assertEqual(effective["packages"][name][field], override[field])
        records = browser_inventory(effective, roots=("starlette",))
        self.assertEqual({row["lock_key"] for row in records}, {"starlette", "anyio", "idna", "sniffio"})
        self.assertNotIn("cryptography", PACKAGES)
        upstream["packages"]["starlette"]["version"] = "1.3.1"
        with self.assertRaises(ValueError):
            effective_runtime_lock(upstream)

    def test_scan_must_cover_every_exact_pin_and_report_no_advisories(self):
        pins = {"my-dep": "1.0"}
        clean = {"dependencies": [{"name": "my_dep", "version": "1.0", "vulns": []}]}
        self.assertEqual(assess_report(clean, pins), [])
        for result in (
            {"dependencies": []},
            {"dependencies": [{"name": "my-dep", "skip_reason": "not found"}]},
            {"dependencies": [{"name": "my-dep", "version": "2.0", "vulns": []}]},
            {"dependencies": [{"name": "my-dep", "version": "1.0",
                               "vulns": [{"id": "EXAMPLE", "fix_versions": ["2.0"]}]}]},
        ):
            self.assertTrue(assess_report(result, pins))

    def test_rejects_unpinned_and_duplicate_requirements(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "requirements.txt"
            path.write_text("My_Dep==1.0\n", encoding="utf-8")
            self.assertEqual(pinned_requirements(path), {"my-dep": "1.0"})
            for text in ("My_Dep>=1.0\n", "My_Dep==1.0\nmy-dep==2.0\n", ""):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    pinned_requirements(path)


if __name__ == "__main__":
    unittest.main()
