# Copyright (C) 2020 Nicolas Legrand
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


DESCRIPTION = "Cardioception Python Package"
LONG_DESCRIPTION = """Measuring interoceptive performance with Psychopy.
"""

DISTNAME = "cardioception"
MAINTAINER = "Nicolas Legrand"
MAINTAINER_EMAIL = "nicolas.legrand@cas.au.dk"
VERSION = "0.4.3"

INSTALL_REQUIRES = [
    "systole>=0.2.2",
    "psychopy>=2020.1.2",
]

PACKAGES = [
    "cardioception",
]

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

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
        install_requires=INSTALL_REQUIRES,
        include_package_data=True,
        packages=PACKAGES,
        package_data={
            "cardioception.HBC": ["*.wav", "*.png"],
            "cardioception.HRD": ["*.wav", "*.png"],
            "cardioception.notebooks": ["*.ipynb", "*.npy", "*.txt"],
        },
    )
