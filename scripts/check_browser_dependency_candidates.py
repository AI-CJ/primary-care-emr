"""Collect upstream wheel evidence for the reported browser advisory fixes.

This is an inventory-only diagnostic. It never installs a package, changes the
runtime lock, suppresses an advisory, or makes a release gate pass.
"""
import json
from pathlib import Path
from urllib.request import urlopen

CANDIDATES = {
    "anyio": "4.14.2",
    "starlette": "1.3.1",
    "cryptography": "50.0.0",
    "fastapi": "0.136.1",
}


def main() -> None:
    destination = Path("/tmp/emr-python-review")
    destination.mkdir(parents=True, exist_ok=True)
    report = {}
    for package, version in CANDIDATES.items():
        with urlopen(f"https://pypi.org/pypi/{package}/{version}/json", timeout=30) as response:
            data = json.load(response)
        info = data["info"]
        if info["name"].lower() != package or info["version"] != version:
            raise ValueError(f"Unexpected registry identity for {package}")
        wheels = [
            {"filename": item["filename"], "sha256": item["digests"]["sha256"],
             "url": item["url"], "requires_python": item.get("requires_python"),
             "yanked": item["yanked"]}
            for item in data["urls"] if item["packagetype"] == "bdist_wheel"
        ]
        compatible = [item for item in wheels if not item["yanked"] and (
            item["filename"].endswith("-none-any.whl")
            or "pyemscripten_2026_0_wasm32.whl" in item["filename"]
        )]
        report[package] = {
            "version": version, "requires_python": info.get("requires_python"),
            "requires_dist": info.get("requires_dist") or [],
            "candidate_wheels": compatible, "other_wheel_count": len(wheels) - len(compatible),
        }
        print(f"{package}=={version}: {len(compatible)} candidate pure-Python or matching ABI wheels")
    (destination / "browser-fix-candidates.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
