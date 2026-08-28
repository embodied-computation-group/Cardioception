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
- `session.log` in the run directory. The tasks narrated themselves with
  `print`, which goes to a terminal nobody keeps and carries no timestamps, so
  a session that failed left nothing to look at. The same messages now go to a
  timestamped file as well as the console.

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

### Internal

Structural work from the audit's refactoring report. None of it changes what a
participant sees or what a trial records, and each step was checked against the
code it replaced rather than read over.

- Participant-facing text moves from 484 lines of Python to one YAML file per
  language, validated against a required key set when the session starts. A
  language missing a key, or a `language` that does not exist, used to fail
  mid-session with a `KeyError`; both are now errors at launch.
- The 64 `visual.TextStim` constructions become one `text()` helper, 370 lines
  to 95.
- The trigger codes and signal constants are named. Worth knowing: **the two
  tasks write different meanings to the same marker channel.** In HRD, 1 is the
  trial starting and 2 the listening window opening; in HBC, 1 is the listening
  window opening and 2 its closing.
- `trial()` returns a `TrialOutcome` rather than an 18-element tuple, and that
  object owns the results row, so column order is decided in one place.
- The two listening phases become `listen_to_heart()` and `listen_to_tone()`.
  The first is now the only place the task touches physiology.
- The Heart Rate Discrimination tutorial is a table of phases — instruction
  screens interleaved with practice blocks — rather than a sequential script.
  What participants are shown, how many practice trials each block runs and at
  what difficulty are all set in one place. Verified by tracing all 440
  presentation steps across every language, device and condition before and
  after; they are identical.
- `TaskConfig` gathers the design values that were literals inside
  `getParameters` — response window, tutorial lengths, ISI, listening duration,
  heart-rate cutoffs, staircase bounds, text size. Pass one to `getParameters`,
  and it is written to `manifest.json` with the data it produced.

**`responseDecision` returns five values, not six.** The second, a
`responseTrigger` timestamp, was unpacked by its only caller and never read.
`parameters` no longer carries `lambdaIntero` or `lambdaExtero`, which were
always empty lists, so a `_parameters.pickle` will not contain them.

### Packaging

- `package_data` listed `*.wav` and `*.png`, but the stimuli live in
  `Images/` and `Sounds/`, so the patterns matched nothing and a wheel built
  from it shipped no sounds. Only `MANIFEST.in` was keeping the sdist usable.
- `psychopy` moves from `==2026.2.2` to `>=2026.2,<2027`. The major-version
  ceiling stays because 2026 moved `visual.RatingScale` into a plugin without a
  deprecation cycle.
- The documentation workflow deployed to `gh-pages` from pull requests as well
  as from master, so a pull request could replace the live documentation before
  review. It now builds on pull requests and publishes only from master.
- `.RData` (50 MB), `.Rhistory` and `.coverage` are no longer tracked. They
  remain in the history; only new clones of the working tree get smaller.

### Deprecated

- `cardioception.reports`. To be rebuilt.
