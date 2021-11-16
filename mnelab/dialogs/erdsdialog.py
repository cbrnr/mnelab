# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QDoubleSpinBox, QGridLayout,
                               QLabel, QVBoxLayout)


class ERDSDialog(QDialog):
    def __init__(self, parent, t_range, f_range):
        super().__init__(parent)
        self.setWindowTitle("ERDS maps")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Frequency range:"), 0, 0)
        self._f1 = QDoubleSpinBox()
        self._f1.setRange(*f_range)
        self._f1.setValue(f_range[0])
        self._f1.setDecimals(1)
        self._f1.setSuffix(" Hz")
        grid.addWidget(self._f1, 0, 1)

        self._f2 = QDoubleSpinBox()
        self._f2.setRange(*f_range)
        self._f2.setValue(f_range[1])
        self._f2.setDecimals(1)
        self._f2.setSuffix(" Hz")
        grid.addWidget(self._f2, 0, 2)

        grid.addWidget(QLabel("Step size:"), 1, 0)
        self._step = QDoubleSpinBox()
        self._step.setRange(0.1, 5)
        self._step.setValue(1)
        self._step.setDecimals(1)
        self._step.setSingleStep(0.1)
        self._step.setSuffix(" Hz")
        grid.addWidget(self._step, 1, 1)

        grid.addWidget(QLabel("Time range:"), 2, 0)
        self._t1 = QDoubleSpinBox()
        self._t1.setRange(*t_range)
        self._t1.setValue(t_range[0])
        self._t1.setDecimals(1)
        self._step.setSingleStep(0.1)
        self._t1.setSuffix(" s")
        grid.addWidget(self._t1, 2, 1)

        self._t2 = QDoubleSpinBox()
        self._t2.setRange(*t_range)
        self._t2.setValue(t_range[1])
        self._t2.setDecimals(1)
        self._step.setSingleStep(0.1)
        self._t2.setSuffix(" s")
        grid.addWidget(self._t2, 2, 2)

        grid.addWidget(QLabel("Baseline:"), 3, 0)
        self._b1 = QDoubleSpinBox()
        self._b1.setRange(*t_range)
        self._b1.setValue(t_range[0])
        self._b1.setDecimals(1)
        self._step.setSingleStep(0.1)
        self._b1.setSuffix(" s")
        grid.addWidget(self._b1, 3, 1)

        self._b2 = QDoubleSpinBox()
        self._b2.setRange(*t_range)
        self._b2.setValue(0)
        self._b2.setDecimals(1)
        self._step.setSingleStep(0.1)
        self._b2.setSuffix(" s")
        grid.addWidget(self._b2, 3, 2)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def f1(self):
        return self._f1.value()

    @property
    def f2(self):
        return self._f2.value()

    @property
    def step(self):
        return self._step.value()

    @property
    def t1(self):
        return self._t1.value()

    @property
    def t2(self):
        return self._t2.value()

    @property
    def b1(self):
        return self._b1.value()

    @property
    def b2(self):
        return self._b2.value()
