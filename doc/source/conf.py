# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a
# full list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

project = 'MNELAB'

extensions = ['myst_parser']

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

html_theme = 'furo'
html_title = project
html_logo = '../../mnelab/images/mnelab_logo.png'
html_theme_options = {
    'sidebar_hide_name': True,
}

templates_path = ["_templates"]
