# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QVBoxLayout


class BrainVisionDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Import BrainVision data")

        vbox = QVBoxLayout(self)
        self._ignore_marker_types = QCheckBox(
            "Ignore marker types (only use description)"
        )
        self._ignore_marker_types.setChecked(False)
        vbox.addWidget(self._ignore_marker_types)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def ignore_marker_types(self):
        return self._ignore_marker_types.isChecked()
