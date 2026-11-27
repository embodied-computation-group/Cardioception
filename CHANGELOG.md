# Changelog

Changes to the 0.7 maintenance line, kept on the `legacy/0.7` branch.

## 0.7.3 (2026-11-27)

A hotfix for the Heart Rate Discrimination task, found in a session run with
PsychoPy 2026.2.2.

### Fixed

- **The confidence marker no longer uses the accuracy feedback colours.** The
  marker was red while it moved (PsychoPy's Slider default) and turned green
  on confirmation. The tutorial shows accuracy as red "False" and green
  "Correct", so a participant could read the rating colours as feedback on
  the decision. The marker is now white while it moves and turns light gray,
  the colour of the slider itself, for the 0.2 s confirmation. This applies to
  every confidence slider in the package: the HRD keyboard and mouse ratings
  and the HBC rating. Timing, scales and keys are unchanged.
- **A mouse button that is already down no longer counts as a response.** In
  the HRD mouse decision, a button held over from the previous screen, or one
  whose release the window never received, was accepted at decision onset as
  a response with `DecisionRT` 0.0: `Mouse.getPressed` reports the buttons
  that are down, and `clickReset` zeroes their press times without releasing
  them. The same held button could then confirm the confidence rating as soon
  as `minRatingTime` had passed. Both now count only presses made after the
  screen appeared. The keyboard path was not affected: `event.waitKeys`
  clears the keyboard buffer before it waits.
- **No more "Font b'Helvetica Bold' was requested. No similar font found"
  warnings on Windows.** The confidence sliders now ask for Arial on Windows.
  Other platforms keep PsychoPy's default, so the look on macOS is unchanged.
