# JadevOS Updater

Software Updater (JadevOS Updater) is a PyQt6 desktop application for Debian 13 and JadevOS
Computers. The interface is in English and works with GNOME.
It checks the public GitHub Releases API for
`jamillansantiago/updates`; that repository must publish signed update assets
before the client can offer an update.

## Build the Debian package

Build on Debian 13 (or a Debian-compatible system) with `dpkg-deb` installed:

```sh
bash updater/build-deb.sh dist/jadevos-updater_1.0.0_all.deb
```

Runtime requirements are declared by the package and include Python 3, PyQt6,
OpenSSL, `pkexec`, `polkitd`, APT, and DPKG. The package recommends a PolicyKit
desktop agent (`mate-polkit`) so administrator authentication has a graphical
prompt.

## Publish a signed update

The private Ed25519 key is a release secret. Keep it outside source control and
restrict its permissions to its owner (`chmod 600`). Never include the private
key in an ISO, Debian package, or release asset. The public key shipped with
the application is pinned in
`src/jadevos_updater/release-signing-public.pem`; changing the signing key
requires a trusted updater package/ISO update.

The OTA server is the **GitHub Releases** area of
[`jamillansantiago/updates`](https://github.com/jamillansantiago/updates), not
the repository's source-code files. For each release:

1. Build the updated Debian package(s) for the target system and increment
   their Debian package versions. Include every changed JadevOS component as a
   `.deb`; the updater does not send arbitrary source files or replace the
   whole ISO.
2. On the trusted signing computer, build and sign one bundle per architecture.
   Never copy the private signing key to GitHub or to the JadevOS ISO.
3. Open the repository's **Releases** page, choose **Draft a new release**,
   create a new tag such as `v1.0.1`, add release notes, and attach both the
   generated `.tar.gz` bundle and matching `.tar.gz.sig` signature.
4. Publish the release as a normal public release (not a draft). JadevOS
   Updater will find it automatically the next time it checks GitHub.

For an amd64 update with a package built at `dist/jadevos-component_1.0.1_amd64.deb`,
create the bundle like this:

```sh
python3 updater/create_bundle.py 1.0.1 amd64 \
  --private-key /secure/path/release-signing-key.pem \
  --output-dir dist \
  dist/jadevos-component_1.0.1_amd64.deb
```

For a universal release, use `all` and include only Debian packages whose
architecture is `all`. A bundle contains `manifest.json` followed by files
under `packages/`. The generated assets are named
`jadevos-update-<version>-<architecture>.tar.gz` and
`jadevos-update-<version>-<architecture>.tar.gz.sig`. Upload both files to a
GitHub Release whose tag is `v<version>` or `<version>`.

The GitHub release should include both architecture variants when publishing
for amd64 and arm64; create one bundle and signature pair for each architecture.
For example, a release `v1.0.1` can contain:

```text
jadevos-update-1.0.1-amd64.tar.gz
jadevos-update-1.0.1-amd64.tar.gz.sig
jadevos-update-1.0.1-arm64.tar.gz
jadevos-update-1.0.1-arm64.tar.gz.sig
```

The current GitHub repository has no published releases yet, so the updater
will report that there are no OTA releases until you publish the first signed
bundle. Keep the signing key backed up securely: losing it means installed
clients will not trust bundles signed with a replacement key.

The signed manifest identifies product `JadevOS Computers`, suite `jadevos`,
schema version `1`, the release version, architecture, and exact package paths.
The privileged installer independently validates the signature and manifest,
copies user-owned input files into a root-owned temporary directory, and runs
APT with `--no-download --no-remove`. Therefore all packages and dependencies
required for an update must be present in the signed bundle or already
installed; an update fails rather than downloading unverified dependencies or
removing packages.

## Security model

The unprivileged GUI fetches and downloads release files, then verifies the
Ed25519 signature and bundle metadata. Only the narrowly scoped privileged
helper can install. PolicyKit requests administrator authentication for each
privileged operation. The helper repeats signature verification as root before
examining the archive or invoking APT. The signing private key is never
installed on client systems.

The updater records its installed release version in
`/var/lib/jadevOS-updater/version`. Kernel or system updates can request a
restart; JadevOS Updater asks the user before invoking the authorized restart
operation. Downloaded bundles are cached under the user's cache directory.

## Add to the JadevOS ISO

The live ISO build stages the locally built `.deb` in the chroot and installs
it with a late chroot hook after its declared dependencies are installed.
This avoids depending on live-build's temporary local-repository signing key.
To test changes, rebuild the ISO with the repository's normal `python build.py`
workflow.
