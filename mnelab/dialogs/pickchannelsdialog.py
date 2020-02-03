# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox
from qtpy.QtCore import Slot


class PickChannelsDialog(QDialog):
    def __init__(self, parent, channels, selected=None, title="Pick channels"):
        super().__init__(parent)
        self.setWindowTitle(title)
        if selected is None:
            selected = []
        self.initial_selection = selected
        vbox = QVBoxLayout(self)
        self.channels = QListWidget()
        self.channels.insertItems(0, channels)
        self.channels.setSelectionMode(QListWidget.ExtendedSelection)
        for i in range(self.channels.count()):
            if self.channels.item(i).data(0) in selected:
                self.channels.item(i).setSelected(True)
        vbox.addWidget(self.channels)
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                          QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.channels.itemSelectionChanged.connect(self.toggle_buttons)
        self.toggle_buttons()  # initialize OK button state

    @Slot()
    def toggle_buttons(self):
        """Toggle OK button.
        """
        selected = [item.data(0) for item in self.channels.selectedItems()]
        if selected != self.initial_selection:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
