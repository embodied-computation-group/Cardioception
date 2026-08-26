# Copyright (C) 2020–2025 Micah Allen, Embodied Computation Group, Aarhus University
from importlib.resources import files


def resource_filename(package: str, resource: str) -> str:
    """Path to a data file (image, sound, notebook) shipped with the package.

    Replaces ``pkg_resources.resource_filename``, which was removed from recent
    versions of setuptools.

    Parameters
    ----------
    package :
        The package holding the file (e.g. ``"cardioception.HRD"``).
    resource :
        Path of the file relative to that package (e.g. ``"Sounds/start.wav"``).

    Returns
    -------
    The absolute path to the file.

    """
    return str(files(package).joinpath(resource))
