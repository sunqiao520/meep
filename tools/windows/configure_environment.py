"""Write machine-local SDK selection, without putting absolute paths in shared presets."""
import argparse
import json

from environment import DEPENDENCIES, LOCAL_CONFIG, find_mkl, local_config, runtime_dir

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--mkl-root")
args = parser.parse_args()
sdk = find_mkl(args.mkl_root)
configuration = local_config()
configuration.update({"schema": 1, "mklRoot": sdk.as_posix(),
                      "mklVersion": DEPENDENCIES["oneMKL"]["version"]})
LOCAL_CONFIG.write_text(json.dumps(configuration, indent=2) + "\n", encoding="utf-8")
print(f"Standalone SDK: {sdk}")
print(f"CPU runtime:   {runtime_dir(sdk)}")
print(f"Local config:  {LOCAL_CONFIG}")
