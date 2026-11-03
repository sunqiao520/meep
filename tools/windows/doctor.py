"""Validate and record the environment needed to reproduce this Windows build."""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sys

from environment import ROOT, DEPENDENCIES, find_mkl, mkl_version, msvc_environment, find_visual_studio, runtime_dir

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ROOT / "build/windows/environment-report.json")
args = parser.parse_args()
errors = []
if os.name != "nt" or sys.version_info[:2] != (3, 12) or sys.maxsize <= 2**32:
    errors.append("Use standard Windows CPython 3.12 x64.")
if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
    errors.append("Run doctor with .venv/Scripts/python.exe.")
packages = {}
for line in (ROOT / "requirements-windows.lock.txt").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    name, expected = line.split("==")
    try:
        actual = metadata.version(name)
    except metadata.PackageNotFoundError:
        actual = "MISSING"
    packages[name] = actual
    if actual != expected:
        errors.append(f"{name}: expected {expected}, found {actual}")
for legacy in ("mkl", "mkl-devel", "mkl-include", "onemkl-license"):
    try:
        metadata.version(legacy)
        errors.append(f"Legacy pip package {legacy} remains; rerun setup.ps1.")
    except metadata.PackageNotFoundError:
        pass
report = {"schema": 1, "platform": platform.platform(), "python": sys.version,
          "pythonExecutable": sys.executable, "packages": packages}
try:
    sdk = find_mkl()
    runtime = runtime_dir(sdk)
    hashes = {}
    for file in (sdk / "include/mkl_version.h", sdk / "lib/cmake/mkl/MKLConfig.cmake",
                 runtime / "mkl_core.2.dll", runtime / "mkl_sequential.2.dll"):
        hashes[file.relative_to(sdk).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    report["oneMKL"] = {"root": str(sdk), "version": mkl_version(sdk),
                        "runtime": str(runtime), "sha256": hashes}
    print(f"[OK] Standalone oneMKL {mkl_version(sdk)}: {sdk}")
    installation = find_visual_studio()
    environment = msvc_environment()
    report["visualStudio"] = {"path": installation["installationPath"],
                             "version": installation["installationVersion"],
                             "toolset": environment.get("VCTOOLSVERSION"),
                             "windowsSdk": environment.get("WINDOWSSDKVERSION", "").rstrip("\\"),
                             "compiler": shutil.which("cl.exe", path=environment.get("PATH"))}
    print(f"[OK] VS2022 toolset {environment.get('VCTOOLSVERSION')}; SDK {report['visualStudio']['windowsSdk']}")
except (FileNotFoundError, ValueError) as error:
    errors.append(str(error))
for module in ("numpy", "scipy", "h5py", "matplotlib"):
    try:
        __import__(module)
    except Exception as error:
        errors.append(f"Cannot import {module}: {error}")
report["requirementsSha256"] = hashlib.sha256((ROOT / "requirements-windows.lock.txt").read_bytes()).hexdigest()
report["dependencyPolicy"] = DEPENDENCIES
report["errors"] = errors
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
for error in errors:
    print(f"[ERROR] {error}")
print(f"Environment report: {args.output}")
if not errors:
    print("[OK] Pinned Python dependencies and standalone SDK are ready.")
raise SystemExit(1 if errors else 0)
