![Python](https://img.shields.io/pypi/pyversions/mnelab.svg?logo=python)
[![PyPI Version](https://img.shields.io/pypi/v/mnelab)](https://pypi.org/project/mnelab/)
[![License](https://img.shields.io/github/license/cbrnr/mnelab)](LICENSE)

![](https://raw.githubusercontent.com/cbrnr/mnelab/main/mnelab/images/mnelab_logo.png)

MNELAB is a graphical user interface (GUI) for [MNE](https://github.com/mne-tools/mne-python), a Python package for EEG/MEG analysis.

![](https://raw.githubusercontent.com/cbrnr/mnelab/main/mnelab.png)

### Changelog
Check out the [changelog](https://github.com/cbrnr/mnelab/blob/main/CHANGELOG.md) to learn what we added, changed, or fixed in the latest release.

### Dependencies
MNELAB requires Python >= 3.8 and the following packages:
- [mne](https://github.com/mne-tools/mne-python) >= 0.24.0
- [PySide6](https://www.qt.io/qt-for-python) >= 6.2.0
- [numpy](http://www.numpy.org/) >= 1.14.0
- [scipy](https://www.scipy.org/scipylib/index.html) >= 1.0.0
- [matplotlib](https://matplotlib.org/) >= 3.5.0
- [pyxdf](https://github.com/xdf-modules/xdf-Python) >= 1.16.0
- [pyobjc-framework-Cocoa](https://pyobjc.readthedocs.io/en/latest/) >= 5.2.0 (macOS only)

Optional dependencies provide additional features if installed:
- [scikit-learn](https://scikit-learn.org/stable/) >= 0.20.0 (ICA computation with FastICA)
- [python-picard](https://pierreablin.github.io/picard/) >= 0.4.0 (ICA computation with PICARD)
- [pyEDFlib](https://github.com/holgern/pyedflib) >= 0.1.15 (EDF/BDF export)
- [pybv](https://github.com/bids-standard/pybv) 0.4.0 (BrainVision VHDR/VMRK/EEG export)

### Installation
You can install MNELAB with:

```
pip install mnelab
```

If you want to use all MNELAB features, the full package including optional dependencies can be installed with:

```
pip install mnelab[full]
```

You can start MNELAB in a terminal with `mnelab` or `python -m mnelab`. On Windows, make sure to use Command Prompt (`cmd.exe`) or PowerShell (`powershell.exe`) &ndash; the `mnelab` command [currently does not work in Git Bash](https://github.com/pypa/pip/issues/10444).

If you use [Arch Linux](https://www.archlinux.org/), you can alternatively install the [python-mnelab](https://aur.archlinux.org/packages/python-mnelab/) AUR package (note that this also requires the [python-mne](https://aur.archlinux.org/packages/python-mne/) AUR package).

You can also install the latest development version as follows:

```
pip install git+https://github.com/cbrnr/mnelab
```

### Contributing
The [contributing guide](https://github.com/cbrnr/mnelab/blob/main/CONTRIBUTING.md) contains detailed instructions on how to contribute to MNELAB.
