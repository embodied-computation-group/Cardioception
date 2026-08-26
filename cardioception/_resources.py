# Copyright (C) 2020–2025 Micah Allen, Embodied Computation Group, Aarhus University
import importlib
import os


def resource_filename(package: str, resource: str) -> str:
    """Path to a data file (image, sound, notebook) shipped with the package.

    Replaces ``pkg_resources.resource_filename``, which was removed from recent
    versions of setuptools.

    Parameters
    ----------
    package :
        The package holding the file (e.g. ``"cardioception.HRD"``).
    resource :
        Path of the file relative to that package, using forward slashes
        (e.g. ``"Sounds/start.wav"``).

    Returns
    -------
    The absolute path to the file.

    """
    module = importlib.import_module(package)
    if module.__file__ is None:
        raise ValueError(f"Cannot locate the files shipped with {package}")
    return os.path.join(os.path.dirname(module.__file__), *resource.split("/"))
