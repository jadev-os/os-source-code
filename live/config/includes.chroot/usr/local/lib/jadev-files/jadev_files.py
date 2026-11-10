#!/usr/bin/python3
import shutil
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import QDir, QStandardPaths, Qt, QUrl
from PyQt6.QtGui import (
    QAction,
    QDesktopServices,
    QFileSystemModel,
    QIcon,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from send2trash import send2trash


STYLE = """
QMainWindow, QWidget { background: #ededed; color: #242a30; }
QToolBar {
    spacing: 5px;
    padding: 6px;
    background: #f4f4f4;
    border: 0;
    border-bottom: 1px solid #c4c9ce;
}
QToolBar QToolButton, QPushButton {
    padding: 5px 10px;
    background: #f4f5f6;
    border: 1px solid #bec5ca;
    border-radius: 4px;
}
QToolBar QToolButton:hover, QPushButton:hover { background: #e2eaf2; }
QLineEdit {
    min-height: 25px;
    padding: 2px 7px;
    background: white;
    border: 1px solid #b8c0c7;
    border-radius: 4px;
    selection-background-color: #428bd1;
}
QListWidget {
    background: #e8e9eb;
    border: 0;
    border-right: 1px solid #c5c9cd;
    outline: 0;
}
QListWidget::item { padding: 6px 8px; border-radius: 4px; }
QListWidget::item:selected { color: #fff; background: #468bd0; }
QTreeView {
    background: #fff;
    alternate-background-color: #f1f3f5;
    border: 1px solid #c9cdd1;
    selection-background-color: #b9d8f4;
    selection-color: #14283b;
    outline: 0;
}
QTreeView::item { height: 23px; }
QHeaderView::section {
    padding: 5px 7px;
    background: #f0f1f2;
    border: 0;
    border-right: 1px solid #d0d3d6;
    border-bottom: 1px solid #c9cdd1;
    color: #49525a;
}
QLabel#sectionTitle { font-weight: bold; color: #364b5e; }
QLabel#status { color: #59646d; padding: 4px 8px; }
QSplitter::handle { background: #c8cdd1; width: 2px; }
"""

PLACES = (
    ("Inicio", QStandardPaths.StandardLocation.HomeLocation),
    ("Escritorio", QStandardPaths.StandardLocation.DesktopLocation),
    ("Documentos", QStandardPaths.StandardLocation.DocumentsLocation),
    ("Descargas", QStandardPaths.StandardLocation.DownloadLocation),
    ("Música", QStandardPaths.StandardLocation.MusicLocation),
    ("Imágenes", QStandardPaths.StandardLocation.PicturesLocation),
    ("Vídeos", QStandardPaths.StandardLocation.MoviesLocation),
)


class JadevFileSystemModel(QFileSystemModel):
    HEADERS = ("Nombre", "Tamaño", "Tipo", "Modificado")

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(self.HEADERS)
        ):
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)


class FilePane(QWidget):
    def __init__(self, model, title, on_focus, on_navigate):
        super().__init__()
        self.model = model
        self.on_focus = on_focus
        self.on_navigate = on_navigate
        self.setMinimumWidth(240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.title = QLabel(title)
        self.title.setObjectName("sectionTitle")
        layout.addWidget(self.title)

        path_bar = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setPlaceholderText("Ruta de la carpeta")
        self.path.returnPressed.connect(self.navigate_to_path)
        go = QPushButton("Ir")
        go.clicked.connect(self.navigate_to_path)
        path_bar.addWidget(self.path, 1)
        path_bar.addWidget(go)
        layout.addLayout(path_bar)

        self.view = QTreeView()
        self.view.setModel(model)
        self.view.setRootIndex(model.index(str(Path.home())))
        self.view.setRootIsDecorated(False)
        self.view.setItemsExpandable(False)
        self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.view.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.view.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.view.setDragEnabled(True)
        self.view.setAcceptDrops(True)
        self.view.setDropIndicatorShown(True)
        self.view.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.view.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.view.doubleClicked.connect(self.open_index)
        self.view.clicked.connect(lambda _index: self.on_focus(self))
        self.view.selectionModel().selectionChanged.connect(
            lambda *_args: self.on_navigate()
        )
        self.view.header().setStretchLastSection(False)
        self.view.setColumnWidth(0, 230)
        self.view.setColumnWidth(1, 85)
        self.view.setColumnWidth(2, 130)
        self.view.setColumnWidth(3, 150)
        layout.addWidget(self.view, 1)

        self.status = QLabel()
        self.status.setObjectName("status")
        layout.addWidget(self.status)
        self.set_directory(Path.home(), notify=False)

    def directory(self):
        return Path(self.model.filePath(self.view.rootIndex()))

    def selected_paths(self):
        return [
            Path(self.model.filePath(index))
            for index in self.view.selectionModel().selectedRows(0)
        ]

    def set_directory(self, path, notify=True):
        path = Path(path).expanduser()
        if not path.is_dir():
            return False
        self.view.setRootIndex(self.model.index(str(path)))
        self.path.setText(str(path))
        if notify:
            self.on_navigate()
        return True

    def navigate_to_path(self):
        if not self.set_directory(self.path.text()):
            QMessageBox.warning(
                self, "No se puede abrir", "La ruta no es una carpeta disponible."
            )

    def open_index(self, index):
        path = Path(self.model.filePath(index))
        if path.is_dir():
            self.set_directory(path)
        else:
            self.on_navigate(path)

    def update_status(self):
        directory = self.directory()
        count = self.model.rowCount(self.view.rootIndex())
        try:
            free = shutil.disk_usage(directory).free
            free_text = f"{free / (1024 ** 3):.1f} GB disponibles"
        except OSError:
            free_text = ""
        self.status.setText(f"{count} elementos    {free_text}")


class JadevFiles(QMainWindow):
    def __init__(self, requested_path=None):
        super().__init__()
        self.setWindowTitle("JadevOS - Archivos")
        self.setWindowIcon(
            QIcon("/usr/share/icons/hicolor/scalable/apps/jadev-files.svg")
        )
        self.resize(1180, 760)
        self.setMinimumSize(800, 520)
        self.setStyleSheet(STYLE)
        self.active_pane = None
        self.clipboard_paths = []
        self.clipboard_moves = False

        self.model = JadevFileSystemModel(self)
        self.model.setRootPath(QDir.rootPath())
        self.model.setFilter(
            QDir.Filter.AllEntries
            | QDir.Filter.NoDotAndDotDot
            | QDir.Filter.AllDirs
        )
        self.model.setNameFilterDisables(False)
        self.model.setReadOnly(False)

        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setCentralWidget(root)

        toolbar = self.addToolBar("Archivos")
        toolbar.setMovable(False)
        for label, callback, shortcut in (
            ("Atrás", self.go_up, "Alt+Up"),
            ("Nueva carpeta", self.create_folder, "Ctrl+Shift+N"),
            ("Copiar", self.copy_selection, "Ctrl+C"),
            ("Cortar", lambda: self.copy_selection(move=True), "Ctrl+X"),
            ("Pegar", self.paste_selection, "Ctrl+V"),
            ("Renombrar", self.rename_selection, "F2"),
            ("A la papelera", self.trash_selection, "Delete"),
            ("Actualizar", self.refresh, "F5"),
        ):
            action = QAction(label, self)
            action.triggered.connect(callback)
            toolbar.addAction(action)
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            self.addAction(action)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.setChildrenCollapsible(False)
        outer.addWidget(body, 1)
        self.places = QListWidget()
        self.places.setFixedWidth(155)
        body.addWidget(self.places)

        columns = QSplitter(Qt.Orientation.Horizontal)
        columns.setChildrenCollapsible(False)
        body.addWidget(columns)
        self.left = FilePane(
            self.model, "Carpeta izquierda", self.activate, self.update_status
        )
        self.right = FilePane(
            self.model, "Carpeta derecha", self.activate, self.update_status
        )
        columns.addWidget(self.left)
        columns.addWidget(self.right)
        columns.setSizes([1, 1])
        body.setSizes([155, 1025])
        self.activate(self.left)

        self.populate_places()
        self.places.currentItemChanged.connect(self.open_place)
        self.left.view.customContextMenuRequested.connect(
            lambda position: self.show_context_menu(self.left, position)
        )
        self.right.view.customContextMenuRequested.connect(
            lambda position: self.show_context_menu(self.right, position)
        )
        self.left.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.right.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.model.directoryLoaded.connect(lambda _path: self.update_status())

        if requested_path:
            path = Path(requested_path).expanduser()
            if path.is_file():
                path = path.parent
            if path.is_dir():
                self.left.set_directory(path)
        self.update_status()

    def active(self):
        return self.active_pane or self.left

    def activate(self, pane):
        self.active_pane = pane
        self.left.title.setText(
            ("▶ " if pane is self.left else "") + "Carpeta izquierda"
        )
        self.right.title.setText(
            ("▶ " if pane is self.right else "") + "Carpeta derecha"
        )

    def populate_places(self):
        for label, location in PLACES:
            path = Path(QStandardPaths.writableLocation(location) or Path.home())
            if not path.exists():
                continue
            icon = self.model.fileIcon(self.model.index(str(path)))
            item = QListWidgetItem(icon, label)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.places.addItem(item)
        self.places.addItem(QListWidgetItem("──── Dispositivos ────"))
        for root in (Path("/media") / Path.home().name, Path("/mnt"), Path("/")):
            if root.exists():
                item = QListWidgetItem(
                    self.model.fileIcon(self.model.index(str(root))),
                    root.name or "Sistema",
                )
                item.setData(Qt.ItemDataRole.UserRole, str(root))
                self.places.addItem(item)

    def open_place(self, item, _previous):
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.active().set_directory(path)

    def go_up(self):
        pane = self.active()
        parent = pane.directory().parent
        if parent != pane.directory():
            pane.set_directory(parent)

    def create_folder(self):
        pane = self.active()
        name, accepted = QInputDialog.getText(
            self, "Nueva carpeta", "Nombre de la carpeta:"
        )
        if not accepted:
            return
        name = name.strip()
        if not name or name in {".", ".."} or Path(name).name != name:
            QMessageBox.warning(
                self,
                "Nombre no válido",
                "Escribe un nombre de carpeta válido.",
            )
            return
        target = pane.directory() / name
        try:
            target.mkdir()
        except OSError as error:
            QMessageBox.critical(self, "No se pudo crear la carpeta", str(error))
            return
        self.select_path(pane, target)

    def select_path(self, pane, path):
        index = self.model.index(str(path))
        if index.isValid():
            pane.view.setCurrentIndex(index)
            pane.view.scrollTo(index)

    def copy_selection(self, move=False):
        pane = self.active()
        self.clipboard_paths = pane.selected_paths()
        self.clipboard_moves = move
        self.statusBar().showMessage(
            f"{len(self.clipboard_paths)} elemento(s) listo(s) para "
            f"{'mover' if move else 'copiar'}",
            4000,
        )

    def paste_selection(self):
        if not self.clipboard_paths:
            return
        destination = self.active().directory()
        remaining = []
        for source in self.clipboard_paths:
            target = destination / source.name
            if source == destination or source in destination.parents:
                QMessageBox.warning(
                    self,
                    "Destino no válido",
                    "No se puede copiar una carpeta dentro de sí misma.",
                )
                remaining.append(source)
                continue
            if source.absolute() == target.absolute():
                continue
            if target.exists():
                answer = QMessageBox.question(
                    self,
                    "Reemplazar elemento",
                    f"«{target.name}» ya existe. ¿Quieres reemplazarlo?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    remaining.append(source)
                    continue
                try:
                    send2trash(str(target))
                except OSError as error:
                    QMessageBox.critical(self, "No se pudo reemplazar", str(error))
                    remaining.append(source)
                    continue
            try:
                if self.clipboard_moves:
                    shutil.move(str(source), str(target))
                elif source.is_dir() and not source.is_symlink():
                    shutil.copytree(source, target, symlinks=True)
                else:
                    shutil.copy2(source, target, follow_symlinks=False)
            except OSError as error:
                QMessageBox.critical(
                    self,
                    "No se pudo completar la operación",
                    str(error),
                )
                if self.clipboard_moves:
                    remaining.append(source)
        if self.clipboard_moves:
            self.clipboard_paths = remaining
            if not remaining:
                self.clipboard_moves = False
        self.refresh()

    def rename_selection(self):
        pane = self.active()
        selected = pane.selected_paths()
        if len(selected) != 1:
            return
        source = selected[0]
        name, accepted = QInputDialog.getText(
            self, "Renombrar", "Nuevo nombre:", text=source.name
        )
        if not accepted:
            return
        name = name.strip()
        if not name or name in {".", ".."} or Path(name).name != name:
            QMessageBox.warning(self, "Nombre no válido", "Escribe un nombre válido.")
            return
        target = source.with_name(name)
        if target.exists() and target != source:
            QMessageBox.warning(self, "Ya existe", "Ya hay un elemento con ese nombre.")
            return
        try:
            source.rename(target)
        except OSError as error:
            QMessageBox.critical(self, "No se pudo renombrar", str(error))
            return
        self.select_path(pane, target)

    def trash_selection(self):
        selected = self.active().selected_paths()
        if not selected:
            return
        names = "\n".join(path.name for path in selected[:8])
        if len(selected) > 8:
            names += f"\n... y {len(selected) - 8} elemento(s) más"
        answer = QMessageBox.question(
            self,
            "Enviar a la papelera",
            f"¿Quieres enviar estos elementos a la papelera?\n\n{names}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for path in selected:
            try:
                send2trash(str(path))
            except OSError as error:
                QMessageBox.critical(
                    self, "No se pudo enviar a la papelera", str(error)
                )
        self.refresh()

    def refresh(self, *_args):
        self.model.setRootPath(QDir.rootPath())
        self.left.update_status()
        self.right.update_status()

    def update_status(self, opened_path=None):
        if opened_path is not None:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(opened_path))):
                QMessageBox.warning(
                    self,
                    "No se pudo abrir",
                    f"No hay una aplicación para {opened_path.name}.",
                )
            return
        self.left.update_status()
        self.right.update_status()

    def show_context_menu(self, pane, position):
        self.activate(pane)
        menu = QMenu(self)
        menu.addAction("Nueva carpeta", self.create_folder)
        menu.addAction("Copiar", self.copy_selection)
        menu.addAction("Cortar", lambda: self.copy_selection(move=True))
        menu.addAction("Pegar", self.paste_selection)
        menu.addAction("Renombrar", self.rename_selection)
        menu.addAction("A la papelera", self.trash_selection)
        menu.exec(pane.view.viewport().mapToGlobal(position))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JadevOS Files")
    app.setOrganizationName("JadevOS")
    app.setStyle("Fusion")

    def report_unhandled_exception(exception_type, exception, tb):
        traceback.print_exception(exception_type, exception, tb)
        QMessageBox.critical(
            None,
            "JadevOS Files",
            f"The file manager could not start.\n\n{exception}",
        )

    sys.excepthook = report_unhandled_exception
    requested_path = sys.argv[1] if len(sys.argv) > 1 else None
    if requested_path and QUrl(requested_path).isLocalFile():
        requested_path = QUrl(requested_path).toLocalFile()
    window = JadevFiles(requested_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
