# Tutorial

## Dependencies

MNELAB requires Python ≥ 3.9 and the following packages:
- [mne](https://mne.tools/stable/index.html) ≥ 1.7.0
- [PySide6](https://www.qt.io/qt-for-python) ≥ 6.7.1
- [edfio](https://edfio.readthedocs.io/en/stable/index.html) ≥ 0.4.2
- [matplotlib](https://matplotlib.org/) ≥ 3.8.0
- [numpy](http://www.numpy.org/) ≥ 1.25.0
- [scipy](https://scipy.org/) ≥ 1.10.0
- [pyxdf](https://github.com/xdf-modules/xdf-Python) ≥ 1.16.4
- [pyobjc-framework-Cocoa](https://pyobjc.readthedocs.io/en/latest/) ≥ 10.0 (macOS only)
- [pybv](https://pybv.readthedocs.io/en/stable/) ≥ 0.7.4 (BrainVision VHDR/VMRK/EEG export)

Optional dependencies provide additional features:
- [mne-qt-browser](https://github.com/mne-tools/mne-qt-browser) ≥ 0.6.2 (alternative raw plot backend)
- [python-picard](https://pierreablin.github.io/picard/) ≥ 0.7.0 (ICA computation with PICARD)
- [scikit-learn](https://scikit-learn.org/stable/) ≥ 1.3.0 (ICA computation with FastICA)


## Installation

You can install MNELAB with [pip](https://pip.pypa.io/en/stable/):

```
pip install mnelab
```

If you want to use all MNELAB features, the full package including optional dependencies can be installed with:

```
pip install "mnelab[full]"
```

You can also use [pipx](https://pypa.github.io/pipx/) to install MNELAB in a completely isolated environment:

```
pipx install mnelab
```

If you want the latest development version, use the following command:

```
pip install git+https://github.com/cbrnr/mnelab
```


## Running MNELAB

MNELAB must be started from a terminal with the following command:

```
mnelab
```

If you get an error, try the following alternative:

```
python -m mnelab
```


## First steps

The main window of MNELAB consists of a menu bar (A), a toolbar (B), a sidebar (C), an info panel (D), and a status bar (E):

![empty window](./empty_window.png)

The main window looks pretty empty initially. In fact, almost all commands are disabled until you load a data set:

![menu disabled](./menu_disabled.png)

Click on the "Open" icon in the toolbar or select _File – Open..._ and pick a file in the dialog window.
The name of the loaded file appears in the sidebar, and the info panel shows information about the data set:

![file loaded](./file_loaded.png)

Select _Plot – Plot data_ to visualize the time course of the individual channels:

![plot menu](./plot_menu.png)
