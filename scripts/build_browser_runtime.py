"""Prepare a pinned, self-hosted Python runtime and the current API source for Pages."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "public" / "runtime"
VERSION = "314.0.8"
CDN = f"https://cdn.jsdelivr.net/pyodide/v{VERSION}/full/"
CORE = (
    "pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm",
    "python_stdlib.zip", "pyodide-lock.json",
)
PACKAGES = ("fastapi", "sqlalchemy", "cryptography")


def download(name: str, sha256: str | None = None) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.+!-]+", name) or name in (".", ".."):
        raise ValueError(f"Unexpected runtime filename: {name}")
    for attempt in range(3):
        try:
            with urlopen(CDN + name, timeout=90) as response:
                content = response.read()
            if sha256 and hashlib.sha256(content).hexdigest() != sha256:
                raise ValueError(f"Runtime package checksum failed: {name}")
            (OUTPUT / name).write_bytes(content)
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main() -> None:
    subprocess.run([sys.executable, '-m', 'scripts.prepare_icd10_catalog'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, '-m', 'scripts.prepare_medication_vaccine_catalogs'], cwd=ROOT, check=True)
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(download, CORE))
    lock = json.loads((OUTPUT / "pyodide-lock.json").read_text())
    packages = lock["packages"]
    resolved: dict[str, dict] = {}

    def include(name: str) -> None:
        key = name.lower().replace("_", "-")
        if key in resolved:
            return
        package = packages.get(key) or packages.get(name)
        if package is None:
            raise KeyError(f"Missing runtime dependency: {name}")
        resolved[key] = package
        for dependency in package.get("depends", []):
            include(dependency)

    for name in PACKAGES:
        include(name)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda package: download(package["file_name"], package.get("sha256")),
                      resolved.values()))
    with ZipFile(OUTPUT / "backend.zip", "w", ZIP_DEFLATED) as archive:
        archive.writestr("backend/__init__.py", "")
        archive.write(ROOT / "backend/data/icd10cm-fy2027.tsv", "backend/data/icd10cm-fy2027.tsv")
        archive.write(ROOT / "backend/data/seed-reference.json", "backend/data/seed-reference.json")
        for source in sorted((ROOT / "backend").glob("*.py")):
            if source.name not in {"__init__.py", "seed.py", "bootstrap_staff.py", "bootstrap_patient.py"}:
                archive.write(source, f"backend/{source.name}")
    # Do not put the larger clinical vocabulary on the login critical path.
    for name in ("rxnorm", "cvx", "mvx"):
        with ZipFile(OUTPUT / (name + ".zip"), "w", ZIP_DEFLATED) as archive:
            archive.write(ROOT / "backend/data" / (name + ".json"), "backend/data/" + name + ".json")
    core_size = sum((OUTPUT / name).stat().st_size for name in CORE)
    package_size = sum((OUTPUT / package["file_name"]).stat().st_size
                       for package in resolved.values())
    archive_size = (OUTPUT / "backend.zip").stat().st_size
    catalog_size = (ROOT / "backend/data/icd10cm-fy2027.tsv").stat().st_size
    print(f"Runtime breakdown: core {core_size} bytes; wheels {package_size} bytes; "
          f"backend archive {archive_size} bytes; unpacked catalog {catalog_size} bytes.")
    deferred = sum((OUTPUT / (name + ".zip")).stat().st_size for name in ("rxnorm", "cvx", "mvx"))
    print(f"Deferred terminology assets: {deferred} bytes; excluded from initial workspace load.")
    size = sum(path.stat().st_size for path in OUTPUT.iterdir())
    print(f"Prepared {len(resolved)} pinned packages; runtime size {size / 1024 / 1024:.1f} MiB.")


if __name__ == "__main__":
    main()
