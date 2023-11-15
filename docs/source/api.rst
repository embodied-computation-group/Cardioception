.. _api_ref:

.. currentmodule:: cardioception


.. contents:: Table of Contents
   :depth: 2

API
+++

Tasks
-----

Heart Beat Counting task
========================

Parameters
**********

.. currentmodule:: cardioception.HBC.parameters

.. autosummary::
   :toctree: generated/HBC.parameters

    getParameters

Scripts
*******

.. currentmodule:: cardioception.HBC.task

.. autosummary::
   :toctree: generated/HBC.task
    
    run
    trial
    tutorial
    rest

Heart Rate Discrimination task
==============================

Parameters
**********

.. currentmodule:: cardioception.HRD.parameters

.. _parameters:

.. autosummary::
   :toctree: generated/HRD.parameters

    getParameters

Scripts
*******

.. currentmodule:: cardioception.HRD.task

.. autosummary::
   :toctree: generated/HRD.task

    run
    trial
    waitInput
    tutorial
    responseDecision
    confidenceRatingTask

Languages
*********

.. currentmodule:: cardioception.HRD.languages

.. autosummary::
   :toctree: generated/HRD.languages

    english
    danish
    danish_children
    french

Reports
-------

.. currentmodule:: cardioception.reports

.. _reports:

.. autosummary::
   :toctree: generated/reports

    report
    preprocessing
    group_level_preprocessing


Stats
-----
Extracting the relevant parameters from long result data frame across group / repeated measures. 

.. currentmodule:: cardioception.stats

.. _reports:

.. autosummary::
   :toctree: generated/stats

    psychophysics
    behaviours
