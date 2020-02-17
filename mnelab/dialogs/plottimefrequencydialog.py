# Authors: Lukas Stranger <l.stranger@student.tugraz.at>
#          Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                            QDoubleSpinBox,QGridLayout, QLabel)
from qtpy.QtCore import Qt, Slot


class PlotTFDialog(QDialog):
    def __init__(self, parent, methods, t_range, f_range, modes,
                 title="Time/Frequency settings"):
        super().__init__(parent)
        self.setWindowTitle(title)

        grid = QGridLayout(self)

        # Method
        grid.addWidget(QLabel("Method:"), 0, 0)
        self._method = QComboBox()
        self._method.insertItems(0, methods)
        self._method.setCurrentIndex(0)
        grid.addWidget(self._method, 0, 2, 1, 4)

        grid.addWidget(QLabel("From"), 1, 2, Qt.AlignCenter)
        grid.addWidget(QLabel("Resolution"), 1, 3, 1, 2, Qt.AlignCenter)
        grid.addWidget(QLabel("To"), 1, 5, Qt.AlignCenter)

        # Frequency
        grid.addWidget(QLabel("Frequency (in Hz):"), 2, 0)

        self._lfreq = QDoubleSpinBox()
        self._lfreq.setRange(f_range[0], f_range[1])
        self._lfreq.setValue(f_range[0])
        self._lfreq.setDecimals(1)
        self._lfreq.setSuffix(" Hz")
        grid.addWidget(self._lfreq, 2, 2)

        self._freq_res = QDoubleSpinBox()
        self._freq_res.setRange(0.2, 4.)
        self._freq_res.setValue(1.)
        self._freq_res.setDecimals(1)
        self._freq_res.setSingleStep(0.1)
        grid.addWidget(self._freq_res, 2, 3, 1, 2)

        self._ufreq = QDoubleSpinBox()
        self._ufreq.setRange(f_range[0], f_range[1])
        self._ufreq.setValue(f_range[1])
        self._ufreq.setDecimals(1)
        self._ufreq.setSuffix(" Hz")
        grid.addWidget(self._ufreq, 2, 5)


        # Time
        grid.addWidget(QLabel("Time (in s):"), 3, 0)

        self._start_time = QDoubleSpinBox()
        self._start_time.setRange(t_range[0], t_range[1])
        self._start_time.setValue(t_range[0])
        self._start_time.setDecimals(2)
        self._start_time.setSingleStep(0.1)
        self._start_time.setSuffix(" s")
        grid.addWidget(self._start_time, 3, 2, 1, 2)

        self._stop_time = QDoubleSpinBox()
        self._stop_time.setRange(t_range[0], t_range[1])
        self._stop_time.setValue(t_range[1])
        self._stop_time.setDecimals(2)
        self._stop_time.setSingleStep(0.1)
        self._stop_time.setSuffix(" s")
        grid.addWidget(self._stop_time, 3, 4, 1, 2)

        grid.addWidget(QLabel("Cycles:"), 4, 0)
        grid.addWidget(QLabel(" Frequency /"), 4, 2)

        self._n_cycles = QDoubleSpinBox()
        self._n_cycles.setRange(1., 8.)
        self._n_cycles.setValue(1.)
        self._n_cycles.setDecimals(1)
        grid.addWidget(self._n_cycles, 4, 3)

        # Baseline
        grid.addWidget(QLabel("Baseline correction:"), 5, 0)
        self.baseline_checkbox = QCheckBox("")
        self.baseline_checkbox.setChecked(True)
        self.baseline_checkbox.stateChanged.connect(self.toggle_baseline)
        grid.addWidget(self.baseline_checkbox, 5, 1)

        self._start_baseline = QDoubleSpinBox()
        self._start_baseline.setRange(t_range[0], t_range[1])
        self._start_baseline.setValue(t_range[0])
        self._start_baseline.setDecimals(2)
        self._start_baseline.setSingleStep(0.05)
        self._start_baseline.setSuffix(" s")
        grid.addWidget(self._start_baseline, 5, 2, 1, 2)

        self._stop_baseline = QDoubleSpinBox()
        self._stop_baseline.setRange(t_range[0], t_range[1])
        self._stop_baseline.setValue(0)
        self._stop_baseline.setDecimals(2)
        self._stop_baseline.setSingleStep(0.05)
        self._stop_baseline.setSuffix(" s")
        grid.addWidget(self._stop_baseline, 5, 4, 1, 2)

        self._baseline_mode = QComboBox()
        self._baseline_mode.insertItems(0, modes)
        self._baseline_mode.setCurrentIndex(0)
        grid.addWidget(self._baseline_mode, 6, 2, 1, 4)

        # Cluster
        grid.addWidget(QLabel("Permutation clustering:"), 7, 0)
        self.cluster_checkbox = QCheckBox("")
        self.cluster_checkbox.setChecked(False)
        grid.addWidget(self.cluster_checkbox, 7, 1)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        grid.addWidget(buttonbox, 8, 1, 1, 6)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        grid.setSizeConstraint(QGridLayout.SetFixedSize)

    @property
    def tfr_method(self):
        return self._method.currentText()

    @property
    def n_cycles(self):
        return self._n_cycles.value()

    @property
    def lower_frequency(self):
        return self._lfreq.value()

    @property
    def upper_frequency(self):
        return self._ufreq.value()

    @property
    def freq_resolution(self):
        return self._freq_res.value()

    @property
    def start_time(self):
        return self._start_time.value()

    @property
    def stop_time(self):
        return self._stop_time.value()

    @property
    def start_baseline(self):
        if self.baseline_checkbox.isChecked():
            return self._start_baseline.value()
        else:
            return None

    @property
    def stop_baseline(self):
        if self.baseline_checkbox.isChecked():
            return self._stop_baseline.value()
        else:
            return None

    @property
    def apply_baseline(self):
        return self.baseline_checkbox.isChecked()

    @property
    def baseline_mode(self):
        return self._baseline_mode.currentText()

    @property
    def cluster(self):
        return self.cluster_checkbox.isChecked()

    @Slot()
    def toggle_baseline(self):
        if self.baseline_checkbox.isChecked():
            self._baseline_mode.setEnabled(True)
            self._start_baseline.setEnabled(True)
            self._stop_baseline.setEnabled(True)
        else:
            self._baseline_mode.setEnabled(False)
            self._start_baseline.setEnabled(False)
            self._stop_baseline.setEnabled(False)
