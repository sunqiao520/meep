"""Exercise an installed wheel, including HDF5 and MPB, without the build runner."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import tempfile

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--h5py-first", action="store_true")
args = parser.parse_args()
if args.h5py_first:
    import h5py
import meep as mp
import h5py

assert not mp.with_mpi()
assert not mp.is_single_precision()
with tempfile.TemporaryDirectory(prefix="meep-wheel-") as directory:
    sim = mp.Simulation(
        cell_size=mp.Vector3(4, 4), resolution=10,
        boundary_layers=[mp.PML(0.5)],
        sources=[mp.Source(mp.GaussianSource(1, fwidth=0.5), mp.Ez, mp.Vector3())],
    )
    sim.use_output_directory(directory)
    sim.run(mp.at_beginning(mp.output_epsilon), until=10)
    field = sim.get_array(component=mp.Ez)
    assert np.isfinite(field).all() and np.max(np.abs(field)) > 1e-6
    files = list(Path(directory).glob("*.h5"))
    assert files, "Meep did not write HDF5 output"
    with h5py.File(files[0]) as output:
        assert "eps" in output and np.isfinite(output["eps"][:]).all()
    amplitude = float(np.max(np.abs(field)))
    sim.reset_meep()

# Uniform medium: the first transverse mode has frequency |k| / n = 0.2.
sim = mp.Simulation(cell_size=mp.Vector3(4, 4), resolution=10)
sim.init_sim()
mode = sim.get_eigenmode(
    frequency=0.2, direction=mp.X,
    where=mp.Volume(center=mp.Vector3(), size=mp.Vector3(0, 4)),
    band_num=1, kpoint=mp.Vector3(0.2), match_frequency=True,
    parity=mp.ODD_Z,
)
assert abs(mode.freq - 0.2) < 1e-7
assert abs(mode.k.x - 0.2) < 1e-6
loaded_mkl = {}
if os.name == "nt":
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
    for name in ("mkl_sequential.2.dll", "mkl_core.2.dll"):
        handle = kernel.GetModuleHandleW(name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        filename = ctypes.create_unicode_buffer(32768)
        if not kernel.GetModuleFileNameW(handle, filename, len(filename)):
            raise ctypes.WinError(ctypes.get_last_error())
        loaded_mkl[name] = filename.value
print(json.dumps({
    "module": mp.__file__, "version": mp.__version__,
    "finite_field_max": amplitude, "mpb_frequency": mode.freq,
    "mpb_kx": mode.k.x, "h5py_first": args.h5py_first,
    "loaded_mkl": loaded_mkl,
}, indent=2))
sim.reset_meep()
