"""Local, versioned ICD-10-CM diagnosis descriptions.

Only complete, reportable diagnosis codes are indexed. Search is a reference
lookup, not a diagnosis or a coding-guideline validator.
"""
from functools import lru_cache
from pathlib import Path
import re
from hashlib import sha256
from heapq import nsmallest
from typing import NamedTuple

from fastapi import HTTPException

RELEASE = "FY2027"
EFFECTIVE_FROM = "2026-10-01"
EFFECTIVE_THROUGH = "2027-09-30"
CATALOG_PATH = Path(__file__).resolve().parent / "data" / "icd10cm-fy2027.tsv"
CODE_PATTERN = re.compile(r"[A-Z][A-Z0-9]{2,6}")
CATALOG_SHA256 = "623c7f250b800aa44e5c34efd7c37f168ceb2c41f33a8de11f9a9b4b6115e353"


class DiagnosisCode(NamedTuple):
    code: str
    title: str


def normalize_code(value: str) -> str:
    return value.strip().upper().replace(".", "")


def display_code(code: str) -> str:
    return code[:3] + "." + code[3:] if len(code) > 3 else code


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, DiagnosisCode]:
    try:
        data = CATALOG_PATH.read_bytes()
        if sha256(data).hexdigest() != CATALOG_SHA256:
            raise ValueError("Catalog checksum mismatch")
        records = {}
        for line in data.decode("utf-8").splitlines():
            code, title = line.split("\t", 1)
            if not CODE_PATTERN.fullmatch(code) or not title or code in records:
                raise ValueError("Invalid diagnosis catalog entry")
            records[code] = DiagnosisCode(display_code(code), title)
        if len(records) != 74879 or not {"I10", "E119", "Z0000", "QA00101"} <= records.keys():
            raise ValueError("Incomplete diagnosis catalog")
        return records
    except (OSError, ValueError):
        raise HTTPException(status_code=503, detail="The diagnosis catalog is unavailable.") from None


def lookup_code(value: str) -> DiagnosisCode:
    raw = value.strip().upper()
    code = normalize_code(raw)
    if raw not in (code, display_code(code)) or not CODE_PATTERN.fullmatch(code):
        raise HTTPException(status_code=422, detail="Enter a valid ICD-10-CM diagnosis code.")
    result = load_catalog().get(code)
    if result is None:
        raise HTTPException(status_code=422, detail="Select a complete code from the ICD-10-CM catalog.")
    return result


@lru_cache(maxsize=1)
def search_index() -> tuple[tuple[str, DiagnosisCode, str], ...]:
    return tuple((raw, item, " ".join(re.findall(r"[a-z0-9]+", item.title.casefold())))
                 for raw, item in load_catalog().items())


def search_codes(query: str, limit: int = 20) -> list[DiagnosisCode]:
    raw = normalize_code(query)
    words = re.findall(r"[a-z0-9]+", query.casefold())
    if len(query.strip()) < 2 or not words:
        return []
    limit = max(1, min(limit, 50))
    normalized = " ".join(words)

    def matches():
        for code, item, title in search_index():
            if code == raw:
                rank = 0
            elif code.startswith(raw):
                rank = 1
            elif title == normalized:
                rank = 2
            elif title.startswith(normalized):
                rank = 3
            elif all(word in title for word in words):
                rank = 4
            else:
                continue
            yield (rank, len(title), code, item)

    return [match[3] for match in nsmallest(limit, matches(), key=lambda match: match[:3])]
