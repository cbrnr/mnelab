# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                            QCheckBox, QDialogButtonBox, QSpinBox, QComboBox)


MAX_INT = 2147483647


class FindEventsDialog(QDialog):
    def __init__(self, parent, channels, default_stim):
        super().__init__(parent)
        self.setWindowTitle("Find Events")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Stim channel:"), 0, 0)
        self.stimchan = QComboBox()
        self.stimchan.addItems(channels)
        self.stimchan.setCurrentIndex(default_stim)
        grid.addWidget(self.stimchan, 0, 1)

        grid.addWidget(QLabel("Consecutive"), 1, 0)
        self.consecutive = QCheckBox()
        self.consecutive.setChecked(True)
        grid.addWidget(self.consecutive, 1, 1)

        grid.addWidget(QLabel("Initial event"), 2, 0)
        self.initial_event = QCheckBox()
        self.initial_event.setChecked(True)
        grid.addWidget(self.initial_event, 2, 1)

        grid.addWidget(QLabel("Cast to unsigned integer"), 3, 0)
        self.uint_cast = QCheckBox()
        self.uint_cast.setChecked(True)
        grid.addWidget(self.uint_cast, 3, 1)

        grid.addWidget(QLabel("Minimum duration:"), 4, 0)
        self.minduredit = QSpinBox()
        self.minduredit.setMaximum(MAX_INT)
        grid.addWidget(self.minduredit, 4, 1)

        grid.addWidget(QLabel("Shortest event:"), 5, 0)
        self.shortesteventedit = QSpinBox()
        self.shortesteventedit.setMaximum(MAX_INT)
        grid.addWidget(self.shortesteventedit, 5, 1)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)
