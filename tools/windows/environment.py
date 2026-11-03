"""Shared discovery for the standalone SDK and the Windows development tools."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DEPENDENCIES = json.loads((ROOT / "tools/windows/dependencies.json").read_text(encoding="utf-8"))
LOCAL_CONFIG = ROOT / "windows.local.json"


def local_config() -> dict:
    return json.loads(LOCAL_CONFIG.read_text(encoding="utf-8")) if LOCAL_CONFIG.exists() else {}


def mkl_version(root: Path) -> str:
    header = (root / "include/mkl_version.h").read_text(encoding="utf-8")
    value = int(re.search(r"^#define\s+INTEL_MKL_VERSION\s+(\d+)", header, re.MULTILINE)[1])
    return f"{value // 10000}.{value // 100 % 100}.{value % 100}"


def validate_mkl(root: Path) -> Path:
    root = root.expanduser().resolve()
    if any(part.lower() in {".venv", ".venv-wheel", "site-packages"} for part in root.parts):
        raise ValueError(f"Use the standalone Intel oneMKL SDK, not a Python package: {root}")
    for relative in ("include/mkl.h", "include/fftw/fftw3.h", "lib/cmake/mkl/MKLConfig.cmake"):
        if not (root / relative).is_file():
            raise ValueError(f"Incomplete oneMKL SDK: {root / relative}")
    expected = DEPENDENCIES["oneMKL"]["version"]
    actual = mkl_version(root)
    if actual != expected:
        raise ValueError(f"Expected oneMKL {expected}, found {actual} at {root}")
    return root


def find_mkl(explicit: str | Path | None = None) -> Path:
    selected = explicit or os.environ.get("MKLROOT") or local_config().get("mklRoot")
    if selected:
        return validate_mkl(Path(selected))
    version = DEPENDENCIES["oneMKL"]["directoryVersion"]
    for program_files in (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                          os.environ.get("ProgramFiles", r"C:\Program Files")):
        for name in (version, DEPENDENCIES["oneMKL"]["version"], "latest"):
            candidate = Path(program_files) / "Intel/oneAPI/mkl" / name
            if (candidate / "include/mkl_version.h").exists():
                try:
                    return validate_mkl(candidate)
                except ValueError:
                    continue
    raise FileNotFoundError(
        "Standalone Intel oneMKL 2025.3.0 was not found. Install it, then run "
        "tools/windows/setup.ps1 -MklRoot '<oneAPI>/mkl/2025.3'. See WINDOWS_BUILD.md.")


def runtime_dir(root: Path) -> Path:
    for relative in ("bin", "bin/intel64", "redist/intel64", "redist/intel64_win/mkl"):
        candidate = root / relative
        if list(candidate.glob("mkl_sequential*.dll")):
            return candidate
    raise FileNotFoundError(f"oneMKL sequential CPU runtime is missing under {root}")


def find_visual_studio() -> dict:
    vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / \
        "Microsoft Visual Studio/Installer/vswhere.exe"
    if not vswhere.exists():
        raise FileNotFoundError("Install Visual Studio 2022 with the Desktop development with C++ workload.")
    installations = json.loads(subprocess.check_output([
        str(vswhere), "-latest", "-products", "*", "-version", "[17.0,18.0)",
        "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-format", "json", "-utf8",
    ], encoding="utf-8"))
    if not installations:
        raise FileNotFoundError("Visual Studio 2022 x64 C++ tools were not found.")
    return installations[0]


def msvc_environment() -> dict[str, str]:
    installation = find_visual_studio()
    devcmd = Path(installation["installationPath"]) / "Common7/Tools/VsDevCmd.bat"
    result = subprocess.check_output(f'"{devcmd}" -arch=x64 -host_arch=x64 >nul && set', shell=True)
    environment = {key.upper(): value for key, value in os.environ.items()}
    for line in result.decode("mbcs").splitlines():
        if "=" in line and not line.startswith("="):
            key, value = line.split("=", 1)
            environment[key.upper()] = value
    return environment
