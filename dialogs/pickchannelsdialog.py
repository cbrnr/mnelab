from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox


class PickChannelsDialog(QDialog):
    def __init__(self, parent, channels, selected=[], title="Pick channels"):
        super().__init__(parent)
        self.setWindowTitle(title)
        vbox = QVBoxLayout(self)
        self.channels = QListWidget()
        self.channels.insertItems(0, channels)
        self.channels.setSelectionMode(QListWidget.ExtendedSelection)
        for i in range(self.channels.count()):
            if self.channels.item(i).data(0) in selected:
                self.channels.item(i).setSelected(True)
        vbox.addWidget(self.channels)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
