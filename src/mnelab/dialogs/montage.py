# © MNELAB developers
#
# License: BSD (3-clause)

from pathlib import Path

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mne.channels import make_standard_montage, read_custom_montage
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mnelab.utils import Montage

SUPPORTED_FILES = [
    "*.loc",
    "*.locs",
    "*.eloc",
    "*.sfp",
    "*.csd",
    "*.elc",
    "*.txt",
    "*.elp",
    "*.bvef",
    "*.csv",
    "*.tsv",
    "*.xyz",
]


class MontageItem(QListWidgetItem):
    def __init__(self, montage, name, path=None):
        super().__init__(name)
        self.montage = montage
        self.name = name
        self.path = path


class MontageDialog(QDialog):
    def __init__(self, parent, montages, current_montage=None):
        super().__init__(parent)
        self.setWindowTitle("Set Montage")
        self.resize(760, 500)

        vbox = QVBoxLayout()
        self.montages = QListWidget()
        self.montages.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        for name in montages:
            montage = make_standard_montage(name)
            item = MontageItem(montage, name)
            self.montages.addItem(item)
        vbox.addWidget(self.montages)

        self.montages.itemSelectionChanged.connect(self.view_montage)
        self.montages.itemSelectionChanged.connect(self._update_clear_button)
        self.match_case = QCheckBox("Match Case-Sensitive", self)
        self.match_alias = QCheckBox("Match Aliases", self)
        self.ignore_missing = QCheckBox("Ignore Missing", self)
        self.ignore_missing.setChecked(True)
        vbox.addWidget(self.match_case)
        vbox.addWidget(self.match_alias)
        vbox.addWidget(self.ignore_missing)

        hbox = QHBoxLayout()
        hbox.addLayout(vbox, stretch=1)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas_container = QWidget(self)
        self.canvas_container.setMinimumWidth(240)
        self.canvas_container.setMinimumHeight(220)
        self.canvas_layout = QVBoxLayout(self.canvas_container)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_layout.setSpacing(0)
        self.canvas_layout.addWidget(self.canvas)
        self.canvas_container.setLayout(self.canvas_layout)
        hbox.addWidget(self.canvas_container, stretch=2)

        button_layout = QHBoxLayout()
        self.open_file_button = QPushButton("Load Custom Montage...", self)
        self.open_file_button.clicked.connect(self.load_custom_montage)
        button_layout.addWidget(self.open_file_button)
        self.clear_button = QPushButton("Clear Montage", self)
        self.clear_button.clicked.connect(self._clear_montage)
        self.clear_button.setEnabled(current_montage is not None)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        button_layout.addWidget(self.buttonbox, alignment=Qt.AlignmentFlag.AlignLeft)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(hbox)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        if current_montage is not None:
            if current_montage.path is not None:
                # custom montage: add it to the list and select it
                self.montages.addItem(
                    MontageItem(
                        current_montage.montage,
                        current_montage.name,
                        current_montage.path,
                    )
                )
                self.montages.setCurrentRow(self.montages.count() - 1)
            else:
                # standard montage: find and select by name
                for i in range(self.montages.count()):
                    if self.montages.item(i).name == current_montage.name:
                        self.montages.setCurrentRow(i)
                        break
        self.view_montage()
        self.setFocus()

    def accept(self):
        selected = self.montages.selectedItems()
        if selected:
            item = selected[0]
            assert isinstance(item, MontageItem)
            self.montage = Montage(item.montage, item.name, item.path)
        else:
            self.montage = None
        super().accept()

    def _clear_montage(self):
        self.montages.clearSelection()
        self.figure.clear()
        self.canvas.draw()

    def _update_clear_button(self):
        self.clear_button.setEnabled(bool(self.montages.selectedItems()))

    def view_montage(self):
        selected = self.montages.selectedItems()
        if not selected:
            self.figure.clear()
            self.canvas.draw()
            return
        item = selected[0]
        assert isinstance(item, MontageItem)
        self.figure.clear()
        ax = self.figure.add_subplot()
        item.montage.plot(show_names=True, show=False, axes=ax)
        ax.set_aspect("equal")
        self.figure.tight_layout(pad=0.5)
        ax.margins(0)
        self.canvas.draw()

    def load_custom_montage(self):
        file_filter = f"Supported Files ({' '.join(SUPPORTED_FILES)});;All Files (*)"
        fpath, _ = QFileDialog.getOpenFileName(self, "Open File", "", file_filter)
        if fpath:
            try:
                montage = read_custom_montage(fpath)
            except Exception as e:
                QMessageBox.critical(self, "Unsupported montage file", str(e))
            else:
                self.montages.addItem(
                    MontageItem(montage, Path(fpath).name, Path(fpath))
                )
                self.montages.setCurrentRow(self.montages.count() - 1)
