"""Run with run.py --preset windows-msvc-debug python ...; add --wait to attach VS."""
import argparse
import os

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--wait", action="store_true", help="Wait before loading the native extension")
args = parser.parse_args()
print(f"Python PID: {os.getpid()}", flush=True)
if args.wait:
    input("Attach Visual Studio using the Native debugger, then press Enter here: ")

import meep as mp
import numpy as np

print(f"Meep package: {mp.__file__}")
sim = mp.Simulation(
    cell_size=mp.Vector3(4, 4), resolution=10, boundary_layers=[mp.PML(0.5)],
    sources=[mp.Source(mp.GaussianSource(1, fwidth=0.5), mp.Ez, mp.Vector3())],
)
sim.run(until=10)
field = sim.get_array(component=mp.Ez)
assert np.isfinite(field).all()
print(f"Field shape: {field.shape}; maximum amplitude: {np.max(np.abs(field))}")
sim.reset_meep()
