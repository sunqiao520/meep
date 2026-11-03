"""Fetch pinned upstream release sources without requiring Git or Guile.

Run from any directory with Python 3.12+. Existing source files are never replaced.
Archive contents are checked before extraction; downloads stay in the workspace.
"""

from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "sources"
SOURCES = [
    ("NanoComp/meep", "v1.35.0", "meep-1.35.0.tar.gz", ".",
     "4334a0c0d7dc302595e17519e35d93c64cdbb4d2944f2e9ae3ddf500265639a0"),
    ("NanoComp/libctl", "v4.7.1", "libctl-4.7.1.tar.gz", "third_party/libctl",
     "e023b4a3b6975b45260bcf343f305a62f2a7988c7349bc0dacc1208ccbf7b6b5"),
    ("NanoComp/harminv", "v1.4.3", "harminv-1.4.3.tar.gz", "third_party/harminv",
     "883b29a126bd5ba00ccf804b986e568980d39a53ec8f86ae05a43ca6c107cc38"),
    ("NanoComp/mpb", "v1.12.0", "mpb-1.12.0.tar.gz", "third_party/mpb",
     "8d2b206254b217f66a53c1ad20cc0c369b93b0e71ee671d68e333a583eaaeda4"),
    ("HDFGroup/hdf5", "hdf5_1.14.6", "hdf5-1.14.6.tar.gz", "third_party/hdf5",
     "e4defbac30f50d64e1556374aa49e574417c9e72c6b1de7a4ff88c4b1bea6e9b"),
]
SUPPLEMENTAL = {
    "python/vec.i": "3f56ebf2730a7ac5d52d5cb4365c62edc111aa7d86e1e5adbf745663118e81a1",
    "python/numpy.i": "b2370ae4e23b276d902df7e6f866496c214a2fbeea54bb2ee37776735ddddc0f",
    "python/mpb.i": "3434aa164c90db647bead3148f34e8cc8b61c0ffc5c45af676f8969262cb2902",
}


def request(url: str):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "meep-windows-port"}),
        timeout=120,
    )


def extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive) as bundle:
        members = []
        for member in bundle.getmembers():
            parts = PurePosixPath(member.name).parts
            if not parts or PurePosixPath(member.name).is_absolute() or ".." in parts:
                raise ValueError(f"Unsafe archive path: {member.name}")
            if len(parts) == 1:
                continue
            relative = Path(*parts[1:])
            target = (destination / relative).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError(f"Archive escapes destination: {member.name}")
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"Unsupported archive entry: {member.name}")
            members.append((member, target))
        for member, target in members:
            if target.exists() and member.isfile():
                original = bundle.extractfile(member).read()
                if target.read_bytes() != original:
                    raise FileExistsError(f"Refusing to replace modified file: {target}")
        for member, target in members:
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.extractfile(member).read())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="Fetch only this repository, e.g. HDFGroup/hdf5")
    parser.add_argument("--verify-only", action="store_true",
                        help="Verify cached archives and supplemental files without extraction or network")
    args = parser.parse_args()
    if args.only and args.only not in {source[0] for source in SOURCES}:
        parser.error("Unknown repository")
    CACHE.mkdir(parents=True, exist_ok=True)
    lock = ROOT / "UPSTREAM_SOURCES.json"
    records = json.loads(lock.read_text(encoding="utf-8")) if lock.exists() else []
    for repository, tag, name, folder, expected in SOURCES:
        if args.only and args.only != repository:
            continue
        url = f"https://github.com/{repository}/releases/download/{tag}/{name}"
        archive = CACHE / name
        if not archive.exists() and not args.verify_only:
            print(f"Downloading {name}", flush=True)
            with request(url) as response:
                archive.write_bytes(response.read())
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if expected != digest:
            raise ValueError(f"SHA256 mismatch: {name}")
        if not args.verify_only:
            extract(archive, ROOT / folder)
        records = [record for record in records if record["destination"] != folder]
        records.append({"repository": repository, "tag": tag,
                        "url": url, "sha256": digest,
                        "destination": folder})
        print(f"Verified {name}: {digest}", flush=True)
    if not args.only or args.only == "NanoComp/meep":
        # These SWIG inputs are absent from the release tarball. Use the same tag.
        for relative, expected in SUPPLEMENTAL.items():
            target = ROOT / relative
            url = f"https://raw.githubusercontent.com/NanoComp/meep/v1.35.0/{relative}"
            if not target.exists() and not args.verify_only:
                with request(url) as response:
                    data = response.read()
                if hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError(f"SHA256 mismatch: {relative}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise ValueError(f"SHA256 mismatch: {relative}")
            records = [record for record in records if record["destination"] != relative]
            records.append({"repository": "NanoComp/meep", "tag": "v1.35.0",
                            "url": url, "sha256": expected, "destination": relative})
            print(f"Verified {relative}", flush=True)
    if not args.verify_only:
        lock.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
