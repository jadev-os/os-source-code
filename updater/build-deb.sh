#!/usr/bin/env bash
set -Eeuo pipefail

output="${1:?Usage: build-deb.sh <output.deb>}"
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
version="$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${project_dir}/src" python3 -c 'from jadevos_updater import __version__; print(__version__)')"
work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT
mkdir -p "$(dirname -- "$output")"

package_root="${work_dir}/jadevos-updater"
install -d \
    "${package_root}/DEBIAN" \
    "${package_root}/usr/bin" \
    "${package_root}/usr/lib/python3/dist-packages/jadevos_updater" \
    "${package_root}/usr/lib/jadevOS-updater" \
    "${package_root}/usr/share/jadevOS-updater" \
    "${package_root}/usr/share/applications" \
    "${package_root}/usr/share/icons/hicolor/scalable/apps" \
    "${package_root}/usr/share/polkit-1/actions"

cp -a "${project_dir}/src/jadevos_updater/." \
    "${package_root}/usr/lib/python3/dist-packages/jadevos_updater/"
find "${package_root}/usr/lib/python3/dist-packages/jadevos_updater" \
    -type d -name __pycache__ -prune -exec rm -rf -- {} +
find "${package_root}/usr/lib/python3/dist-packages/jadevos_updater" \
    -type d -exec chmod 0755 {} +
find "${package_root}/usr/lib/python3/dist-packages/jadevos_updater" \
    -type f -exec chmod 0644 {} +
install -m 0755 "${project_dir}/data/jadevOS-updater" \
    "${package_root}/usr/bin/jadevOS-updater"
install -m 0755 "${project_dir}/data/privileged" \
    "${package_root}/usr/lib/jadevOS-updater/privileged"
install -m 0644 \
    "${project_dir}/src/jadevos_updater/release-signing-public.pem" \
    "${package_root}/usr/share/jadevOS-updater/release-signing-public.pem"
install -m 0644 "${project_dir}/data/jadevOS-updater.desktop" \
    "${package_root}/usr/share/applications/jadevOS-updater.desktop"
install -m 0644 "${project_dir}/data/jadevOS-updater.svg" \
    "${package_root}/usr/share/icons/hicolor/scalable/apps/jadevOS-updater.svg"
install -m 0644 "${project_dir}/data/org.jadevOS.updater.policy" \
    "${package_root}/usr/share/polkit-1/actions/org.jadevOS.updater.policy"

cat > "${package_root}/DEBIAN/control" <<EOF
Package: jadevos-updater
Version: ${version}
Section: admin
Priority: optional
Architecture: all
Depends: python3 (>= 3.11), python3-pyqt6, openssl, pkexec, polkitd, apt, dpkg
Recommends: mate-polkit
Maintainer: JadevOS Computers <support@jadevos.invalid>
Description: Secure signed update manager for JadevOS Computers
 Desktop updater for signed JadevOS releases hosted on GitHub.
EOF

install -D -m 0644 /dev/null "${package_root}/usr/share/doc/jadevos-updater/changelog.Debian.gz"
gzip -n -c > "${package_root}/usr/share/doc/jadevos-updater/changelog.Debian.gz" <<EOF
jadevos-updater (${version}) unstable; urgency=medium

  * Initial secure signed-bundle updater.

 -- JadevOS Computers <support@jadevos.invalid>  $(date -Ru)
EOF

dpkg-deb --root-owner-group --build "$package_root" "$output"
printf 'Built %s\n' "$output"
