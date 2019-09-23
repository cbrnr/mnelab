## Contributing to MNELAB
If you want to implement a new feature, fix an existing bug or improve MNELAB in any other way (such as adding or improving documentation), please consider submitting a [pull request](https://github.com/cbrnr/mnelab/pulls) on GitHub. It might be a good idea to open an [issue](https://github.com/cbrnr/mnelab/issues) beforehand and discuss your planned contributions with the developers.

Before you start working on your contribution, please make sure to follow the guidelines described in this document.


### Setting up the development environment
You will need to have a working Python environment. Make sure to use at least Python 3.6 (MNELAB makes extensive use of f-strings). Installation methods vary across platforms (for example, you could use [Homebrew](https://brew.sh/) on macOS), but if you don't have any specific preferences, [Anaconda](https://www.anaconda.com/) is one of the best options available for Windows, macOS, and Linux.

In addition to Python, you will also need a working [Git](https://git-scm.com/) installation. Again, installation methods are different depending on which platform you develop, but if you use Anaconda you can type `conda install git` in a terminal and you should be all set.

### Forking and cloning MNELAB
On the [GitHub website](https://github.com/cbrnr/mnelab), click on the "Fork" button in the top right corner to create your own fork of MNELAB (you need to be logged in with your GitHub account). Next, from the main page of your fork, click on the green "Clone or download" button. Copy the URL to the clipboard - you will need this URL to create your local MNELAB repository.

Open a terminal and change into the folder where you would like your MNELAB project to live. Then, type `git clone <URL>` (replace `<URL>` with the repository URL you copied to the clipboard earlier). Your fork of MNELAB is now available in the `mnelab` folder.

### Installing required Python packages
Still in a terminal, change to the `mnelab` folder containing your MNELAB fork. Now you are ready to install all MNELAB dependencies. If you use Anaconda, you should run `conda install numpy scipy matplotlib pyqt scikit-learn` followed by `pip install mne python-picard pyEDFlib pyxdf pybv`. If you do not use Anaconda, run `pip install -r requirements.txt` followed by `pip install -r requirements-optional.txt`.

### Creating a new branch
Before you start working with the MNELAB codebase you need to create a new branch. In a terminal, type `git checkout -b <BRANCH_NAME>` (replacing `<BRANCH_NAME>` with a suitable name for your branch). Now you are ready to work on your contribution.

### Making a pull request
Once you have committed all of your changes, you can push them to your remote fork by typing `git push`. The GitHub main page of your fork will now show a prompt to create a new pull request. Think of a good title, and describe what your contribution is about. If you have a corresponding issue, make sure to mention this issue in your description (so it will be automatically closed after your pull request is merged).

### Adding a changelog entry


### Coding style
MNELAB adheres to [PEP8](https://www.python.org/dev/peps/pep-0008/) wherever possible. However, because PyQt5 is based on the C++-based Qt library, most of its names use camel case (violating PEP8 recommendations) instead of snake case. In your own code, please follow PEP8 naming conventions.
