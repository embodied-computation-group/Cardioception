# Copyright (C) 2019 Nicolas Legrand
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


DESCRIPTION = "Cardioception Python Package"
LONG_DESCRIPTION = """Measuring interoceptive performance with Psychopy.
"""

DISTNAME = 'cardioception'
MAINTAINER = 'Nicolas Legrand'
MAINTAINER_EMAIL = 'nicolas.legrand@cfin.au.dk'
VERSION = '0.1.0'

INSTALL_REQUIRES = [
    'numpy>=1.15',
    'scipy>=1.3',
    'matplotlib>=3.0.2',
    'pingouin>=0.2.9',
    'pyserial>=3.4',
    'bayesfit==2.3',
    'pyglet==1.3.2',
]

PACKAGES = [
    'cardioception',
    'cardioception.HeartRateDiscrimination',
    'cardioception.HeartBeatCounting'
]

try:
    from setuptools import setup
    _has_setuptools = True
except ImportError:
    from distutils.core import setup

if __name__ == "__main__":

    setup(name=DISTNAME,
          author=MAINTAINER,
          author_email=MAINTAINER_EMAIL,
          maintainer=MAINTAINER,
          maintainer_email=MAINTAINER_EMAIL,
          description=DESCRIPTION,
          long_description=LONG_DESCRIPTION,
          license=read('LICENSE'),
          version=VERSION,
          install_requires=INSTALL_REQUIRES,
          include_package_data=True,
          packages=PACKAGES,
          )
