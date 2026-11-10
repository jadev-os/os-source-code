from __future__ import annotations

import json
import sys
import tarfile
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jadevos_updater import core
from jadevos_updater import install_bundle


class ReleaseParsingTests(unittest.TestCase):
    def test_parse_release_selects_bundle_for_architecture(self) -> None:
        release = core._parse_release(
            {
                "tag_name": "v1.2.0",
                "draft": False,
                "prerelease": False,
                "published_at": "2026-01-02T03:04:05Z",
                "body": "Security and stability improvements.",
                "assets": [
                    {
                        "name": "jadevos-update-1.2.0-amd64.tar.gz",
                        "browser_download_url": "https://github.com/example/update",
                        "size": 120,
                        "digest": None,
                    },
                    {
                        "name": "jadevos-update-1.2.0-amd64.tar.gz.sig",
                        "browser_download_url": "https://github.com/example/signature",
                        "size": 64,
                        "digest": None,
                    },
                    {
                        "name": "jadevos-update-1.2.0-arm64.tar.gz",
                        "browser_download_url": "https://github.com/example/arm64",
                        "size": 120,
                        "digest": None,
                    },
                ],
            },
            "amd64",
        )
        self.assertIsNotNone(release)
        assert release is not None
        self.assertEqual(release.version, "1.2.0")
        self.assertEqual(release.bundle.name, "jadevos-update-1.2.0-amd64.tar.gz")
        self.assertEqual(
            release.signature.name, "jadevos-update-1.2.0-amd64.tar.gz.sig"
        )

    def test_parse_release_rejects_untrusted_asset_urls(self) -> None:
        asset = core._asset_info(
            {
                "name": "jadevos-update-1.2.0-amd64.tar.gz",
                "browser_download_url": "http://evil.example/update",
                "size": 100,
            }
        )
        self.assertIsNone(asset)

    def test_draft_and_prerelease_are_not_offered(self) -> None:
        for flags in ({"draft": True}, {"prerelease": True}):
            release = core._parse_release(
                {"tag_name": "v1.0.1", "assets": [], **flags}, "amd64"
            )
            self.assertIsNone(release)

    def test_missing_repository_is_reported_as_an_error(self) -> None:
        class MissingRepository:
            def open(self, *_args, **_kwargs):
                raise urllib.error.HTTPError(
                    core.RELEASES_URL, 404, "Not Found", {}, None
                )

        with patch.object(core, "_opener", return_value=MissingRepository()):
            with self.assertRaisesRegex(core.UpdateError, "not found or is not public"):
                core.fetch_releases("amd64")


class BundleMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.bundle = Path(self.temp_dir.name) / "update.tar.gz"

    def _write_bundle(self, manifest: dict[str, object]) -> None:
        manifest_path = Path(self.temp_dir.name) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with tarfile.open(self.bundle, "w:gz") as archive:
            archive.add(manifest_path, arcname="manifest.json")

    def test_validate_bundle_manifest_accepts_matching_release(self) -> None:
        self._write_bundle(
            {
                "schema_version": 1,
                "product": "JadevOS Computers",
                "suite": "jadevos",
                "version": "1.1.0",
                "architecture": "amd64",
            }
        )
        core.validate_bundle_metadata(self.bundle, "1.1.0", "amd64")

    def test_validate_bundle_manifest_rejects_mismatched_architecture(self) -> None:
        self._write_bundle(
            {
                "schema_version": 1,
                "product": "JadevOS Computers",
                "suite": "jadevos",
                "version": "1.1.0",
                "architecture": "arm64",
            }
        )
        with self.assertRaisesRegex(core.UpdateError, "architecture"):
            core.validate_bundle_metadata(self.bundle, "1.1.0", "amd64")

    def test_validate_bundle_manifest_rejects_wrong_architecture_type(self) -> None:
        self._write_bundle(
            {
                "schema_version": 1,
                "product": "JadevOS Computers",
                "suite": "jadevos",
                "version": "1.1.0",
                "architecture": ["amd64"],
            }
        )
        with self.assertRaisesRegex(core.UpdateError, "architecture"):
            core.validate_bundle_metadata(self.bundle, "1.1.0", "amd64")

    def test_download_refuses_non_github_https_host(self) -> None:
        asset = core.Asset(
            "bundle.tar.gz",
            "https://untrusted.example/bundle.tar.gz",
            10,
            None,
        )
        with self.assertRaisesRegex(core.UpdateError, "untrusted host"):
            core._download(
                asset,
                Path(self.temp_dir.name) / "bundle.tar.gz",
                threading.Event(),
                lambda _current, _total: None,
                lambda _message: None,
                1024,
            )

    def test_privileged_extractor_rejects_parent_traversal(self) -> None:
        manifest = {
            "schema_version": 1,
            "product": "JadevOS Computers",
            "suite": "jadevos",
            "version": "1.1.0",
            "architecture": "amd64",
            "packages": ["packages/test_1.1.0_amd64.deb"],
        }
        manifest_path = Path(self.temp_dir.name) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        unsafe_file = Path(self.temp_dir.name) / "package.deb"
        unsafe_file.write_bytes(b"not a real package")
        with tarfile.open(self.bundle, "w:gz") as archive:
            archive.add(manifest_path, arcname="manifest.json")
            archive.add(unsafe_file, arcname="../test_1.1.0_amd64.deb")
        with self.assertRaisesRegex(core.UpdateError, "unsafe archive path"):
            install_bundle._extract_packages(
                self.bundle, Path(self.temp_dir.name) / "packages"
            )

    def test_privileged_extractor_returns_manifest_packages(self) -> None:
        manifest = {
            "schema_version": 1,
            "product": "JadevOS Computers",
            "suite": "jadevos",
            "version": "1.1.0",
            "architecture": "amd64",
            "packages": ["packages/test_1.1.0_amd64.deb"],
        }
        manifest_path = Path(self.temp_dir.name) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        package = Path(self.temp_dir.name) / "test_1.1.0_amd64.deb"
        package.write_bytes(b"test")
        with tarfile.open(self.bundle, "w:gz") as archive:
            archive.add(manifest_path, arcname="manifest.json")
            archive.add(package, arcname="packages/test_1.1.0_amd64.deb")
        package_directory = Path(self.temp_dir.name) / "packages"
        package_directory.mkdir()
        with (
            patch.object(install_bundle, "_system_architecture", return_value="amd64"),
            patch.object(install_bundle, "_require_newer_version"),
        ):
            version, packages = install_bundle._extract_packages(
                self.bundle, package_directory
            )
        self.assertEqual(version, "1.1.0")
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0].read_bytes(), b"test")


if __name__ == "__main__":
    unittest.main()
