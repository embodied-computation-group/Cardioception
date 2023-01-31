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
import time

import cardioception
import sphinx_bootstrap_theme

# -- Project information -----------------------------------------------------
project = "cardioception"
copyright = "2022-{}, Nicolas Legrand".format(time.strftime("%Y"))
author = "Nicolas Legrand"
release = cardioception.__version__


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

html_theme = "pydata_sphinx_theme"
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()
html_theme_options = {
    "icon_links": [
        dict(
            name="GitHub",
            url="https://github.com/embodied-computation-group/Cardioception",
            icon="fab fa-github-square",
        ),
        dict(
            name="Twitter",
            url="https://twitter.com/visceral_mind",
            icon="fab fa-twitter-square",
        ),
        dict(
            name="Pypi",
            url="https://pypi.org/project/Cardioception/",
            icon="fas fa-box",
        ),
    ],
    "logo": {
        "text": "Cardioception",
    },
}

html_sidebars = {"**": []}

html_css_files = [
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"
]
html_logo = "images/logo_small.svg"
html_favicon = "images/logo_small.svg"


def setup(app):
    app.add_css_file("style.css")


# -- Intersphinx ------------------------------------------------

intersphinx_mapping = {
    "numpy": ("http://docs.scipy.org/doc/numpy/", None),
    "scipy": ("http://docs.scipy.org/doc/scipy/reference/", None),
    "matplotlib": ("http://matplotlib.org/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    "seaborn": ("https://seaborn.pydata.org/", None),
}
