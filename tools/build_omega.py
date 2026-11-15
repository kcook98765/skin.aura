#!/usr/bin/env python3
"""Build a deterministic local ZIP and native /tmp stage. No validation is implied."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.dont_write_bytecode = True
from omega_common import BASELINE_VERSION, DIRECTORIES, VERSION, Source

ROOT = Path(__file__).resolve().parents[1]
STAMP = (1980, 1, 1, 0, 0, 0)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def new_output(path, source_root):
    path = Path(os.path.abspath(path))
    if path.is_symlink() or path.exists():
        raise ValueError("Output must not exist (including symlinks): " + str(path))
    if not path.parent.is_dir():
        raise ValueError("Output parent must already exist")
    if not path.parent.resolve().is_relative_to(Path("/tmp")):
        raise ValueError("Use a native Linux /tmp output parent for toolkit staging")
    if path.resolve().is_relative_to(Path(source_root).resolve()):
        raise ValueError("Output must be outside the source/package")
    if any(parent.is_symlink() for parent in path.parents):
        raise ValueError("Output ancestors must not be symlinks")
    return path


def build(source, output):
    output = new_output(output, source.root)
    identity = ET.fromstring(source.read("addon.xml"))
    version = BASELINE_VERSION if source.baseline else VERSION
    expected = {"id": "skin.aura", "name": "Aura", "provider-name": "kcook98765", "version": version}
    if any(identity.get(key) != value for key, value in expected.items()):
        raise ValueError("Manifest identity/version differs from the fixed local package identity")
    provenance = source.provenance()
    # Snapshot bytes before creating output; baseline uses git archive, not worktree.
    payload = {name: source.read(name) for name in source.files}
    directories = {"skin.aura", *("skin.aura/" + name for name in DIRECTORIES)}
    for name in payload:
        directories.update(str(parent) for parent in PurePosixPath("skin.aura/" + name).parents if str(parent) != ".")
    output.mkdir(mode=0o755)  # Exclusive creation also handles a concurrent creator.
    output.chmod(0o755)
    for directory in sorted(directories, key=lambda name: (name.count("/"), name)):
        path = output / directory
        path.mkdir(mode=0o755)
        path.chmod(0o755)
    files = {}
    for name, data in payload.items():
        path = output / "skin.aura" / name
        with path.open("xb") as stream:
            stream.write(data)
        path.chmod(0o644)
        files[name] = {"sha256": sha256(data), "size": len(data), "mode": "0644"}
    suffix = "-omega-baseline-local" if source.baseline else ""
    archive = output / ("skin.aura-" + version + suffix + ".zip")
    # Production admission requires regular file entries only. Keep genuine
    # historical baseline output stable; Kodi creates parent directories.
    entries = {directory + "/": b"" for directory in directories} if source.baseline else {}
    entries.update({"skin.aura/" + name: data for name, data in payload.items()})
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as tree:
        for name in sorted(entries):
            directory = name.endswith("/")
            info = zipfile.ZipInfo(name, date_time=STAMP)
            info.create_system = 3
            info.external_attr = ((stat.S_IFDIR | 0o755) if directory else (stat.S_IFREG | 0o644)) << 16
            if directory:
                info.external_attr |= 0x10
            info.compress_type = zipfile.ZIP_DEFLATED
            tree.writestr(info, entries[name], compresslevel=9)
    archive.chmod(0o644)
    with zipfile.ZipFile(archive) as tree:
        bad = tree.testzip()
        if bad:
            raise ValueError("ZIP CRC failed: " + bad)
        if tree.namelist() != sorted(entries):
            raise ValueError("ZIP inventory/order mismatch")
        for info in tree.infolist():
            mode = 0o755 if info.is_dir() else 0o644
            path = output / info.filename.rstrip("/")
            if stat.S_IMODE(path.stat().st_mode) != mode or stat.S_IMODE(info.external_attr >> 16) != mode:
                raise ValueError("Stage/ZIP mode mismatch: " + info.filename)
            if not info.is_dir():
                data = tree.read(info)
                if data != entries[info.filename] or path.read_bytes() != data:
                    raise ValueError("ZIP/source/stage readback mismatch: " + info.filename)
    staged_files = {path.relative_to(output / "skin.aura").as_posix()
                    for path in (output / "skin.aura").rglob("*") if path.is_file()}
    if staged_files != set(files):
        raise ValueError("Staged file inventory mismatch")
    receipt = {
        **provenance, "addon": expected, "file_count": len(files), "files": files,
        "directories": {directory: "0755" for directory in sorted(directories)},
        "zip": {"name": archive.name, "sha256": sha256(archive.read_bytes()),
                "size": archive.stat().st_size, "timestamp": list(STAMP),
                "compression": "deflate-9", "crc_verified": True,
                "readback_tree_consistent": True},
        "validation": "Not run by builder; run checker and toolkit separately; baseline failures are expected, not waived.",
    }
    receipt_path = output / "receipt.json"
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    receipt_path.chmod(0o644)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory; existing native /tmp parent required")
    parser.add_argument("--baseline", action="store_true", help="Package git archive of 203aba5 instead of the worktree")
    args = parser.parse_args(argv)
    try:
        # Refuse a bad destination before reading the source snapshot.
        new_output(args.output, ROOT)
        receipt = build(Source(ROOT, baseline=args.baseline, archive=args.baseline), args.output)
        print("Built %s: %d files; normalized files=0644, directories=0755" % (receipt["source"], receipt["file_count"]))
        print("Stage: " + str(args.output.absolute() / "skin.aura"))
        print("ZIP: " + str(args.output.absolute() / receipt["zip"]["name"]))
        print("SHA256: " + receipt["zip"]["sha256"])
        print("CRC/readback/tree consistency: PASS")
        print("Receipt: " + str(args.output.absolute() / "receipt.json"))
        print("WARNING: " + receipt["validation"])
        return 0
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as error:
        print("ERROR: %s; exit=2" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
