from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QSpinBox, QComboBox, QDialogButtonBox, QCheckBox,
                             QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSlot


class RunICADialog(QDialog):
    def __init__(self, parent, nchan, have_picard=True, have_sklearn=True):
        super().__init__(parent)
        self.nchan = nchan
        self.setWindowTitle("Run ICA")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Method:"), 0, 0)
        self.method = QComboBox()
        self.method.setToolTip("The ICA method to use")
        self.methods = {"Infomax": "infomax", "Extended-infomax": "extended-infomax"}
        if have_sklearn:
            self.methods["FastICA"] = "fastica"
        if have_picard:
            self.methods["Picard"] = "picard"
        self.method.addItems(self.methods.keys())
        self.method.setCurrentText("infomax")
        min_len = max(len(key) for key in self.methods.keys())
        self.method.setMinimumContentsLength(min_len)
        grid.addWidget(self.method, 0, 1)

        grid.addWidget(QLabel("Number of components:"),1, 0)
        self.n_components = QSpinBox()
        self.n_components.setToolTip("Controls the number of PCA components "
                                   + "from the pre-ICA PCA entering the ICA "
                                   + "decomposition")
        self.n_components.setMinimum(0)
        self.n_components.setMaximum(nchan)
        self.n_components.setValue(nchan)
        self.n_components.setAlignment(Qt.AlignRight)
        grid.addWidget(self.n_components, 1, 1)

        self.groupBox_advancedparameters = QGroupBox()
        self.groupBox_advancedparameters.setTitle("Advanced parameters")
        self.gridLayout_advanced = QGridLayout(self.groupBox_advancedparameters)

        self.gridLayout_advanced.addWidget(QLabel("pca components:"),1, 0)
        self.pca_components = QSpinBox()
        self.pca_components.setToolTip("The number of PCA components used for "
                                     + "re-projecting the decomposed "
                                     + "data into sensor space")
        self.pca_components.setMinimum(0)
        self.pca_components.setMaximum(nchan)
        self.pca_components.setValue(nchan)
        self.pca_components.setAlignment(Qt.AlignRight)
        self.gridLayout_advanced.addWidget(self.pca_components, 1, 1)

        self.gridLayout_advanced.addWidget(QLabel("max pca components:"),2, 0)
        self.max_pca_components = QSpinBox()
        self.max_pca_components.setToolTip("The number of components returned "
                                         + "by the PCA decomposition")
        self.max_pca_components.setMinimum(0)
        self.max_pca_components.setMaximum(nchan)
        self.max_pca_components.setValue(nchan)
        self.max_pca_components.setAlignment(Qt.AlignRight)
        self.gridLayout_advanced.addWidget(self.max_pca_components, 2, 1)

        self.gridLayout_advanced.addWidget(QLabel("random seed:"),3, 0)
        self.random_seed = QSpinBox()
        self.random_seed.setToolTip("Random state to initialize ICA estimation "
                                  + "for reproducible results.")
        self.random_seed.setMinimum(0)
        self.random_seed.setMaximum(9999)
        self.random_seed.setValue(42)
        self.random_seed.setAlignment(Qt.AlignRight)
        self.gridLayout_advanced.addWidget(self.random_seed, 3, 1)

        self.gridLayout_advanced.addWidget(QLabel("max iter:"),4, 0)
        self.max_iter = QSpinBox()
        self.max_iter.setToolTip("Maximum number of iterations during fit")
        self.max_iter.setMinimum(0)
        self.max_iter.setMaximum(9999)
        self.max_iter.setValue(500)
        self.max_iter.setAlignment(Qt.AlignRight)
        self.gridLayout_advanced.addWidget(self.max_iter, 4, 1)


        self.groupBox_advancedparameters.setCheckable(True)
        self.groupBox_advancedparameters.setChecked(False)

        grid.addWidget(self.groupBox_advancedparameters, 2, 0)

        grid.addWidget(QLabel("decim:"),3, 0)
        self.decim = QSpinBox()
        self.decim.setToolTip("Increment for selecting each nth time slice")
        self.decim.setMinimum(0)
        self.decim.setMaximum(9999)
        self.decim.setValue(1)
        self.decim.setAlignment(Qt.AlignRight)
        grid.addWidget(self.decim)

        grid.addWidget(QLabel("Exclude bad segments:"), 4, 0)
        self.exclude_bad_segments = QCheckBox()
        self.exclude_bad_segments.setToolTip("Whether to omit bad segments "
                                            +"from the data before fitting")
        self.exclude_bad_segments.setChecked(True)
        grid.addWidget(self.exclude_bad_segments)
        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.check_parameters)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    def check_parameters(self):
        """Checks if ica parameters are correctly set and accept dialog"""
        if int(self.max_pca_components.text()) > self.nchan:
            self.validparameters = False
            QMessageBox.critical(self, "Invalid Parameters",
                    "the number of max pca components must be <="
                  + " to the number of channels")
            return()
        elif int(self.max_pca_components.text()) < int(self.n_components.text()):
            self.validparameters = False
            QMessageBox.critical(self, "Invalid Parameters",
                    "the number of ica components must be <="
                  + " to the number of max pca components")
            return()
        elif int(self.pca_components.text()) > int(self.max_pca_components.text()):
            QMessageBox.critical(self, "Invalid Parameters",
                    "the number of pca components must be <= "
                  + "to the number of max pca components")
            self.validparameters = False
            return()
        else:
            self.validparameters = True
            self.accept()
            return()
