"""Root-side verification and safe installation of signed .deb bundles."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from .core import (
    MAX_BUNDLE_BYTES,
    MAX_SIGNATURE_BYTES,
    VERSION_PATTERN,
    UpdateError,
)

PUBLIC_KEY = Path("/usr/share/jadevOS-updater/release-signing-public.pem")
MAX_PACKAGE_COUNT = 256
MAX_UNPACKED_SIZE = 8 * 1024 * 1024 * 1024
MAX_PACKAGE_SIZE = 2 * 1024 * 1024 * 1024
PACKAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9+.-]*_[A-Za-z0-9.+:~_-]+_(?:amd64|arm64|all)\.deb$")


def _copy_trusted_user_file(
    source: Path,
    destination: Path,
    expected_uid: int,
    maximum_size: int,
) -> None:
    try:
        source_fd = os.open(
            source,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise UpdateError(f"Could not safely open the downloaded file: {error}") from error

    try:
        info = os.fstat(source_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != expected_uid:
            raise UpdateError("Update files must be regular files owned by the logged-in user.")
        if info.st_size <= 0 or info.st_size > maximum_size:
            raise UpdateError("An update file is empty or exceeds its allowed size.")
        with os.fdopen(source_fd, "rb", closefd=False) as source_file:
            with destination.open("xb") as destination_file:
                shutil.copyfileobj(source_file, destination_file, length=1024 * 1024)
                destination_file.flush()
                os.fsync(destination_file.fileno())
    finally:
        os.close(source_fd)


def _verify_signature(bundle: Path, signature: Path) -> None:
    if not PUBLIC_KEY.is_file():
        raise UpdateError("The trusted JadevOS release signing key is not installed.")
    result = subprocess.run(
        [
            "/usr/bin/openssl",
            "pkeyutl",
            "-verify",
            "-pubin",
            "-inkey",
            str(PUBLIC_KEY),
            "-sigfile",
            str(signature),
            "-rawin",
            "-in",
            str(bundle),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise UpdateError("The update signature is invalid; installation was refused.")


def _validate_version(version: object) -> str:
    if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
        raise UpdateError("The signed update manifest contains an invalid version.")
    return version


def _installed_version() -> str:
    values: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator:
                values[key] = value.strip().strip('"')
    except OSError as error:
        raise UpdateError(f"Could not read the installed JadevOS identity: {error}") from error

    if (
        values.get("NAME") != "JadevOS Computers"
        or values.get("VERSION_CODENAME") != "jadevos"
    ):
        raise UpdateError(
            "JadevOS system updates can only be installed on JadevOS Computers."
        )

    state_file = Path("/var/lib/jadevOS-updater/version")
    try:
        value = state_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        value = ""
    if value and VERSION_PATTERN.fullmatch(value):
        return value

    value = values.get("VERSION_ID", "")
    if VERSION_PATTERN.fullmatch(value):
        return value
    raise UpdateError("The installed JadevOS version is missing or invalid.")


def _require_newer_version(version: str) -> None:
    result = subprocess.run(
        ["/usr/bin/dpkg", "--compare-versions", version, "gt", _installed_version()],
        capture_output=True,
        timeout=5,
        check=False,
    )
    if result.returncode != 0:
        raise UpdateError("This update is not newer than the installed system.")


def _system_architecture() -> str:
    result = subprocess.run(
        ["/usr/bin/dpkg", "--print-architecture"],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    return result.stdout.strip()


def _validate_manifest(raw: object) -> tuple[str, list[str]]:
    if not isinstance(raw, dict):
        raise UpdateError("The signed bundle has no valid update manifest.")
    if raw.get("schema_version") != 1:
        raise UpdateError("This update bundle uses an unsupported manifest version.")
    if raw.get("product") != "JadevOS Computers":
        raise UpdateError("This update bundle is not for JadevOS Computers.")
    if raw.get("suite") != "jadevos":
        raise UpdateError("This update bundle targets a different operating system.")
    version = _validate_version(raw.get("version"))
    architecture = raw.get("architecture")
    if not isinstance(architecture, str) or architecture not in {
        "all",
        _system_architecture(),
    }:
        raise UpdateError("This update bundle is for a different system architecture.")
    _require_newer_version(version)

    package_entries = raw.get("packages")
    if (
        not isinstance(package_entries, list)
        or not package_entries
        or len(package_entries) > MAX_PACKAGE_COUNT
    ):
        raise UpdateError("The update manifest has an invalid package list.")
    unique: set[str] = set()
    for entry in package_entries:
        if not isinstance(entry, str):
            raise UpdateError("The update manifest contains an invalid package path.")
        path = PurePosixPath(entry)
        if (
            len(path.parts) != 2
            or path.parts[0] != "packages"
            or path.name != entry.split("/")[-1]
            or not PACKAGE_NAME.fullmatch(path.name)
            or entry in unique
        ):
            raise UpdateError("The update manifest contains an unsafe package path.")
        unique.add(entry)
    return version, package_entries


def _extract_packages(bundle: Path, destination: Path) -> tuple[str, list[Path]]:
    if bundle.stat().st_size > MAX_BUNDLE_BYTES:
        raise UpdateError("The update bundle exceeds the allowed size.")
    extracted: dict[str, Path] = {}
    total_size = 0
    manifest: object | None = None
    try:
        with tarfile.open(bundle, mode="r:gz") as archive:
            for index, member in enumerate(archive):
                if index >= MAX_PACKAGE_COUNT + 1:
                    raise UpdateError("The update bundle contains too many files.")
                path = PurePosixPath(member.name)
                if (
                    path.is_absolute()
                    or len(path.parts) != 2 and member.name != "manifest.json"
                    or any(part in {"", ".", ".."} for part in path.parts)
                ):
                    raise UpdateError("The update bundle contains an unsafe archive path.")
                if not member.isfile() or member.issym() or member.islnk():
                    raise UpdateError("The update bundle contains a non-regular file.")
                if member.size < 0 or member.size > MAX_PACKAGE_SIZE:
                    raise UpdateError("A file in the update bundle exceeds the size limit.")
                total_size += member.size
                if total_size > MAX_UNPACKED_SIZE:
                    raise UpdateError("The expanded update bundle exceeds the size limit.")

                if member.name == "manifest.json":
                    if manifest is not None or index != 0 or member.size > 256 * 1024:
                        raise UpdateError("The signed bundle manifest is misplaced or invalid.")
                    manifest_stream = archive.extractfile(member)
                    if manifest_stream is None:
                        raise UpdateError("Could not read the signed bundle manifest.")
                    try:
                        manifest = json.load(manifest_stream)
                    except (UnicodeDecodeError, json.JSONDecodeError) as error:
                        raise UpdateError("The signed bundle manifest is not valid JSON.") from error
                    continue

                if (
                    manifest is None
                    or len(path.parts) != 2
                    or path.parts[0] != "packages"
                    or not PACKAGE_NAME.fullmatch(path.name)
                    or member.name in extracted
                ):
                    raise UpdateError("The update bundle contains an unexpected file.")
                output_path = destination / path.name
                input_stream = archive.extractfile(member)
                if input_stream is None:
                    raise UpdateError(f"Could not read package {path.name}.")
                with input_stream, output_path.open("xb") as output_stream:
                    shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
                output_path.chmod(0o600)
                extracted[member.name] = output_path
    except (tarfile.TarError, OSError) as error:
        if isinstance(error, UpdateError):
            raise
        raise UpdateError(f"The update bundle could not be safely unpacked: {error}") from error

    if manifest is None:
        raise UpdateError("The update bundle is missing its manifest.")
    version, package_entries = _validate_manifest(manifest)
    if set(package_entries) != set(extracted):
        raise UpdateError("The signed manifest does not match the bundle contents.")
    return version, [extracted[entry] for entry in package_entries]


def install_bundle(bundle_source: Path, signature_source: Path) -> tuple[str, bool]:
    if os.geteuid() != 0:
        raise UpdateError("The system installer must run through PolicyKit.")
    try:
        requester_uid = int(os.environ.get("PKEXEC_UID", ""))
    except ValueError as error:
        raise UpdateError("This installer must be started by an authenticated desktop user.") from error
    if requester_uid <= 0:
        raise UpdateError("This installer must be started by an authenticated desktop user.")

    with tempfile.TemporaryDirectory(
        prefix="jadevos-updater-", dir="/var/tmp"
    ) as temporary_directory:
        work_dir = Path(temporary_directory)
        trusted_bundle = work_dir / "update.tar.gz"
        trusted_signature = work_dir / "update.tar.gz.sig"
        _copy_trusted_user_file(
            bundle_source, trusted_bundle, requester_uid, MAX_BUNDLE_BYTES
        )
        _copy_trusted_user_file(
            signature_source, trusted_signature, requester_uid, MAX_SIGNATURE_BYTES
        )
        _verify_signature(trusted_bundle, trusted_signature)

        packages_directory = work_dir / "packages"
        packages_directory.mkdir(mode=0o700)
        version, package_paths = _extract_packages(trusted_bundle, packages_directory)

        print("Preparing the signed JadevOS update...", flush=True)
        process = subprocess.Popen(
            [
                "/usr/bin/apt-get",
                "--no-download",
                "--no-remove",
                "--yes",
                "-o",
                "Dpkg::Use-Pty=0",
                "-o",
                "Dpkg::Status-Fd=1",
                "install",
                *[str(path) for path in package_paths],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line.rstrip(), flush=True)
        return_code = process.wait()
        if return_code != 0:
            raise UpdateError(
                f"APT could not complete the update (exit code {return_code}). "
                "The package manager may need repair before retrying."
            )

        state_dir = Path("/var/lib/jadevOS-updater")
        state_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
        temporary_state = state_dir / ".version.tmp"
        temporary_state.write_text(version + "\n", encoding="ascii")
        temporary_state.chmod(0o644)
        os.replace(temporary_state, state_dir / "version")

    reboot_required = Path("/run/reboot-required").exists() or Path(
        "/var/run/reboot-required"
    ).exists()
    print(
        f"reboot-required:{'true' if reboot_required else 'false'}",
        flush=True,
    )
    return version, reboot_required


def reboot_system() -> None:
    if os.geteuid() != 0 or os.environ.get("PKEXEC_UID", "").isdigit() is False:
        raise UpdateError("A confirmed, authenticated desktop session is required to reboot.")
    subprocess.run(["/usr/bin/systemctl", "reboot"], check=True, timeout=10)
