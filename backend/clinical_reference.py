"""Locally hosted, versioned clinical terminology; no external patient queries."""
from functools import lru_cache
from heapq import nsmallest
import json
from pathlib import Path
import re

from fastapi import HTTPException

DATA = Path(__file__).resolve().parent / "data"
CATALOGS = {"rxnorm", "cvx", "mvx"}


@lru_cache(maxsize=3)
def load_reference(kind: str):
    if kind not in CATALOGS:
        raise ValueError("Unsupported reference")
    try:
        document = json.loads((DATA / (kind + ".json")).read_text(encoding="utf-8"))
        release = document["release"]
        if not release or not document["source_sha256"]:
            raise ValueError("Missing reference provenance")
        records = {item["code"]: item for item in document["rows"]}
        if len(records) != len(document["rows"]) or not records:
            raise ValueError("Invalid reference contents")
        return release, records
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, detail="The clinical reference is unavailable. Try again or prepare the local catalog.") from None


def reference_code(kind: str, code: str):
    release, records = load_reference(kind)
    item = records.get(code.strip().upper())
    if item is None:
        raise HTTPException(422, detail="Select a valid code from the clinical reference.")
    return release, item


def reference_search(kind: str, query: str):
    release, records = load_reference(kind)
    normalized = query.strip().casefold()
    words = re.findall(r"[a-z0-9]+", normalized)
    if len(normalized) < 2 or not words:
        return {"release": release, "results": []}

    def candidates():
        for item in records.values():
            code, title = item["code"], item["name"].casefold()
            alias = item.get("short_name", "").casefold()
            text = title + " " + alias
            if code.casefold() == normalized:
                rank = 0
            elif normalized in (title, alias):
                rank = 1
            elif title.startswith(normalized) or alias.startswith(normalized):
                rank = 2
            elif all(word in text for word in words):
                rank = 3
            elif code.casefold().startswith(normalized):
                rank = 4
            else:
                continue
            yield rank, len(title), code, item

    return {"release": release, "results": [
        row[3] for row in nsmallest(20, candidates(), key=lambda row: row[:3])
    ]}


def medication_values(payload, existing=None):
    """Require a selected RxCUI to match the documented medication name.

    Older records stay uncoded until explicitly reconciled. An existing code
    survives ordinary edits and does not require a current catalog match.
    """
    values = payload.model_dump(exclude={"problem_ids", "rxnorm_cui"})
    if existing is not None:
        if "rxnorm_cui" not in payload.model_fields_set:
            if existing.rxnorm_cui and payload.name != existing.name:
                raise HTTPException(422, detail="Reconcile the medication code before changing its name.")
            return values
        if payload.rxnorm_cui == existing.rxnorm_cui and payload.name == existing.name:
            return values
    if payload.rxnorm_cui is None:
        return dict(values, rxnorm_cui=None, rxnorm_release=None, rxnorm_kind=None)
    release, item = reference_code("rxnorm", payload.rxnorm_cui)
    if item["name"].casefold() != payload.name.casefold():
        raise HTTPException(422, detail="Medication name must match the selected RxNorm concept.")
    return dict(values, name=item["name"], rxnorm_cui=item["code"],
                rxnorm_release=release, rxnorm_kind=item["kind"])
