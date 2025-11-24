# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class AnnotationsIntervalDialog(QDialog):
    def __init__(self, parent, event_counts, annotations):
        super().__init__(parent)
        self.setWindowTitle("Create Annotations from Events")
        vbox = QVBoxLayout(self)
        self.event_counts = event_counts
        self.event_names = list(event_counts.keys())

        # radio buttons
        self.annotations_events_button = QRadioButton("Copy Events to Annotations")
        vbox.addWidget(self.annotations_events_button)
        self.annotations_events_button.setChecked(True)

        self.event_event_button = QRadioButton("Define Intervals between Events")
        vbox.addWidget(self.event_event_button)

        self.annotation_type_group = QButtonGroup(self)
        self.annotation_type_group.addButton(self.annotations_events_button)
        self.annotation_type_group.addButton(self.event_event_button)

        # Settings widget
        self.interval_settings_widget = QWidget()
        self.grid = QGridLayout(self.interval_settings_widget)
        self.grid.setContentsMargins(20, 0, 0, 0)
        self.grid.setColumnStretch(1, 1)

        # Event to Event
        self.grid.addWidget(QLabel("Start Event:"), 0, 0)
        self.start_event_combo = QComboBox()
        self.start_event_combo.setPlaceholderText("Select Event ...")
        self.start_event_combo.addItems(self.event_names)
        self.start_event_combo.setCurrentIndex(-1)
        self.grid.addWidget(self.start_event_combo, 0, 1)

        self.grid.addWidget(QLabel("Start Offset:"), 1, 0)
        self.start_offset_spin = QDoubleSpinBox()
        self.start_offset_spin.setSingleStep(0.5)
        self.start_offset_spin.setMinimum(-99)
        self.start_offset_spin.setMaximum(99)
        self.start_offset_spin.setSuffix(" s")
        self.grid.addWidget(self.start_offset_spin, 1, 1)

        self.grid.addWidget(QLabel("End Event:"), 2, 0)
        self.end_event_combo = QComboBox()
        self.end_event_combo.setPlaceholderText("Select Event ...")
        self.end_event_combo.addItems(self.event_names)
        self.end_event_combo.setCurrentIndex(-1)
        self.grid.addWidget(self.end_event_combo, 2, 1)

        self.grid.addWidget(QLabel("End Offset:"), 3, 0)
        self.end_offset_spin = QDoubleSpinBox()
        self.end_offset_spin.setSingleStep(0.5)
        self.end_offset_spin.setMinimum(-99)
        self.end_offset_spin.setMaximum(99)
        self.end_offset_spin.setSuffix(" s")
        self.grid.addWidget(self.end_offset_spin, 3, 1)

        self.grid.addWidget(QLabel("Annotation"), 4, 0)
        self.annotation_combo = QComboBox()
        self.annotation_combo.setEditable(True)
        self.annotation_combo.lineEdit().setPlaceholderText("Enter Annotation ...")
        self.annotation_combo.addItems(annotations)
        self.annotation_combo.setCurrentIndex(-1)
        self.annotation_combo.setMinimumWidth(130)
        self.grid.addWidget(self.annotation_combo, 4, 1)

        self.to_start_check = QCheckBox("Extend to start")
        self.to_start_check.setChecked(True)
        self.grid.addWidget(self.to_start_check, 5, 1)

        self.to_end_check = QCheckBox("Extend to end")
        self.to_end_check.setChecked(True)
        self.grid.addWidget(self.to_end_check, 6, 1)

        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: #d32f2f;")
        self.warning_label.setWordWrap(True)
        self.warning_label.setVisible(False)
        self.grid.addWidget(self.warning_label, 7, 0, 1, 2)

        vbox.addWidget(self.interval_settings_widget)

        # Buttons
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        vbox.addWidget(self.buttonbox)

        # Connections/logic
        self.ok_button = self.buttonbox.button(QDialogButtonBox.Ok)
        self.annotation_type_group.buttonToggled.connect(self._on_interval_type_changed)
        self.annotation_type_group.buttonToggled.connect(self._check_validity)

        self.start_event_combo.currentTextChanged.connect(self._on_start_event_changed)
        self.start_event_combo.currentIndexChanged.connect(self._check_validity)
        self.end_event_combo.currentIndexChanged.connect(self._check_validity)

        self.annotation_combo.currentTextChanged.connect(self._check_validity)

        self.interval_settings_widget.setEnabled(self.event_event_button.isChecked())

        # initial check
        self._check_validity()
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    def _check_validity(self):
        if self.annotations_events_button.isChecked():
            self.ok_button.setEnabled(True)
            self.warning_label.setVisible(False)
            return

        start_event_selected = self.start_event_combo.currentIndex() != -1
        end_event_selected = self.end_event_combo.currentIndex() != -1

        annotation_text = self.annotation_combo.currentText().strip()
        annotation_filled = len(annotation_text) > 0

        show_warning = False
        if start_event_selected and end_event_selected:
            start_event = self.start_event_combo.currentText()
            end_event = self.end_event_combo.currentText()

            count_start = self.event_counts.get(start_event, 0)
            count_end = self.event_counts.get(end_event, 0)

            if count_start != count_end:
                show_warning = True
                self.warning_label.setText(
                    f"Warning: Unequal number of events. '{start_event}' has "
                    f"{count_start} occurrences, while '{end_event}' has {count_end}."
                    f" Unpaired events will be ignored."
                )

        self.warning_label.setVisible(show_warning)

        if start_event_selected and end_event_selected and annotation_filled:
            self.ok_button.setEnabled(True)
        else:
            self.ok_button.setEnabled(False)

    def _on_interval_type_changed(self, button, checked):
        if not checked:
            return
        is_interval_mode = button == self.event_event_button
        self.interval_settings_widget.setEnabled(is_interval_mode)

        if not is_interval_mode:
            self.warning_label.setVisible(False)

    def _on_start_event_changed(self, start_text):
        current_end_selection = self.end_event_combo.currentText()

        if start_text:
            filtered_events = [e for e in self.event_names if e != start_text]
        else:
            filtered_events = self.event_names

        self.end_event_combo.blockSignals(True)
        self.end_event_combo.clear()
        self.end_event_combo.setPlaceholderText("Select Event ...")
        self.end_event_combo.addItems(filtered_events)

        if current_end_selection in filtered_events:
            self.end_event_combo.setCurrentText(current_end_selection)
        else:
            self.end_event_combo.setCurrentIndex(-1)

        self.end_event_combo.blockSignals(False)

    def annotations_from_events(self):
        return self.annotations_events_button.isChecked()

    def event_to_event_data(self):
        return {
            "start_event": self.start_event_combo.currentText(),
            "start_offset": self.start_offset_spin.value(),
            "end_event": self.end_event_combo.currentText(),
            "end_offset": self.end_offset_spin.value(),
            "annotation": self.annotation_combo.currentText(),
            "extend_start": self.to_start_check.isChecked(),
            "extend_end": self.to_end_check.isChecked(),
        }
