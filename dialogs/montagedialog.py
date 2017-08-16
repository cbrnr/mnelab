from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox
from PyQt5.QtCore import pyqtSlot


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
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                          QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.montages.itemSelectionChanged.connect(self.toggle_ok)
        self.toggle_ok()  # initialize OK button state

    @pyqtSlot()
    def toggle_ok(self):
        if self.montages.selectedItems():
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
