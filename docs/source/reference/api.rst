.. _api_ref:

.. meta::
   :description: The Cardioception API: parameters and task functions for the
      Heart Rate Discrimination, Heartbeat Counting, Heartbeat Synchrony
      Discrimination and Phase Adjustment tasks in PsychoPy.
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
   :toctree: ../generated/HBC.parameters

    getParameters

Scripts
*******

.. currentmodule:: cardioception.HBC.task

.. autosummary::
   :toctree: ../generated/HBC.task
    
    run
    trial
    tutorial
    rest

Languages
*********

.. currentmodule:: cardioception.HBC.languages

.. autosummary::
   :toctree: ../generated/HBC.languages

    available
    get_texts

Heart Rate Discrimination task
==============================

Parameters
**********

.. currentmodule:: cardioception.HRD.parameters

.. _parameters:

.. autosummary::
   :toctree: ../generated/HRD.parameters

    getParameters

Configuration
*************

.. currentmodule:: cardioception.HRD.config

.. autosummary::
   :toctree: ../generated/HRD.config

    TaskConfig

Scripts
*******

.. currentmodule:: cardioception.HRD.task

.. autosummary::
   :toctree: ../generated/HRD.task

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
   :toctree: ../generated/HRD.languages

    available
    get_texts
    english
    danish
    danish_children
    french
    german

Heartbeat Synchrony Discrimination task
=======================================

Beta; see the
:doc:`design document </tasks/hsd/design>` and the
:doc:`HSD page </tasks/hsd/index>`.

Parameters
**********

.. currentmodule:: cardioception.HSD.parameters

.. autosummary::
   :toctree: ../generated/HSD.parameters

    getParameters

Configuration
*************

.. currentmodule:: cardioception.HSD.config

.. autosummary::
   :toctree: ../generated/HSD.config

    TaskConfig

Scripts
*******

.. currentmodule:: cardioception.HSD.task

.. autosummary::
   :toctree: ../generated/HSD.task

    run
    trial
    tutorial

Engine
******

.. currentmodule:: cardioception.HSD.psi

.. autosummary::
   :toctree: ../generated/HSD.psi

    SynchronyPsi
    gaussian_envelope
    default_grids

Languages
*********

.. currentmodule:: cardioception.HSD.languages

.. autosummary::
   :toctree: ../generated/HSD.languages

    available
    get_texts

Phase Adjustment Task
=====================

Beta, after the PAT-ECG of Hodgetts et al. (2026); see the
:doc:`PAT page </tasks/pat>`.

Parameters
**********

.. currentmodule:: cardioception.PAT.parameters

.. autosummary::
   :toctree: ../generated/PAT.parameters

    getParameters
    startPhaseSequence

Scripts
*******

.. currentmodule:: cardioception.PAT.task

.. autosummary::
   :toctree: ../generated/PAT.task

    run
    trial
    tutorial
    dialLoop
    confidenceRatingTask

Engine
******

.. currentmodule:: cardioception.PAT.engine

.. autosummary::
   :toctree: ../generated/PAT.engine

    PhaseEngine

Scoring
*******

.. currentmodule:: cardioception.PAT.scoring

.. autosummary::
   :toctree: ../generated/PAT.scoring

    consistency_grid
    mean_resultant_length
    phase_angles
    monte_carlo_threshold
    extero_threshold
    mad_outliers

Languages
*********

.. currentmodule:: cardioception.PAT.languages

.. autosummary::
   :toctree: ../generated/PAT.languages

    available
    get_texts

Recording devices
-----------------

.. currentmodule:: cardioception.devices

.. autosummary::
   :toctree: ../generated/devices

    ContinuousOximeter
    LSLRecorder
    ReplayRecorder

Beat sources and tone player
============================

Shared by the Heartbeat Synchrony Discrimination task and the Phase Adjustment
Task, which time their tones from the R-wave.

.. currentmodule:: cardioception.devices.beat_source

.. autosummary::
   :toctree: ../generated/devices.beat_source

    LSLBeatSource
    VirtualBeatSource

.. currentmodule:: cardioception.devices.tone_player

.. autosummary::
   :toctree: ../generated/devices.tone_player

    TonePlayer

Confidence scales
-----------------

.. currentmodule:: cardioception.scales

.. autosummary::
   :toctree: ../generated/scales

    ConfidenceScale

Reports
-------

.. currentmodule:: cardioception.reports

.. _reports:

.. autosummary::
   :toctree: ../generated/reports

    report
    preprocessing
