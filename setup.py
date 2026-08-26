# Copyright (C) 2020–2025 Micah Allen, Embodied Computation Group, Aarhus University
import os
import codecs
from setuptools import find_packages, setup

PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements.txt")

def read(fname):
    with codecs.open(
        os.path.join(os.path.dirname(__file__), fname), encoding="utf-8"
    ) as buff:
        return buff.read()

def get_requirements():
    """Requirement specifiers from requirements.txt, ignoring comments.

    Comments and blank lines are stripped rather than passed through: setuptools
    treats every line as a specifier, so a `#` line here becomes an unparseable
    requirement and the build fails on a file that looks fine.
    """
    with codecs.open(REQUIREMENTS_FILE, encoding="utf-8") as buff:
        lines = (line.strip() for line in buff.read().splitlines())
        return [line for line in lines if line and not line.startswith("#")]

DESCRIPTION = (
    "Measuring interoceptive performance with Psychopy - the official "
    "Cardioception toolbox from the Embodied Computation Group."
)
LONG_DESCRIPTION = read("README.md")

DISTNAME = "cardioception-toolbox"
MAINTAINER = "Micah Allen"
MAINTAINER_EMAIL = "micah.allen@clin.au.dk"
VERSION = "0.6.1"
URL = "https://github.com/embodied-computation-group/Cardioception"

if __name__ == "__main__":

    setup(
        name=DISTNAME,
        author=MAINTAINER,
        author_email=MAINTAINER_EMAIL,
        maintainer=MAINTAINER,
        maintainer_email=MAINTAINER_EMAIL,
        url=URL,
        project_urls={
            "Homepage": URL,
            "Documentation": "https://embodied-computation-group.github.io/Cardioception/",
            "Source": URL,
            "Bug Tracker": URL + "/issues",
        },
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        long_description_content_type="text/markdown",
        license="MIT",
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Science/Research",
            "Programming Language :: Python :: 3",
            "Topic :: Scientific/Engineering",
        ],
        # Upper bound is pywinhook, not PsychoPy: pywinhook 1.6.2 publishes wheels only
        # up to cp311, and without one it needs SWIG to build on Windows. psychopy
        # 2026.2.2 itself allows up to 3.12.
        python_requires=">=3.10,<3.12",
        version=VERSION,
        install_requires=get_requirements(),
        include_package_data=True,
        packages=find_packages(),
        package_data={
            "cardioception.HBC": ["*.wav", "*.png"],
            "cardioception.HRD": ["*.wav", "*.png"],
            "cardioception.notebooks": ["*.ipynb"],
        },
    )
