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
    with codecs.open(REQUIREMENTS_FILE) as buff:
        return buff.read().splitlines()

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
