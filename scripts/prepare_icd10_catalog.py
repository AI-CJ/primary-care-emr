"""Build the local diagnosis catalog from the official FY 2027 release archive."""
import argparse
import hashlib
import os
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
    "https://ftp.cdc.gov/pub/health_statistics/nchs/publications/ICD10CM/2027/icd10cm-code-descriptions-2027.zip",
)
CODE = re.compile(r"[A-Z][A-Z0-9]{2,6}")


def parse_archive(content: bytes) -> dict[str, str]:
    with ZipFile(BytesIO(content)) as archive:
        matches = [name for name in archive.namelist()
                   if re.fullmatch(r"icd10cm[-_]codes[-_]2027\.txt", Path(name).name, re.I)]
        orders = [name for name in archive.namelist()
                  if re.fullmatch(r"icd10cm[-_]order[-_]2027\.txt", Path(name).name, re.I)]
        candidates = []
        if len(orders) == 1:
            lines = archive.read(orders[0]).decode("utf-8-sig").splitlines()
            candidates.append((orders[0], [(line[6:13].strip(), line[77:].strip())
                                          for line in lines if len(line) > 77 and line[14] == "1"]))
        if len(matches) == 1:
            lines = archive.read(matches[0]).decode("utf-8-sig").splitlines()
            candidates.append((matches[0], [line.split(maxsplit=1) for line in lines if line.strip()]))
        errors = []
        for filename, pairs in candidates:
            records = {}
            invalid = 0
            examples = []
            for pair in pairs:
                if len(pair) != 2:
                    invalid += 1
                    continue
                code, title = pair
                title = " ".join(title.split())
                if not CODE.fullmatch(code) or not title or code in records:
                    invalid += 1
                    if len(examples) < 3:
                        examples.append(code)
                    continue
                records[code] = title
            print(f"{Path(filename).name}: {len(records)} structurally valid, {invalid} invalid; examples {examples}", flush=True)
            if invalid or not 65_000 <= len(records) <= 100_000:
                errors.append(f"{Path(filename).name}: {len(records)} valid and {invalid} invalid entries")
                continue
            if not {"I10", "E119", "E785", "Z0000", "Z130", "QA00101"} <= records.keys():
                errors.append(f"{Path(filename).name}: expected reference diagnoses missing")
                continue
            return records
        raise ValueError("No complete FY 2027 description file passed validation; " +
                         ("; ".join(errors) or "members: " + ", ".join(archive.namelist()[:20])))


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
                    if os.environ.get('EMR_ICD10_SOURCE_DIR'):
                        directory = Path(os.environ['EMR_ICD10_SOURCE_DIR'])
                        directory.mkdir(parents=True, exist_ok=True)
                        (directory / ('source-' + hashlib.sha256(content).hexdigest()[:16] + '.zip')).write_bytes(content)
                    candidates.append((url, content))
                    break
                except (OSError, ValueError) as error:
                    print(f"Download from {url} failed: {type(error).__name__}: {error}", flush=True)
                    if attempt == 0:
                        time.sleep(2)
            if candidates:
                try:
                    parse_archive(candidates[-1][1])
                    break
                except (ValueError, BadZipFile, UnicodeError) as error:
                    print(f"Archive from {url} rejected: {type(error).__name__}: {error}", flush=True)
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
