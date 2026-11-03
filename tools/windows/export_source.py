"""Export the port sources without local environments, SDKs or build caches."""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ROOT / "dist/meep-windows-msvc2-source.zip")
args = parser.parse_args()
directories = ["build-aux", "cmake", "docs", "examples", "libpympb", "m4", "python", "scheme", "src", "tests", "third_party", "tools"]
names = [".gitattributes", ".gitignore", "AUTHORS", "CMakeLists.txt", "CMakePresets.json", "CMakeSettings.json", "COPYRIGHT", "LICENSE",
         ".vscode/launch.json", ".vscode/tasks.json", ".vscode/settings.json", ".vscode/extensions.json",
         "README.md", "WINDOWS_BUILD.md", "WINDOWS_DEBUG.md", "WINDOWS_PORTING_PLAN.md",
         "requirements-windows.lock.txt", "requirements-notebooks.lock.txt", "UPSTREAM_SOURCES.json", "pyproject.toml", "aclocal.m4",
         "configure", "configure.ac", "config.h.in", "ltmain.sh", "Makefile.am", "Makefile.in",
         "meep-pkgconfig.in", "version.sh", "NEWS.md", "TODO"]
files = [ROOT / name for name in names]
for directory in directories:
    files.extend((ROOT / directory).rglob("*"))
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
    for path in sorted(set(files)):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(ROOT)
        if any(part in {"__pycache__", ".pytest_cache", ".git"} for part in relative.parts):
            continue
        if path.suffix.lower() in {".pyc", ".obj", ".pdb", ".exe", ".dll", ".lib"}:
            continue
        bundle.write(path, relative.as_posix())
digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
args.output.with_suffix(args.output.suffix + ".sha256").write_text(f"{digest}  {args.output.name}\n", encoding="utf-8")
print(f"Source archive: {args.output}\nSHA256: {digest}")
