## Contributing to MNELAB

If you want to implement a new feature, fix an existing bug, or help improve MNELAB in any other way (such as adding or improving documentation), please consider submitting a [pull request](https://github.com/cbrnr/mnelab/pulls). It might be a good idea to open an [issue](https://github.com/cbrnr/mnelab/issues) first to discuss your planned contributions with the developers.

Before you start working on your contribution, please make sure to follow the guidelines described in this document.


### Setting up the development environment

We recommend using [uv](https://docs.astral.sh/uv/) to install and manage your Python environment. Install the tool according to the instructions on the website and you are all set (there is no need to install Python separately as uv will automatically download and install the required version).

In addition to uv, you will also need a working [Git](https://git-scm.com/) installation. If you are on Windows, you can install [Git for Windows](https://gitforwindows.org/). If you are on macOS, you can install the XCode command line tools with `xcode-select --install`, which contain Git. On Linux, use your package manager to install Git.


### Forking and cloning MNELAB

On the [repository website](https://github.com/cbrnr/mnelab), click on the "Fork" button in the top right corner to create your own fork of MNELAB (you need to be logged in with your GitHub account). Next, from the main page of your fork, click on the green "Clone or download" button. Copy the URL to the clipboard – you will need this URL to create your local MNELAB repository.

Open a terminal and change into the folder where you would like your MNELAB fork to live. Then, type `git clone <URL>` (replace `<URL>` with the repository URL you copied to the clipboard earlier). Your fork of MNELAB is now available in the `mnelab` folder.


### Installing the project

In a terminal, change to the `mnelab` folder containing your MNELAB fork and run the following command:

```
uv sync --python=3.10 --all-extras
```

You can then run MNELAB with `uv run mnelab`, or run the tests with `uv run pytest`. We recommend to use the minimum required Python version (currently 3.10) to ensure compatibility with this release.


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

MNELAB uses [Ruff](https://docs.astral.sh/ruff/formatter/) for formatting. Because [PySide6](https://doc.qt.io/qtforpython-6/index.html) is based on the C++-based Qt library, most of its names use camel case instead of snake case. In your own code, please use snake case wherever possible.


## Making a PyPI release

Follow these steps to make a new [PyPI](https://pypi.org/project/mnelab/) release (requires write permissions for GitHub and PyPI project sites):

- Remove the `.dev0` suffix from the `version` field in `pyproject.toml` (and/or adapt the version to be released if necessary)
- Update the section in `CHANGELOG.md` corresponding to the new release with the version and current date
- Update the section on the standalone installers in `README.md` and `docs/index.md` (use the to-be-released version in the URLs, e.g., https://github.com/cbrnr/mnelab/releases/download/v1.0.3/MNELAB-1.0.3.exe)
- Commit these changes and push
- Create a new release on GitHub and use the version as the tag name (make sure to prepend the version with a `v`, e.g. `v0.7.0`)
- A GitHub Action takes care of building and uploading wheels to PyPI as well as adding standalone installers to the release

This concludes the new release. Now prepare the source for the next planned release as follows:

- Update the `version` field to the next planned release and append `.dev0`
- Start a new section at the top of `CHANGELOG.md` titled `## [UNRELEASED] - YYYY-MM-DD`

Don't forget to push these changes!


## Creating standalone packages

To create standalone packages for Windows, macOS, and Linux, we use [PyInstaller](https://www.pyinstaller.org/). GitHub Actions take care of automatically building the standalone packages, but you can also build them manually. It is important that all optional dependencies are available in the current environment by installing the project with `uv sync --all-extras`. Additionally, the environment must be *activated* (which is typically not necessary when working with uv, but is required in this case). You can activate the environment by running `./.venv/bin/activate` on macOS or Linux, or `.\.venv\Scripts\activate` on Windows (from the root of the source tree). Once the environment is active, run the corresponding script for your platform as described below.


### macOS

To create the DMG file containing the app bundle, run the following command in the `standalone` folder:

```
./create-standalone-macos.py
```

This creates the standalone app bundle in the `standalone/dist` folder as well as the DMG file (which is named `MNELAB-<VERSION>.dmg`) in the `standalone` folder. This DMG file can be distributed to macOS users. Signing and notarization of the app bundle requires a valid Apple Developer ID. Details on how to sign and notarize the app bundle will be provided later. For now, users can run the app by right-clicking on it and selecting "Open" to bypass Gatekeeper checks (this is only necessary for the first run).


#### Creating the app icon

Recreating the app icon is only necessary if the SVG logo has been modified. To generate the app icon from `mnelab-logo-macos.svg`, navigate to the `src/mnelab/icons` folder and run the following commands (this process requires [Inkscape](https://inkscape.org/)):

```
inkscape --export-filename=icon_16x16.png --export-width=16 --export-height=16 mnelab-logo-macos.svg
inkscape --export-filename=icon_32x32.png --export-width=32 --export-height=32 mnelab-logo-macos.svg
inkscape --export-filename=icon_128x128.png --export-width=128 --export-height=128 mnelab-logo-macos.svg
inkscape --export-filename=icon_256x256.png --export-width=256 --export-height=256 mnelab-logo-macos.svg
inkscape --export-filename=icon_512x512.png --export-width=512 --export-height=512 mnelab-logo-macos.svg
inkscape --export-filename=icon_512x512@2x.png --export-width=1024 --export-height=1024 mnelab-logo-macos.svg
mkdir icon.iconset
mv *.png icon.iconset
iconutil -c mnelab-logo-macos icon.iconset
rm -rf icon.iconset
```


### Windows

On Windows, download and install [Inno Setup](https://jrsoftware.org/isinfo.php). Add the installation directory to the path (by default `C:\Program Files (x86)\Inno Setup 6`). Then run the following command in the `standalone` folder (make sure to run this in a PowerShell terminal):

```
.\create-standalone-windows.ps1
```

This will produce a single `mnelab-<VERSION>.exe` installer in the `standalone` folder, which can be distributed to Windows users.


#### Creating the app icon

Recreating the app icon is only necessary if the SVG logo has been modified. To generate the app icon from `mnelab-logo-macos.svg`, navigate to the `src/mnelab/icons` folder and run the following commands (this process requires [Inkscape](https://inkscape.org/) and currently only works on Linux or macOS):

```
inkscape --export-filename=icon_16x16.png --export-width=16 --export-height=16 mnelab-logo.svg
inkscape --export-filename=icon_32x32.png --export-width=32 --export-height=32 mnelab-logo.svg
inkscape --export-filename=icon_48x48.png --export-width=48 --export-height=48 mnelab-logo.svg
inkscape --export-filename=icon_64x64.png --export-width=64 --export-height=64 mnelab-logo.svg
inkscape --export-filename=icon_128x128.png --export-width=128 --export-height=128 mnelab-logo.svg
inkscape --export-filename=icon_256x256.png --export-width=256 --export-height=256 mnelab-logo.svg
magick icon_16x16.png icon_32x32.png icon_48x48.png icon_64x64.png icon_128x128.png icon_256x256.png mnelab-logo.ico
rm icon_16x16.png icon_32x32.png icon_48x48.png icon_64x64.png icon_128x128.png icon_256x256.png
```
