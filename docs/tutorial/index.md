# Tutorial

## Running MNELAB

We recommend using [uv](https://docs.astral.sh/uv/) to install and run MNELAB. After installing uv, you can start MNELAB with the following command:

```
uvx mnelab
```

If you want to run the latest development version, you can use the following command:

```
uvx --from https://github.com/cbrnr/mnelab/archive/refs/heads/main.zip mnelab
```


## First steps

The main window of MNELAB consists of a menu bar (A), a toolbar (B), a sidebar (C), an info panel (D), and a status bar (E):

![empty window](images/empty_window.png)

The main window looks pretty empty initially. In fact, almost all commands are disabled until you load a data set:

![menu disabled](images/menu_disabled.png)

Click on the "Open" icon in the toolbar or select _File – Open..._ and pick a file in the dialog window.
The name of the loaded file appears in the sidebar, and the info panel shows information about the data set:

![file loaded](images/file_loaded.png)

Select _Plot – Plot data_ to visualize the time course of the individual channels:

![plot menu](images/plot_menu.png)
