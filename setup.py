# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from setuptools import setup, find_packages
from os import path
from importlib import import_module


def optdep(*args, default=None):
    """Manage alternative dependencies"""
    for dep in args:
        try:
            import_module(dep)
        except ImportError:
            continue
        else:
            return dep
    return default


here = path.abspath(path.dirname(__file__))

# get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# get the version (without importing)
with open(path.join('mnelab', 'mainwindow.py'), 'r') as f:
    for line in f:
        if line.strip().startswith('__version__'):
            version = line.split('=')[1].strip().strip('"')
            break

# get install requirements
with open(path.join(here, "requirements.txt")) as f:
    requires = f.read().splitlines()

qtpkg = optdep("PySide2", "PyQt5", default="PySide2")
requires.append(qtpkg)

# get extra (optional) requirements
extras_require = {}
with open(path.join(here, "requirements-extras.txt")) as f:
    for extra in f:
        package, text = extra.split("#")
        extras_require[text.strip()] = [package.strip()]

setup(
    name='mnelab',
    version=version,
    description='A graphical user interface for MNE',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/cbrnr/mnelab',
    author='Clemens Brunner',
    author_email='clemens.brunner@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ],
    keywords='EEG MEG MNE GUI electrophysiology',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    python_requires='>=3.6, <4',
    install_requires=requires,
    extras_require=extras_require,
    license="BSD-3-Clause",
    include_package_data=True,
    entry_points={
        'gui_scripts': [
            'mnelab=mnelab.__main__:main',
        ],
    }
)
