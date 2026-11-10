#!/usr/bin/python3
from __future__ import annotations

import configparser
import re
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QDateTime, QSize, Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)


STYLE = """
QWidget { color: #e8f0f1; font-family: "Noto Sans"; font-size: 10pt; }
QMainWindow, QDialog { background: #11191d; }
QFrame#card { background: #1b282e; border: 1px solid #2d4047; border-radius: 12px; }
QPushButton {
  background: #23343a; border: 1px solid #385057; border-radius: 9px;
  padding: 10px 14px; text-align: left;
}
QPushButton:hover { background: #3b332f; border-color: #ff9a54; }
QPushButton:pressed { background: #50311f; }
QLineEdit { background: #1b282e; border: 1px solid #385057; border-radius: 9px; padding: 10px; }
QListWidget { background: transparent; border: 0; outline: 0; }
QListWidget::item { padding: 9px; border-radius: 8px; }
QListWidget::item:selected, QListWidget::item:hover { background: #493327; }
QLabel#muted { color: #9eb0b4; }
QLabel#heading { font-size: 19pt; font-weight: 600; }
"""


def configure_icon_theme() -> None:
    QIcon.setThemeSearchPaths(["/usr/share/icons", "/usr/local/share/icons"])
    theme = "Papirus" if Path("/usr/share/icons/Papirus").is_dir() else "hicolor"
    QIcon.setThemeName(theme)


def application_icon(
    name: str, fallback: QStyle.StandardPixmap = QStyle.StandardPixmap.SP_ComputerIcon
) -> QIcon:
    icon_path = Path(name)
    if icon_path.is_absolute() and icon_path.is_file():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            return icon
    icon = QIcon.fromTheme(name)
    if not icon.isNull():
        return icon
    return QApplication.style().standardIcon(fallback)


def desktop_applications() -> list[tuple[str, str, Path]]:
    entries: dict[str, tuple[str, str, Path]] = {}
    roots = [
        Path("/usr/share/applications"),
        Path("/usr/local/share/applications"),
        Path.home() / ".local/share/applications",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.desktop"):
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                parser.read(path, encoding="utf-8")
                entry = parser["Desktop Entry"]
                if (
                    entry.get("Type") != "Application"
                    or entry.getboolean("Hidden", fallback=False)
                    or entry.getboolean("NoDisplay", fallback=False)
                    or entry.getboolean("Terminal", fallback=False)
                    or not entry.get("Exec")
                    or (
                        entry.get("OnlyShowIn")
                        and "Carbon" not in entry.get("OnlyShowIn", "").split(";")
                    )
                    or "Carbon" in entry.get("NotShowIn", "").split(";")
                ):
                    continue
                name = entry.get("Name", path.stem)
                icon = entry.get("Icon", "application-x-executable")
                entries[path.name] = (name, icon, path)
            except (OSError, KeyError, configparser.Error, ValueError):
                continue
    return sorted(entries.values(), key=lambda app: app[0].casefold())


def launch_desktop_file(path: Path) -> None:
    try:
        from gi.repository import Gio, GLib
    except ImportError as error:
        QMessageBox.critical(None, "Carbon DSK", f"Application support is unavailable:\n{error}")
        return
    try:
        application = Gio.DesktopAppInfo.new_from_filename(str(path))
        if application is None:
            raise RuntimeError(f"Invalid application entry: {path}")
        if not application.launch([], None):
            raise RuntimeError(f"The application refused to start: {path}")
    except (GLib.Error, RuntimeError) as error:
        QMessageBox.critical(None, "Carbon DSK", f"Could not launch this application:\n{error}")


class ApplicationDrawer(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Applications")
        self.setMinimumSize(420, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search applications")
        self.listing = QListWidget()
        self.listing.setIconSize(QSize(24, 24))
        layout.addWidget(self.search)
        layout.addWidget(self.listing, 1)
        self.entries = desktop_applications()
        self.search.textChanged.connect(self.populate)
        self.listing.itemClicked.connect(self.open_item)
        self.populate()

    def populate(self) -> None:
        needle = self.search.text().casefold()
        self.listing.clear()
        for name, icon, path in self.entries:
            if needle not in name.casefold():
                continue
            item = QListWidgetItem(
                application_icon(icon, QStyle.StandardPixmap.SP_ComputerIcon), name
            )
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.listing.addItem(item)

    def open_item(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(path, Path):
            launch_desktop_file(path)
            self.accept()


class CarbonPanel(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Window
            | Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setObjectName("carbonPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(
            "#carbonPanel { background: rgba(17, 26, 31, 238); "
            "border: 1px solid rgba(115, 150, 158, 120); border-radius: 14px; }"
            "#carbonPanel QPushButton { background: rgba(35, 52, 58, 150); "
            "border: 0; border-radius: 8px; padding: 0; text-align: center; }"
            "#carbonPanel QPushButton:hover { background: rgba(255, 154, 84, 150); }"
            "#carbonPanel QLabel { background: transparent; padding: 0; }"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 3, 8, 3)
        row.setSpacing(4)
        brand = QPushButton()
        brand.setIcon(application_icon("computer", QStyle.StandardPixmap.SP_ComputerIcon))
        brand.setIconSize(QSize(18, 18))
        brand.setFixedSize(30, 30)
        brand.setToolTip("JadevOS")
        brand.clicked.connect(self.show_quick_menu)
        row.addWidget(brand)
        self.workspaces: list[QPushButton] = []
        for index in range(4):
            button = QPushButton()
            button.setFixedSize(26, 26)
            button.setToolTip(f"Workspace {index + 1}")
            button.clicked.connect(
                lambda _checked=False, target=index: self.switch_workspace(target)
            )
            self.workspaces.append(button)
            row.addWidget(button)
        row.addStretch(1)
        self.clock = QLabel()
        self.clock.setMinimumWidth(58)
        self.clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.clock)
        row.addStretch(1)
        self.control_buttons: dict[str, QPushButton] = {}
        for name, icon, fallback in (
            ("Network", "network-wireless", QStyle.StandardPixmap.SP_DriveNetIcon),
            ("Sound", "audio-volume-high", QStyle.StandardPixmap.SP_MediaVolume),
            ("Bluetooth", "bluetooth", QStyle.StandardPixmap.SP_ComputerIcon),
        ):
            button = QPushButton()
            button.setIcon(application_icon(icon, fallback))
            button.setIconSize(QSize(16, 16))
            button.setFixedSize(28, 28)
            button.setToolTip(name)
            button.clicked.connect(
                lambda _checked=False, target=name: self.open_control(target)
            )
            self.control_buttons[name] = button
            row.addWidget(button)
        self.status = QPushButton()
        self.status.setIcon(application_icon("preferences-system"))
        self.status.setIconSize(QSize(16, 16))
        self.status.setFixedSize(28, 28)
        self.status.setToolTip("Quick settings")
        self.status.clicked.connect(self.show_quick_menu)
        row.addWidget(self.status)
        self.refresh_clock()
        timer = QTimer(self)
        timer.timeout.connect(self.refresh_clock)
        timer.start(1000)
        indicator_timer = QTimer(self)
        indicator_timer.timeout.connect(self.refresh_indicators)
        indicator_timer.start(10000)
        QTimer.singleShot(0, self.refresh_indicators)
        screen = QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.geometry()
            width = min(600, geometry.width() - 24)
            self.setGeometry(
                geometry.x() + (geometry.width() - width) // 2,
                geometry.y() + 10,
                width,
                38,
            )
        self.show()
        workspace_timer = QTimer(self)
        workspace_timer.timeout.connect(self.refresh_workspaces)
        workspace_timer.start(1500)
        QTimer.singleShot(0, self.refresh_workspaces)

    def refresh_clock(self) -> None:
        now = QDateTime.currentDateTime()
        self.clock.setText(now.toString("HH:mm"))
        self.clock.setToolTip(now.toString("dddd, d MMMM yyyy"))

    def refresh_indicators(self) -> None:
        try:
            network = subprocess.run(
                ["nmcli", "-t", "-f", "STATE", "general"],
                capture_output=True,
                text=True,
                check=False,
                timeout=3,
            )
            network_state = (
                network.stdout.strip() if network.returncode == 0 else "Network"
            )
        except (OSError, subprocess.SubprocessError) as error:
            print(f"Carbon DSK network indicator unavailable: {error}", file=sys.stderr)
            network_state = "Network"
        try:
            audio = subprocess.run(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                capture_output=True,
                text=True,
                check=False,
                timeout=3,
            )
            audio_output = audio.stdout if audio.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError) as error:
            print(f"Carbon DSK audio indicator unavailable: {error}", file=sys.stderr)
            audio_output = ""
        volume_match = re.search(r"(\d+)%", audio_output)
        volume = f"{volume_match.group(1)}%" if volume_match else "Sound"
        batteries = sorted(Path("/sys/class/power_supply").glob("BAT*/capacity"))
        battery = f"{read_file(batteries[0], '?')}%" if batteries else ""
        self.control_buttons["Network"].setToolTip(f"Network: {network_state}")
        self.control_buttons["Sound"].setToolTip(f"Sound: {volume}")
        self.control_buttons["Bluetooth"].setToolTip("Bluetooth settings")
        indicator_text = f"Quick settings · {network_state} · Sound {volume}"
        if battery:
            indicator_text += f" · Battery {battery}"
        self.status.setToolTip(indicator_text)

    def refresh_workspaces(self) -> None:
        try:
            result = subprocess.run(
                ["wmctrl", "-d"],
                capture_output=True,
                text=True,
                check=True,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError) as error:
            print(f"Carbon DSK workspace indicator unavailable: {error}", file=sys.stderr)
            return
        for index, line in enumerate(result.stdout.splitlines()):
            if index >= len(self.workspaces):
                break
            active = "*" in line.split()
            self.workspaces[index].setStyleSheet(
                "background: #ff9a54; border: 2px solid #ff9a54; border-radius: 13px;"
                if active
                else "background: #23343a; border: 2px solid #385057; border-radius: 13px;"
            )

    def switch_workspace(self, index: int) -> None:
        try:
            subprocess.run(
                ["wmctrl", "-s", str(index)],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError) as error:
            QMessageBox.critical(None, "Carbon DSK", f"Could not switch workspace:\n{error}")

    def open_control(self, name: str) -> None:
        commands = {
            "Network": ["nm-connection-editor"],
            "Sound": ["pavucontrol"],
            "Bluetooth": ["blueman-manager"],
        }
        self.launch_command(commands[name])

    def show_quick_menu(self) -> None:
        menu = QMenu(self)
        network = menu.addAction("Network settings")
        network.triggered.connect(lambda: self.launch_command(["nm-connection-editor"]))
        wifi = menu.addAction("Toggle Wi-Fi")
        wifi.triggered.connect(self.toggle_wifi)
        bluetooth = menu.addAction("Bluetooth settings")
        bluetooth.triggered.connect(lambda: self.launch_command(["blueman-manager"]))
        bluetooth_power = menu.addAction("Toggle Bluetooth")
        bluetooth_power.triggered.connect(self.toggle_bluetooth)
        menu.addSeparator()
        sound = menu.addAction("Sound settings")
        sound.triggered.connect(lambda: self.launch_command(["pavucontrol"]))
        mute = menu.addAction("Toggle mute")
        mute.triggered.connect(
            lambda: self.run_control(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
        )
        menu.addSeparator()
        lock = menu.addAction("Lock screen")
        lock.triggered.connect(lambda: self.launch_command(["carbon-dsk", "--lock"]))
        power = menu.addMenu("Power")
        for label, command in (
            ("Suspend", ["systemctl", "suspend"]),
            ("Log out", ["openbox", "--exit"]),
            ("Restart", ["systemctl", "reboot"]),
            ("Shut down", ["systemctl", "poweroff"]),
        ):
            action = power.addAction(label)
            action.triggered.connect(lambda _checked=False, args=command: self.run_control(args))
        menu.exec(self.status.mapToGlobal(self.status.rect().bottomLeft()))

    def toggle_wifi(self) -> None:
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "WIFI", "radio"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            state = "off" if result.stdout.strip().lower() == "enabled" else "on"
            self.run_control(["nmcli", "radio", "wifi", state])
            self.refresh_indicators()
        except (OSError, subprocess.SubprocessError) as error:
            QMessageBox.critical(None, "Carbon DSK", f"Could not toggle Wi-Fi:\n{error}")

    def toggle_bluetooth(self) -> None:
        try:
            result = subprocess.run(
                ["bluetoothctl", "show"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            powered = any(
                line.strip().lower() == "powered: yes"
                for line in result.stdout.splitlines()
            )
            self.run_control(["bluetoothctl", "power", "off" if powered else "on"])
        except (OSError, subprocess.SubprocessError) as error:
            QMessageBox.critical(None, "Carbon DSK", f"Could not toggle Bluetooth:\n{error}")

    def launch_command(self, command: list[str]) -> None:
        try:
            subprocess.Popen(command, start_new_session=True)
        except OSError as error:
            QMessageBox.critical(None, "Carbon DSK", f"Could not start {command[0]}:\n{error}")

    def run_control(self, command: list[str]) -> None:
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError) as error:
            QMessageBox.critical(None, "Carbon DSK", f"Could not run {command[0]}:\n{error}")


def run_desktop() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Carbon DSK")
    application.setStyle("Fusion")
    application.setStyleSheet(STYLE)
    configure_icon_theme()
    panel = CarbonPanel()
    dock = CarbonDock()
    panel.show()
    dock.show()
    return application.exec()


class CarbonDock(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Window
            | Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        dock = QFrame()
        dock.setObjectName("dock")
        dock.setStyleSheet(
            "#dock { background: rgba(17, 26, 31, 238); "
            "border: 1px solid rgba(115, 150, 158, 120); border-radius: 16px; }"
        )
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(6, 5, 6, 5)
        dock_layout.setSpacing(4)
        self.drawer_button = QPushButton("▦")
        self.drawer_button.setFixedSize(40, 40)
        self.drawer_button.setStyleSheet("font-size: 19pt; padding: 2px;")
        self.drawer_button.setToolTip("Applications")
        self.drawer_button.clicked.connect(self.open_drawer)
        dock_layout.addWidget(self.drawer_button)
        dock_layout.addSpacing(4)
        for name, icon, fallback in (
            ("Files", "system-file-manager", QStyle.StandardPixmap.SP_DirIcon),
            ("Web Browser", "web-browser", QStyle.StandardPixmap.SP_ComputerIcon),
            ("Terminal", "utilities-terminal", QStyle.StandardPixmap.SP_ComputerIcon),
        ):
            button = QPushButton()
            button.setIcon(application_icon(icon, fallback))
            button.setIconSize(QSize(24, 24))
            button.setFixedSize(40, 40)
            button.setToolTip(name)
            button.setStyleSheet("padding: 2px;")
            button.clicked.connect(
                lambda _checked=False, target=name: self.launch_named(target)
            )
            dock_layout.addWidget(button)
        dock_layout.addSpacing(4)
        self.status = QPushButton("⏻")
        self.status.setFixedSize(40, 40)
        self.status.setStyleSheet("font-size: 17pt; padding: 2px;")
        self.status.setToolTip("Power and session controls")
        self.status.clicked.connect(self.show_power_menu)
        dock_layout.addWidget(self.status)
        layout.addWidget(dock)
        self.adjustSize()
        screen = QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.geometry()
            self.move(
                geometry.x() + (geometry.width() - self.width()) // 2,
                geometry.y() + geometry.height() - self.height() - 12,
            )

    def open_drawer(self) -> None:
        drawer = ApplicationDrawer(self)
        drawer.adjustSize()
        drawer.move(12, self.y() - drawer.height() - 8)
        drawer.exec()

    def launch_named(self, name: str) -> None:
        command = {
            "Files": "jadev-files",
            "Web Browser": "hyperbrowser",
            "Terminal": "x-terminal-emulator",
        }[name]
        try:
            subprocess.Popen([command], start_new_session=True)
        except OSError as error:
            QMessageBox.critical(None, "Carbon DSK", f"Could not start {command}:\n{error}")

    def show_power_menu(self) -> None:
        menu = QMenu(self)
        for label, command in (
            ("Lock screen", ["carbon-dsk", "--lock"]),
            ("Suspend", ["systemctl", "suspend"]),
            ("Log out", ["openbox", "--exit"]),
            ("Restart", ["systemctl", "reboot"]),
            ("Shut down", ["systemctl", "poweroff"]),
        ):
            action = menu.addAction(label)
            action.triggered.connect(
                lambda _checked=False, args=command: self.run_control(args)
            )
        menu.exec(self.status.mapToGlobal(self.status.rect().topLeft()))

    def run_control(self, command: list[str]) -> None:
        try:
            if command == ["carbon-dsk", "--lock"]:
                subprocess.Popen(command, start_new_session=True)
            else:
                subprocess.run(command, check=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as error:
            QMessageBox.critical(None, "Carbon DSK", f"Could not run {command[0]}:\n{error}")


def run_lock_screen() -> int:
    wallpaper = Path.home() / ".config" / "carbon-dsk" / "wallpaper"
    if not wallpaper.is_file():
        wallpaper = Path("/usr/share/backgrounds/jadevos-default-wallpaper.jpg")
    command = ["i3lock", "--nofork"]
    if wallpaper.is_file():
        command.extend(["--image", str(wallpaper)])
    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--lock":
        raise SystemExit(run_lock_screen())
    if len(sys.argv) > 1 and sys.argv[1] == "--drawer":
        application = QApplication(sys.argv)
        application.setStyle("Fusion")
        application.setStyleSheet(STYLE)
        configure_icon_theme()
        drawer = ApplicationDrawer()
        drawer.show()
        raise SystemExit(application.exec())
    if len(sys.argv) > 1 and sys.argv[1] == "desktop":
        raise SystemExit(run_desktop())
    raise SystemExit(run_desktop())
