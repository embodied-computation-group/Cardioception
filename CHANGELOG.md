# Changelog

## 0.8.0 (unreleased)

The first release since the 2026 audit. It changes the output schema and the
output layout, so analysis scripts written against 0.7.x need the migration
notes below. Everything else is a fix.

### Breaking

**Results now live in per-run directories.**
`data/<participant><session>/` becomes
`data/sub-<participant>/ses-<session>/run-<YYYYMMDD-HHMMSS>/`, and every
filename carries all three identifiers. Two consequences:

- Participant and session are no longer concatenated. `("P0", "1001")` and
  `("P01", "001")` used to land in the same directory; they no longer can.
- A repeated session cannot overwrite an earlier one. This has cost real data
  in longitudinal studies, and the workaround — telling people to append the
  session to the participant ID — is no longer needed. Starting a session over
  an existing set of results raises `FileExistsError` unless you pass
  `overwrite=True`.

Read `<run directory>/*_final.txt` rather than a name you construct yourself.
`parameters["resultPath"]` still exists and now points at the run directory.

**`listenBPM` is the rate over the listening window,** `60000 / mean(IBI)`,
where it was previously `mean(60000 / IBI)`. By Jensen's inequality the second
is always the larger; on real PPG the difference is about +0.33 BPM. The tone
was therefore reliably faster than the heart it was meant to match. The old
value is kept as `listenBPM_arithmetic`. New sessions are not directly
comparable to published ones on this variable.

**`Confidence` is labelled.** It previously held 0-100 from the mouse, 1-10
from the HRD keyboard and 1-7 from HBC, with nothing in the output saying
which. The raw rating still uses its own scale; `ConfidenceUnit` carries the
same rating on 0-1 so sessions run on different scales can be pooled, and the
scale definition is written on every row next to `Device`.

**`stairType="updown"` raises.** The nUp/nDown staircase is gone. It described
itself as a 1-down 2-up procedure converging at ~71% accuracy, but built its
conditions with `nUp=1, nDown=1`, which converges at 50% — chance on a
two-alternative task. The documentation and the code never agreed, no published
Cardioception data used it, and it could not estimate a slope. `TrialType` no
longer contains `updown`.

**Missed trials no longer reach the staircase.** A trial with no response was
previously scored as `Less` and fed to `addResponse`, which pushed the psi
posterior on evidence the participant never gave. Missed trials are now
excluded and, by default, re-presented later in the session — so session length
varies. Set `onMissedTrial="skip"` for a fixed number of presentations.
`nRepresentations` records how many times each trial was shown.

### Added

- `time` in `_signal.txt`: absolute epoch seconds for every sample. Without it
  the PPG recording could not be aligned with the trial triggers or with
  anything recorded alongside it.
- `manifest.json`, written at session **start**: participant, session, run,
  seed, version, device, language, staircase, trial count and confidence scale.
  The parameters pickle is written at the end, so an aborted session used to
  leave no record of its own settings.
- A recorded random seed. Every session draws from one generator, and the seed
  is saved even when the caller did not choose one, so any session can be
  replayed.
- Quality columns: `HeartRateAttempts`, `HeartRateAccepted`,
  `nRepresentations`, `DroppedFrames`. `HeartRateAccepted` distinguishes a
  trial where the task settled on a heart rate from one where it exhausted its
  attempts and used the last window anyway — previously invisible.
- `cardioception.scales.ConfidenceScale`, including a signed
  −100 (certain error) / 0 / +100 (certain correct) VAS. On a signed scale the
  sign is the believed outcome and the magnitude is the confidence; use
  `magnitude()` and `believes_correct()` to separate them before modelling.
- Trigger callables at each trial event. These were documented for years but
  never created, so following the documentation raised `KeyError`.
- `python -m cardioception.validate <run directory>`, which checks a finished
  session against the invariants the test suite uses.
- A test suite that runs whole sessions without hardware or a human, and CI
  that runs it.

### Fixed

- A memory leak that reached 2.6 GB over 60 psi trials. The stored posterior
  was a view onto that trial's likelihood array, which pinned all of them.
- Escape now aborts from the Heart Rate Discrimination task's response and
  rating screens. It previously did not.
- A button still held down from the decision no longer submits the confidence
  rating on the first frame past `minRatingTime`. `Mouse.getPressed` reports
  the button's level, not a press, and `clickReset` resets click times rather
  than state, so a held button was read as a fresh click on the next screen —
  observed in real data as 17 trials with a decision response time of exactly
  zero.
- The heart-rate acquisition loop is bounded and can be escaped. A single
  artefactual interbeat interval could previously hold a participant on the
  listening screen indefinitely.
- Every `core.wait` is now a loop that keeps drawing and flipping. Stimulus
  durations are unchanged; the window simply stays responsive and frame
  intervals get recorded.
- An odd `nTrials` no longer fails at setup with an `IndexError`.
- The keyboard confidence rating uses `visual.Slider`. `visual.RatingScale`
  moved to the `psychopy-legacy` plugin in PsychoPy 2026 and now raises.
- A crash or an abort still saves everything the session produced.

### Deprecated

- `cardioception.reports`. To be rebuilt.
