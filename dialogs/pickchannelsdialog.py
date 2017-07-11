from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox


class PickChannelsDialog(QDialog):
    def __init__(self, channels):
        super().__init__()
        self.setWindowTitle("Pick channels")
        vbox = QVBoxLayout(self)
        self.channels = QListWidget()
        self.channels.insertItems(0, channels)
        self.channels.setSelectionMode(QListWidget.ExtendedSelection)
        vbox.addWidget(self.channels)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
