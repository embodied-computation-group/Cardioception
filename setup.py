# Copyright (C) 2020–2025 Micah Allen, Embodied Computation Group, Aarhus University
import os
import codecs
from setuptools import find_packages, setup

PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements.txt")

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def get_requirements():
    with codecs.open(REQUIREMENTS_FILE) as buff:
        return buff.read().splitlines()

DESCRIPTION = "Cardioception Python Package"
LONG_DESCRIPTION = """Measuring interoceptive performance with Psychopy.
"""

DISTNAME = "cardioception"
MAINTAINER = "Micah Allen"
MAINTAINER_EMAIL = "micah.allen@clin.au.dk"
VERSION = "0.4.5"

if __name__ == "__main__":

    setup(
        name=DISTNAME,
        author=MAINTAINER,
        author_email=MAINTAINER_EMAIL,
        maintainer=MAINTAINER,
        maintainer_email=MAINTAINER_EMAIL,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        license=read("LICENSE"),
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
