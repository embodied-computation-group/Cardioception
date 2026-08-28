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
    "sphinxcontrib.bibtex",
    "sphinx_design",
    "sphinx_sitemap",
    "sphinxext.opengraph",
]

bibtex_bibfiles = ['refs.bib']
bibtex_reference_style = "author_year"
bibtex_default_style = "unsrt"

myst_enable_extensions = ["dollarmath", "colon_fence"]
# Give headings real anchors, so a link like (page.md#some-heading) resolves.
# Several pages cross-reference each other by heading slug.
myst_heading_anchors = 3

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

# The example notebooks are archived and are not re-run at build time; their
# stored outputs are rendered as they are.
nb_execution_mode = "off"
nb_execution_timeout = 300

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# examples/R/README.md duplicates R_analysis/README.md and is not part of the
# navigation, so it is left out of the build rather than published orphaned.
exclude_patterns = ["examples/R/README.md"]

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


# -- Canonical URLs, sitemap and page metadata -------------------------------

# The documentation is published under the group domain, and the
# embodied-computation-group.github.io address is a permanent redirect to it.
# Naming the canonical base here makes Sphinx write a <link rel="canonical">
# into every page, so the two hostnames are read as one site rather than as two
# copies competing with each other.
html_baseurl = "https://www.the-ecg.org/Cardioception/"

# sphinx-sitemap defaults to a "{lang}{version}{link}" layout, which suits a
# Read the Docs project publishing several versions side by side. This build
# publishes a single version at the root of the path above, so those two extra
# segments would fill the sitemap with URLs that do not exist.
sitemap_url_scheme = "{link}"

# The search page is an empty shell filled in by JavaScript and the index is a
# list of links, so neither is worth pointing a crawler at.
sitemap_excludes = ["search.html", "genindex.html"]

ogp_site_url = html_baseurl
ogp_site_name = "Cardioception Toolbox"
ogp_type = "website"

# Pages that do not set their own description in `html_meta` front matter fall
# back to their opening prose, cut to this length. sphinxext-opengraph leaves a
# page alone when it already carries a description of its own, so the hand
# written ones on the main pages win.
ogp_description_length = 200

# `ogp_image` is deliberately unset: with no fixed image, sphinxext-opengraph
# draws a preview card per page with Matplotlib, which the documentation build
# already installs, using html_logo and the page title.
ogp_social_cards = {
    "enable": True,
    "site_url": "the-ecg.org/Cardioception",
    "line_color": "#1f3352",
}


# -- Intersphinx ------------------------------------------------

intersphinx_mapping = {
    "numpy": ("http://docs.scipy.org/doc/numpy/", None),
    "scipy": ("http://docs.scipy.org/doc/scipy/reference/", None),
    "matplotlib": ("http://matplotlib.org/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    "seaborn": ("https://seaborn.pydata.org/", None),
}
