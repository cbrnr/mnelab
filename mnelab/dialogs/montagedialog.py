# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from mne.channels import make_standard_montage
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSlot as Slot
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QListWidget,
                             QPushButton, QVBoxLayout)


class MontageDialog(QDialog):
    def __init__(self, parent, montages, selected=None):
        super().__init__(parent)
        self.setWindowTitle("Set montage")
        vbox = QVBoxLayout(self)
        self.montages = QListWidget()
        self.montages.insertItems(0, montages)
        self.montages.setSelectionMode(QListWidget.SingleSelection)
        if selected is not None:
            for i in range(self.montages.count()):
                if self.montages.item(i).data(0) == selected:
                    self.montages.item(i).setSelected(True)
        vbox.addWidget(self.montages)
        hbox = QHBoxLayout()
        self.view_button = QPushButton("View")
        self.view_button.clicked.connect(self.view_montage)
        hbox.addWidget(self.view_button)
        hbox.addStretch()
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        hbox.addWidget(self.buttonbox)
        vbox.addLayout(hbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.montages.itemSelectionChanged.connect(self.toggle_buttons)
        self.toggle_buttons()  # initialize OK and View buttons state

    @Slot()
    def toggle_buttons(self):
        """Toggle OK and View buttons.
        """
        if self.montages.selectedItems():
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
            self.view_button.setEnabled(True)
        else:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
            self.view_button.setEnabled(False)

    def view_montage(self):
        name = self.montages.selectedItems()[0].data(0)
        montage = make_standard_montage(name)
        fig = montage.plot(show_names=True, show=False)
        win = fig.canvas.manager.window
        win.setWindowModality(Qt.WindowModal)
        win.setWindowTitle("Montage")
        win.statusBar().hide()  # not necessary since matplotlib 3.3
        fig.show()
