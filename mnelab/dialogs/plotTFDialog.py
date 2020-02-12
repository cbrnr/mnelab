# Authors: Lukas Stranger <l.stranger@student.tugraz.at>
#          Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                            QGridLayout, QLabel, QListWidget, QVBoxLayout)
from qtpy.QtCore import Qt, Slot


class PlotTFDialog(QDialog):
    def __init__(self, parent, t_range, f_range, modi, title="Time/Frequency settings"):
        super().__init__(parent)
        self.setWindowTitle(title)
        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("From"), 0, 2, Qt.AlignCenter)
        grid.addWidget(QLabel("Resolution"), 0, 3, 1, 2, Qt.AlignCenter)
        grid.addWidget(QLabel("To"), 0, 5, Qt.AlignCenter)

        # Frequency
        grid.addWidget(QLabel("Frequecy (in Hz):"), 1, 0)
        self.freq_checkbox = QCheckBox()
        self.freq_checkbox.setChecked(True)
        self.freq_checkbox.setEnabled(False)
        grid.addWidget(self.freq_checkbox, 1, 1)

        self._lfreq = QDoubleSpinBox()
        self._lfreq.setMinimum(f_range[0])
        self._lfreq.setValue(f_range[0])
        self._lfreq.setMaximum(f_range[1])
        self._lfreq.setDecimals(1)
        self._lfreq.setSuffix(" Hz")
        grid.addWidget(self._lfreq, 1, 2)

        self._freq_reso = QDoubleSpinBox()
        self._freq_reso.setMinimum(0.2)
        self._freq_reso.setValue(1.)
        self._freq_reso.setMaximum(4.)
        self._freq_reso.setDecimals(1)
        self._freq_reso.setSingleStep(0.1)
        grid.addWidget(self._freq_reso, 1, 3, 1, 2)

        self._ufreq = QDoubleSpinBox()
        self._ufreq.setMinimum(f_range[0])
        self._ufreq.setValue(f_range[1])
        self._ufreq.setMaximum(f_range[1])
        self._ufreq.setDecimals(1)
        self._ufreq.setSuffix(" Hz")
        grid.addWidget(self._ufreq, 1, 5)


        # Time
        grid.addWidget(QLabel("Time (in s):"), 2, 0)
        self.time_checkbox = QCheckBox()
        self.time_checkbox.setChecked(True)
        self.time_checkbox.setEnabled(False)
        grid.addWidget(self.time_checkbox, 2, 1)

        self._start_time = QDoubleSpinBox()
        self._start_time.setMinimum(t_range[0])
        self._start_time.setValue(t_range[0])
        self._start_time.setMaximum(t_range[1])
        self._start_time.setDecimals(2)
        self._start_time.setSingleStep(0.1)
        self._start_time.setSuffix(" s")
        grid.addWidget(self._start_time, 2, 2, 1, 2)

        self._stop_time = QDoubleSpinBox()
        self._stop_time.setMinimum(t_range[0])
        self._stop_time.setValue(t_range[1])
        self._stop_time.setMaximum(t_range[1])
        self._stop_time.setDecimals(2)
        self._stop_time.setSingleStep(0.1)
        self._stop_time.setSuffix(" s")
        grid.addWidget(self._stop_time, 2, 4, 1, 2)

        # Baseline
        grid.addWidget(QLabel("Baseline correction:"), 3, 0)
        self.baseline_checkbox = QCheckBox("")
        self.baseline_checkbox.setChecked(True)
        self.baseline_checkbox.stateChanged.connect(self.toggle_baseline)
        grid.addWidget(self.baseline_checkbox, 3, 1)

        self._start_baseline = QDoubleSpinBox()
        self._start_baseline.setMinimum(t_range[0])
        self._start_baseline.setValue(t_range[0])
        self._start_baseline.setMaximum(t_range[0])
        self._start_baseline.setDecimals(2)
        self._start_baseline.setSingleStep(0.05)
        self._start_baseline.setSuffix(" s")
        grid.addWidget(self._start_baseline, 3, 2, 1, 2)

        self._stop_baseline = QDoubleSpinBox()
        self._stop_baseline.setMinimum(t_range[0])
        self._stop_baseline.setValue(0)
        self._stop_baseline.setMaximum(t_range[1])
        self._stop_baseline.setDecimals(2)
        self._stop_baseline.setSingleStep(0.05)
        self._stop_baseline.setSuffix(" s")
        grid.addWidget(self._stop_baseline, 3, 4, 1, 2)

        self._baseline_mode = QListWidget()
        self._baseline_mode.insertItems(0, modi)
        self._baseline_mode.setSelectionMode(QListWidget.SingleSelection)
        grid.addWidget(self._baseline_mode, 4, 2, 1, 4)

        # Cluster
        grid.addWidget(QLabel("Permutation clustering:"), 5, 0)
        self.cluster_checkbox = QCheckBox("")
        self.cluster_checkbox.setChecked(True)
        grid.addWidget(self.cluster_checkbox, 5, 1)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def lower_frequency(self):
        if self.freq_checkbox.isChecked():
            return self._lfreq.value()
        else:
            return None

    @property
    def upper_frequency(self):
        if self.freq_checkbox.isChecked():
            return self._ufreq.value()
        else:
            return None

    @property
    def freq_resolution(self):
        if self.freq_checkbox.isChecked():
            return self._freq_reso.value()
        else:
            return None

    @property
    def start_time(self):
        if self.time_checkbox.isChecked():
            return self._start_time.value()
        else:
            return None

    @property
    def stop_time(self):
        if self.time_checkbox.isChecked():
            return self._stop_time.value()
        else:
            return None

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
        mode = [item.data(0) for item in self._baseline_mode.selectedItems()]
        return mode[0] if mode else None

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