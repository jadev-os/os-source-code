#!/usr/bin/python3
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

from PyQt6.QtCore import QStandardPaths, QUrl
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolBar,
)
from PyQt6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView


HOME_URL = QUrl("https://www.google.com/")
HOME_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inicio - HyperBrowser</title>
<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  color: #18283a;
  background: linear-gradient(180deg, #dce8f3 0, #f3f4f4 190px, #f3f4f4 100%);
  font: 16px Tahoma, Verdana, sans-serif;
}
header {
  padding: 34px 20px 20px;
  text-align: center;
  background: linear-gradient(180deg, #174a78, #347ba7);
  border-bottom: 4px solid #9ab4c7;
  color: white;
}
.globe {
  display: inline-grid;
  width: 58px;
  height: 58px;
  place-items: center;
  margin-bottom: 8px;
  border: 3px solid #fff;
  border-radius: 50%;
  color: #fff;
  font-size: 32px;
}
h1 { margin: 0; font-size: 30px; letter-spacing: 1px; }
header p { margin: 8px 0 0; color: #e2edf5; }
main { width: min(700px, calc(100% - 32px)); margin: 34px auto; }
.panel {
  padding: 20px;
  border: 1px solid #8b9ba8;
  background: #fff;
  box-shadow: 3px 3px 0 #c0cbd3;
}
h2 { margin: 0 0 14px; color: #214f75; font-size: 18px; }
form { display: flex; gap: 8px; }
input {
  flex: 1;
  min-width: 0;
  padding: 11px;
  border: 2px inset #d5dce1;
  font: inherit;
}
button, .link {
  display: inline-block;
  padding: 10px 15px;
  border: 2px outset #e7edf1;
  background: #e5edf3;
  color: #174a78;
  font: bold 14px Tahoma, Verdana, sans-serif;
  text-decoration: none;
}
button { cursor: pointer; }
button:hover, .link:hover { background: #d3e2ec; }
.links { display: flex; flex-wrap: wrap; gap: 10px; }
footer { margin-top: 20px; color: #596b79; font-size: 13px; text-align: center; }
</style>
</head>
<body>
<header>
  <div class="globe">&#9673;</div>
  <h1>HyperBrowser</h1>
  <p>La web de hoy, con el encanto de antes.</p>
</header>
<main>
  <section class="panel">
    <h2>Buscar en Internet</h2>
    <form action="https://duckduckgo.com/" method="get">
      <input name="q" type="search" placeholder="Escribe una búsqueda o dirección web"
             aria-label="Buscar en Internet" autofocus>
      <button type="submit">Buscar</button>
    </form>
  </section>
  <section class="panel" style="margin-top:18px">
    <h2>Enlaces rápidos</h2>
    <div class="links">
      <a class="link" href="https://www.debian.org/">Debian</a>
      <a class="link" href="https://duckduckgo.com/">DuckDuckGo</a>
    </div>
  </section>
  <footer>HyperBrowser para JadevOS Computers</footer>
</main>
</body>
</html>
"""

RETRO_STYLE = """
QMainWindow { background: #c4c4c4; }
QToolBar {
    spacing: 4px;
    padding: 5px;
    background: #d2d2d2;
    border: 0;
    border-bottom: 1px solid #8a8a8a;
}
QToolBar QToolButton, QMenuBar::item {
    padding: 5px 8px;
    color: #171717;
    background: #d2d2d2;
    border: 2px outset #eeeeee;
    font: 12px Tahoma, sans-serif;
}
QToolBar QToolButton:hover, QMenuBar::item:selected { background: #e4e4e4; }
QLineEdit {
    min-height: 25px;
    padding: 2px 6px;
    color: #101820;
    background: white;
    border: 2px inset #eeeeee;
    font: 13px Tahoma, sans-serif;
}
QTabWidget::pane {
    border: 2px groove #eeeeee;
    background: white;
}
QTabBar::tab {
    padding: 6px 12px;
    color: #202020;
    background: #c4c4c4;
    border: 2px outset #eeeeee;
}
QTabBar::tab:selected { background: #f5f5f5; border-bottom-color: #f5f5f5; }
QStatusBar { color: #1b1b1b; background: #d2d2d2; }
"""


def resolve_address(text):
    text = text.strip()
    if not text:
        return HOME_URL

    candidate = QUrl.fromUserInput(text)
    if (
        candidate.isValid()
        and candidate.scheme().lower() in {"http", "https"}
        and candidate.host()
    ):
        return candidate

    return QUrl("https://duckduckgo.com/?" + urlencode({"q": text}))


class BrowserPage(QWebEnginePage):
    def __init__(self, profile, browser, parent=None):
        super().__init__(profile, parent)
        self.browser = browser

    def createWindow(self, _window_type):
        return self.browser.add_tab().page()


class HyperBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HyperBrowser - JadevOS")
        self.setWindowIcon(
            QIcon("/usr/share/icons/hicolor/scalable/apps/hyperbrowser.svg")
        )
        self.resize(1120, 760)
        self.setMinimumSize(720, 480)
        self.setStyleSheet(RETRO_STYLE)

        app_data = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        self.profile_dir = app_data / "profile"
        self.cache_dir = app_data / "cache"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.profile = QWebEngineProfile("HyperBrowser", self)
        self.profile.setPersistentStoragePath(str(self.profile_dir))
        self.profile.setCachePath(str(self.cache_dir))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        self.profile.setHttpCacheType(
            QWebEngineProfile.HttpCacheType.DiskHttpCache
        )
        self.profile.setHttpCacheMaximumSize(128 * 1024 * 1024)
        self.profile.downloadRequested.connect(self.handle_download)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_window_title)
        self.setCentralWidget(self.tabs)

        self.address = QLineEdit()
        self.address.setPlaceholderText("Escribe una dirección o busca en Internet")
        self.address.returnPressed.connect(self.navigate)

        toolbar = QToolBar("Navegación")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        for label, callback, tooltip in (
            ("Atrás", self.go_back, "Volver a la página anterior"),
            ("Adelante", self.go_forward, "Ir a la página siguiente"),
            ("Recargar", self.reload_page, "Recargar o detener la página"),
            ("Inicio", self.go_home, "Abrir la página de inicio"),
        ):
            action = QAction(label, self)
            action.setToolTip(tooltip)
            action.triggered.connect(callback)
            toolbar.addAction(action)

        toolbar.addWidget(self.address)
        bookmark_action = QAction("Añadir marcador", self)
        bookmark_action.triggered.connect(self.add_bookmark)
        toolbar.addAction(bookmark_action)

        self.bookmark_menu = self.menuBar().addMenu("Marcadores")
        self.file_menu = self.menuBar().addMenu("Archivo")
        new_tab_action = QAction("Nueva pestaña", self)
        new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        new_tab_action.triggered.connect(lambda: self.add_tab())
        close_action = QAction("Cerrar pestaña", self)
        close_action.setShortcut(QKeySequence("Ctrl+W"))
        close_action.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self.file_menu.addAction(new_tab_action)
        self.file_menu.addAction(close_action)

        self.add_shortcut("Ctrl+L", self.focus_address)
        self.add_shortcut("Ctrl+R", self.reload_page)
        self.add_shortcut("Alt+Left", self.go_back)
        self.add_shortcut("Alt+Right", self.go_forward)
        self.refresh_bookmarks()
        self.add_tab()

    def add_shortcut(self, sequence, callback):
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.activated.connect(callback)

    def add_tab(self, url=None):
        view = QWebEngineView()
        view.setProperty("hyperbrowserHome", url is None)
        page = BrowserPage(self.profile, self, view)
        view.setPage(page)
        settings = page.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )

        index = self.tabs.addTab(view, "Nueva pestaña")
        self.tabs.setCurrentIndex(index)
        view.urlChanged.connect(lambda current_url, item=view: self.update_address(item, current_url))
        view.titleChanged.connect(lambda title, item=view: self.update_tab_title(item, title))
        view.loadStarted.connect(lambda item=view: self.set_loading_status(item, True))
        view.loadFinished.connect(lambda _ok, item=view: self.set_loading_status(item, False))
        view.iconChanged.connect(lambda icon, item=view: self.tabs.setTabIcon(self.tabs.indexOf(item), icon))
        view.setUrl(url or HOME_URL)
        return page

    def current_view(self):
        return self.tabs.currentWidget()

    def navigate(self):
        view = self.current_view()
        if view is not None:
            view.setUrl(resolve_address(self.address.text()))
            view.setFocus()

    def focus_address(self):
        self.address.setFocus()
        self.address.selectAll()

    def update_address(self, view, url):
        if view is self.current_view():
            is_home = url == HOME_URL or (
                view.property("hyperbrowserHome") and url.scheme() == "data"
            )
            if not is_home:
                view.setProperty("hyperbrowserHome", False)
            text = "" if is_home else url.toString()
            self.address.setText(text)

    def update_tab_title(self, view, title):
        index = self.tabs.indexOf(view)
        if index >= 0:
            clean_title = title or "Nueva pestaña"
            self.tabs.setTabText(index, clean_title[:32])
        self.update_window_title()

    def update_window_title(self, _index=None):
        view = self.current_view()
        if view is not None:
            self.setWindowTitle(f"{view.title() or 'Nueva pestaña'} - HyperBrowser")
            self.update_address(view, view.url())

    def set_loading_status(self, view, loading):
        if view is self.current_view():
            self.statusBar().showMessage(
                "Conectando..." if loading else "Listo"
            )

    def go_back(self):
        view = self.current_view()
        if view is not None:
            view.back()

    def go_forward(self):
        view = self.current_view()
        if view is not None:
            view.forward()

    def reload_page(self):
        view = self.current_view()
        if view is not None:
            if view.isLoading():
                view.stop()
            else:
                view.reload()

    def go_home(self):
        view = self.current_view()
        if view is not None:
            view.setUrl(HOME_URL)

    def close_tab(self, index):
        if index < 0:
            return
        if self.tabs.count() == 1:
            self.go_home()
            return
        view = self.tabs.widget(index)
        self.tabs.removeTab(index)
        view.deleteLater()

    def bookmark_path(self):
        return self.profile_dir.parent / "bookmarks.json"

    def read_bookmarks(self):
        path = self.bookmark_path()
        if not path.exists():
            return []
        try:
            bookmarks = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            QMessageBox.warning(
                self,
                "Marcadores no disponibles",
                f"No se pudieron leer los marcadores: {error}",
            )
            return []
        if not isinstance(bookmarks, list):
            QMessageBox.warning(
                self,
                "Marcadores no disponibles",
                "El archivo de marcadores debe contener una lista.",
            )
            return []
        return [
            item
            for item in bookmarks
            if isinstance(item, dict)
            and isinstance(item.get("title"), str)
            and isinstance(item.get("url"), str)
            and QUrl(item["url"]).scheme().lower() in {"http", "https"}
        ]

    def refresh_bookmarks(self):
        self.bookmark_menu.clear()
        for item in self.read_bookmarks():
            action = QAction(item["title"], self)
            action.triggered.connect(
                lambda _checked=False, address=item["url"]: self.open_bookmark(address)
            )
            self.bookmark_menu.addAction(action)
        if self.bookmark_menu.isEmpty():
            empty = QAction("Sin marcadores guardados", self)
            empty.setEnabled(False)
            self.bookmark_menu.addAction(empty)

    def add_bookmark(self):
        view = self.current_view()
        if view is None or view.url() == HOME_URL:
            return
        url = view.url()
        if url.scheme().lower() not in {"http", "https"}:
            return
        bookmarks = self.read_bookmarks()
        if not any(item["url"] == url.toString() for item in bookmarks):
            bookmarks.append(
                {"title": view.title() or url.host(), "url": url.toString()}
            )
            path = self.bookmark_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(bookmarks, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        self.refresh_bookmarks()

    def open_bookmark(self, address):
        view = self.current_view()
        if view is not None:
            view.setUrl(QUrl(address))

    def handle_download(self, download):
        suggested_path = Path(download.downloadFileName())
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Guardar descarga",
            str(Path.home() / suggested_path.name),
        )
        if not destination:
            download.cancel()
            return
        destination_path = Path(destination)
        download.setDownloadDirectory(str(destination_path.parent))
        download.setDownloadFileName(destination_path.name)
        download.accept()
        download.stateChanged.connect(
            lambda state, item=download: self.report_download(item, state)
        )
        self.statusBar().showMessage(f"Descargando {destination_path.name}")

    def report_download(self, download, state):
        if (
            state
            == QWebEngineDownloadRequest.DownloadState.DownloadCompleted
        ):
            self.statusBar().showMessage(
                f"Descarga completada: {download.downloadFileName()}", 8000
            )
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            self.statusBar().showMessage(
                f"Descarga interrumpida: {download.downloadFileName()}", 8000
            )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("HyperBrowser")
    app.setOrganizationName("JadevOS")
    app.setStyle("Fusion")
    app.setStyleSheet(RETRO_STYLE)

    window = HyperBrowser()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
