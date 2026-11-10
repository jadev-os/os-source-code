"""GitHub release discovery, signed bundle downloads, and system metadata."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import threading
import urllib.parse
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


REPOSITORY = "jamillansantiago/updates"
RELEASES_URL = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=30"
USER_AGENT = "JadevOS-Updater/1.0"
MAX_API_BYTES = 4 * 1024 * 1024
MAX_SIGNATURE_BYTES = 4096
MAX_BUNDLE_BYTES = 8 * 1024 * 1024 * 1024
VERSION_PATTERN = re.compile(r"^[0-9][A-Za-z0-9.+:~_-]*$")
ARCH_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
ProgressCallback = Callable[[int, int], None]
MessageCallback = Callable[[str], None]


class UpdateError(Exception):
    """A user-displayable error while checking, downloading, or verifying."""


class UpdateCancelled(UpdateError):
    """The user cancelled an update download."""


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    size: int
    digest: str | None


@dataclass(frozen=True)
class Release:
    version: str
    tag: str
    published_at: str
    notes: str
    bundle: Asset | None
    signature: Asset | None


class GitHubRedirectHandler(urllib.request.HTTPRedirectHandler):
    ALLOWED_HOSTS = {
        "github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
    }

    def redirect_request(self, request, file_pointer, code, message, headers, url):
        if urllib.parse.urlparse(url).hostname not in self.ALLOWED_HOSTS:
            raise UpdateError("GitHub redirected the download to an untrusted host.")
        return super().redirect_request(
            request, file_pointer, code, message, headers, url
        )


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(GitHubRedirectHandler())


def _request(url: str, accept: str) -> urllib.request.Request:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        raise UpdateError("The update service returned an invalid API address.")
    return urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


def installed_version() -> tuple[str, str]:
    """Return the updater's tracked system release version and display name."""
    tracked = Path("/var/lib/jadevOS-updater/version")
    os_release = Path("/etc/os-release")
    values: dict[str, str] = {}
    try:
        for line in os_release.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator:
                values[key] = value.strip().strip('"')
    except OSError as error:
        raise UpdateError(f"Could not read system version information: {error}") from error

    try:
        version = tracked.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        version = values.get("VERSION_ID", "")
    except OSError as error:
        raise UpdateError(f"Could not read the installed update version: {error}") from error

    if not VERSION_PATTERN.fullmatch(version):
        version = values.get("VERSION_ID", "unknown")
    display = values.get("PRETTY_NAME", f"JadevOS Computers {version}")
    return version, display


def system_architecture() -> str:
    try:
        result = subprocess.run(
            ["dpkg", "--print-architecture"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise UpdateError(f"Could not detect the system architecture: {error}") from error
    architecture = result.stdout.strip()
    if not ARCH_PATTERN.fullmatch(architecture):
        raise UpdateError("The system reported an invalid package architecture.")
    return architecture


def _version_is_newer(candidate: str, installed: str) -> bool:
    if not VERSION_PATTERN.fullmatch(candidate):
        raise UpdateError(f"GitHub returned an invalid release version: {candidate}")
    if not VERSION_PATTERN.fullmatch(installed):
        raise UpdateError(f"The installed version is invalid: {installed}")
    try:
        result = subprocess.run(
            ["dpkg", "--compare-versions", candidate, "gt", installed],
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise UpdateError(f"Could not compare Debian package versions: {error}") from error
    return result.returncode == 0


def _release_version(tag: object) -> str:
    if not isinstance(tag, str):
        raise UpdateError("A GitHub release has no valid version tag.")
    version = tag[1:] if tag[:1].lower() == "v" else tag
    if not VERSION_PATTERN.fullmatch(version):
        raise UpdateError(f"GitHub returned an invalid release tag: {tag}")
    return version


def _asset_info(raw_asset: object) -> Asset | None:
    if not isinstance(raw_asset, dict):
        return None
    name = raw_asset.get("name")
    url = raw_asset.get("browser_download_url")
    size = raw_asset.get("size")
    digest = raw_asset.get("digest")
    if not isinstance(name, str) or not isinstance(url, str):
        return None
    if not isinstance(size, int) or size < 0 or size > MAX_BUNDLE_BYTES:
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        return None
    if digest is not None and not (
        isinstance(digest, str) and re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest)
    ):
        digest = None
    return Asset(name=name, url=url, size=size, digest=digest)


def _parse_release(raw: object, architecture: str) -> Release | None:
    if not isinstance(raw, dict) or raw.get("draft") or raw.get("prerelease"):
        return None
    version = _release_version(raw.get("tag_name"))
    assets_raw = raw.get("assets")
    if not isinstance(assets_raw, list):
        assets_raw = []
    assets = [asset for entry in assets_raw if (asset := _asset_info(entry))]
    exact_name = f"jadevos-update-{version}-{architecture}.tar.gz"
    universal_name = f"jadevos-update-{version}-all.tar.gz"
    bundle = next((asset for asset in assets if asset.name == exact_name), None)
    if bundle is None:
        bundle = next((asset for asset in assets if asset.name == universal_name), None)
    signature = None
    if bundle is not None:
        signature = next(
            (asset for asset in assets if asset.name == f"{bundle.name}.sig"),
            None,
        )

    published_at = raw.get("published_at")
    if not isinstance(published_at, str):
        published_at = ""
    try:
        datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        published_at = ""
    notes = raw.get("body")
    if not isinstance(notes, str):
        notes = ""
    return Release(
        version=version,
        tag=raw.get("tag_name", version),
        published_at=published_at,
        notes=notes,
        bundle=bundle,
        signature=signature,
    )


def fetch_releases(
    architecture: str,
    progress: ProgressCallback | None = None,
    message: MessageCallback | None = None,
) -> list[Release]:
    if message:
        message("Connecting to GitHub...")
    request = _request(RELEASES_URL, "application/vnd.github+json")
    try:
        with _opener().open(request, timeout=20) as response:
            payload = response.read(MAX_API_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise UpdateError(
                "The JadevOS GitHub update repository was not found or is not public."
            ) from error
        if error.code == 403 and error.headers.get("X-RateLimit-Remaining") == "0":
            raise UpdateError("GitHub API rate limit reached. Try again later.") from error
        raise UpdateError(f"GitHub returned HTTP {error.code}: {error.reason}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise UpdateError(f"Could not connect to GitHub: {reason}") from error
    if len(payload) > MAX_API_BYTES:
        raise UpdateError("GitHub's release list is larger than the allowed limit.")
    try:
        raw_releases = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UpdateError("GitHub returned an invalid releases response.") from error
    if not isinstance(raw_releases, list):
        raise UpdateError("GitHub returned an unexpected releases response.")

    releases = [
        parsed
        for entry in raw_releases
        if (parsed := _parse_release(entry, architecture))
    ]
    releases.sort(key=lambda item: item.published_at, reverse=True)
    if progress:
        progress(1, 1)
    if message:
        message(f"Found {len(releases)} published release(s).")
    return releases


def _download(
    asset: Asset,
    destination: Path,
    cancel: threading.Event,
    progress: ProgressCallback,
    message: MessageCallback,
    maximum_size: int,
) -> str:
    request = urllib.request.Request(
        asset.url,
        headers={"Accept": "application/octet-stream", "User-Agent": USER_AGENT},
    )
    parsed = urllib.parse.urlparse(asset.url)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise UpdateError("Refusing to download an update from an untrusted host.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    received = 0
    try:
        with _opener().open(request, timeout=20) as response, partial.open("wb") as output:
            content_length = response.headers.get("Content-Length")
            total = int(content_length) if content_length and content_length.isdigit() else asset.size
            if total > maximum_size:
                raise UpdateError("The update file exceeds the allowed download size.")
            while True:
                if cancel.is_set():
                    raise UpdateCancelled("Download cancelled.")
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                if received > maximum_size:
                    raise UpdateError("The update file exceeds the allowed download size.")
                output.write(chunk)
                digest.update(chunk)
                progress(received, total)
        if asset.size and received != asset.size:
            raise UpdateError("The downloaded file size does not match GitHub's metadata.")
        actual_digest = digest.hexdigest()
        if asset.digest and actual_digest.lower() != asset.digest[7:].lower():
            raise UpdateError("The download SHA-256 does not match GitHub's asset digest.")
        os.replace(partial, destination)
        message(f"Downloaded {asset.name}.")
        return actual_digest
    except UpdateCancelled:
        partial.unlink(missing_ok=True)
        raise
    except urllib.error.HTTPError as error:
        partial.unlink(missing_ok=True)
        raise UpdateError(f"GitHub download failed with HTTP {error.code}.") from error
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        partial.unlink(missing_ok=True)
        reason = getattr(error, "reason", error)
        raise UpdateError(f"Could not download {asset.name}: {reason}") from error


def download_release(
    release: Release,
    cache_dir: Path,
    cancel: threading.Event,
    progress: ProgressCallback,
    message: MessageCallback,
) -> tuple[Path, Path, str]:
    if release.bundle is None or release.signature is None:
        raise UpdateError("This release has no signed update bundle for this system.")
    if release.bundle.size > MAX_BUNDLE_BYTES:
        raise UpdateError("The update bundle exceeds the allowed download size.")

    stem = f"jadevos-update-{release.version}"
    bundle_path = cache_dir / f"{stem}.tar.gz"
    signature_path = cache_dir / f"{stem}.tar.gz.sig"
    try:
        checksum = _download(
            release.bundle,
            bundle_path,
            cancel,
            progress,
            message,
            MAX_BUNDLE_BYTES,
        )
        _download(
            release.signature,
            signature_path,
            cancel,
            progress,
            message,
            MAX_SIGNATURE_BYTES,
        )
    except Exception:
        bundle_path.unlink(missing_ok=True)
        signature_path.unlink(missing_ok=True)
        raise
    return bundle_path, signature_path, checksum


def verify_download(bundle: Path, signature: Path) -> None:
    public_key = Path("/usr/share/jadevOS-updater/release-signing-public.pem")
    if not public_key.is_file():
        raise UpdateError("The trusted JadevOS release signing key is missing.")
    if bundle.stat().st_size > MAX_BUNDLE_BYTES:
        raise UpdateError("The downloaded update bundle exceeds the allowed size.")
    if signature.stat().st_size > MAX_SIGNATURE_BYTES:
        raise UpdateError("The downloaded signature is invalid or too large.")
    try:
        result = subprocess.run(
            [
                "openssl",
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(public_key),
                "-sigfile",
                str(signature),
                "-rawin",
                "-in",
                str(bundle),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise UpdateError(f"Could not verify the update signature: {error}") from error
    if result.returncode:
        raise UpdateError(
            "The update signature is invalid. The bundle was not installed."
        )


def validate_bundle_metadata(
    bundle: Path, expected_version: str, architecture: str
) -> None:
    try:
        with tarfile.open(bundle, mode="r:gz") as archive:
            first_member = next(iter(archive), None)
            if first_member is None or first_member.name != "manifest.json":
                raise UpdateError("The update bundle must start with its signed manifest.")
            if not first_member.isfile() or first_member.size > 256 * 1024:
                raise UpdateError("The update bundle manifest is invalid.")
            stream = archive.extractfile(first_member)
            if stream is None:
                raise UpdateError("Could not read the update bundle manifest.")
            manifest = json.load(stream)
    except UpdateError:
        raise
    except (OSError, tarfile.TarError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UpdateError(f"Could not read the signed update manifest: {error}") from error

    if not isinstance(manifest, dict):
        raise UpdateError("The signed update manifest is invalid.")
    bundle_architecture = manifest.get("architecture")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("product") != "JadevOS Computers"
        or manifest.get("suite") != "jadevos"
        or manifest.get("version") != expected_version
        or not isinstance(bundle_architecture, str)
        or bundle_architecture not in {"all", architecture}
    ):
        raise UpdateError(
            "The signed bundle does not match the selected JadevOS release and architecture."
        )


def reboot_is_required() -> bool:
    return Path("/run/reboot-required").exists() or Path(
        "/var/run/reboot-required"
    ).exists()


def cache_directory() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    if base:
        root = Path(base).expanduser()
    else:
        root = Path.home() / ".cache"
    result = root / "jadevos-updater"
    result.mkdir(parents=True, exist_ok=True)
    return result
