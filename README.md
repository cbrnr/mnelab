[![PyPI Version](https://img.shields.io/pypi/v/mnelab)](https://pypi.org/project/mnelab/)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/mnelab)](https://anaconda.org/conda-forge/mnelab)
![Python](https://img.shields.io/badge/python-3.6--3.7-green.svg)
![Downloads PyPI](https://img.shields.io/pypi/dm/mnelab?color=blue&label=downloads%20pypi)
![Downloads Conda](https://img.shields.io/conda/dn/conda-forge/mnelab?color=blue&label=downloads%20conda)
![License](https://img.shields.io/github/license/cbrnr/mnelab)

![](https://raw.githubusercontent.com/cbrnr/mnelab/master/mnelab/images/mnelab_logo.png)

Graphical user interface (GUI) for [MNE](https://github.com/mne-tools/mne-python), a Python-based toolbox for EEG/MEG analysis.

![](https://raw.githubusercontent.com/cbrnr/mnelab/master/mnelab.png)

### Dependencies
MNELAB requires Python >= 3.6. In addition, the following Python packages are required:
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5) >= 5.10.0
- [numpy](http://www.numpy.org/) >= 1.14.0
- [scipy](https://www.scipy.org/scipylib/index.html) >= 1.0.0
- [matplotlib](https://matplotlib.org/) >= 2.0.0
- [mne](https://github.com/mne-tools/mne-python) >= 0.17.0
- [pyobjc-framework-Cocoa](https://pyobjc.readthedocs.io/en/latest/) >= 5.2.0 (macOS only)

Optional dependencies provide additional features if installed:
- [scikit-learn]() (ICA computation via FastICA)
- [python-picard](https://pierreablin.github.io/picard/) (ICA computation via PICARD)
- [pyEDFlib](https://github.com/holgern/pyedflib) (export to EDF/BDF)
- [pyxdf](https://github.com/xdf-modules/xdf-Python) (import XDF)
- [pybv](https://github.com/bids-standard/pybv) (export to BrainVision VHDR/VMRK/EEG)

In general, it is recommended to always use the latest package versions.

### Additional features
MNELAB comes with the following features that are not (yet) available in MNE:
- Export to EDF/BDF (requires [pyEDFlib](https://github.com/holgern/pyedflib))
- Export to EEGLAB SET
- Export to BrainVision VHDR/VMRK/EEG (requires [pybv](https://github.com/bids-standard/pybv))
- Import [XDF](https://github.com/sccn/xdf/wiki/Specifications) files (requires [pyxdf](https://github.com/xdf-modules/xdf-Python))

### Installation
#### Via pip
The latest release is available on [PyPI](https://pypi.python.org/pypi) and can be installed with:
```
pip install mnelab
mnelab
```
The `mnelab` command in the last line starts the application.

#### Via conda
An (unofficial, but regularly updated) conda package can be installed from [conda-forge](https://conda-forge.org/).
We strongly suggest to install MNELAB into its own dedicated environment to ensure smooth installation and operation:
```
conda create -y --name mnelab -c conda-forge mnelab
conda activate mnelab
mnelab
```
The `mnelab` command in the last line starts the application. Any issues with this conda package should be reported to the respective [issue tracker](https://github.com/conda-forge/mnelab-feedstock/issues).

#### Arch Linux
If you use [Arch Linux](https://www.archlinux.org/), you can install the [python-mnelab](https://aur.archlinux.org/packages/python-mnelab/) AUR package (note that this requires the [python-mne](https://aur.archlinux.org/packages/python-mne/) AUR package).


#### Standalone installer
A stand-alone installer will be available soon.


#### Development version
Follow these steps to use the latest development version of MNELAB:

1. [Download the source code](https://github.com/cbrnr/mnelab/archive/master.zip) and unpack it into a folder of your choice.
2. Open a terminal and change to the MNELAB source folder.
    - If you use [Anaconda](https://www.anaconda.com/distribution/) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html), install all dependencies with `conda install numpy scipy matplotlib pyqt` followed by `pip install mne`.
    - Otherwise, install all dependencies with `pip install -r requirements.txt` (and optionally `pip install -r requirements-optional.txt`).
3. Finally, run `python3 -m mnelab` to start MNELAB (if this does not work try `python -m mnelab`, just make sure to use Python 3 because Python 2 is not supported).

### Contributing
The [contributing guide](https://github.com/cbrnr/mnelab/blob/master/CONTRIBUTING.md) contains details on how to contribute to MNELAB.
