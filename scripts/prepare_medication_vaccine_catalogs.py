"""Import official US medication and vaccine reference vocabularies.

Only unrestricted, normalized RxNorm terms are retained. CVX includes historical
formulations; non-vaccine passive agents and never-active/pending codes are
excluded from the vaccine selection list. No patient data is involved.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backend" / "data"
RX_RELEASE = "2026-11-02"
RX_URL = "https://download.nlm.nih.gov/rxnorm/RxNorm_full_prescribe_11022026.zip"
RX_MD5 = "cd240fc9655dcd2cb54b1e185f3d8702"
CVX_URL = "https://www2.cdc.gov/vaccines/iis/iisstandards/downloads/CVX.txt"
TERM_TYPES = {"IN", "PIN", "MIN", "SCD", "SBD", "BN", "GPCK", "BPCK"}


def download(url, path):
    with urlopen(Request(url, headers={"User-Agent": "PrimaryCareEMR reference importer"}), timeout=120) as response:
        data = response.read()
    path.write_bytes(data)


def rxnorm_rows(path):
    if hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest() != RX_MD5:
        raise ValueError("RxNorm archive differs from NLM's published November release checksum")
    rows = {}
    with ZipFile(path) as archive:
        files = [name for name in archive.namelist() if name.endswith("/RXNCONSO.RRF") or name == "RXNCONSO.RRF"]
        if len(files) != 1:
            raise ValueError("Expected one RxNorm concept file")
        with archive.open(files[0]) as source:
            for raw in source:
                fields = raw.decode("utf-8").rstrip("\r\n").split("|")
                if len(fields) < 18:
                    raise ValueError("Malformed RxNorm concept record")
                code, term_type, title = fields[0], fields[12], fields[14]
                if fields[11] != "RXNORM" or fields[16] != "N" or term_type not in TERM_TYPES:
                    continue
                # Existing chart name limits apply; never silently truncate a drug name.
                if not code.isdigit() or not title or len(title) > 200:
                    continue
                entry = {"code": code, "name": title, "kind": term_type}
                if code in rows and rows[code] != entry:
                    raise ValueError("Ambiguous normalized RxNorm concept")
                rows[code] = entry
    if len(rows) < 10000 or not any(x["kind"] == "SCD" for x in rows.values()):
        raise ValueError("RxNorm import unexpectedly incomplete")
    return sorted(rows.values(), key=lambda row: int(row["code"]))


def cvx_rows(path):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    rows = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = [field.strip() for field in line.split("|")]
        if len(fields) != 7:
            raise ValueError("Malformed CDC CVX row")
        code, short, title, _, status, nonvaccine, updated = fields
        if not re.fullmatch(r"\d{1,3}", code) or not short or not title:
            raise ValueError("Invalid CVX identifier or name")
        if nonvaccine.casefold() == "true" or status not in ("Active", "Inactive", "Non-US"):
            continue
        if code in rows:
            raise ValueError("Duplicate CVX code")
        rows[code] = {"code": code, "name": title, "short_name": short, "kind": status, "updated": updated}
    if len(rows) < 150 or not {"03", "88", "115", "187", "216", "213"} <= rows.keys():
        raise ValueError("CDC CVX import unexpectedly incomplete")
    return sorted(rows.values(), key=lambda row: int(row["code"]))


def write_catalog(name, release, rows, source, url):
    payload = {"release": release, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "source_url": url, "rows": rows}
    target = DATA / (name + ".json")
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(f"{name}: {len(rows)} concepts; {target.stat().st_size} bytes; source sha256 {payload['source_sha256']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rxnorm", type=Path)
    parser.add_argument("--cvx", type=Path)
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    evidence = Path(os.environ.get("EMR_TERMINOLOGY_SOURCE_DIR", str(DATA / "terminology-sources")))
    evidence.mkdir(parents=True, exist_ok=True)
    rx = args.rxnorm or evidence / "RxNorm_full_prescribe_11022026.zip"
    cvx = args.cvx or evidence / "CVX.txt"
    if not rx.exists():
        download(RX_URL, rx)
    if not cvx.exists():
        download(CVX_URL, cvx)
    write_catalog("rxnorm", RX_RELEASE, rxnorm_rows(rx), rx, RX_URL)
    vaccines = cvx_rows(cvx)
    digest = hashlib.sha256(cvx.read_bytes()).hexdigest()
    # The CDC live flat file changes over time. Record its exact content digest
    # as the release identity; retain the original file for reproducibility.
    write_catalog("cvx", "CDC-" + digest[:16], vaccines, cvx, CVX_URL)


if __name__ == "__main__":
    main()
