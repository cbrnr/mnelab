[![PyPI Version](https://img.shields.io/pypi/v/mnelab)](https://pypi.org/project/mnelab/)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/mnelab)](https://anaconda.org/conda-forge/mnelab)
![Python](https://img.shields.io/badge/python-3.6&ndash;3.9-green.svg)
![Downloads PyPI](https://img.shields.io/pypi/dm/mnelab?color=blue&label=downloads%20pypi)
![Downloads Conda](https://img.shields.io/conda/dn/conda-forge/mnelab?color=blue&label=downloads%20conda)
![License](https://img.shields.io/github/license/cbrnr/mnelab)

![](https://raw.githubusercontent.com/cbrnr/mnelab/main/mnelab/images/mnelab_logo.png)

MNELAB is a graphical user interface (GUI) for [MNE](https://github.com/mne-tools/mne-python), a Python package for EEG/MEG analysis.

![](https://raw.githubusercontent.com/cbrnr/mnelab/main/mnelab.png)

### Changelog
Check out the [changelog](https://github.com/cbrnr/mnelab/blob/main/CHANGELOG.md) to learn what we added, changed or fixed in the latest release.

### Dependencies
MNELAB requires Python >= 3.6 and the following packages:
- [mne](https://github.com/mne-tools/mne-python) >= 0.22.0
- [QtPy](https://github.com/spyder-ide/qtpy) >= 1.9.0
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5) >= 5.10.0 or [PySide2](https://www.qt.io/qt-for-python) >= 5.10.0
- [numpy](http://www.numpy.org/) >= 1.14.0
- [scipy](https://www.scipy.org/scipylib/index.html) >= 1.0.0
- [matplotlib](https://matplotlib.org/) >= 2.1.0
- [pyobjc-framework-Cocoa](https://pyobjc.readthedocs.io/en/latest/) >= 5.2.0 (macOS only)
- [python.app](https://anaconda.org/anaconda/python.app) (only when using Anaconda on macOS)

Optional dependencies provide additional features if installed:
- [scikit-learn]() (ICA computation with FastICA)
- [python-picard](https://pierreablin.github.io/picard/) (ICA computation with PICARD)
- [pyxdf](https://github.com/xdf-modules/xdf-Python) (XDF import)
- [pyEDFlib](https://github.com/holgern/pyedflib) (EDF/BDF export)
- [pybv](https://github.com/bids-standard/pybv) (BrainVision VHDR/VMRK/EEG export)

### Additional features
MNELAB comes with the following features that are not (yet) available in MNE:
- Export to EDF/BDF (requires [pyEDFlib](https://github.com/holgern/pyedflib))
- Export to EEGLAB SET
- Export to BrainVision VHDR/VMRK/EEG (requires [pybv](https://github.com/bids-standard/pybv))
- Import [XDF](https://github.com/sccn/xdf/wiki/Specifications) files (requires [pyxdf](https://github.com/xdf-modules/xdf-Python))

### Installation
#### pip
Make sure you have either `PySide2` or `PyQt5` installed. If you have neither, we recommend `PySide2`, which you can install with `pip install PySide2`. Then install MNELAB with:

```
pip install mnelab
```

You can start MNELAB in a terminal with `mnelab` or `python -m mnelab`.

#### conda
An unofficial but regularly updated conda package can be installed from [conda-forge](https://conda-forge.org/).
We strongly suggest to install MNELAB into its own dedicated environment:

```
conda create -y -n mnelab -c conda-forge mnelab
```

You can start MNELAB in a terminal with `conda activate mnelab` followed by `mnelab` or `python -m mnelab`. Any issues with this conda package should be reported to the package [issue tracker](https://github.com/conda-forge/mnelab-feedstock/issues).

#### Arch Linux
If you use [Arch Linux](https://www.archlinux.org/), you can install the [python-mnelab](https://aur.archlinux.org/packages/python-mnelab/) AUR package (note that this also requires the [python-mne](https://aur.archlinux.org/packages/python-mne/) AUR package).

### Contributing
The [contributing guide](https://github.com/cbrnr/mnelab/blob/main/CONTRIBUTING.md) contains detailed instructions on how to contribute to MNELAB.
