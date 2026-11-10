#!/usr/bin/env python3
"""Create and Ed25519-sign a JadevOS OTA bundle from Debian packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


VERSION_PATTERN = re.compile(r"^[0-9][A-Za-z0-9.+:~_-]*$")
ARCHITECTURES = {"amd64", "arm64"}


def _run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Release version, for example 1.0.1")
    parser.add_argument("architecture", choices=sorted(ARCHITECTURES | {"all"}))
    parser.add_argument("packages", nargs="+", type=Path, help="Input .deb package files")
    parser.add_argument(
        "--private-key",
        required=True,
        type=Path,
        help="Path to the Ed25519 release private key (never included in the bundle)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="Output directory (default: ./dist)",
    )
    args = parser.parse_args()

    if not VERSION_PATTERN.fullmatch(args.version):
        parser.error("version contains unsupported characters")
    if not args.private_key.is_file():
        parser.error(f"private key does not exist: {args.private_key}")
    if os.name == "posix" and stat.S_IMODE(args.private_key.stat().st_mode) & 0o077:
        parser.error("private key permissions must not allow group or other access")
    if len(args.packages) > 256:
        parser.error("at most 256 packages can be included")

    packages: list[tuple[Path, str]] = []
    for package in args.packages:
        if not package.is_file() or package.suffix != ".deb":
            parser.error(f"not a Debian package file: {package}")
        metadata = subprocess.run(
            ["dpkg-deb", "-f", str(package), "Package", "Version", "Architecture"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        fields = {
            key: value.strip()
            for line in metadata.splitlines()
            for key, separator, value in [line.partition(":")]
            if separator
        }
        if not {"Package", "Version", "Architecture"} <= fields.keys():
            parser.error(f"could not read package metadata: {package}")
        package_architecture = fields["Architecture"]
        if package_architecture not in {"all", args.architecture}:
            parser.error(
                f"{package.name} targets {package_architecture}, not {args.architecture}"
            )
        packages.append((package, f"packages/{package.name}"))

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"jadevos-update-{args.version}-{args.architecture}"
    bundle = output_dir / f"{stem}.tar.gz"
    signature = output_dir / f"{stem}.tar.gz.sig"
    manifest = {
        "schema_version": 1,
        "product": "JadevOS Computers",
        "suite": "jadevos",
        "version": args.version,
        "architecture": args.architecture,
        "packages": [archive_path for _, archive_path in packages],
    }

    with tempfile.TemporaryDirectory(
        prefix=".jadevos-update-", dir=output_dir
    ) as temporary:
        temporary_path = Path(temporary)
        manifest_path = temporary_path / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_bundle = temporary_path / bundle.name
        with tarfile.open(temporary_bundle, mode="w:gz") as archive:
            archive.add(manifest_path, arcname="manifest.json")
            for package, archive_path in packages:
                archive.add(package, arcname=archive_path)
        temporary_signature = temporary_path / signature.name
        subprocess.run(
            [
                "openssl",
                "pkeyutl",
                "-sign",
                "-inkey",
                str(args.private_key.resolve()),
                "-rawin",
                "-in",
                str(temporary_bundle),
                "-out",
                str(temporary_signature),
            ],
            check=True,
        )
        temporary_bundle.replace(bundle)
        temporary_signature.replace(signature)

    digest_state = hashlib.sha256()
    with bundle.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest_state.update(chunk)
    print(f"Bundle: {bundle}")
    print(f"Signature: {signature}")
    print(f"SHA-256: {digest_state.hexdigest()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_run())
    except (OSError, subprocess.CalledProcessError, tarfile.TarError) as error:
        print(f"Could not create update bundle: {error}", file=sys.stderr)
        raise SystemExit(1) from error
