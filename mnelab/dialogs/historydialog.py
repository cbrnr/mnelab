# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QPlainTextEdit,
                             QDialogButtonBox)


class HistoryDialog(QDialog):
    def __init__(self, parent, history):
        super().__init__(parent=parent)
        self.setWindowTitle("History")
        layout = QVBoxLayout()
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(history)
        layout.addWidget(text)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        layout.addWidget(buttonbox)
        self.setLayout(layout)
        buttonbox.accepted.connect(self.accept)
        self.resize(700, 500)
