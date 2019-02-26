from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QCheckBox, QDialogButtonBox, QSpinBox)


MAX_INT = 2147483647


class FindEventsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Find Events")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Consecutive"), 0, 0)
        self.consecutive = QCheckBox()
        self.consecutive.setChecked(True)
        grid.addWidget(self.consecutive, 0, 1)

        grid.addWidget(QLabel("Initial Event"), 1, 0)
        self.initial_event = QCheckBox()
        self.initial_event.setChecked(True)
        grid.addWidget(self.initial_event, 1, 1)

        grid.addWidget(QLabel("Cast to unsigned integer"), 2, 0)
        self.uint_cast = QCheckBox()
        self.uint_cast.setChecked(True)
        grid.addWidget(self.uint_cast, 2, 1)

        grid.addWidget(QLabel("Minimum duration:"), 3, 0)
        self.minduredit = QSpinBox()
        self.minduredit.setMaximum(MAX_INT)
        grid.addWidget(self.minduredit, 3, 1)

        grid.addWidget(QLabel("Shortest event:"), 4, 0)
        self.shortesteventedit = QSpinBox()
        self.shortesteventedit.setMaximum(MAX_INT)
        grid.addWidget(self.shortesteventedit, 4, 1)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
