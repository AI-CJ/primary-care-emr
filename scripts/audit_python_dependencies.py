"""Audit the exact server environment and the browser runtime's package closure.

Run with the isolated pip-audit environment. The browser's Pyodide/CPython,
non-wheel runtime modules and native libraries require separate review; this
script does not pretend that the PyPI advisory database covers those assets.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import urlopen

from scripts.build_browser_runtime import CDN, PACKAGES, VERSION


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def browser_inventory(lock: dict, roots=PACKAGES) -> list[dict]:
    packages = lock["packages"]
    resolved = {}

    def include(name):
        key = name.lower().replace("_", "-")
        if key in resolved:
            return
        item = packages.get(key) or packages.get(name)
        if item is None:
            raise ValueError(f"Missing browser dependency: {name}")
        filename = item["file_name"]
        digest = item.get("sha256", "")
        if not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            raise ValueError(f"Missing browser package digest: {name}")
        # Match the distributed wheel's actual Python distribution name.
        # Non-wheel modules belong to the runtime inventory, not PyPI.
        wheel = filename.endswith(".whl")
        distribution = normalize(filename.split("-", 1)[0]) if wheel else None
        resolved[key] = {
            "lock_key": key, "name": distribution, "version": item["version"],
            "file_name": filename, "sha256": digest, "pypi_wheel": wheel,
        }
        for dependency in item.get("depends", []):
            include(dependency)

    for name in roots:
        include(name)
    return sorted(resolved.values(), key=lambda row: row["lock_key"])


def pinned_requirements(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)", line)
        if not match:
            raise ValueError(f"Expected an exact package pin in {path.name}")
        name, version = match.groups()
        key = normalize(name)
        if key in result:
            raise ValueError(f"Duplicate dependency: {name}")
        result[key] = version
    if not result:
        raise ValueError(f"No dependencies in {path.name}")
    return result


def assess_report(report: dict, expected: dict[str, str]) -> list[str]:
    problems = []
    scanned = {}
    for item in report["dependencies"]:
        name = normalize(item["name"])
        if item.get("skip_reason"):
            problems.append(f"{name}: not audited ({item['skip_reason']})")
            continue
        if name in scanned:
            problems.append(f"{name}: duplicate audit result")
        scanned[name] = item["version"]
        for vulnerability in item["vulns"]:
            problems.append(f"{name} {item['version']}: {vulnerability['id']} "
                            f"fix versions={vulnerability.get('fix_versions', [])}")
    if scanned != expected:
        problems.append("Audit package/version coverage differs from the pinned inventory")
    return problems


def audit(path: Path, report_path: Path) -> bool:
    expected = pinned_requirements(path)
    result = subprocess.run([
        sys.executable, "-m", "pip_audit", "--no-deps", "--disable-pip",
        "--progress-spinner", "off", "--format", "json", "-r", str(path),
        "--output", str(report_path),
    ], check=False)
    try:
        problems = assess_report(json.loads(report_path.read_text(encoding="utf-8")), expected)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"{path.name}: no usable advisory report ({error})", flush=True)
        return False
    print(f"{path.name}: {len(expected)} pinned distributions; "
          f"{len(problems)} advisory or coverage findings", flush=True)
    for problem in problems:
        print(problem, flush=True)
    return result.returncode == 0 and not problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = args.output / "server-requirements.txt"
    server.write_bytes(args.server.read_bytes())
    # Audit server even if the browser lock cannot be obtained.
    server_ok = audit(server, args.output / "server-audit.json")
    with urlopen(CDN + "pyodide-lock.json", timeout=90) as response:
        lock = json.load(response)
    (args.output / "pyodide-lock.json").write_text(json.dumps(lock, indent=2), encoding="utf-8")
    inventory = browser_inventory(lock)
    (args.output / "browser-inventory.json").write_text(
        json.dumps({"pyodide_version": VERSION, "packages": inventory}, indent=2) + "\n",
        encoding="utf-8",
    )
    browser = args.output / "browser-requirements.txt"
    browser.write_text("".join(f"{row['name']}=={row['version']}\n"
                              for row in inventory if row["pypi_wheel"]), encoding="utf-8")
    for row in inventory:
        if not row["pypi_wheel"]:
            print(f"Runtime-only module (not covered by PyPI audit): {row['lock_key']} {row['version']}")
    browser_ok = audit(browser, args.output / "browser-audit.json")
    if not server_ok or not browser_ok:
        raise SystemExit("Python advisory gate failed; review the archived inventory and results.")
    print("No known PyPI advisories in the audited server and browser wheel inventories.")


if __name__ == "__main__":
    main()
