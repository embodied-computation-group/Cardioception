.. _api_ref:

.. meta::
   :description: The Cardioception API: parameters and task functions for the
      Heart Rate Discrimination and Heartbeat Counting tasks in PsychoPy.
   :keywords: cardioception API, heart rate discrimination, heartbeat counting,
      PsychoPy, python interoception

.. currentmodule:: cardioception


API
+++

Tasks
-----

Heartbeat Counting task
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

Languages
*********

.. currentmodule:: cardioception.HBC.languages

.. autosummary::
   :toctree: generated/HBC.languages

    available
    get_texts

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
    german

Heartbeat Synchrony Discrimination task
=======================================

Experimental, run on hardware once so far; see the
:doc:`design document <hsd_design>` and the
:doc:`user guide <user_guide>`.

Parameters
**********

.. currentmodule:: cardioception.HSD.parameters

.. autosummary::
   :toctree: generated/HSD.parameters

    getParameters

Scripts
*******

.. currentmodule:: cardioception.HSD.task

.. autosummary::
   :toctree: generated/HSD.task

    run
    trial
    tutorial

Engine
******

.. currentmodule:: cardioception.HSD.psi

.. autosummary::
   :toctree: generated/HSD.psi

    SynchronyPsi
    gaussian_envelope
    default_grids

Recording devices
-----------------

.. currentmodule:: cardioception.devices

.. autosummary::
   :toctree: generated/devices

    ContinuousOximeter
    LSLRecorder
    ReplayRecorder

Reports
-------

.. currentmodule:: cardioception.reports

.. _reports:

.. autosummary::
   :toctree: generated/reports

    report
    preprocessing
