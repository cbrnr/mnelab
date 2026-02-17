# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QVBoxLayout,
)


class BVRFDialog(QDialog):
    def __init__(self, parent, participants):
        super().__init__(parent)

        self.setWindowTitle("Import BVRF data")

        vbox = QVBoxLayout(self)

        n_participants = len(participants)
        label = QLabel(f"This dataset contains {n_participants} participants:")
        vbox.addWidget(label)

        # list widget for participant selection
        self._participant_list = QListWidget()
        self._participant_list.addItems(participants)
        for i in range(self._participant_list.count()):
            item = self._participant_list.item(i)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)  # All selected by default
        vbox.addWidget(self._participant_list)

        # checkbox for creating separate datasets
        self._create_separate = QCheckBox("Create separate data sets")
        self._create_separate.setChecked(True)  # Checked by default
        vbox.addWidget(self._create_separate)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def selected_participants(self):
        """Return list of selected participant IDs."""
        selected = []
        for i in range(self._participant_list.count()):
            item = self._participant_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

    @property
    def create_separate(self):
        """Return whether to create separate datasets."""
        return self._create_separate.isChecked()
