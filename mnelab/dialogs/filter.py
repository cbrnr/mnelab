# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class DataSetChangeDialog(QDialog):
    def add_buttonbox(self, force_new, vbox):
        buttonbox = QDialogButtonBox()
        buttonbox.addButton("Create new data set", QDialogButtonBox.YesRole)
        overwrite_button = buttonbox.addButton(
            "Overwrite current data set",
            QDialogButtonBox.YesRole,
        )
        buttonbox.addButton("Cancel", QDialogButtonBox.RejectRole)

        self.inplace = False
        if force_new:
            overwrite_button.setEnabled(False)
            overwrite_button.setToolTip("Data sets with filenames are always duplicated.")

        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        overwrite_button.clicked.connect(self.set_overwrite)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    def set_overwrite(self):
        self.inplace = True


class FilterDialog(DataSetChangeDialog):
    def __init__(self, parent, force_new=False):
        super().__init__(parent)
        self.setWindowTitle("Filter data")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Low cutoff frequency (Hz):"), 0, 0)
        self.lowedit = QLineEdit()
        grid.addWidget(self.lowedit, 0, 1)
        grid.addWidget(QLabel("High cutoff frequency (Hz):"), 1, 0)
        self.highedit = QLineEdit()
        grid.addWidget(self.highedit, 1, 1)
        vbox.addLayout(grid)

        self.add_buttonbox(force_new, vbox)

    @property
    def low(self):
        low = self.lowedit.text()
        return float(low) if low else None

    @property
    def high(self):
        high = self.highedit.text()
        return float(high) if high else None
