from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QCheckBox, QLineEdit, QDialogButtonBox)


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
        self.initial_event.setChecked(False)
        grid.addWidget(self.initial_event, 1, 1)

        grid.addWidget(QLabel("Cast to unsigned integer"), 2, 0)
        self.uint_cast = QCheckBox()
        self.uint_cast.setChecked(False)
        grid.addWidget(self.uint_cast, 2, 1)

        grid.addWidget(QLabel("Minimum duration:"), 3, 0)
        self.minduredit = QLineEdit()
        grid.addWidget(self.minduredit, 3, 1)

        grid.addWidget(QLabel("Shortest event:"), 4, 0)
        self.shortesteventedit = QLineEdit()
        grid.addWidget(self.shortesteventedit, 4, 1)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

    @property
    def min_dur(self):
        min_dur = self.minduredit.text()
        return int(min_dur) if min_dur else None

    @property
    def shortest_event(self):
        shortest_event = self.shortesteventedit.text()
        return int(shortest_event) if shortest_event else None
