![Python 3.6](https://img.shields.io/badge/python-3.6-green.svg)
![Python 3.7](https://img.shields.io/badge/python-3.7-green.svg)
![License](https://img.shields.io/badge/license-BSD-green.svg)

MNELAB
======

Graphical user interface (GUI) for [MNE](https://github.com/mne-tools/mne-python), a Python-based toolbox for EEG/MEG analysis.

### Screenshots

![](mnelab.png)

### Dependencies
MNELAB requires Python >= 3.6. In addition, the following Python packages are required:
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5) >= 5.6.0
- [numpy](http://www.numpy.org/) >= 1.8.1
- [scipy](https://www.scipy.org/scipylib/index.html) >= 0.17.1
- [matplotlib](https://matplotlib.org/) >= 2.0.0
- [mne](https://github.com/mne-tools/mne-python) >= 0.17

Optional dependencies provide additional features if installed:
- [scikit-learn]() (ICA computation via FastICA)
- [python-picard](https://pierreablin.github.io/picard/) (ICA computation via PICARD)
- [pyEDFlib](https://github.com/holgern/pyedflib) (export raw to EDF/BDF)
- [pyxdf](https://github.com/xdf-modules/xdf-Python) (import XDF files)

In general, it is recommended to always use the latest package versions.

### Additional features
MNELAB comes with the following features that are not available in MNE:
- Export raw to EDF/BDF (requires [pyEDFlib](https://github.com/holgern/pyedflib))
- Export raw to EEGLAB SET
- Import [XDF](https://github.com/sccn/xdf/wiki/Specifications) files (requires [pyxdf](https://github.com/xdf-modules/xdf-Python))

### Installation
A package on [PyPI](https://pypi.python.org/pypi) and a stand-alone installer will be available soon.

Meanwhile, follow these steps to use MNELAB:

1. [Download the source code](https://github.com/cbrnr/mnelab/archive/master.zip) and unpack it into a folder of your choice.
2. Open a terminal, change to the folder where you unpacked the MNELAB source.
    - If you use [Anaconda](https://www.anaconda.com/distribution/) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html), install all dependencies with `conda install numpy scipy matplotlib pyqt` followed by `pip install mne`.
    - Otherwise, install all dependencies with `pip install -r requirements.txt`.
3. Finally, run `python3 -m mnelab` to start MNELAB (if this does not work try `python -m mnelab`, just make sure to use Python 3).
