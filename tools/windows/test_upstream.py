"""Run upstream unittest modules without importing the source python/ package.

Usage: python tools/windows/run.py python tools/windows/test_upstream.py test_geom ...
The default suite covers basic geometry, sources, fields, callbacks and HDF5.
"""
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "python/tests"))
modules = sys.argv[1:] or [
    "test_geom", "test_source", "test_simulation", "test_array_metadata",
    "test_get_epsilon_grid", "test_user_defined_material", "test_materials_library",
]
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in modules)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
