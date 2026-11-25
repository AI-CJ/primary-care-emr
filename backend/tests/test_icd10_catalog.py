"""Catalog selection and search tests using an explicitly isolated fixture."""
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from backend.icd10_catalog import DiagnosisCode, lookup_code, search_codes, search_index


class DiagnosisCatalogTests(unittest.TestCase):
    def setUp(self):
        self.fixture = {
            "I10": DiagnosisCode("I10", "Essential (primary) hypertension"),
            "E119": DiagnosisCode("E11.9", "Type 2 diabetes mellitus without complications"),
            "E785": DiagnosisCode("E78.5", "Hyperlipidemia, unspecified"),
        }
        self.catalog = patch("backend.icd10_catalog.load_catalog", return_value=self.fixture)
        self.catalog.start()
        search_index.cache_clear()
        self.addCleanup(self.catalog.stop)
        self.addCleanup(search_index.cache_clear)

    def test_name_and_code_queries(self):
        self.assertEqual(search_codes("hypertension")[0].code, "I10")
        self.assertEqual(search_codes("E11.9")[0].code, "E11.9")
        self.assertEqual(search_codes("e119")[0].code, "E11.9")
        self.assertEqual(search_codes("type diabetes")[0].code, "E11.9")
        self.assertEqual(search_codes("zzzz"), [])
        self.assertEqual(search_codes("I"), [])

    def test_exact_code_validation(self):
        self.assertEqual(lookup_code("e785").code, "E78.5")
        for invalid in ("E11", "E.11.9", "Q99ZZZZ", "I10."):
            with self.assertRaises(HTTPException) as error:
                lookup_code(invalid)
            self.assertEqual(error.exception.status_code, 422)
