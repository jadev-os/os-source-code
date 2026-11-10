"""English-language Liquid Glass desktop UI for JadevOS Updater."""

from __future__ import annotations

import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QPropertyAnimation, QSettings, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .core import (
    Release,
    UpdateCancelled,
    UpdateError,
    cache_directory,
    download_release,
    fetch_releases,
    installed_version,
    reboot_is_required,
    system_architecture,
    validate_bundle_metadata,
    verify_download,
    _version_is_newer,
)


PRIVILEGED_HELPER = "/usr/lib/jadevOS-updater/privileged"
CHECK_INTERVALS = {
    "Every 6 hours": 6,
    "Every 12 hours": 12,
    "Once a day": 24,
    "Once a week": 168,
}

LIGHT_STYLE = """
QMainWindow, QDialog { background: #e8eef7; color: #17283d; }
QWidget#page { background: transparent; }
QFrame#glass {
    background: rgba(255, 255, 255, 218);
    border: 1px solid rgba(255, 255, 255, 245);
    border-bottom: 1px solid rgba(140, 164, 193, 150);
    border-radius: 18px;
}
QFrame#hero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #3f7fba, stop:0.55 #6d9bd1, stop:1 #8cb5d9);
    border: 1px solid rgba(255, 255, 255, 180);
    border-radius: 22px;
    color: white;
}
QLabel#heroTitle { color: white; font-size: 27px; font-weight: 700; }
QLabel#heroSub { color: #edf6ff; font-size: 13px; }
QLabel#sectionTitle { color: #1b3450; font-size: 16px; font-weight: 700; }
QLabel#muted { color: #62748a; }
QLabel#status { color: #36546f; font-size: 13px; }
QLabel#version { color: #193c61; font-size: 24px; font-weight: 700; }
QPushButton {
    min-height: 34px;
    padding: 4px 15px;
    border-radius: 11px;
    border: 1px solid #c3d1df;
    background: rgba(255, 255, 255, 225);
    color: #1d4267;
    font-weight: 600;
}
QPushButton:hover { background: white; border-color: #7ca9d2; }
QPushButton:disabled { color: #99a6b4; background: #e2e8ee; }
QPushButton#primary {
    border: 1px solid #3978af;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #69a8df, stop:1 #3e7fb9);
    color: white;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #80b8e8, stop:1 #4b8dcc);
}
QProgressBar {
    min-height: 12px;
    max-height: 12px;
    border: 0;
    border-radius: 6px;
    background: #dbe4ed;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4b91ce, stop:1 #7ab7e4);
}
QTextEdit {
    background: rgba(250, 252, 255, 210);
    border: 1px solid #d2dce6;
    border-radius: 10px;
    padding: 8px;
    color: #263b51;
}
QComboBox {
    min-height: 30px;
    padding: 3px 9px;
    border: 1px solid #c3d1df;
    border-radius: 9px;
    background: rgba(255, 255, 255, 225);
}
QScrollArea { border: 0; background: transparent; }
"""

DARK_STYLE = """
QMainWindow, QDialog { background: #111a29; color: #e5edf7; }
QWidget#page { background: transparent; }
QFrame#glass {
    background: rgba(34, 49, 69, 232);
    border: 1px solid rgba(166, 199, 229, 85);
    border-bottom: 1px solid rgba(166, 199, 229, 125);
    border-radius: 18px;
}
QFrame#hero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #234b73, stop:0.55 #3a6694, stop:1 #4a7ca8);
    border: 1px solid rgba(193, 224, 250, 130);
    border-radius: 22px;
    color: white;
}
QLabel#heroTitle { color: white; font-size: 27px; font-weight: 700; }
QLabel#heroSub { color: #e2effb; font-size: 13px; }
QLabel#sectionTitle { color: #e2edf8; font-size: 16px; font-weight: 700; }
QLabel#muted { color: #a9bbce; }
QLabel#status { color: #c6d8e9; font-size: 13px; }
QLabel#version { color: #e6f2ff; font-size: 24px; font-weight: 700; }
QPushButton {
    min-height: 34px;
    padding: 4px 15px;
    border-radius: 11px;
    border: 1px solid #526a84;
    background: rgba(58, 76, 99, 235);
    color: #ecf5ff;
    font-weight: 600;
}
QPushButton:hover { background: #4a6686; border-color: #83acd1; }
QPushButton:disabled { color: #8795a5; background: #29374a; }
QPushButton#primary {
    border: 1px solid #6597c5;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #5e9bd2, stop:1 #356c9f);
    color: white;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #77b0e1, stop:1 #4784bb);
}
QProgressBar {
    min-height: 12px;
    max-height: 12px;
    border: 0;
    border-radius: 6px;
    background: #3a4c62;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #55a5e8, stop:1 #8acaff);
}
QTextEdit {
    background: rgba(24, 37, 53, 220);
    border: 1px solid #43586f;
    border-radius: 10px;
    padding: 8px;
    color: #dae6f2;
}
QComboBox {
    min-height: 30px;
    padding: 3px 9px;
    border: 1px solid #526a84;
    border-radius: 9px;
    background: #26384d;
    color: #ecf5ff;
}
QScrollArea { border: 0; background: transparent; }
"""


class OperationWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()
    progress = pyqtSignal(int, int)
    message = pyqtSignal(str)

    def __init__(
        self,
        operation: Callable[
            [
                Callable[[int, int], None],
                Callable[[str], None],
                threading.Event,
            ],
            object,
        ],
    ) -> None:
        super().__init__()
        self.operation = operation
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            result = self.operation(
                self.progress.emit,
                self.message.emit,
                self.cancel_event,
            )
        except UpdateCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(result)


class SettingsDialog(QDialog):
    def __init__(self, settings: QSettings, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Updater Settings")
        self.setMinimumWidth(430)
        self.settings = settings

        layout = QVBoxLayout(self)
        auto_check = QCheckBox("Check for updates automatically")
        auto_check.setChecked(settings.value("autoCheck", True, type=bool))
        layout.addWidget(auto_check)

        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Check interval"))
        interval = QComboBox()
        interval.addItems(CHECK_INTERVALS)
        current_interval = int(settings.value("intervalHours", 6))
        interval.setCurrentText(
            next(
                (
                    name
                    for name, hours in CHECK_INTERVALS.items()
                    if hours == current_interval
                ),
                "Every 6 hours",
            )
        )
        interval_row.addWidget(interval, 1)
        layout.addLayout(interval_row)

        dark_mode = QCheckBox("Use dark appearance")
        dark_mode.setChecked(settings.value("theme", "light") == "dark")
        layout.addWidget(dark_mode)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.auto_check = auto_check
        self.interval = interval
        self.dark_mode = dark_mode

    def save(self) -> None:
        hours = CHECK_INTERVALS[self.interval.currentText()]
        self.settings.setValue("autoCheck", self.auto_check.isChecked())
        self.settings.setValue("intervalHours", hours)
        self.settings.setValue(
            "theme", "dark" if self.dark_mode.isChecked() else "light"
        )
        self.settings.sync()


class HistoryDialog(QDialog):
    def __init__(
        self,
        releases: list[Release],
        installed_history: list[dict[str, str]],
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Update History")
        self.resize(760, 520)
        layout = QHBoxLayout(self)
        versions = QWidget()
        version_layout = QVBoxLayout(versions)
        self.version_list = QListWidget()
        version_layout.addWidget(self.version_list)
        layout.addWidget(versions, 1)

        details = QWidget()
        details_layout = QVBoxLayout(details)
        self.title = QLabel("Select a release")
        self.title.setObjectName("sectionTitle")
        self.notes = QTextEdit()
        self.notes.setReadOnly(True)
        details_layout.addWidget(self.title)
        details_layout.addWidget(self.notes, 1)
        layout.addWidget(details, 2)
        self.entries: list[tuple[str, str]] = []
        for item in installed_history:
            version = item.get("version", "unknown")
            date = format_date(item.get("date", ""))
            self.entries.append(
                (f"{version}    Installed {date}", f"Successfully installed version {version} on {date}.")
            )
        for release in releases:
            date = format_date(release.published_at)
            self.entries.append(
                (
                    f"{release.version}    Released {date}",
                    release.notes or "No release notes were provided.",
                )
            )
        for label, _details in self.entries:
            self.version_list.addItem(label)
        self.version_list.currentRowChanged.connect(self.show_release)
        if self.entries:
            self.version_list.setCurrentRow(0)

    def show_release(self, row: int) -> None:
        if row < 0 or row >= len(self.entries):
            return
        label, details = self.entries[row]
        self.title.setText(label)
        self.notes.setPlainText(details)


class VersionCard(QFrame):
    def __init__(self, title: str, version: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        title_label = QLabel(title)
        title_label.setObjectName("muted")
        self.version_label = QLabel(version)
        self.version_label.setObjectName("version")
        self.version_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(title_label)
        layout.addWidget(self.version_label)


def format_date(value: str) -> str:
    if not value:
        return "Date unavailable"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "Date unavailable"
    return parsed.strftime("%b %d, %Y")


class UpdaterWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("JadevOS", "Updater")
        self.architecture = system_architecture()
        self.installed_version, self.system_name = installed_version()
        self.releases: list[Release] = []
        self.latest: Release | None = None
        self.downloaded_bundle: Path | None = None
        self.downloaded_signature: Path | None = None
        self.worker: OperationWorker | None = None
        self.operation = ""
        self._quit_requested = False
        self.setWindowTitle("JadevOS Updater")
        self.setWindowIcon(QIcon("/usr/share/icons/hicolor/scalable/apps/jadevOS-updater.svg"))
        self.resize(1060, 760)
        self.setMinimumSize(820, 640)

        self._build_ui()
        self._create_tray_icon()
        self.apply_theme()
        self.interval_timer = QTimer(self)
        self.interval_timer.timeout.connect(self.check_updates)
        self.reset_interval_timer()
        if self.settings.value("autoCheck", True, type=bool):
            QTimer.singleShot(900, self.check_updates)

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        page.setObjectName("page")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(28, 22, 28, 24)
        page_layout.setSpacing(16)
        scroll.setWidget(page)
        self.setCentralWidget(scroll)

        top = QHBoxLayout()
        brand = QLabel("JADEVOS  /  SYSTEM")
        brand.setObjectName("muted")
        brand.setStyleSheet("font-weight: 700; letter-spacing: 2px;")
        top.addWidget(brand)
        top.addStretch(1)
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self.history_button = QPushButton("Update history")
        self.history_button.clicked.connect(self.open_history)
        top.addWidget(self.history_button)
        top.addWidget(self.settings_button)
        page_layout.addLayout(top)

        self.hero = QFrame()
        self.hero.setObjectName("hero")
        hero_layout = QHBoxLayout(self.hero)
        hero_layout.setContentsMargins(24, 18, 24, 18)
        text_column = QVBoxLayout()
        self.hero_title = QLabel("JadevOS Updater")
        self.hero_title.setObjectName("heroTitle")
        self.hero_subtitle = QLabel("A clearer way to keep your system current.")
        self.hero_subtitle.setObjectName("heroSub")
        text_column.addWidget(self.hero_title)
        text_column.addWidget(self.hero_subtitle)
        hero_layout.addLayout(text_column, 1)
        self.check_button = QPushButton("Check for updates")
        self.check_button.setObjectName("primary")
        self.check_button.clicked.connect(self.check_updates)
        hero_layout.addWidget(self.check_button, 0, Qt.AlignmentFlag.AlignVCenter)
        page_layout.addWidget(self.hero)
        opacity = QGraphicsOpacityEffect(self.hero)
        self.hero.setGraphicsEffect(opacity)
        self.hero_animation = QPropertyAnimation(opacity, b"opacity", self)
        self.hero_animation.setDuration(320)
        self.hero_animation.setStartValue(0.72)
        self.hero_animation.setEndValue(1.0)
        self.hero_animation.start()

        version_row = QHBoxLayout()
        self.installed_card = self._version_card("Installed version", self.installed_version)
        self.latest_card = self._version_card("Latest version", "Checking…")
        version_row.addWidget(self.installed_card)
        version_row.addWidget(self.latest_card)
        page_layout.addLayout(version_row)

        details_card = QFrame()
        details_card.setObjectName("glass")
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(20, 18, 20, 18)
        notes_header = QHBoxLayout()
        notes_title = QLabel("Release notes")
        notes_title.setObjectName("sectionTitle")
        self.release_date = QLabel("Waiting for update information")
        self.release_date.setObjectName("muted")
        notes_header.addWidget(notes_title)
        notes_header.addStretch(1)
        notes_header.addWidget(self.release_date)
        self.release_notes = QTextEdit()
        self.release_notes.setReadOnly(True)
        self.release_notes.setMinimumHeight(170)
        self.release_notes.setPlaceholderText("Release notes will appear here.")
        details_layout.addLayout(notes_header)
        details_layout.addWidget(self.release_notes)
        page_layout.addWidget(details_card)

        download_card = QFrame()
        download_card.setObjectName("glass")
        download_layout = QVBoxLayout(download_card)
        download_layout.setContentsMargins(20, 17, 20, 17)
        progress_header = QHBoxLayout()
        self.status_label = QLabel("Connecting to the update service…")
        self.status_label.setObjectName("status")
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("muted")
        progress_header.addWidget(self.status_label, 1)
        progress_header.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        download_buttons = QHBoxLayout()
        download_buttons.addStretch(1)
        self.cancel_button = QPushButton("Cancel download")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.download_button = QPushButton("Download update")
        self.download_button.setObjectName("primary")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.start_download)
        self.install_button = QPushButton("Install update")
        self.install_button.setEnabled(False)
        self.install_button.clicked.connect(self.install_update)
        download_buttons.addWidget(self.cancel_button)
        download_buttons.addWidget(self.download_button)
        download_buttons.addWidget(self.install_button)
        download_layout.addLayout(progress_header)
        download_layout.addWidget(self.progress_bar)
        download_layout.addLayout(download_buttons)
        page_layout.addWidget(download_card)

        self.system_info = QLabel(
            f"{self.system_name}  ·  Debian 13 compatible  ·  {self.architecture}"
        )
        self.system_info.setObjectName("muted")
        self.system_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_layout.addWidget(self.system_info)
        page_layout.addStretch(1)

        menu = self.menuBar().addMenu("Updater")
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        history_action = QAction("Update history", self)
        history_action.triggered.connect(self.open_history)
        menu.addAction(settings_action)
        menu.addAction(history_action)
        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        menu.addAction(quit_action)

    def _version_card(self, title: str, version: str) -> VersionCard:
        return VersionCard(title, version)

    def _create_tray_icon(self) -> None:
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = QIcon("/usr/share/icons/hicolor/scalable/apps/jadevOS-updater.svg")
        tray = QSystemTrayIcon(icon, self)
        tray_menu = QMenu(self)
        open_action = QAction("Open JadevOS Updater", self)
        open_action.triggered.connect(self.showNormal)
        tray_menu.addAction(open_action)
        tray_menu.addSeparator()
        tray_menu.addAction("Check for updates", self.check_updates)
        tray_menu.addAction("Quit", self.quit_application)
        tray.setContextMenu(tray_menu)
        tray.activated.connect(lambda _reason: self.showNormal())
        tray.show()
        self.tray = tray

    def quit_application(self) -> None:
        self._quit_requested = True
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.tray and self.tray.isVisible() and not self._quit_requested:
            self.hide()
            event.ignore()
            return
        super().closeEvent(event)

    def apply_theme(self) -> None:
        theme = self.settings.value("theme", "light")
        self.setStyleSheet(DARK_STYLE if theme == "dark" else LIGHT_STYLE)

    def reset_interval_timer(self) -> None:
        if not self.settings.value("autoCheck", True, type=bool):
            self.interval_timer.stop()
            return
        hours = int(self.settings.value("intervalHours", 6))
        if hours not in set(CHECK_INTERVALS.values()):
            hours = 6
        self.interval_timer.start(hours * 60 * 60 * 1000)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save()
            self.apply_theme()
            self.reset_interval_timer()

    def open_history(self) -> None:
        installed_history = self.settings.value("installedHistory", [], type=list)
        if not self.releases and not installed_history:
            QMessageBox.information(
                self,
                "Update history",
                "No JadevOS releases or installed updates are recorded yet.",
            )
            return
        dialog = HistoryDialog(self.releases, installed_history, self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def _start_worker(
        self,
        name: str,
        operation: Callable[
            [
                Callable[[int, int], None],
                Callable[[str], None],
                threading.Event,
            ],
            object,
        ],
    ) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.operation = name
        self.worker = OperationWorker(operation)
        self.worker.succeeded.connect(self._operation_succeeded)
        self.worker.failed.connect(self._operation_failed)
        self.worker.cancelled.connect(self._operation_cancelled)
        self.worker.progress.connect(self._update_progress)
        self.worker.message.connect(self.status_label.setText)
        self.worker.finished.connect(self._worker_finished)
        self.set_busy(True)
        self.status_label.setText(
            {
                "check": "Checking GitHub releases…",
                "download": "Preparing secure download…",
                "install": "Authenticating and installing the update…",
                "reboot": "Restarting JadevOS…",
            }.get(name, "Working…")
        )
        if name in {"download", "install"}:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0 if name == "install" else 100)
            self.cancel_button.setVisible(name == "download")
        self.worker.start()

    def set_busy(self, busy: bool) -> None:
        self.check_button.setEnabled(not busy)
        self.settings_button.setEnabled(not busy)
        self.history_button.setEnabled(not busy)
        self.download_button.setEnabled(
            not busy
            and self.latest is not None
            and self.latest.bundle is not None
            and self.latest.signature is not None
        )
        self.install_button.setEnabled(not busy and self.downloaded_bundle is not None)

    def check_updates(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        def check(_progress, message, _cancel_event):
            return fetch_releases(self.architecture, message=message)

        self._start_worker("check", check)

    def _on_releases(self, releases: list[Release]) -> None:
        self.releases = releases
        self.latest = releases[0] if releases else None
        self.downloaded_bundle = None
        self.downloaded_signature = None
        self.install_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        if not releases:
            self.latest_card.version_label.setText("Not available")
            self.release_date.setText("No published releases")
            self.release_notes.setPlainText(
                "The GitHub repository does not have any published releases yet. "
                "When a signed JadevOS update bundle is published, it will appear here."
            )
            self.status_label.setText(
                "No updates are published yet. Check again later."
            )
            self.download_button.setEnabled(False)
            return

        latest = releases[0]
        self.latest_card.version_label.setText(latest.version)
        self.release_date.setText(format_date(latest.published_at))
        self.release_notes.setPlainText(
            latest.notes or "No release notes were provided."
        )
        if not self._is_newer(latest.version):
            self.status_label.setText("Your system is up to date.")
            self.download_button.setEnabled(False)
            return
        if latest.bundle is None or latest.signature is None:
            self.status_label.setText(
                "A newer release exists, but it has no signed bundle for "
                f"{self.architecture}."
            )
            self.download_button.setEnabled(False)
            self._notify_once(
                latest.version,
                "Update package unavailable",
                f"Version {latest.version} has no signed {self.architecture} bundle.",
            )
            return
        self.status_label.setText(
            f"Version {latest.version} is ready to download."
        )
        self.download_button.setEnabled(True)
        self._notify_once(
            latest.version,
            "JadevOS update available",
            f"Version {latest.version} is ready to download.",
        )

    def _is_newer(self, version: str) -> bool:
        return _version_is_newer(version, self.installed_version)

    def start_download(self) -> None:
        release = self.latest
        if release is None or release.bundle is None or release.signature is None:
            return
        cache = cache_directory()

        def operation(progress, message, cancel_event):
            bundle, signature, checksum = download_release(
                release,
                cache,
                cancel_event,
                progress,
                message,
            )
            message("Verifying SHA-256 and Ed25519 signature…")
            verify_download(bundle, signature)
            validate_bundle_metadata(bundle, release.version, self.architecture)
            return bundle, signature, checksum

        self._start_worker("download", operation)

    def cancel_download(self) -> None:
        if self.worker and self.operation == "download":
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelling download…")

    def install_update(self) -> None:
        if not self.downloaded_bundle or not self.downloaded_signature:
            return
        answer = QMessageBox.warning(
            self,
            "Install system update",
            "The downloaded update has a valid JadevOS signature. "
            "Installing it will change system packages and requires administrator "
            "authentication. Continue?",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Ok:
            return
        bundle = self.downloaded_bundle
        signature = self.downloaded_signature

        def operation(progress, message, _cancel_event):
            message("Waiting for administrator authentication…")
            process = subprocess.Popen(
                [
                    "/usr/bin/pkexec",
                    PRIVILEGED_HELPER,
                    "install",
                    str(bundle),
                    str(signature),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            output_lines: list[str] = []
            assert process.stdout is not None
            for line in process.stdout:
                text = line.strip()
                if not text:
                    continue
                output_lines.append(text)
                if text.startswith("pmstatus:"):
                    parts = text.split(":", 3)
                    if len(parts) >= 3:
                        try:
                            percentage = max(0, min(100, int(float(parts[2]))))
                        except ValueError:
                            percentage = 0
                        progress(percentage, 100)
                        if len(parts) == 4:
                            message(parts[3])
                else:
                    message(text)
            result = process.wait()
            if result != 0:
                detail = output_lines[-1] if output_lines else "Authentication was cancelled."
                raise UpdateError(f"Installation failed: {detail}")
            reboot = any(
                line == "reboot-required:true" for line in output_lines
            ) or reboot_is_required()
            return release.version, reboot

        self._start_worker("install", operation)

    def _update_progress(self, current: int, total: int) -> None:
        if self.operation == "install":
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(max(0, min(current, 100)))
            return
        if total <= 0:
            self.progress_bar.setRange(0, 0)
            self.progress_label.setText("")
            return
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(max(0, min(int(current * 100 / total), 100)))
        self.progress_label.setText(
            f"{format_size(current)} / {format_size(total)}"
        )

    def _operation_succeeded(self, result: object) -> None:
        if self.operation == "check":
            if not isinstance(result, list) or not all(
                isinstance(release, Release) for release in result
            ):
                self._operation_failed("The update service returned invalid release data.")
                return
            self._on_releases(result)
        elif self.operation == "download":
            if (
                not isinstance(result, tuple)
                or len(result) != 3
                or not isinstance(result[0], Path)
                or not isinstance(result[1], Path)
                or not isinstance(result[2], str)
            ):
                self._operation_failed("The downloaded update result is invalid.")
                return
            bundle, signature, checksum = result
            self.downloaded_bundle = bundle
            self.downloaded_signature = signature
            self.progress_bar.setValue(100)
            self.status_label.setText(
                f"Download verified. SHA-256: {checksum[:16]}…"
            )
            self.progress_label.setText("Signature verified")
            self.install_button.setEnabled(True)
            self.download_button.setEnabled(False)
        elif self.operation == "install":
            if (
                not isinstance(result, tuple)
                or len(result) != 2
                or not isinstance(result[0], str)
                or not isinstance(result[1], bool)
            ):
                self._operation_failed("The update installer returned invalid status.")
                return
            version, reboot = result
            self.installed_version = version
            self.installed_card.version_label.setText(version)
            history = self.settings.value("installedHistory", [], type=list)
            history.insert(0, {"version": version, "date": datetime.now().isoformat()})
            self.settings.setValue("installedHistory", history[:50])
            self.settings.sync()
            self.status_label.setText(f"Version {version} was installed successfully.")
            self.downloaded_bundle = None
            self.downloaded_signature = None
            self.install_button.setEnabled(False)
            if reboot:
                self._confirm_reboot()
        elif self.operation == "reboot":
            self.status_label.setText("Restart request sent.")
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")

    def _operation_failed(self, error: str) -> None:
        self.status_label.setText(error)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        QMessageBox.critical(self, "JadevOS Updater", error)

    def _operation_cancelled(self) -> None:
        self.status_label.setText("Download cancelled.")
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.cancel_button.setEnabled(True)

    def _worker_finished(self) -> None:
        if self.worker:
            self.worker.deleteLater()
        self.worker = None
        self.operation = ""
        self.cancel_button.setVisible(False)
        self.cancel_button.setEnabled(True)
        self.set_busy(False)

    def _confirm_reboot(self) -> None:
        answer = QMessageBox.question(
            self,
            "Restart required",
            "The update is installed. A system restart is required to finish "
            "applying it. Restart JadevOS now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            self.status_label.setText(
                "Update installed. Restart JadevOS later to finish applying it."
            )
            return

        def reboot(_progress, message, _cancel_event):
            message("Requesting a privileged system restart…")
            return subprocess.run(
                ["/usr/bin/pkexec", PRIVILEGED_HELPER, "reboot"],
                check=True,
                timeout=20,
                capture_output=True,
                text=True,
            )

        self._start_worker("reboot", reboot)

    def _notify(self, title: str, body: str) -> None:
        if self.tray:
            self.tray.showMessage(
                title,
                body,
                QSystemTrayIcon.MessageIcon.Information,
                8000,
            )

    def _notify_once(self, version: str, title: str, body: str) -> None:
        notification_key = f"{version}:{title}"
        if self.settings.value("lastNotification", "") == notification_key:
            return
        self.settings.setValue("lastNotification", notification_key)
        self.settings.sync()
        self._notify(title, body)


def format_size(size: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("JadevOS Updater")
    app.setOrganizationName("JadevOS")
    app.setWindowIcon(QIcon("/usr/share/icons/hicolor/scalable/apps/jadevOS-updater.svg"))
    try:
        window = UpdaterWindow()
    except UpdateError as error:
        QMessageBox.critical(None, "JadevOS Updater", str(error))
        raise SystemExit(1) from error
    if "--background" in sys.argv and window.tray:
        window.hide()
    else:
        window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
