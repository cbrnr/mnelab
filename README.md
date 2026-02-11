![Python](https://img.shields.io/pypi/pyversions/mnelab.svg?logo=python&logoColor=white)
[![PyPI](https://img.shields.io/pypi/v/mnelab)](https://pypi.org/project/mnelab/)
[![Docs](https://readthedocs.org/projects/mnelab/badge/?version=latest)](https://mnelab.readthedocs.io/)
[![DOI](https://joss.theoj.org/papers/10.21105/joss.04650/status.svg)](https://doi.org/10.21105/joss.04650)
[![License](https://img.shields.io/github/license/cbrnr/mnelab?color=68%2C192%2C58)](LICENSE)


## MNELAB

![](https://raw.githubusercontent.com/cbrnr/mnelab/main/mnelab/images/mnelab_logo.png)

MNELAB provides a graphical user interface for [MNE-Python](https://mne.tools/stable/index.html) (the most popular Python package for EEG/MEG analysis) and ensures full transparency by recording the underlying commands for each action in its command history.

![](https://raw.githubusercontent.com/cbrnr/mnelab/main/mnelab.png)

Key features include:

- Cross-platform support (Linux, macOS, Windows).
- A command history that records the underlying MNE-Python commands for each action, allowing users to learn how to use MNE-Python and to reproduce their analyses in code.
- Import data from various formats supported by MNE-Python, and some additional formats like [XDF](https://github.com/sccn/xdf/wiki/Specifications) (`.xdf`, `.xdfz`, `.xdf.gz`), MATLAB (`.mat`), and NumPy (`.npy`).
- Export to EDF, BDF, BrainVision, EEGLAB, and FIFF formats.
- XDF-specific features such as chunk inspection (useful for debugging corrupted XDF files), stream selection, metadata inspection, resampling, gap detection and filling, and more.
- Support for various ICA algorithms, including [FastICA](https://en.wikipedia.org/wiki/FastICA), [Infomax ICA](https://arnauddelorme.com/ica_for_dummies/), and [PICARD](https://mind-inria.github.io/picard/).
- Automatic classification of independent components using [ICLabel](https://github.com/sccn/ICLabel).
- Comprehensive tools for managing events and annotations.
- Support for channel locations (montages), rereferencing, cropping, filtering, epoching, and more.
- Plotting capabilities for raw data, epochs, evoked responses, independent components, ERD/ERS maps, and more.
 

### Documentation

Instructions for installing and using MNELAB as well as step-by-step examples for different use cases are available in the [documentation](https://mnelab.readthedocs.io/). Check out the [changelog](https://github.com/cbrnr/mnelab/blob/main/CHANGELOG.md) to learn what we added, changed, or fixed.


### Quick start

We recommend our standalone installers currently available for macOS and Windows:

- [MNELAB 1.1.0 (macOS)](https://github.com/cbrnr/mnelab/releases/download/v1.1.0/MNELAB-1.1.0.dmg)
- [MNELAB 1.1.0 (Windows)](https://github.com/cbrnr/mnelab/releases/download/v1.1.0/MNELAB-1.1.0.exe)

If you use Arch Linux, you can install MNELAB from the [AUR](https://aur.archlinux.org/packages/python-mnelab) (e.g., `yay -S python-mnelab`).

Alternatively, you can use [uv](https://docs.astral.sh/uv/) to run MNELAB on all platforms:

```
uvx mnelab
```

If you want to run the latest development version, you can use the following command:

```
uvx --from https://github.com/cbrnr/mnelab/archive/refs/heads/main.zip mnelab
```


### Contributing

The [contributing guide](https://github.com/cbrnr/mnelab/blob/main/CONTRIBUTING.md) contains detailed instructions on how to contribute to MNELAB.
