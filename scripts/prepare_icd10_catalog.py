"""Build the local diagnosis catalog from the official FY 2027 release archive."""
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen
from zipfile import ZipFile, BadZipFile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "backend/data/icd10cm-fy2027.tsv"
SOURCES = (
    "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2027/icd10cm-code-descriptions-2027.zip",
    "https://www.cms.gov/files/zip/2027-code-descriptions-tabular-order.zip",
)
CODE = re.compile(r"[A-Z][0-9][A-Z0-9]{1,5}")


def parse_archive(content: bytes) -> dict[str, str]:
    with ZipFile(BytesIO(content)) as archive:
        matches = [name for name in archive.namelist()
                   if re.fullmatch(r"icd10cm-codes-2027\.txt", Path(name).name, re.I)]
        if len(matches) == 1:
            lines = archive.read(matches[0]).decode("utf-8-sig").splitlines()
            pairs = [line.split(maxsplit=1) for line in lines if line.strip()]
        else:
            # The tabular order file marks reportable codes with a 1 in column 15.
            orders = [name for name in archive.namelist()
                      if re.fullmatch(r"icd10cm-order-2027\.txt", Path(name).name, re.I)]
            if len(orders) != 1:
                raise ValueError("Expected a FY 2027 ICD-10-CM descriptions file")
            pairs = [(line[6:13].strip(), line[77:].strip())
                     for line in archive.read(orders[0]).decode("utf-8-sig").splitlines()
                     if len(line) > 77 and line[14] == "1"]
    records = {}
    for code, title in pairs:
        title = " ".join(title.split())
        if not CODE.fullmatch(code) or not title or code in records:
            raise ValueError("Unexpected or duplicate code in official descriptions")
        records[code] = title
    if not 65_000 <= len(records) <= 100_000:
        raise ValueError(f"Unexpected number of reportable codes: {len(records)}")
    if not {"I10", "E119", "E785", "Z0000", "Z130"} <= records.keys():
        raise ValueError("Expected reference diagnoses are missing")
    return records


def prepare(archive_path: Path | None = None, force: bool = False) -> None:
    if OUTPUT.exists() and not force and archive_path is None:
        print("Existing FY 2027 diagnosis catalog retained.")
        return
    candidates = [(str(archive_path), archive_path.read_bytes())] if archive_path else []
    if not candidates:
        for url in SOURCES:
            for attempt in range(2):
                try:
                    with urlopen(Request(url, headers={"User-Agent": "PrimaryCareEMR/1.0"}), timeout=60) as response:
                        content = response.read(12_000_001)
                    if len(content) > 12_000_000:
                        raise ValueError("Description archive exceeds expected size")
                    candidates.append((url, content))
                    break
                except (OSError, ValueError):
                    if attempt == 0:
                        time.sleep(2)
            if candidates:
                try:
                    parse_archive(candidates[-1][1])
                    break
                except (ValueError, BadZipFile, UnicodeError):
                    candidates.clear()
    if not candidates:
        raise RuntimeError("Could not retrieve the official FY 2027 diagnosis archive")
    source, content = candidates[-1]
    records = parse_archive(content)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text("".join(f"{code}\t{records[code]}\n" for code in sorted(records)), encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"ICD-10-CM FY2027: {len(records)} reportable codes from {source}")
    print(f"Source SHA-256: {hashlib.sha256(content).hexdigest()}")
    print(f"Catalog SHA-256: {hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use an official locally downloaded archive")
    parser.add_argument("--force", action="store_true", help="Replace the existing generated catalog")
    args = parser.parse_args()
    prepare(args.archive, args.force)
