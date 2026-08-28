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
    # Puts an "Edit this page" link at the top of every page, pointing into the
    # repository. Without it the only link back to the source was a single
    # footer entry, and the badges that name the project live on the landing
    # page alone.
    "source_repository": "https://github.com/embodied-computation-group/Cardioception",
    "source_branch": "master",
    "source_directory": "docs/source/",
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
            "html": '<svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path></svg>',
            "class": "",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/cardioception-toolbox/",
            "html": '<svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16"><path d="M8.878.392a1.75 1.75 0 0 0-1.756 0l-5.25 3.045A1.75 1.75 0 0 0 1 4.951v6.098c0 .624.332 1.2.872 1.514l5.25 3.045a1.75 1.75 0 0 0 1.756 0l5.25-3.045c.54-.313.872-.89.872-1.514V4.951c0-.624-.332-1.2-.872-1.514ZM7.875 1.69a.25.25 0 0 1 .25 0l4.63 2.685L8 7.133 3.245 4.375Zm-5.375 9.36V5.677l4.75 2.755v5.339l-4.626-2.683a.25.25 0 0 1-.124-.216Zm6.25 2.755V8.432l4.75-2.755v5.372a.25.25 0 0 1-.124.216Z"></path></svg>',
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
