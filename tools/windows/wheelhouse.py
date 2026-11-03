"""Record or verify wheel hashes for a Windows CPython 3.12 offline environment."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--write", action="store_true")
parser.add_argument("directory", type=Path)
args = parser.parse_args()
manifest = args.directory / "sha256.json"
if args.write:
    wheels = sorted(args.directory.glob("*.whl"))
    if not wheels:
        raise SystemExit("No wheels found")
    records = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in wheels}
    manifest.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
else:
    records = json.loads(manifest.read_text(encoding="utf-8"))
    for name, expected in records.items():
        if Path(name).name != name:
            raise SystemExit(f"Invalid wheel filename in manifest: {name}")
        path = args.directory / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Wheel checksum mismatch: {path}")
print(f"{'Recorded' if args.write else 'Verified'} {len(records)} wheel checksums: {manifest}")
