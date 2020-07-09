# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>
# Adapted from: https://stackoverflow.com/questions/33879523/python-how-can-i-generate-a-wav-file-with-beeps
# This script generates the BPM stimulu (wav files) used by the task.
# Not called by the actual task, but included for reproducibility.

import math
import wave
import struct
import numpy as np


def append_silence(audio, duration_milliseconds=500):
    """Add silence to the signal.

    Parameters
    ----------
    audio : array
        The signal where the sine should be added.
    duration_milliseconds : int
        The sine length.

    Returns
    -------
    audio : list
        The signal with the added silence.
    """
    num_samples = duration_milliseconds * (sample_rate / 1000.0)

    for x in range(int(num_samples)):
        audio.append(0.0)

    return audio


def append_sinewave(audio, freq=440, duration_milliseconds=200, volume=1.0):
    """Add sinewave to the signal.

    Parameters
    ----------
    audio : list
        The signal where the sine should be added.
    freq : int
        The sine frequency.
    duration_milliseconds : int
        The sine length.
    volume : float
        The sine amplitude.

    Returns
    -------
    audio : array
        The signal with the added sound.
    """
    num_samples = duration_milliseconds * (sample_rate / 1000.0)

    for x in range(int(num_samples)):
        audio.append(
            volume * math.sin(2 * math.pi * freq * (x / sample_rate)))

    return audio

def save_wav(audio, file_name):
    """Save the audio signal as wav file.

    Parameters
    ----------
    audio : list
        The signal where the sine should be added.
    freq : int
        The sine frequency.
    duration_milliseconds : int
        The sine length.
    volume : float
        The sine amplitude.
    """
    # Open up a wav file
    wav_file = wave.open(file_name, "w")

    # wav params
    nchannels, sampwidth = 1, 2

    # 44100 is the industry standard sample rate
    nframes = len(audio)
    wav_file.setparams((nchannels, sampwidth, sample_rate,
                        nframes, "NONE", "not compressed"))

    for sample in audio:
        wav_file.writeframes(struct.pack('h', int(sample * 32767.0)))

    wav_file.close()


# Generate wav files for frequencies between 15 and 200 beats per minutes
for bpm in np.arange(15, 200, .5):

    rr = (60000/bpm) - 200
    audio = []
    sample_rate = 44100.0

    # Create
    beats = 5
    while beats > 0:

        # Sound
        audio = append_sinewave(audio, volume=0.5)
        audio = append_silence(audio, duration_milliseconds=rr)
        beats -= 1

    save_wav(audio, 'sounds/' + str(bpm) + '.wav')
