"""Prepare a pinned, self-hosted Python runtime and the current API source for Pages."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
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
PACKAGES = ("fastapi", "sqlalchemy")

# Reviewed upstream pure-Python wheels, from the PyPI release inventory
# archived by Checks 45605761646. Keep the upstream ABI/runtime pinned.
# The build and advisory scanner use the same effective lock.
WHEEL_OVERRIDES = {
    "anyio": {
        "upstream_version": "4.13.0",
        "version": "4.14.2",
        "file_name": "anyio-4.14.2-py3-none-any.whl",
        "sha256": "9f505dda5ac9f0c8309b5e8bd445a8c2bf7246f3ce950121e45ea15bc41d1494",
        "url": "https://files.pythonhosted.org/packages/da/35/f2287558c17e29fafc8ef3daf819bb9834061cfa43bff8014f7df7f63bdc/anyio-4.14.2-py3-none-any.whl",
        # Retain the upstream closure and add the unconditional idna requirement.
        "additional_dependencies": ["idna"],
    },
    "idna": {
        "upstream_version": "3.11",
        "version": "3.20",
        "file_name": "idna-3.20-py3-none-any.whl",
        "sha256": "ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c",
        "url": "https://files.pythonhosted.org/packages/58/a2/bb081bab032533a855d44de1d56f8e8426114ff1ba5d1f07a438a0a654f8/idna-3.20-py3-none-any.whl",
        "additional_dependencies": [],
    },
    "starlette": {
        "upstream_version": "1.0.0",
        "version": "1.3.1",
        "file_name": "starlette-1.3.1-py3-none-any.whl",
        "sha256": "c7372aae11c3c3f26a42df7bd626cec2f47d03483d261d369516a615a53714c6",
        "url": "https://files.pythonhosted.org/packages/ec/bb/2799cc2ede3ed41131f8975621e7213dfc7ef4acbbaadfa440f32500c370/starlette-1.3.1-py3-none-any.whl",
        "additional_dependencies": ["anyio"],
    },
}


def effective_runtime_lock(upstream: dict) -> dict:
    lock = deepcopy(upstream)
    packages = lock["packages"]
    for name, override in WHEEL_OVERRIDES.items():
        item = packages[name]
        if item["version"] != override["upstream_version"]:
            raise ValueError(f"Review the browser override against the new upstream lock: {name}")
        if not override["file_name"].endswith("-py3-none-any.whl"):
            raise ValueError(f"Only reviewed pure-Python wheel overrides are supported: {name}")
        item.update({key: override[key] for key in ("version", "file_name", "sha256")})
        item["depends"] = sorted(set(item.get("depends", [])) | set(override["additional_dependencies"]))
        if any(dependency not in packages for dependency in item["depends"]):
            raise ValueError(f"Missing dependency in effective browser lock: {name}")
    return lock


def download(name: str, sha256: str | None = None, source: str | None = None) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.+!-]+", name) or name in (".", ".."):
        raise ValueError(f"Unexpected runtime filename: {name}")
    for attempt in range(3):
        try:
            with urlopen(source or CDN + name, timeout=90) as response:
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
    lock_path = OUTPUT / "pyodide-lock.json"
    lock = effective_runtime_lock(json.loads(lock_path.read_text()))
    lock_path.write_text(json.dumps(lock, separators=(",", ":")), encoding="utf-8")
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
    def download_package(entry: tuple[str, dict]) -> None:
        key, package = entry
        source = WHEEL_OVERRIDES.get(key, {}).get("url")
        digest = package.get("sha256")
        if not digest or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            raise ValueError(f"Missing runtime wheel checksum: {key}")
        download(package["file_name"], digest, source)

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(download_package, resolved.items()))
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
