![Python](https://img.shields.io/pypi/pyversions/mnelab.svg?logo=python)
[![PyPI Version](https://img.shields.io/pypi/v/mnelab)](https://pypi.org/project/mnelab/)
[![Docs](https://readthedocs.org/projects/mnelab/badge/?version=latest)](https://mnelab.readthedocs.io/)
[![License](https://img.shields.io/github/license/cbrnr/mnelab)](LICENSE)

![](https://raw.githubusercontent.com/cbrnr/mnelab/main/mnelab/images/mnelab_logo.png)

MNELAB is a graphical user interface (GUI) for [MNE-Python](https://mne.tools/stable/index.html), a Python package for EEG/MEG analysis.

![](https://raw.githubusercontent.com/cbrnr/mnelab/main/mnelab.png)

### Documentation
Instructions for installing and using MNELAB as well as step-by-step examples for different use cases are available in the [documentation](https://mnelab.readthedocs.io/).

### Changelog
Check out the [changelog](https://github.com/cbrnr/mnelab/blob/main/CHANGELOG.md) to learn what we added, changed, or fixed.

### Dependencies
MNELAB requires Python ≥ 3.8 and the following packages:
- [mne](https://mne.tools/stable/index.html) ≥ 1.0.0
- [PySide6](https://www.qt.io/qt-for-python) ≥ 6.2.0
- [numpy](http://www.numpy.org/) ≥ 1.20.0
- [scipy](https://scipy.org/) ≥ 1.7.0
- [matplotlib](https://matplotlib.org/) ≥ 3.5.0
- [pyxdf](https://github.com/xdf-modules/xdf-Python) ≥ 1.16.0
- [pyobjc-framework-Cocoa](https://pyobjc.readthedocs.io/en/latest/) ≥ 7.3.0 (macOS only)

Optional dependencies provide additional features:
- [scikit-learn](https://scikit-learn.org/stable/) ≥ 1.0.0 (ICA computation with FastICA)
- [python-picard](https://pierreablin.github.io/picard/) ≥ 0.7.0 (ICA computation with PICARD)
- [pyEDFlib](https://pyedflib.readthedocs.io/en/latest/) ≥ 0.1.22 (EDF/BDF export)
- [pybv](https://pybv.readthedocs.io/en/stable/) ≥ 0.7.4 (BrainVision VHDR/VMRK/EEG export)

### Installation
You can install MNELAB with [pip](https://pip.pypa.io/en/stable/):

```
pip install mnelab
```

If you want to use all MNELAB features, the full package including optional dependencies can be installed with:

```
pip install mnelab[full]
```

You can also use [pipx](https://pypa.github.io/pipx/) to install MNELAB in a completely isolated environment:

```
pipx install mnelab
```

If you want the latest development version, use the following command:

```
pip install git+https://github.com/cbrnr/mnelab
```

Then start MNELAB in a terminal with `mnelab`.

### Contributing
The [contributing guide](https://github.com/cbrnr/mnelab/blob/main/CONTRIBUTING.md) contains detailed instructions on how to contribute to MNELAB.
