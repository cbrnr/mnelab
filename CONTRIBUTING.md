## Contributing to MNELAB

If you want to implement a new feature, fix an existing bug, or help improve MNELAB in any other way (such as adding or improving documentation), please consider submitting a [pull request](https://github.com/cbrnr/mnelab/pulls). It might be a good idea to open an [issue](https://github.com/cbrnr/mnelab/issues) first to discuss your planned contributions with the developers.

Before you start working on your contribution, please make sure to follow the guidelines described in this document.


### Setting up the development environment

We recommend using [uv](https://docs.astral.sh/uv/) to install and manage your Python environment. Install the tool according to the instructions on the website and you are all set (there is no need to install Python separately as uv will automatically download and install the required version).

In addition to uv, you will also need a working [Git](https://git-scm.com/) installation. Again, installation methods are different depending on which platform you are using. If you are on Windows, you can install [Git for Windows](https://gitforwindows.org/). If you are on macOS, you can install the XCode command line tools with `xcode-select --install`, which contain Git. On Linux, use your package manager to install Git.


### Forking and cloning MNELAB

On the [repository website](https://github.com/cbrnr/mnelab), click on the "Fork" button in the top right corner to create your own fork of MNELAB (you need to be logged in with your GitHub account). Next, from the main page of your fork, click on the green "Clone or download" button. Copy the URL to the clipboard – you will need this URL to create your local MNELAB repository.

Open a terminal and change into the folder where you would like your MNELAB fork to live. Then, type `git clone <URL>` (replace `<URL>` with the repository URL you copied to the clipboard earlier). Your fork of MNELAB is now available in the `mnelab` folder.


### Installing the project

In a terminal, change to the `mnelab` folder containing your MNELAB fork. We recommend [uv](https://docs.astral.sh/uv/) as a package and project manager, but you can use any standard-compliant tool of your choice. With uv, you can install MNELAB and all development dependencies with the following command in the project root:

```
uv sync --python=3.9 --all-extras
```

You can then run MNELAB with `uv run mnelab`, or run the tests with `uv run pytest`. We recommend to use the minimum required Python version (currently 3.9) to ensure compatibility with this release.


### Creating a new branch

Before you start working with the MNELAB codebase, you should create a new branch. In a terminal, type `git switch -c <BRANCH_NAME>` (replacing `<BRANCH_NAME>` with a suitable name for your branch). You are now ready to work on your contribution.


### Making a pull request

Once you have committed all of your changes, you can push them to your remote fork by typing `git push`. The GitHub page of your fork will now show a prompt to create a new pull request. Think of a good title and describe your contribution. If you have a corresponding issue, make sure to reference this issue in your description (it will be automatically closed after your pull request is merged).


### Modifying icons

MNELAB bundles its icons in the `icons` folder, which contains two themes ("light" and "dark"). If you want to modify an existing icon or add a new one, make sure to apply your changes to both the "light" and "dark" themes. All icons are SVGs and taken from the [Material Symbols](https://fonts.google.com/icons) icon set.

If you want to add a new icon, download it from the Material Symbols website, rename it (use a suitable name reflecting its intended action), and place it in the `icons/light/actions` folder. Next, edit the SVG file in a text editor and add the `fill="black"` attribute to the `<svg>` tag. Finally, copy the SVG file to the `icons/dark/actions` folder and change the `fill` attribute to `fill="white"`.


### Adding a changelog entry

Once you have an open pull request, add an entry to the top of `CHANGELOG.md` in the most suitable section: "Added" lists new features, "Fixed" lists bug fixes, and "Changed" lists changes to existing functionality. Finally, make sure to mention the pull request and your name.


### Coding style

MNELAB uses [Ruff](https://docs.astral.sh/ruff/formatter/) for formatting. Because [PySide6](https://doc.qt.io/qtforpython-6/index.html) is based on the C++-based Qt library, most of its names use camel case instead of snake case. In your own code, please use snake case whereever possible.


## Making a PyPI release

Follow these steps to make a new [PyPI](https://pypi.org/project/mnelab/) release (requires write permissions for GitHub and PyPI project sites):

- Remove the `.dev0` suffix from the `__version__` string in `mnelab/__init__.py` (and adapt the version to be released if necessary)
- Update the section in `CHANGELOG.md` corresponding to the new release with the version and current date
- Commit these changes and push
- Create a new release on GitHub and use the version as the tag name (make sure to prepend the version with a `v`, e.g. `v0.7.0`)
- A GitHub Action takes care of building and uploading wheels to PyPI

This concludes the new release. Now prepare the source for the next planned release as follows:

- Update the `__version__` string to the next planned release and append `.dev0`
- Start a new section at the top of `CHANGELOG.md` titled `[UNRELEASED] - YYYY-MM-DD`

Don't forget to push these changes!
