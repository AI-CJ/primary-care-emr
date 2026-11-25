"""Offline regressions for the dependency inventory and advisory gate."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.audit_python_dependencies import assess_report, browser_inventory, pinned_requirements


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
