"""Portable replacements for the upstream sed/cp/shell source generators."""
from pathlib import Path
import subprocess
import sys
import tomllib

operation, source, destination = sys.argv[1:]
if operation == "sphere":
    content = subprocess.check_output([source], text=True)
elif operation == "stride":
    content = Path(source).read_text(encoding="utf-8")
    for old, new in [("LOOP_OVER", "S1LOOP_OVER"), ("step_curl", "step_curl_stride1"),
                     ("step_update_EDHB", "step_update_EDHB_stride1"),
                     ("step_beta", "step_beta_stride1"), ("step_bfast", "step_bfast_stride1")]:
        content = content.replace(old, new)
elif operation == "package":
    content = Path(source).read_text(encoding="utf-8")
    # DLL-directory handles must remain alive for later oneMKL dispatch loading.
    prelude = '''import os as _os
from pathlib import Path as _Path
_dll_handles = []
if _os.name == "nt":
    for _directory in (_Path(__file__).parent / ".libs", _Path(__file__).parent):
        if _directory.is_dir():
            _dll_handles.append(_os.add_dll_directory(str(_directory)))
'''
    project = Path(__file__).resolve().parents[2] / "pyproject.toml"
    version = tomllib.loads(project.read_text(encoding="utf-8"))["project"]["version"]
    content = prelude + content + f'\n__version__ = {version!r}\n'
else:
    raise SystemExit(f"Unknown generation operation: {operation}")
Path(destination).write_text(content, encoding="utf-8")
