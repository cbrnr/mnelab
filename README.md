![Python](https://img.shields.io/pypi/pyversions/mnelab.svg?logo=python&logoColor=white)
[![PyPI](https://img.shields.io/pypi/v/mnelab)](https://pypi.org/project/mnelab/)
[![Docs](https://readthedocs.org/projects/mnelab/badge/?version=latest)](https://mnelab.readthedocs.io/)
[![DOI](https://joss.theoj.org/papers/10.21105/joss.04650/status.svg)](https://doi.org/10.21105/joss.04650)
[![License](https://img.shields.io/github/license/cbrnr/mnelab?color=68%2C192%2C58)](LICENSE)


# MNELAB

![](https://raw.githubusercontent.com/cbrnr/mnelab/main/mnelab/images/mnelab_logo.png)

MNELAB is a graphical user interface for [MNE-Python](https://mne.tools/stable/index.html) (the most popular Python package for EEG/MEG analysis).

![](https://raw.githubusercontent.com/cbrnr/mnelab/main/mnelab.png)

Key features include:

- Cross-platform support (Linux, macOS, Windows).
- A command history that records the underlying MNE-Python commands for each action, allowing users to learn how to use MNE-Python and to reproduce their analyses in code.
- Import data from various formats supported by MNE-Python, and some additional formats like [XDF](https://github.com/sccn/xdf/wiki/Specifications), MATLAB, NumPy, and [BVRF](https://www.brainproducts.com/download/bvrf-reference-specification/).
- Export to EDF, BDF, BrainVision, EEGLAB, and FIFF formats.
- XDF-specific features such as chunk inspection (useful for debugging corrupted XDF files), stream selection, metadata inspection, resampling, gap detection and filling, and more.
- Support for various ICA algorithms, including [FastICA](https://en.wikipedia.org/wiki/FastICA), [Infomax ICA](https://arnauddelorme.com/ica_for_dummies/), and [PICARD](https://mind-inria.github.io/picard/).
- Automatic classification of independent components using [ICLabel](https://github.com/sccn/ICLabel).
- Comprehensive tools for managing events and annotations.
- Support for channel locations (montages), re-referencing, cropping, filtering, epoching, and more.
- Plotting functions for raw data, epochs, evoked responses, independent components, ERD/ERS maps, and more.
 

## Documentation

The [documentation](https://mnelab.readthedocs.io/) contains hands-on examples and tutorials for different use cases. Check out the [changelog](https://github.com/cbrnr/mnelab/blob/main/CHANGELOG.md) to learn what we added, changed, or fixed.


## Quick Start

We recommend using the standalone installers for macOS and Windows:

- [MNELAB 1.5.3 (macOS)](https://github.com/cbrnr/mnelab/releases/download/v1.5.3/MNELAB-1.5.3.dmg)
- [MNELAB 1.5.3 (Windows)](https://github.com/cbrnr/mnelab/releases/download/v1.5.3/MNELAB-1.5.3.exe)

If you use [Arch Linux](https://archlinux.org/), you can install MNELAB from the [AUR](https://aur.archlinux.org/packages/python-mnelab) (e.g., `yay -S python-mnelab`).

Alternatively, you can use [uv](https://docs.astral.sh/uv/) to run MNELAB directly without installing it (this works on all platforms, but for the best experience we recommend using the standalone installers when available):

```
uvx mnelab
```


## Advanced Usage

To run the latest development version:

```
uvx --from https://github.com/cbrnr/mnelab/archive/refs/heads/main.zip mnelab
```

On Linux, running MNELAB via `uvx mnelab` uses the [Fusion](https://doc.qt.io/qt-6/gallery.html) style shipped with [PySide6](https://doc.qt.io/qtforpython-6/index.html), which may not fit well with the rest of the system. However, if you use [KDE](https://kde.org/), you can set the `QT_PLUGIN_PATH` environment variable to force the use of the native KDE theme instead, for example:

```
QT_PLUGIN_PATH=/usr/lib/qt6/plugins uvx mnelab
```


## Contributing

The [contributing guide](https://github.com/cbrnr/mnelab/blob/main/CONTRIBUTING.md) provides detailed instructions for contributing to MNELAB.
