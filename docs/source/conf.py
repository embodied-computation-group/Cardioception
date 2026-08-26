# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import re
import time

def get_version():
    """Read __version__ from the package without importing it.

    Importing cardioception here would pull in PsychoPy and its GUI stack,
    which the documentation build does not need and cannot install on the
    Linux runner.
    """
    init = os.path.join(
        os.path.dirname(__file__), "..", "..", "cardioception", "__init__.py"
    )
    with open(init, encoding="utf-8") as buff:
        match = re.search(r"""^__version__ = ["'](.+)["']""", buff.read(), re.M)
    if match is None:
        raise RuntimeError("Could not find __version__ in cardioception/__init__.py")
    return match.group(1)

# -- Project information -----------------------------------------------------
project = "cardioception"
copyright = "2020–2025, Micah Allen, Embodied Computation Group, Aarhus University"
author = "Micah Allen"
release = get_version()


image_scrapers = ("matplotlib",)

sphinx_gallery_conf = {
    "backreferences_dir": "api",
    "image_scrapers": image_scrapers,
}

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.mathjax",
    "sphinx.ext.doctest",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinx.ext.autosummary",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "matplotlib.sphinxext.plot_directive",
    "numpydoc",
    "myst_nb",
    "sphinxcontrib.bibtex"
]

bibtex_bibfiles = ['refs.bib']
bibtex_reference_style = "author_year"
bibtex_default_style = "unsrt"

myst_enable_extensions = ["dollarmath"]

panels_add_bootstrap_css = False

# Generate the API documentation when building
autosummary_generate = True

# The API pages only need the docstrings, so the packages that talk to the
# screen and the recording device are mocked rather than installed.
autodoc_mock_imports = [
    "psychopy",
    "serial",
    "systole",
    "pymc",
    "pytensor",
    "metadpy",
    "papermill",
    "pingouin",
]
numpydoc_show_class_members = False

# Include the example source for plots in API docs
plot_include_source = True
plot_formats = [("png", 90)]
plot_html_show_formats = False
plot_html_show_source_link = False

source_suffix = [".rst", ".md"]

# The master toctree document.
master_doc = "index"

nb_execution_timeout = 300

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages. See the documentation for
# a list of builtin themes.

html_theme = "furo"
html_title = "Cardioception Toolbox"

html_theme_options = {
    "sidebar_hide_name": True,
    "light_css_variables": {
        "color-brand-primary": "#1f3352",
        "color-brand-content": "#2f4b73",
    },
    "dark_css_variables": {
        "color-brand-primary": "#9fc0e8",
        "color-brand-content": "#9fc0e8",
    },
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/embodied-computation-group/Cardioception",
            "html": "GitHub",
            "class": "",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/cardioception-toolbox/",
            "html": "PyPI",
            "class": "",
        },
    ],
}

html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_logo = "images/cardioception_icon.png"
html_favicon = "images/favicon.png"


# -- Intersphinx ------------------------------------------------

intersphinx_mapping = {
    "numpy": ("http://docs.scipy.org/doc/numpy/", None),
    "scipy": ("http://docs.scipy.org/doc/scipy/reference/", None),
    "matplotlib": ("http://matplotlib.org/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    "seaborn": ("https://seaborn.pydata.org/", None),
}
