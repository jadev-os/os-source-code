#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="${1:?Uso: build-live.sh <proyecto> <iso-salida>}"
output_iso="${2:?Uso: build-live.sh <proyecto> <iso-salida>}"

if [[ "${EUID}" -ne 0 ]]; then
    printf 'La compilacion necesita privilegios de root para preparar el sistema live.\n' >&2
    exit 1
fi

if ! dpkg-query -W -f='${Status}' live-build 2>/dev/null | grep -q 'install ok installed'; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
fi
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends \
    live-build debootstrap xorriso squashfs-tools cpio rsync curl \
    isolinux syslinux-common syslinux-utils dosfstools mtools librsvg2-bin \
    debian-archive-keyring

build_dir="$(mktemp -d /var/tmp/jadevos-build.XXXXXXXX)"
cleanup() {
    rm -rf -- "$build_dir"
}
trap cleanup EXIT

cp -a "${project_dir}/live/config" "${build_dir}/config"
find "${build_dir}/config" -type f -exec sed -i 's/\r$//' {} +
theme_stage="${build_dir}/config/includes.chroot/tmp/jadevos-mactahoe"
mkdir -p "$theme_stage"
fetch_theme_source() {
    local repository="$1"
    local revision="$2"
    local checksum="$3"
    local name="$4"
    local archive="${build_dir}/${name}.tar.gz"
    local source_dir="${theme_stage}/${name}"

    curl --fail --location --retry 3 \
        "https://codeload.github.com/${repository}/tar.gz/${revision}" \
        --output "$archive"
    if ! printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check --status; then
        printf 'La suma SHA-256 de la fuente fijada %s no coincide.\n' "$name" >&2
        exit 1
    fi

    mkdir -p "$source_dir"
    tar -xzf "$archive" -C "$source_dir" --strip-components=1
    install -m 0644 "$archive" "${theme_stage}/${name}.tar.gz"
}
fetch_theme_source \
    "vinceliuice/MacTahoe-gtk-theme" \
    "0aa2a2ba1e07277a49dae9a3b90881c899d2afbe" \
    "53842037acac3cde6fed384e54878d8cc2aef2d7662287639ba1bbabdf454bb8" \
    "gtk-theme"
fetch_theme_source \
    "vinceliuice/MacTahoe-icon-theme" \
    "839848b9a8a38a92a6936e30c4abe35cc6f2546d" \
    "00cb36a3883e40687ade9f57a0c1dd3e14fda84b73efc69aa86e2be67f32ab0a" \
    "icon-theme"
updater_package="${build_dir}/config/includes.chroot/tmp/jadevOS-updater.deb"
mkdir -p "$(dirname "$updater_package")"
updater_version="$(
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${project_dir}/updater/src" \
        python3 -c 'from jadevos_updater import __version__; print(__version__)'
)"
bash "${project_dir}/updater/build-deb.sh" \
    "${updater_package}"
wallpaper_source="${project_dir}/Wallpapers"
default_wallpaper="${wallpaper_source}/JadevOS Computers BETA 4.png"
if [[ ! -d "$wallpaper_source" || ! -f "$default_wallpaper" ]]; then
    printf 'Falta la carpeta Wallpapers o el fondo predeterminado de JadevOS.\n' >&2
    exit 1
fi

wallpaper_stage="${build_dir}/config/includes.chroot/tmp/jadevos-wallpapers"
mkdir -p "$wallpaper_stage"
mapfile -d '' -t wallpaper_files < <(
    find "$wallpaper_source" -maxdepth 1 -type f \
        \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) \
        -print0 | sort -z
)
if [[ "${#wallpaper_files[@]}" -eq 0 ]]; then
    printf 'No hay fondos compatibles en %s\n' "$wallpaper_source" >&2
    exit 1
fi

for image in "${wallpaper_files[@]}"; do
    install -m 0644 "$image" "$wallpaper_stage/$(basename "$image")"
done

session_wants="${build_dir}/config/includes.chroot/etc/systemd/system/graphical.target.wants"
mkdir -p "$session_wants"
ln -sfn ../jadevos-live-session.service \
    "${session_wants}/jadevos-live-session.service"
isolinux_dir="${build_dir}/config/bootloaders/isolinux"
mkdir -p "$isolinux_dir"
mkdir -p "${build_dir}/tools"
cp "${build_dir}/config/includes.chroot/usr/bin/rsvg" "${build_dir}/tools/rsvg"
chmod 0755 "${build_dir}/tools/rsvg"
export PATH="${build_dir}/tools:${PATH}"
cp -a /usr/share/live/build/bootloaders/isolinux/. "$isolinux_dir/"
cp "${project_dir}/live/config/bootloaders/isolinux/splash.svg.in" "$isolinux_dir/splash.svg.in"
rm -f "$isolinux_dir/isolinux.bin" "$isolinux_dir/vesamenu.c32"
cp /usr/lib/ISOLINUX/isolinux.bin "$isolinux_dir/isolinux.bin"
cp /usr/lib/syslinux/modules/bios/vesamenu.c32 "$isolinux_dir/vesamenu.c32"
for module in ldlinux.c32 libcom32.c32 libutil.c32; do
    cp "/usr/lib/syslinux/modules/bios/${module}" "$isolinux_dir/${module}"
done
sed -i 's/^timeout 0$/timeout 50/' "$isolinux_dir/isolinux.cfg"
cat > "$isolinux_dir/menu.cfg" <<'EOF'
menu width 48
menu hshift 16
menu vshift 9
menu rows 6
menu helpmsgrow 22
menu tabmsgrow 22
menu tabmsg Use the arrow keys to move, and Enter to select.
menu color screen 0 #00000000 #00000000 none
menu color border 0 #00000000 #00000000 none
menu color title 0 #00000000 #00000000 none
menu color unsel 0 #ffffffff #00000000 none
menu color sel 0 #ffffffff #ff1677ff none
menu color hotkey 0 #ffffffff #00000000 none
menu color hotsel 0 #ffffffff #ff1677ff none
menu color tabmsg 0 #ffffffff #00000000 none
menu color help 0 #00000000 #00000000 none
menu color timeout 0 #00000000 #00000000 none
menu color timeout_msg 0 #00000000 #00000000 none
include live.cfg
menu end
EOF
sed -i \
    -e 's/menu label \^Live (.*failsafe)$/menu label ^Boot into Safe Mode/' \
    -e 's/menu label \^Live (.*)$/menu label ^Start JadevOS/' \
    "$isolinux_dir/live.cfg.in"
sed -i '/^label live-@FLAVOUR@-failsafe$/,/^kernel /{/^[[:space:]]*menu default$/d;}' \
    "$isolinux_dir/live.cfg.in"
(cd "$isolinux_dir" && : | cpio -o -H newc --quiet > bootlogo)
chmod 0755 \
    "${build_dir}/config/hooks/0100-jadevos-branding.hook.chroot" \
    "${build_dir}/config/includes.chroot/usr/bin/rsvg" \
    "${build_dir}/config/includes.chroot/usr/local/bin/carbon-dsk" \
    "${build_dir}/config/includes.chroot/usr/local/bin/carbon-session" \
    "${build_dir}/config/includes.chroot/usr/local/bin/carbon-snap" \
    "${build_dir}/config/includes.chroot/usr/local/lib/carbon-dsk/carbon_dsk.py" \
    "${build_dir}/config/includes.chroot/usr/local/sbin/jadevos-live-session" \
    "${build_dir}/config/includes.chroot/usr/local/bin/hyperbrowser" \
    "${build_dir}/config/includes.chroot/usr/local/lib/hyperbrowser/hyperbrowser.py" \
    "${build_dir}/config/includes.chroot/usr/local/bin/jadev-files" \
    "${build_dir}/config/includes.chroot/usr/local/lib/jadev-files/jadev_files.py" \
    "${build_dir}/config/hooks/0200-jadevOS-updater.hook.chroot" \
    "${build_dir}/config/hooks/0300-jadevOS-wallpapers.hook.chroot" \
    "${build_dir}/config/hooks/0400-jadevOS-locale.hook.chroot" \
    "${build_dir}/config/hooks/0500-jadevOS-gnome.hook.chroot" \
    "${build_dir}/config/hooks/0600-jadevOS-mactahoe.hook.chroot"
cd "$build_dir"

lb config \
    --mode debian \
    --initsystem systemd \
    --distribution trixie \
    --architectures amd64 \
    --binary-images iso-hybrid \
    --bootloader syslinux \
    --apt-recommends false \
    --archive-areas "main contrib non-free-firmware" \
    --mirror-bootstrap "http://deb.debian.org/debian" \
    --mirror-chroot "http://deb.debian.org/debian" \
    --mirror-binary "http://deb.debian.org/debian" \
    --security false \
    --firmware-binary false \
    --firmware-chroot false \
    --debian-installer false \
    --iso-application "JadevOS Computers" \
    --iso-publisher "JadevOS Computers" \
    --iso-volume "JADEVOS_1_0" \
    --bootappend-live "components quiet splash hostname=jadevos locales=en_US.UTF-8 keyboard-layouts=us timezone=Europe/Madrid live-config.nocomponents=user-setup,sddm"

lb build

image="${build_dir}/binary.hybrid.iso"
if [[ ! -s "$image" ]]; then
    printf 'live-build termino sin generar la imagen esperada: %s\n' "$image" >&2
    exit 1
fi

install -D -m 0644 "$image" "$output_iso"
printf 'ISO de JadevOS lista: %s\n' "$output_iso"
