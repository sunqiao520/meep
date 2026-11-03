"""Run the wheel smoke test with developer paths and SDK variables removed."""
import argparse
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--python", type=Path, default=root / ".venv-wheel/Scripts/python.exe")
args = parser.parse_args()
environment = {key.upper(): value for key, value in os.environ.items()}
for key in list(environment):
    if key.upper() in {"PYTHONPATH", "PYTHONHOME", "MKLROOT", "LIB", "LIBPATH", "INCLUDE"}:
        del environment[key]
system = Path(environment.get("SYSTEMROOT", r"C:\Windows"))
environment["PATH"] = os.pathsep.join([str(system / "System32"), str(system)])
environment["MPLBACKEND"] = "Agg"
environment["OMP_NUM_THREADS"] = "1"
environment["MKL_NUM_THREADS"] = "1"
for extra in ([], ["--h5py-first"]):
    subprocess.run([str(args.python.resolve()), "-I", str(root / "tools/windows/smoke.py"), *extra],
                   cwd=root, env=environment, check=True)
print("Wheel verification passed with isolated Python and a system-only PATH.")
