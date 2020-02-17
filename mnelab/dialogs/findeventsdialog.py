# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                            QFormLayout, QLabel, QSpinBox)

MAX_INT = 2147483647


class FindEventsDialog(QDialog):
    def __init__(self, parent, channels, default_stim):
        super().__init__(parent)
        self.setWindowTitle("Find Events")

        form = QFormLayout(self)
        self.stimchan = QComboBox()
        self.stimchan.addItems(channels)
        self.stimchan.setCurrentIndex(default_stim)
        form.addRow(QLabel("Stim channel:"), self.stimchan)

        self.consecutive = QCheckBox()
        self.consecutive.setChecked(True)
        form.addRow(QLabel("Consecutive"), self.consecutive)

        self.initial_event = QCheckBox()
        self.initial_event.setChecked(True)
        form.addRow(QLabel("Initial event"), self.initial_event)

        self.uint_cast = QCheckBox()
        self.uint_cast.setChecked(True)
        form.addRow(QLabel("Cast to unsigned integer"), self.uint_cast)

        self.minduredit = QSpinBox()
        self.minduredit.setMaximum(MAX_INT)
        form.addRow(QLabel("Minimum duration:"), self.minduredit)

        self.shortesteventedit = QSpinBox()
        self.shortesteventedit.setMaximum(MAX_INT)
        form.addRow(QLabel("Shortest event:"), self.shortesteventedit)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        form.addRow(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        form.setSizeConstraint(QFormLayout.SetFixedSize)
