# © MNELAB developers
#
# License: BSD (3-clause)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mne.channels import make_standard_montage
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QListWidget,
    QVBoxLayout,
    QWidget,
)


class MontageDialog(QDialog):
    def __init__(self, parent, montages):
        super().__init__(parent)
        self.setWindowTitle("Set montage")

        vbox = QVBoxLayout()
        self.montages = QListWidget()
        self.montages.insertItems(0, montages)
        self.montages.setSelectionMode(QListWidget.SingleSelection)
        vbox.addWidget(self.montages)

        self.match_case = QCheckBox("Match case-sensitive", self)
        self.match_alias = QCheckBox("Match aliases", self)
        self.ignore_missing = QCheckBox("Ignore missing", self)
        self.ignore_missing.setChecked(True)
        vbox.addWidget(self.match_case)
        vbox.addWidget(self.match_alias)
        vbox.addWidget(self.ignore_missing)

        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        controls_layout.addWidget(self.buttonbox)
        vbox.addLayout(controls_layout)

        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.montages.itemSelectionChanged.connect(self.view_montage)
        hbox = QHBoxLayout(self)
        hbox.addLayout(vbox)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas_container = QWidget(self)
        self.canvas_layout = QVBoxLayout(self.canvas_container)
        self.canvas_layout.addWidget(self.canvas)
        self.canvas_container.setLayout(self.canvas_layout)
        hbox.addWidget(self.canvas_container)

        if self.montages.count() > 0:
            self.montages.setCurrentRow(0)
            self.view_montage()

    def view_montage(self):
        name = self.montages.selectedItems()[0].data(0)
        montage = make_standard_montage(name)
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        montage.plot(show_names=True, show=False, axes=ax)
        ax.set_aspect("equal")
        self.figure.tight_layout(pad=1.0)
        self.canvas.draw()
