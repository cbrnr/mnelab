# Tutorial

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
