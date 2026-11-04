# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""Find R peaks while the ECG arrives, for tasks that time stimuli on the heart.

:func:`cardioception.devices._beats.detect_beats` looks at a whole recording
and is the reference. This detector sees one sample at a time and must say
"that was a beat" as soon after the R peak as it can be sure, because every
millisecond it waits is a millisecond the tone cannot be played in.

How it works, per sample:

1. QRS energy, as in Pan and Tompkins (1985): a 5 to 20 Hz band pass (two
   biquads), the first difference, its square, and a moving average over
   :data:`INTEGRATION` seconds. A QRS is detected when the average rises
   through an adaptive threshold, set between running estimates of the QRS
   and the noise level.
2. The R peak, as in :func:`~cardioception.devices._beats.snap_to_qrs`: the
   largest deflection of the unfiltered signal, searched from
   :data:`~cardioception.devices._beats.QRS_SEARCH` seconds before the
   detection onwards. Filters would move the peak, so none are applied here.
3. The beat is committed as soon as the signal has fallen back to
   :data:`FALL` of the peak's height above the baseline, a few milliseconds
   after the peak on a clean ECG. Which way is "up" (the polarity of the
   largest deflection) is learnt from the beats already seen, so electrode
   orientation does not matter. Until it is known, the detector waits for the
   whole search window instead.

The signal is raw ADC counts, with whatever offset and gain the device has:
the thresholds are relative, and the peak is measured from a local baseline.

Two guards keep a bad signal from being reported as beats:

- A step in the timestamps longer than :data:`GAP` sample intervals is a gap
  in the signal (a dropped Bluetooth link, say). The filters and the moving
  average start again after it from the new samples, the QRS being followed
  is dropped, and nothing is learnt or detected for one anticipated period
  (:data:`RESUME_HOLD` seconds at least, 1.2 s while the period is unknown),
  while the filters settle and the buffer fills with signal from after the
  gap. The thresholds learnt before the gap are kept. An inlet that dejitters
  its timestamps can hide much of a gap; only the part it shows is seen.
- Without a beat for :data:`SEARCH_LIMIT` periods the QRS energy estimate is
  halved, so that a large artefact cannot silence the detector, but never
  below :data:`ENERGY_FLOOR` of the median energy of the last
  :data:`ENERGY_BEATS` beats. Sustained noise, an electrode coming off, then
  cannot lower the threshold until the noise itself is taken for beats.
"""

import math
from collections import deque
from typing import Deque, List, NamedTuple, Optional, Sequence, Union

import numpy as np

from ._beats import QRS_SEARCH

#: Pass band of the filter the QRS energy is computed from, in Hz.
BAND = (5.0, 20.0)

#: Seconds over which the squared slope is averaged. Pan and Tompkins use
#: 0.15 s, about the widest QRS.
INTEGRATION = 0.15

#: Fraction of the QRS energy estimate, above the noise estimate, at which a
#: QRS is detected.
THRESHOLD = 0.25

#: Seconds after an R peak during which no other is accepted, by default.
REFRACTORY = 0.25

#: Weight of the newest peak in the running QRS and noise estimates.
LEARNING_RATE = 0.125

#: The beat is committed once the signal has fallen back to this fraction of
#: the R peak's height above the baseline.
FALL = 0.5

#: Seconds before the detection over which the baseline is measured, as
#: (start, end). This is the PR segment when the detection is near the R peak.
BASELINE = (0.16, 0.06)

#: A candidate closer than this many seconds to the previous beat, and less
#: than :data:`T_WAVE_RATIO` of the usual R height, is taken for a T wave.
T_WAVE_WINDOW = 0.36
T_WAVE_RATIO = 0.5

#: Without a beat for this many mean RR intervals, the QRS estimate is
#: halved, so one large artefact cannot silence the detector.
SEARCH_LIMIT = 1.66

#: The QRS energy estimate is never halved below this fraction of the median
#: QRS energy of the last :data:`ENERGY_BEATS` beats: two halvings. On a
#: synthetic ECG, white noise up to a fifth of the R height is then not taken
#: for beats, and a QRS that drops to half its height is still followed; one
#: that drops to a quarter at once is not, until the detector is reset.
ENERGY_FLOOR = 0.25
ENERGY_BEATS = 8

#: A step between consecutive timestamps longer than this many sample
#: intervals is a gap in the signal.
GAP = 3

#: Seconds, at least, after a gap during which nothing is learnt or detected.
#: It is one anticipated period if that is longer (1.2 s while unknown).
RESUME_HOLD = 0.5

#: Seconds of signal kept in memory.
BUFFER = 1.0

Number = Union[int, float]


class Beat(NamedTuple):
    """One R peak, as reported by :class:`OnlineRDetector`."""

    #: Timestamp of the R-peak sample, on the caller's clock (LSL time).
    r_time: float
    #: Global sample index of the R peak (0 is the first sample ever fed).
    r_index: int
    #: Global index of the sample at which the detector committed to the beat.
    commit_index: int
    #: Seconds since the previous beat, ``None`` for the first.
    rr: Optional[float]


def _biquad(kind: str, freq: float, sfreq: float) -> List[float]:
    """Butterworth second-order section, ``[b0, b1, b2, a1, a2]``.

    The coefficients from Robert Bristow-Johnson's audio EQ cookbook, with
    Q = 1/sqrt(2), so no filter design library is needed.
    """
    w0 = 2 * math.pi * freq / sfreq
    alpha = math.sin(w0) / math.sqrt(2)
    cos = math.cos(w0)
    a0 = 1 + alpha
    if kind == "low":
        b = [(1 - cos) / 2, 1 - cos, (1 - cos) / 2]
    else:
        b = [(1 + cos) / 2, -(1 + cos), (1 + cos) / 2]
    return [c / a0 for c in b] + [-2 * cos / a0, (1 - alpha) / a0]


class OnlineRDetector:
    """Causal R-peak detector, fed in chunks of any size.

    Parameters
    ----------
    sfreq :
        Sampling rate in Hz, at least 50.
    refractory :
        Seconds after an R peak during which no other is accepted.
    warmup :
        Seconds at the start used to learn the signal's scale. No beat is
        reported before this.

    Notes
    -----
    Feed it whatever the inlet returns, and act on the beats it gives back::

        detector = OnlineRDetector(sfreq=1000)
        samples, stamps = inlet.pull_chunk()
        for beat in detector.process([s[channel] for s in samples], stamps):
            ...

    The beats returned do not depend on how the signal is cut into chunks.
    """

    def __init__(
        self, sfreq: float, refractory: float = REFRACTORY, warmup: float = 2.0
    ):
        if sfreq < 2.5 * BAND[1]:
            raise ValueError(f"sfreq should be at least {2.5 * BAND[1]:g} Hz.")
        if warmup <= 0 or refractory < 0:
            raise ValueError("warmup should be positive, refractory not negative.")
        self.sfreq = float(sfreq)
        self.refractory = refractory
        self.warmup = warmup

        def samples(seconds: float) -> int:
            return max(int(round(seconds * self.sfreq)), 1)

        self._refractory_n = int(round(refractory * self.sfreq))
        self._warmup_samples = samples(warmup)
        self._pre_n, self._post_n = (samples(s) for s in QRS_SEARCH)
        self._base_n = (samples(BASELINE[0]), samples(BASELINE[1]))
        self._mwi_n = samples(INTEGRATION)
        self._buffer_n = samples(max(BUFFER, INTEGRATION + sum(QRS_SEARCH) + 0.2))
        self._high = _biquad("high", BAND[0], self.sfreq)
        self._low = _biquad("low", BAND[1], self.sfreq)
        self.reset()

    # -- public surface ----------------------------------------------------

    def reset(self) -> None:
        """Forget everything, as if no sample had been fed."""
        self._n = 0
        self._warmup_n = self._warmup_samples
        self._last_t: Optional[float] = None
        self._hold_until = 0
        #: Gaps in the timestamps seen since the last reset.
        self.n_gaps = 0
        self._x = np.zeros(self._buffer_n)
        self._t = np.zeros(self._buffer_n)
        self._last_x = 0.0
        self._reset_filters()
        # Thresholds, set at the end of the warmup.
        self._warm_max = 0.0
        self._warm_sum = 0.0
        self._spk = self._npk = self._thr = 0.0
        self._energies: Deque[float] = deque(maxlen=ENERGY_BEATS)
        self._armed = False
        self._event_max = 0.0
        self._event_is_beat = False
        self._last_detect = 0
        self._height = 0.0
        # The QRS being followed, if any.
        self._active = False
        self._onset = 0
        self._baseline = 0.0
        self._peak_hi = self._peak_lo = 0
        # Polarity: votes from finished beats, clipped to +-2; sign is used.
        self._score = 0
        self._votes: Deque[int] = deque()  # sample index at which to vote
        self._warm_vote_at = -1
        self._last_r = -(10**9)
        self._last_r_time: Optional[float] = None
        self._rr: List[float] = []

    def _reset_filters(self) -> None:
        """Clear the filters and the moving average, as before the first sample."""
        self._primed = False
        # Filter state: input and output history of each biquad.
        self._hx1 = self._hx2 = self._hy1 = self._hy2 = 0.0
        self._ly1 = self._ly2 = self._lx1 = self._lx2 = 0.0
        self._f1 = 0.0
        self._energy = np.zeros(self._mwi_n)
        self._mwi_sum = 0.0
        self._mwi1 = self._mwi2 = 0.0

    def process(
        self, samples: Sequence[Number], timestamps: Sequence[float]
    ) -> List[Beat]:
        """Feed a chunk (any length, including 1). Returns beats committed in it.

        ``samples`` are the ECG values of one channel, ``timestamps`` their
        times on the caller's clock. Non-finite samples are replaced by the
        previous value.
        """
        x = np.asarray(samples, dtype=float).ravel()
        t = np.asarray(timestamps, dtype=float).ravel()
        if x.size != t.size:
            raise ValueError(
                f"{x.size} samples but {t.size} timestamps; they should match."
            )
        beats = []
        for value, stamp in zip(x.tolist(), t.tolist()):
            beat = self._step(value, stamp)
            if beat is not None:
                beats.append(beat)
        return beats

    @property
    def anticipated_period(self) -> Optional[float]:
        """Mean of the last 3 RR intervals in seconds, None until 3 are known."""
        if len(self._rr) < 3:
            return None
        return sum(self._rr[-3:]) / 3

    @property
    def rr_history(self) -> List[float]:
        """Every RR interval reported so far, in seconds, oldest first."""
        return list(self._rr)

    @property
    def polarity(self) -> int:
        """+1 if the largest deflection points up, -1 if down, 0 if unknown."""
        return (self._score > 0) - (self._score < 0)

    # -- one sample ----------------------------------------------------------

    def _step(self, x: float, t: float) -> Optional[Beat]:
        n = self._n
        if self._last_t is not None and t - self._last_t > GAP / self.sfreq:
            self._resume(n)
        self._last_t = t
        if not math.isfinite(x):
            x = self._last_x
        elif not self._primed:
            # Start the high pass in its steady state for a constant input,
            # so the DC offset does not ring through the warmup.
            self._hx1 = self._hx2 = x
            self._primed = True
        self._last_x = x
        i = n % self._buffer_n
        self._x[i] = x
        self._t[i] = t

        # QRS energy: band pass, slope, square, moving average.
        b0, b1, b2, a1, a2 = self._high
        hp = b0 * x + b1 * self._hx1 + b2 * self._hx2 - a1 * self._hy1 - a2 * self._hy2
        self._hx2, self._hx1, self._hy2, self._hy1 = self._hx1, x, self._hy1, hp
        b0, b1, b2, a1, a2 = self._low
        lp = b0 * hp + b1 * self._lx1 + b2 * self._lx2 - a1 * self._ly1 - a2 * self._ly2
        self._lx2, self._lx1, self._ly2, self._ly1 = self._lx1, hp, self._ly1, lp
        slope = lp - self._f1
        self._f1 = lp
        j = n % self._mwi_n
        self._mwi_sum += slope * slope - self._energy[j]
        self._energy[j] = slope * slope
        if j == self._mwi_n - 1:
            # Recompute now and then, so rounding cannot accumulate.
            self._mwi_sum = float(self._energy.sum())
        mwi = max(self._mwi_sum, 0.0) / self._mwi_n

        beat = None
        if n < self._hold_until:
            pass  # settling after a gap
        elif n < self._warmup_n:
            self._learn(n, mwi)
        else:
            if n == self._hold_until and n > self._warmup_n:
                self._rearm(n, mwi)
            beat = self._detect(n, x, mwi)
        self._mwi2, self._mwi1 = self._mwi1, mwi

        while self._votes and self._votes[0] <= n:
            self._vote(self._votes.popleft() - self._post_n, n)
        if self._warm_vote_at == n:
            # The QRS lies in the integration window that ends at the
            # energy maximum, a little later for the filter's delay.
            peak = n - self._post_n
            self._vote(peak - self._mwi_n // 2, n)
        self._n = n + 1
        return beat

    def _learn(self, n: int, mwi: float) -> None:
        """Warmup: find the scale of the QRS energy, and a first polarity."""
        self._warm_sum += mwi
        if mwi > self._warm_max:
            self._warm_max = mwi
            self._warm_vote_at = n + self._post_n
        if n == self._warmup_n - 1:
            self._spk = self._warm_max
            self._energies.append(self._spk)
            self._npk = self._warm_sum / (self._warmup_n - self._hold_until)
            self._update_threshold()
            self._rearm(n, mwi)

    def _rearm(self, n: int, mwi: float) -> None:
        """Start detecting, after the warmup or after a gap."""
        # Still above threshold: in a QRS, whose energy is learnt.
        self._armed = mwi < self._thr
        self._event_max = 0.0
        self._event_is_beat = True
        self._last_detect = n

    def _resume(self, n: int) -> None:
        """A gap in the signal ends at sample ``n``: let the filters start again."""
        self.n_gaps += 1
        self._reset_filters()
        self._active = False
        hold = max(RESUME_HOLD, self.anticipated_period or 1.2)
        self._hold_until = n + int(round(hold * self.sfreq))
        if n < self._warmup_n:
            # Learn the scale again, from the signal after the gap.
            self._warmup_n = self._hold_until + self._warmup_samples
            self._warm_max = self._warm_sum = 0.0
            self._warm_vote_at = -1

    def _detect(self, n: int, x: float, mwi: float) -> Optional[Beat]:
        # Noise peaks: local maxima of the energy outside any QRS.
        if (
            self._armed
            and not self._active
            and self._mwi2 < self._mwi1 >= mwi
            and self._mwi1 < self._thr
        ):
            self._npk += LEARNING_RATE * (self._mwi1 - self._npk)
            self._update_threshold()

        if not self._armed:
            # Following the energy of the last QRS until it falls back, to
            # learn its height. Give up after a second, so that a level
            # that never falls cannot block detection.
            self._event_max = max(self._event_max, mwi)
            if mwi < self._thr or n - self._last_detect > self.sfreq:
                if self._event_is_beat:
                    self._spk += LEARNING_RATE * (self._event_max - self._spk)
                    self._energies.append(self._event_max)
                else:
                    self._npk += LEARNING_RATE * (self._event_max - self._npk)
                self._update_threshold()
                self._armed = True
        elif (
            not self._active
            and mwi > self._thr
            and n - self._last_r >= self._refractory_n
        ):
            self._start(n)

        if not self._active:
            limit = SEARCH_LIMIT * self.sfreq * (self.anticipated_period or 1.2)
            if n - self._last_detect > limit:
                floor = ENERGY_FLOOR * float(np.median(self._energies))
                self._spk = max(self._spk * 0.5, floor)
                self._update_threshold()
                self._last_detect = n
            return None
        return self._follow(n, x)

    def _start(self, n: int) -> None:
        """A QRS was detected at sample ``n``: look back for its peak."""
        self._active = True
        self._armed = False
        self._event_max = 0.0
        self._event_is_beat = False
        self._onset = self._last_detect = n
        lo = max(n - self._pre_n, self._n_oldest())
        window = self._window(lo, n + 1)
        self._peak_hi = lo + int(np.argmax(window))
        self._peak_lo = lo + int(np.argmin(window))
        base_lo = max(n - self._base_n[0], self._n_oldest())
        base_hi = max(n - self._base_n[1], base_lo + 1)
        self._baseline = float(np.median(self._window(base_lo, base_hi)))

    def _follow(self, n: int, x: float) -> Optional[Beat]:
        """Track the peak of the current QRS, and commit once it is past."""
        if n > self._onset:
            if x > self._x[self._peak_hi % self._buffer_n]:
                self._peak_hi = n
            if x < self._x[self._peak_lo % self._buffer_n]:
                self._peak_lo = n
        base = self._baseline
        high = self._x[self._peak_hi % self._buffer_n] - base
        low = base - self._x[self._peak_lo % self._buffer_n]
        sign = self.polarity
        timeout = n - self._onset >= self._post_n
        if sign > 0:
            peak, done = self._peak_hi, high > 0 and x - base <= FALL * high
        elif sign < 0:
            peak, done = self._peak_lo, low > 0 and base - x <= FALL * low
        else:
            peak, done = (self._peak_hi if high >= low else self._peak_lo), False
        if not (done or timeout):
            return None
        self._active = False
        if peak - self._last_r < self._refractory_n:
            return None
        height = abs(self._x[peak % self._buffer_n] - base)
        if (
            peak - self._last_r < T_WAVE_WINDOW * self.sfreq
            and height < T_WAVE_RATIO * self._height
        ):
            return None
        self._height += (LEARNING_RATE if self._height else 1.0) * (
            height - self._height
        )
        self._event_is_beat = True
        self._last_r = peak
        self._votes.append(peak + self._post_n)
        if peak < self._warmup_n:
            return None
        r_time = float(self._t[peak % self._buffer_n])
        rr = None if self._last_r_time is None else r_time - self._last_r_time
        self._last_r_time = r_time
        if rr is not None:
            self._rr.append(rr)
        return Beat(r_time, peak, n, rr)

    # -- helpers -------------------------------------------------------------

    def _update_threshold(self) -> None:
        self._thr = self._npk + THRESHOLD * (self._spk - self._npk)

    def _vote(self, centre: int, n: int) -> None:
        """Which way the largest deflection around ``centre`` points.

        The same window and baseline as ``snap_to_qrs``, so the polarity
        learnt is the one it would pick.
        """
        lo = max(centre - self._pre_n, self._n_oldest())
        hi = min(centre + self._post_n, n) + 1
        if hi - lo < 2:
            return
        window = self._window(lo, hi)
        median = float(np.median(window))
        up = float(window.max()) - median
        down = median - float(window.min())
        self._score = max(-2, min(2, self._score + (1 if up >= down else -1)))

    def _n_oldest(self) -> int:
        """Global index of the oldest sample still in the buffer."""
        return max(self._n - self._buffer_n + 1, 0)

    def _window(self, lo: int, hi: int) -> np.ndarray:
        """Samples ``lo`` to ``hi - 1``, by global index, from the buffer."""
        return self._x[np.arange(lo, hi) % self._buffer_n]
