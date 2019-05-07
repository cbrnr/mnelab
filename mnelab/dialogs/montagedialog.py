from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QDialogButtonBox, QPushButton, QStatusBar,
                             QToolBar, QFileDialog, QLabel)
from PyQt5.QtCore import pyqtSlot, Qt

from mne.channels import read_montage


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
        self.imported = QLabel("No file imported... Using builtin montages")
        vbox.addWidget(self.imported)
        hbox = QHBoxLayout()
        self.import_button = QPushButton("Import file")
        self.import_button.clicked.connect(self.import_montage)
        self.view_button = QPushButton("View")
        self.view_button.clicked.connect(self.view_montage)
        hbox.addWidget(self.import_button)
        hbox.addWidget(self.view_button)
        hbox.addStretch()
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                          QDialogButtonBox.Cancel)
        hbox.addWidget(self.buttonbox)
        vbox.addLayout(hbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.montages.itemSelectionChanged.connect(self.toggle_buttons)
        self.is_imported = False
        self.montage_path = ''
        self.toggle_buttons()  # initialize OK and View buttons state

    @pyqtSlot()
    def toggle_buttons(self):
        """Toggle OK and View buttons.
        """
        if self.montages.selectedItems() or self.is_imported:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
            self.view_button.setEnabled(True)
        else:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
            self.view_button.setEnabled(False)

    def view_montage(self):
        if self.montage_path == '':
            kind = self.montages.selectedItems()[0].data(0)
            montage = read_montage(kind)
        else:
            from ..utils.montage import xyz_to_montage
            montage = xyz_to_montage(self.montage_path)
        fig = montage.plot(show_names=True, show=False)
        win = fig.canvas.manager.window
        win.setWindowModality(Qt.WindowModal)
        win.setWindowTitle("Montage")
        win.findChild(QStatusBar).hide()
        win.findChild(QToolBar).hide()
        fig.show()

    def import_montage(self):
        self.montage_path, _ = QFileDialog.getOpenFileName(
                                    self, "Choose montage path", '',
                                    "3D Coordinates (*.xyz)")
        self.imported.setText('File succesfully imported from : \n'
                              + self.montage_path)
        self.is_imported = True
        self.toggle_buttons()
