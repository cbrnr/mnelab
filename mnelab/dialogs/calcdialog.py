# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import QDialog, QLabel, QVBoxLayout, QDialogButtonBox


class CalcDialog(QDialog):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.setWindowTitle(title)
        vbox = QVBoxLayout(self)
        label = QLabel(message)
        button = QDialogButtonBox(QDialogButtonBox.Cancel)
        button.rejected.connect(self.close)
        vbox.addWidget(label)
        vbox.addWidget(button)
