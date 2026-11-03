"""Run in the VS2022 x64 environment with the selected standalone oneMKL SDK."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

from environment import ROOT, find_mkl, msvc_environment, runtime_dir

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--preset", default="windows-msvc-release")
parser.add_argument("--build-dir", type=Path)
parser.add_argument("--mkl-root", type=Path)
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
if not args.command:
    parser.error("provide a command, for example: --preset windows-msvc-debug python examples/windows/debug_simulation.py")
try:
    sdk = find_mkl(args.mkl_root)
    environment = msvc_environment()
except (FileNotFoundError, ValueError) as error:
    parser.exit(1, f"{error}\n")
venv = ROOT / ".venv"
build = (args.build_dir or ROOT / "out/build" / args.preset).resolve()
environment["PATH"] = os.pathsep.join([
    str(venv / "Scripts"), str(runtime_dir(sdk)), environment.get("PATH", ""),
])
environment["MKLROOT"] = str(sdk)
environment["PYTHONPATH"] = str(build / "python")
environment["MPLBACKEND"] = "Agg"
environment["OMP_NUM_THREADS"] = "1"
environment["MKL_NUM_THREADS"] = "1"
environment["CMAKE_GENERATOR"] = "Ninja"
environment["CMAKE_BUILD_PARALLEL_LEVEL"] = "4"
command = args.command
tool = venv / "Scripts" / (command[0] + ".exe")
command[0] = str(tool) if tool.is_file() else shutil.which(command[0], path=environment["PATH"]) or command[0]
raise SystemExit(subprocess.call(command, env=environment, cwd=ROOT))
