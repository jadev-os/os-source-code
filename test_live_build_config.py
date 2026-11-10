import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class LiveBuildConfigTests(unittest.TestCase):
    def test_live_image_includes_desktop_editor_browser_and_installer(self):
        package_list = (
            ROOT / "live" / "config" / "package-lists" / "jadevos.list.chroot"
        ).read_bytes()
        self.assertNotIn(b"\r", package_list)
        packages = package_list.decode("utf-8").splitlines()

        for required_package in (
            "live-boot",
            "locales",
            "isolinux",
            "syslinux-utils",
            "calamares",
            "calamares-settings-debian",
            "plymouth",
            "plymouth-themes",
            "sddm",
            "xserver-xorg",
            "gnome-shell",
            "gnome-session",
            "gnome-session-xsession",
            "gnome-control-center",
            "gnome-tweaks",
            "gnome-shell-extension-dashtodock",
            "gnome-shell-extension-blur-my-shell",
            "gnome-shell-extension-user-theme",
            "gnome-shell-extension-prefs",
            "gnome-shell-extension-desktop-icons-ng",
            "nautilus",
            "gnome-terminal",
            "file-roller",
            "dconf-cli",
            "libglib2.0-bin",
            "libglib2.0-dev-bin",
            "libxml2-utils",
            "sassc",
            "openbox",
            "picom",
            "dunst",
            "pcmanfm",
            "wmctrl",
            "xdotool",
            "xss-lock",
            "i3lock",
            "xfce4-power-manager",
            "mate-polkit",
            "network-manager-gnome",
            "bluez",
            "blueman",
            "pavucontrol",
            "pipewire-audio",
            "pipewire-pulse",
            "wireplumber",
            "pulseaudio-utils",
            "zram-tools",
            "network-manager",
            "xdg-user-dirs",
            "mousepad",
            "python3-gi",
            "gir1.2-gtk-3.0",
            "python3-pyqt6.qtwebengine",
            "python3-pyqt6.qtsvg",
            "python3-send2trash",
            "cheese",
            "parole",
            "firefox-esr",
        ):
            with self.subTest(package=required_package):
                self.assertIn(required_package, packages)
        self.assertIn("openbox", packages)
        self.assertIn("xfce4-power-manager", packages)
        self.assertNotIn("lightdm", packages)
        self.assertNotIn("dolphin", packages)
        for removed_package in (
            "plasma-desktop",
            "plasma-workspace",
            "kwin-x11",
            "plasma-nm",
            "plasma-pa",
            "systemsettings",
            "polkit-kde-agent-1",
            "sddm-theme-breeze=4:6.3.6-1",
            "konsole",
            "ark",
        ):
            with self.subTest(removed_package=removed_package):
                self.assertNotIn(removed_package, packages)

    def test_custom_two_pane_file_manager_replaces_dolphin(self):
        includes = ROOT / "live" / "config" / "includes.chroot"
        manager = (
            includes
            / "usr"
            / "local"
            / "lib"
            / "jadev-files"
            / "jadev_files.py"
        ).read_text(encoding="utf-8")
        launcher = (includes / "usr" / "local" / "bin" / "jadev-files").read_text(
            encoding="utf-8"
        )
        desktop = (
            includes / "usr" / "share" / "applications" / "jadev-files.desktop"
        ).read_text(encoding="utf-8")
        icon = (
            includes
            / "usr"
            / "share"
            / "icons"
            / "hicolor"
            / "scalable"
            / "apps"
            / "jadev-files.svg"
        ).read_text(encoding="utf-8")
        mimeapps = (includes / "etc" / "xdg" / "mimeapps.list").read_text(
            encoding="utf-8"
        )
        build_script = (ROOT / "scripts" / "build-live.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("QFileSystemModel", manager)
        self.assertIn("from PyQt6.QtGui import (\n", manager)
        self.assertIn("    QFileSystemModel,\n", manager)
        self.assertIn("self.set_directory(Path.home(), notify=False)", manager)
        self.assertIn("QSplitter", manager)
        self.assertIn("Carpeta izquierda", manager)
        self.assertIn("Carpeta derecha", manager)
        self.assertIn("class JadevFileSystemModel", manager)
        self.assertIn('"Nombre", "Tamaño", "Tipo", "Modificado"', manager)
        self.assertIn("send2trash", manager)
        self.assertIn("setDragDropMode", manager)
        self.assertIn("create_folder", manager)
        self.assertIn("rename_selection", manager)
        self.assertIn("trash_selection", manager)
        self.assertIn("sys.excepthook = report_unhandled_exception", manager)
        self.assertIn("The file manager could not start.", manager)
        self.assertIn("Exec=/usr/local/bin/jadev-files %f", desktop)
        self.assertIn("Icon=jadev-files", desktop)
        self.assertIn("Name=Files", desktop)
        self.assertIn("GenericName=File Manager", desktop)
        self.assertIn("Keywords=file;files;explorer;", desktop)
        self.assertIn("Keywords[es]=archivo;archivos;explorador;", desktop)
        self.assertIn("inode/directory=jadev-files.desktop", mimeapps)
        self.assertIn("application/x-directory=jadev-files.desktop", mimeapps)
        self.assertIn("<svg", icon)
        self.assertIn("python3-send2trash", self.package_list())
        self.assertIn("jadev_files.py", build_script)
        self.assertNotIn("dolphin", self.package_list())

    def test_updater_deb_is_installed_in_the_live_image(self):
        project = ROOT / "updater"
        build_script = (ROOT / "scripts" / "build-live.sh").read_text(
            encoding="utf-8"
        )
        package_hook = (
            ROOT
            / "live"
            / "config"
            / "hooks"
            / "0200-jadevOS-updater.hook.chroot"
        ).read_text(encoding="utf-8")
        package_builder = (project / "build-deb.sh").read_text(encoding="utf-8")

        self.assertIn("updater/build-deb.sh", build_script)
        self.assertIn("jadevOS-updater.deb", build_script)
        self.assertIn("dpkg -i \"$package\"", package_hook)
        self.assertIn("rm -f \"$package\"", package_hook)
        self.assertIn("python3-pyqt6", self.package_list())
        self.assertIn("pkexec", self.package_list())
        self.assertIn("polkitd", self.package_list())
        self.assertIn("Recommends: mate-polkit", package_builder)
        self.assertFalse(
            (project / "data" / "jadevOS-updater-autostart.desktop").exists()
        )
        self.assertNotIn("jadevOS-updater-autostart", package_builder)
        self.assertNotIn("/etc/xdg/autostart", package_builder)
        updater_desktop = (
            project / "data" / "jadevOS-updater.desktop"
        ).read_text(encoding="utf-8")
        self.assertIn("Name=Software Updater", updater_desktop)
        self.assertIn("Name[es]=Actualizador de software", updater_desktop)
        self.assertIn("GenericName=Software Updater", updater_desktop)
        self.assertIn("Keywords=updater;update;software;", updater_desktop)

    def test_english_default_and_spanish_language_switch_are_configured(self):
        packages = self.package_list()
        build_script = (ROOT / "scripts" / "build-live.sh").read_text(
            encoding="utf-8"
        )
        locale_hook = (
            ROOT / "live" / "config" / "hooks" / "0400-jadevOS-locale.hook.chroot"
        ).read_text(encoding="utf-8")

        self.assertIn("locales", packages)
        self.assertIn(
            "locales=en_US.UTF-8 keyboard-layouts=us",
            build_script,
        )
        self.assertIn("locale-gen en_US.UTF-8 es_ES.UTF-8", locale_hook)
        self.assertIn("update-locale LANG=en_US.UTF-8", locale_hook)
        self.assertIn("network-manager-gnome", packages)

    def test_carbon_wallpapers_are_installed_and_default_is_used_by_sddm(self):
        wallpaper_source = ROOT / "Wallpapers"
        source_images = [
            path
            for path in wallpaper_source.iterdir()
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
        build_script = (ROOT / "scripts" / "build-live.sh").read_text(
            encoding="utf-8"
        )
        wallpaper_hook = (
            ROOT
            / "live"
            / "config"
            / "hooks"
            / "0300-jadevOS-wallpapers.hook.chroot"
        ).read_text(encoding="utf-8")
        shell = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "usr"
            / "local"
            / "lib"
            / "carbon-dsk"
            / "carbon_dsk.py"
        ).read_text(encoding="utf-8")
        sddm_theme = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "usr"
            / "share"
            / "sddm"
            / "themes"
            / "jadevos"
        )
        sddm_config = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "etc"
            / "sddm.conf.d"
            / "10-jadevOS.conf"
        ).read_text(encoding="utf-8")
        includes = ROOT / "live" / "config" / "includes.chroot"

        source_image_names = {path.name for path in source_images}
        self.assertIn("JadevOS Computers BETA 4.png", source_image_names)
        self.assertGreater(len(source_images), 0)
        self.assertIn('"${project_dir}/Wallpapers"', build_script)
        self.assertIn(
            'default_wallpaper="${wallpaper_source}/JadevOS Computers BETA 4.png"',
            build_script,
        )
        self.assertNotIn("KPackageStructure", build_script)
        self.assertIn('destination=/usr/share/backgrounds/jadevos', wallpaper_hook)
        self.assertIn(
            'cp -a "${staged_wallpapers}/." "$destination/"', wallpaper_hook
        )
        self.assertIn(
            'default_destination=/usr/share/backgrounds/jadevos-default-wallpaper.jpg',
            wallpaper_hook,
        )
        self.assertIn(
            'default_image="${staged_wallpapers}/JadevOS Computers BETA 4.png"',
            wallpaper_hook,
        )
        self.assertIn(
            '"${destination}/JadevOS Computers BETA 4.png"',
            wallpaper_hook,
        )
        self.assertIn("name 'debian-*.xml' -delete", wallpaper_hook)
        self.assertIn("-name wallpaper -o -name wallpaper-withlogo", wallpaper_hook)
        self.assertIn(
            "/usr/share/gnome-background-properties/jadevos.xml", wallpaper_hook
        )
        self.assertIn("html.escape(image.stem)", wallpaper_hook)
        self.assertIn("html.escape(str(image))", wallpaper_hook)
        self.assertIn("<filename>", wallpaper_hook)
        self.assertIn('install -D -m 0644 "$default_image" "$default_destination"', wallpaper_hook)
        self.assertIn("Current=jadevos", sddm_config)
        self.assertIn("RememberLastSession=true", sddm_config)
        gnome_hook = (
            ROOT
            / "live"
            / "config"
            / "hooks"
            / "0500-jadevOS-gnome.hook.chroot"
        ).read_text(encoding="utf-8")
        self.assertIn("Session=gnome-xorg.desktop", gnome_hook)
        trust_launcher = (
            includes / "usr" / "local" / "bin" / "jadevos-trust-desktop-launchers"
        )
        trust_autostart = (
            includes
            / "etc"
            / "xdg"
            / "autostart"
            / "jadevos-trust-desktop-launchers.desktop"
        )
        self.assertFalse(trust_launcher.exists())
        self.assertFalse(trust_autostart.exists())
        self.assertNotIn("jadevos-trust-desktop-launchers", build_script)
        self.assertIn("0500-jadevOS-gnome.hook.chroot", build_script)
        self.assertNotIn("debian-elarun", sddm_config)
        theme_qml = (sddm_theme / "Main.qml").read_text(encoding="utf-8")
        self.assertIn("JadevOS", theme_qml)
        self.assertIn("jadevos-default-wallpaper.jpg", theme_qml)
        self.assertNotIn("Debian", theme_qml)
        theme_config = (sddm_theme / "theme.conf").read_text(encoding="utf-8")
        self.assertIn("background=/usr/share/backgrounds/jadevos-default-wallpaper.jpg", theme_config)
        pcmanfm_config = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "etc"
            / "skel"
            / ".config"
            / "pcmanfm"
            / "default"
            / "pcmanfm.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("wallpaper=/usr/share/backgrounds/jadevos-default-wallpaper.jpg", pcmanfm_config)
        self.assertIn("wallpaper_mode=5", pcmanfm_config)

    def test_hyperbrowser_is_installed_as_the_custom_web_browser(self):
        includes = ROOT / "live" / "config" / "includes.chroot"
        launcher = (includes / "usr" / "local" / "bin" / "hyperbrowser").read_text(
            encoding="utf-8"
        )
        browser = (
            includes
            / "usr"
            / "local"
            / "lib"
            / "hyperbrowser"
            / "hyperbrowser.py"
        ).read_text(encoding="utf-8")
        desktop = (
            includes / "usr" / "share" / "applications" / "hyperbrowser.desktop"
        ).read_text(encoding="utf-8")
        icon = (
            includes
            / "usr"
            / "share"
            / "icons"
            / "hicolor"
            / "scalable"
            / "apps"
            / "hyperbrowser.svg"
        ).read_text(encoding="utf-8")
        build_script = (ROOT / "scripts" / "build-live.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("python3-pyqt6.qtwebengine", self.package_list())
        self.assertIn("QWebEngineView", browser)
        self.assertIn("QTabWidget", browser)
        self.assertIn("QWebEngineDownloadRequest.DownloadState", browser)
        self.assertIn('HOME_URL = QUrl("https://www.google.com/")', browser)
        self.assertIn("view.setUrl(url or HOME_URL)", browser)
        self.assertIn("view.setUrl(HOME_URL)", browser)
        self.assertIn("DuckDuckGo", browser)
        self.assertIn("PersistentCookiesPolicy.ForcePersistentCookies", browser)
        self.assertIn("candidate.scheme().lower() in {\"http\", \"https\"}", browser)
        self.assertIn("python3 /usr/local/lib/hyperbrowser/hyperbrowser.py", launcher)
        self.assertIn("Exec=/usr/local/bin/hyperbrowser", desktop)
        self.assertIn("Icon=hyperbrowser", desktop)
        self.assertIn("<svg", icon)
        self.assertIn("hyperbrowser.py", build_script)

    def package_list(self):
        return (
            ROOT / "live" / "config" / "package-lists" / "jadevos.list.chroot"
        ).read_text(encoding="utf-8").splitlines()

    def test_live_build_targets_debian_and_creates_bootable_iso(self):
        script = (ROOT / "scripts" / "build-live.sh").read_text(encoding="utf-8")

        self.assertIn("--distribution trixie", script)
        self.assertIn("--initsystem systemd", script)
        self.assertIn("--architectures amd64", script)
        self.assertIn("--binary-images iso-hybrid", script)
        self.assertIn("--bootloader syslinux", script)
        self.assertIn("--apt-recommends false", script)
        self.assertIn("--security false", script)
        self.assertIn("splash.svg.in", script)
        self.assertIn("menu width 48", script)
        self.assertIn("menu hshift 16", script)
        self.assertIn("menu vshift 9", script)
        self.assertIn("menu color screen 0 #00000000 #00000000 none", script)
        self.assertIn("menu color sel 0 #ffffffff #ff1677ff none", script)
        self.assertIn("menu tabmsg Use the arrow keys to move, and Enter to select.", script)
        self.assertIn("menu label ^Start JadevOS", script)
        self.assertIn("menu label ^Boot into Safe Mode", script)
        self.assertNotIn("include stdmenu.cfg", script)
        self.assertIn("quiet splash hostname=jadevos", script)
        self.assertIn("live-config.nocomponents=user-setup,sddm", script)
        self.assertIn("s/^timeout 0$/timeout 50/", script)
        self.assertIn("live-@FLAVOUR@-failsafe", script)
        self.assertIn("graphical.target.wants", script)
        self.assertIn("ln -sfn ../jadevos-live-session.service", script)
        self.assertIn("/usr/lib/ISOLINUX/isolinux.bin", script)
        self.assertIn("syslinux-utils", script)
        for module in ("ldlinux.c32", "libcom32.c32", "libutil.c32"):
            with self.subTest(module=module):
                self.assertIn(module, script)
        self.assertIn("cpio -o -H newc", script)
        self.assertIn("librsvg2-bin", script)
        self.assertIn("binary.hybrid.iso", script)
        security_repo = (
            ROOT / "live" / "config" / "archives" / "security.list.chroot"
        ).read_text(encoding="utf-8")
        self.assertIn("trixie-security", security_repo)

    def test_installer_is_app_drawer_only_and_custom_calamares_branding_exists(self):
        desktop_launcher = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "etc"
            / "skel"
            / "Desktop"
            / "Install-JadevOS.desktop"
        )
        branding = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "etc"
            / "calamares"
            / "branding"
            / "jadevOS"
            / "branding.desc"
        ).read_text(encoding="utf-8")
        hook = (
            ROOT
            / "live"
            / "config"
            / "hooks"
            / "0100-jadevos-branding.hook.chroot"
        ).read_text(encoding="utf-8")
        self.assertIn("sddm-theme-debian-elarun sddm-theme-debian-breeze", hook)
        self.assertIn('dpkg --purge "$theme_package"', hook)

        self.assertFalse(desktop_launcher.exists())
        self.assertIn("calamares-install-debian.desktop", hook)
        self.assertIn("-iname 'calamares*.desktop'", hook)
        self.assertIn("jadevos-installer.desktop", hook)
        self.assertIn("pkexec /usr/bin/calamares", hook)
        self.assertIn("TryExec=/usr/bin/pkexec", hook)
        self.assertIn("Icon=jadevos-installer", hook)
        self.assertIn("plymouth-set-default-theme --rebuild-initrd jadevos", hook)
        self.assertIn("/etc/skel/Desktop/Install-JadevOS.desktop", hook)
        self.assertIn("/etc/skel/Desktop/JadevOS-About.desktop", hook)
        self.assertIn("chmod 0644 /usr/share/applications/jadevos-installer.desktop", hook)
        self.assertIn("rm -f", hook)
        self.assertIn("spinner.plymouth", hook)
        self.assertIn("Description=JadevOS black boot screen with white text and spinner", hook)
        self.assertIn("BackgroundStartColor=0x000000", hook)
        self.assertIn("BackgroundEndColor=0x000000", hook)
        self.assertIn("UseProgressBar=false", hook)
        self.assertIn('"$theme_dir/watermark.png"', hook)
        self.assertIn("/usr/share/desktop-base/debian-logos/logo-text-version-64.png", hook)
        self.assertIn("dpkg-divert --local --rename --add", hook)
        self.assertIn("MessageBelowAnimation=false", hook)
        self.assertIn("-e '/^SubTitle=BETA 4$/d'", hook)
        self.assertIn("/usr/share/applications/jadevos-about.desktop", hook)
        self.assertIn("/usr/local/bin/jadevos-about", hook)
        self.assertIn("Title=JadevOS", hook)
        self.assertIn("MessageBelowAnimation=false", hook)
        self.assertIn("s/^ID=debian$/ID=jadevos/", hook)
        self.assertIn("-e '/^SubTitle=BETA 4$/d'", hook)
        self.assertIn("plymouth-set-default-theme --rebuild-initrd jadevos", hook)
        self.assertIn("systemctl enable sddm.service", hook)
        self.assertIn("systemctl enable zramswap.service", hook)
        self.assertIn("productName:         JadevOS Computers", branding)
        self.assertIn('slideshow:               "show.qml"', branding)
        self.assertIn("slideshowAPI: 2", branding)
        self.assertIn("branding: jadevOS", hook)
        slideshow = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "etc"
            / "calamares"
            / "branding"
            / "jadevOS"
            / "show.qml"
        ).read_text(encoding="utf-8")
        self.assertIn("import calamares.slideshow 1.0", slideshow)
        self.assertIn("Bienvenido a JadevOS Computers", slideshow)
        live_session_service = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "etc"
            / "systemd"
            / "system"
            / "jadevos-live-session.service"
        ).read_text(encoding="utf-8")
        self.assertIn("ConditionKernelCommandLine=boot=live", live_session_service)
        self.assertIn("After=live-config.service", live_session_service)
        live_session_script = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "usr/local/sbin/jadevos-live-session"
        ).read_text(encoding="utf-8")
        self.assertIn('session_user="jadevos-session-', live_session_script)
        self.assertIn('useradd --create-home --shell /bin/bash --groups sudo "$session_user"', live_session_script)
        self.assertNotIn('live_user="live"', live_session_script)
        self.assertIn("chpasswd", live_session_script)
        self.assertIn("boot=live", live_session_script)
        self.assertIn("20-jadevOS-live-autologin.conf", live_session_script)
        self.assertIn("Session=gnome-xorg.desktop", live_session_script)
        build_script = (ROOT / "scripts" / "build-live.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "live-config.nocomponents=user-setup,sddm",
            build_script,
        )
        self.assertNotIn("username=jadev", build_script)
        sddm = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "etc"
            / "sddm.conf.d"
            / "10-jadevOS.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("DisplayServer=x11", sddm)
        self.assertNotIn("[Autologin]", sddm)
        self.assertNotIn("User=jadev", sddm)
        self.assertIn("Current=jadevos", sddm)
        release = (
            ROOT / "live" / "config" / "includes.chroot" / "etc" / "os-release"
        ).read_text(encoding="utf-8")
        self.assertIn('PRETTY_NAME="JadevOS Computers 1.0 BETA 4"', release)
        self.assertIn("ID=jadevos", release)
        self.assertIn('VERSION="1.0 BETA 4"', release)
        self.assertIn("JadevOS Computers 1.0 BETA 4", release)
        library_release = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "usr"
            / "lib"
            / "os-release"
        ).read_text(encoding="utf-8")
        self.assertIn('PRETTY_NAME="JadevOS Computers 1.0 BETA 4"', library_release)
        self.assertIn("ID=jadevos", library_release)
        self.assertNotIn("Debian", library_release)
        issue = (
            ROOT / "live" / "config" / "includes.chroot" / "etc" / "issue"
        ).read_text(encoding="utf-8")
        self.assertIn("JadevOS Computers 1.0 BETA 4", issue)
        splash = (
            ROOT / "live" / "config" / "bootloaders" / "isolinux" / "splash.svg.in"
        ).read_text(encoding="utf-8")
        self.assertIn(">JadevOS</text>", splash)
        self.assertIn("#10224d", splash)
        self.assertNotIn("Debian", splash)
        self.assertIn('version:             "1.0 BETA 4"', branding)

    def test_jadevos_about_application_and_shortcut_are_removed(self):
        includes = ROOT / "live" / "config" / "includes.chroot"
        self.assertFalse(
            (includes / "etc" / "skel" / "Desktop" / "JadevOS-About.desktop").exists()
        )
        self.assertFalse(
            (includes / "usr" / "local" / "bin" / "jadevos-about").exists()
        )
        hook = (
            ROOT
            / "live"
            / "config"
            / "hooks"
            / "0100-jadevos-branding.hook.chroot"
        ).read_text(encoding="utf-8")
        self.assertIn("/usr/share/applications/jadevos-about.desktop", hook)
        self.assertIn("/usr/local/bin/jadevos-about", hook)

    def test_gnome_is_default_and_carbon_remains_available_without_kde(self):
        package_list = (
            ROOT / "live" / "config" / "package-lists" / "jadevos.list.chroot"
        ).read_text(encoding="utf-8")
        includes = ROOT / "live" / "config" / "includes.chroot"
        live_session = (
            includes / "usr" / "local" / "sbin" / "jadevos-live-session"
        ).read_text(encoding="utf-8")
        build_script = (ROOT / "scripts" / "build-live.sh").read_text(
            encoding="utf-8"
        )
        sddm = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "etc"
            / "sddm.conf.d"
            / "10-jadevOS.conf"
        ).read_text(encoding="utf-8")
        gnome_defaults = (
            includes / "etc" / "dconf" / "db" / "local.d" / "00-jadevos-gnome"
        ).read_text(encoding="utf-8")
        dconf_profile = (includes / "etc" / "dconf" / "profile" / "user").read_text(
            encoding="utf-8"
        )
        gnome_hook = (
            ROOT
            / "live"
            / "config"
            / "hooks"
            / "0500-jadevOS-gnome.hook.chroot"
        ).read_text(encoding="utf-8")
        theme_hook = (
            ROOT
            / "live"
            / "config"
            / "hooks"
            / "0600-jadevOS-mactahoe.hook.chroot"
        ).read_text(encoding="utf-8")

        self.assertIn("gnome-session-xsession", package_list)
        self.assertIn("gnome-tweaks", package_list)
        self.assertIn("gnome-shell-extension-dashtodock", package_list)
        self.assertIn("gnome-shell-extension-blur-my-shell", package_list)
        self.assertIn("gnome-shell-extension-user-theme", package_list)
        self.assertIn("gnome-shell-extension-prefs", package_list)
        self.assertIn("dock-fixed=false", gnome_defaults)
        self.assertIn("transparency-mode='FIXED'", gnome_defaults)
        self.assertIn("apply-custom-theme=true", gnome_defaults)
        self.assertIn("gnome-shell-extension-desktop-icons-ng", package_list)
        self.assertIn("'blur-my-shell@aunetx'", gnome_defaults)
        self.assertIn("dock-position='BOTTOM'", gnome_defaults)
        self.assertIn("autohide=true", gnome_defaults)
        self.assertIn("button-layout='close,minimize,maximize:'", gnome_defaults)
        self.assertIn(
            "'user-theme@gnome-shell-extensions.gcampax.github.com'",
            gnome_defaults,
        )
        self.assertIn("name='MacTahoe-Dark-orange'", gnome_defaults)
        self.assertIn("gtk-theme='MacTahoe-Dark-orange'", gnome_defaults)
        self.assertIn("icon-theme='MacTahoe-orange-dark'", gnome_defaults)
        self.assertIn("color-scheme='prefer-dark'", gnome_defaults)
        for removed_package in ("plasma-", "kwin", "systemsettings", "konsole", "ark"):
            self.assertNotIn(removed_package, package_list)
        self.assertIn("Session=gnome-xorg.desktop", live_session)
        self.assertIn('useradd --create-home --shell /bin/bash --groups sudo "$session_user"', live_session)
        self.assertIn('session_user="jadevos-session-', live_session)
        self.assertNotIn('session_user="live"', live_session)
        self.assertIn("live-config.nocomponents=user-setup,sddm", build_script)
        self.assertNotIn("username=jadev", build_script)
        self.assertFalse((includes / "usr" / "share" / "xsessions" / "jadevos.desktop").exists())
        self.assertNotIn("[Autologin]", sddm)
        self.assertIn("Current=jadevos", sddm)
        self.assertIn("RememberLastSession=true", sddm)
        self.assertIn("system-db:local", dconf_profile)
        self.assertIn("dash-to-dock@micxgx.gmail.com", gnome_defaults)
        self.assertIn("ding@rastersoft.com", gnome_defaults)
        self.assertIn("favorite-apps=['firefox-esr.desktop', 'org.gnome.Nautilus.desktop']", gnome_defaults)
        self.assertIn("dock-position='BOTTOM'", gnome_defaults)
        self.assertIn("dock-fixed=false", gnome_defaults)
        self.assertIn("autohide=true", gnome_defaults)
        self.assertIn("picture-uri='file:///usr/share/backgrounds/jadevos-default-wallpaper.jpg'", gnome_defaults)
        self.assertIn("dconf update", gnome_hook)
        self.assertIn("--libadwaita", theme_hook)
        self.assertIn("--shell -i simple -p 30 -h smaller -sf", theme_hook)
        self.assertIn("/usr/share/themes", theme_hook)
        self.assertIn("/usr/share/icons", theme_hook)
        self.assertIn("/etc/skel/.config/gtk-4.0", theme_hook)
        self.assertIn('chown -R nobody:nogroup "$gtk_source"', theme_hook)
        self.assertIn("chmod 1777 /tmp", theme_hook)
        self.assertNotIn("BASH_XTRACEFD", theme_hook)
        self.assertIn("USER=root TERM=xterm bash", theme_hook)
        self.assertIn("MacTahoe-gtk-theme", build_script)
        self.assertIn("MacTahoe-icon-theme", build_script)
        self.assertIn(
            "53842037acac3cde6fed384e54878d8cc2aef2d7662287639ba1bbabdf454bb8",
            build_script,
        )
        self.assertIn(
            "00cb36a3883e40687ade9f57a0c1dd3e14fda84b73efc69aa86e2be67f32ab0a",
            build_script,
        )
        self.assertIn("Session=gnome-xorg.desktop", gnome_hook)
        self.assertFalse(
            (includes / "usr" / "share" / "xsessions" / "jadevos.desktop").exists()
        )
        self.assertTrue(
            (includes / "usr" / "share" / "xsessions" / "carbon-dsk.desktop").is_file()
        )
        xfce_profile = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "etc"
            / "skel"
            / ".config"
            / "xfce4"
        )
        self.assertFalse(xfce_profile.exists())

    def test_carbon_desktop_is_integrated_without_jadev_settings(self):
        includes = ROOT / "live" / "config" / "includes.chroot"
        shell = (
            includes / "usr" / "local" / "lib" / "carbon-dsk" / "carbon_dsk.py"
        ).read_text(encoding="utf-8")
        shell_launcher = (includes / "usr" / "local" / "bin" / "carbon-dsk").read_text(
            encoding="utf-8"
        )
        session = (
            includes / "usr" / "share" / "xsessions" / "carbon-dsk.desktop"
        ).read_text(encoding="utf-8")
        session_launcher = (
            includes / "usr" / "local" / "bin" / "carbon-session"
        ).read_text(encoding="utf-8")
        window_snap = (
            includes / "usr" / "local" / "bin" / "carbon-snap"
        ).read_text(encoding="utf-8")
        openbox_config = (
            includes / "etc" / "xdg" / "openbox" / "rc.xml"
        ).read_text(encoding="utf-8")
        compositor_config = (
            includes / "etc" / "xdg" / "picom.conf"
        ).read_text(encoding="utf-8")
        pcmanfm_config = (
            includes
            / "etc"
            / "skel"
            / ".config"
            / "pcmanfm"
            / "default"
            / "pcmanfm.conf"
        ).read_text(encoding="utf-8")
        self.assertFalse(
            (includes / "usr" / "share" / "applications" / "jadevos-settings.desktop").exists()
        )
        self.assertFalse(
            (includes / "etc" / "skel" / "Desktop" / "JadevOS-Settings.desktop").exists()
        )
        self.assertFalse(
            (includes / "usr" / "local" / "bin" / "jadevos-settings").exists()
        )
        self.assertFalse(
            (
                includes
                / "usr"
                / "share"
                / "icons"
                / "hicolor"
                / "scalable"
                / "apps"
                / "jadevos-settings.svg"
            ).exists()
        )
        build_script = (ROOT / "scripts" / "build-live.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("desktop_applications()", shell)
        self.assertIn("Gio.DesktopAppInfo.new_from_filename", shell)
        self.assertIn("run_lock_screen", shell)
        self.assertIn("application_icon(icon", shell)
        self.assertIn('QIcon.setThemeName(theme)', shell)
        self.assertIn("button.setIconSize(QSize(24, 24))", shell)
        self.assertNotIn("button.setText(name)", shell)
        self.assertIn("self.adjustSize()", shell)
        self.assertIn('self.clock.setText(now.toString("HH:mm"))', shell)
        self.assertIn('for name, icon, fallback in (', shell)
        self.assertIn("wallpaper=/usr/share/backgrounds/jadevos-default-wallpaper.jpg", pcmanfm_config)
        self.assertIn("nm-connection-editor", shell)
        self.assertIn("nmcli", shell)
        self.assertIn("bluetoothctl", shell)
        self.assertIn("pavucontrol", shell)
        self.assertIn("Name=Carbon DSK", session)
        self.assertIn("Exec=carbon-session", session)
        self.assertIn("openbox --config-file", session_launcher)
        self.assertIn("start_component \"picom compositor\" picom", session_launcher)
        self.assertIn("start_component \"desktop icons and wallpaper\" pcmanfm --desktop", session_launcher)
        self.assertIn('pcmanfm --wallpaper-mode=crop --set-wallpaper="$wallpaper"', session_launcher)
        self.assertIn('class CarbonDock(QWidget):', shell)
        self.assertIn('class CarbonPanel(QWidget):', shell)
        self.assertIn("wmctrl", window_snap)
        self.assertIn('key="A-Tab"', openbox_config)
        self.assertIn('key="A-F9"', openbox_config)
        self.assertIn('key="A-F10"', openbox_config)
        self.assertIn('key="A-F11"', openbox_config)
        self.assertIn('key="W-Left"', openbox_config)
        self.assertIn('action name="ToggleMaximizeFull"', openbox_config)
        self.assertIn('<titleLayout>NLIMC</titleLayout>', openbox_config)
        self.assertIn('backend = "xrender";', compositor_config)
        self.assertNotIn("plasma-apply", shell)
        self.assertNotIn("kcm_", shell)
        self.assertIn('if [ "$#" -eq 0 ]; then', shell_launcher)
        self.assertIn("carbon_dsk.py \"$@\"", shell_launcher)
        self.assertNotIn("run_settings", shell)
        self.assertNotIn("jadevos-settings", shell)
        self.assertNotIn("JadevOS Settings", shell)
        self.assertIn("carbon-session", build_script)
        self.assertIn("carbon-snap", build_script)
        self.assertNotIn("jadevos-apply-carbon-theme", build_script)

    def test_operating_system_codename_is_kiwi_everywhere(self):
        for release_file in (
            ROOT / "live" / "config" / "includes.chroot" / "etc" / "os-release",
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "usr"
            / "lib"
            / "os-release",
        ):
            with self.subTest(path=release_file):
                release = release_file.read_text(encoding="utf-8")
                self.assertIn("VERSION_CODENAME=kiwi", release)
                self.assertNotIn("VERSION_CODENAME=jadevos", release)

    def test_zram_is_enabled_for_compressed_memory_swap(self):
        settings = (
            ROOT
            / "live"
            / "config"
            / "includes.chroot"
            / "etc"
            / "default"
            / "zramswap"
        ).read_text(encoding="utf-8")

        self.assertIn("ALGO=lz4", settings)
        self.assertIn("PERCENT=50", settings)
        self.assertIn("PRIORITY=100", settings)


if __name__ == "__main__":
    unittest.main()
