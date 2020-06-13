# QRS detection
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.signal import find_peaks


def interpolate_clipping(signal, threshold=255):
    """Interoplate clipping segment.

    Parameters
    ----------
    signal : 1d array-like
        Noisy signal.
    threshold : int
        Threshold of clipping artefact.

    Returns
    -------
    clean_signal : 1d array-like
        Interpolated signal.

    Notes
    -----
    Correct signal segment reaching recording threshold (default is 255)
    using a cubic spline interpolation. Adapted from [#]_.

    .. Warning:: If clipping artefact is found at the edge of the signal, this
        function will decrement the first/last value to allow interpolation,
        which can lead to incorrect estimation.

    References
    ----------
    .. [#] https://python-heart-rate-analysis-toolkit.readthedocs.io/en/latest/
    """
    if isinstance(signal, list):
        signal = np.array(signal)

    # Security check for clipping at signal edge
    if signal[0] == threshold:
        signal[0] = threshold-1
    if signal[-1] == threshold:
        signal[-1] = threshold-1

    time = np.arange(0, len(signal))

    # Interpolate
    f = interp1d(time[np.where(signal != 255)[0]],
                 signal[np.where(signal != 255)[0]],
                 kind='cubic')

    # Use the peaks vector as time input
    clean_signal = f(time)

    return clean_signal


def oxi_peaks(x, sfreq=75, win=1, new_sfreq=1000, clipping=True,
              noise_removal=True, peak_enhancement=True):
    """A simple peak finder for PPG signal.

    Parameters
    ----------
    x : list or 1d array-like
        The oxi signal.
    sfreq : int
        The sampling frequency. Default is set to 75 Hz.
    win : int
        Window size (in seconds) used to compute the threshold.
    new_sfreq : int
        If resample is *True*, the new sampling frequency.
    resample : bool
        If *True (defaults), will resample the signal at *new_sfreq*. Default
        value is 1000 Hz.

    Returns
    -------
    peaks : 1d array-like
        Numpy array containing R peak timing, in sfreq.
    resampled_signal : 1d array-like
        Signal resampled to the `new_sfreq` frequency.

    Notes
    -----
    This algorithm use a simple rolling average to detect peaks. The signal is
    first resampled and a rolling average is applyed to correct high frequency
    noise and clipping. The signal is then squared and detection of peaks is
    performed using threshold set by the moving averagte + stadard deviation.

    .. warning :: This function will resample the signal to 1000 Hz.

    References
    ----------
    Some of the processing steps were adapted from the HeartPy toolbox [1]:
    https://python-heart-rate-analysis-toolkit.readthedocs.io/en/latest/index.html

    [1] : van Gent, P., Farah, H., van Nes, N. and van Arem, B., 2019.
    Analysing Noisy Driver Physiology Real-Time Using Off-the-Shelf Sensors:
    Heart Rate Analysis Software from the Taking the Fast Lane Project. Journal
    of Open Research Software, 7(1), p.32. DOI: http://doi.org/10.5334/jors.241
    """
    if isinstance(x, list):
        x = np.asarray(x)

    # Interpolate
    f = interp1d(np.arange(0, len(x)/sfreq, 1/sfreq), x,
                 fill_value="extrapolate")
    time = np.arange(0, len(x)/sfreq, 1/new_sfreq)
    x = f(time)

    # Copy resampled signal for output
    resampled_signal = np.copy(x)

    # Remove clipping artefacts with cubic interpolation
    if clipping is True:
        x = interpolate_clipping(x)

    if noise_removal is True:
        # Moving average (high frequency noise + clipping)
        rollingNoise = int(new_sfreq*.1)  # 0.1 second window
        x = pd.DataFrame(
            {'signal': x}).rolling(rollingNoise,
                                   center=True).mean().signal.values
    if peak_enhancement is True:
        # Square signal (peak enhancement)
        x = x ** 2

    # Compute moving average and standard deviation
    signal = pd.DataFrame({'signal': x})
    mean_signal = signal.rolling(int(new_sfreq*0.75),
                                 center=True).mean().signal.values
    std_signal = signal.rolling(int(new_sfreq*0.75),
                                center=True).std().signal.values

    # Substract moving average + standard deviation
    x -= (mean_signal + std_signal)

    # Find positive peaks
    peaks_idx = find_peaks(x, height=0)[0]

    # Create boolean vector
    peaks = np.zeros(len(x))
    peaks[peaks_idx] = 1

    if len(peaks) != len(x):
        raise ValueError('Inconsistent output lenght')

    return resampled_signal, peaks
