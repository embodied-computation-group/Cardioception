# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""TonePlayer on the real sound card, and the sound it makes.

The live tests skip when PsychToolbox or pylsl is missing, or no audio
device opens.
"""

import math
import subprocess
import sys

import numpy as np
import pytest

from cardioception.devices.tone_player import KINDS, make_tone


def test_import_does_not_need_hardware():
    """Both device modules and the task engines import with pylsl and
    PsychToolbox (and PsychoPy) made unimportable, in a fresh interpreter.

    The PAT and HSD engines are checked when their packages are present, so
    the test holds on a checkout that carries only one of the two tasks.
    """
    code = (
        "import importlib\n"
        "import importlib.util\n"
        "import sys\n"
        "class Block:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.')[0] in ('pylsl', 'psychtoolbox', 'psychopy'):\n"
        "            raise ImportError('blocked ' + name)\n"
        "sys.meta_path.insert(0, Block())\n"
        "import cardioception.devices.beat_source\n"
        "import cardioception.devices.tone_player\n"
        "for engine in ('cardioception.PAT.engine', 'cardioception.HSD._stimulus'):\n"
        "    if importlib.util.find_spec(engine.rsplit('.', 1)[0]) is not None:\n"
        "        importlib.import_module(engine)\n"
        "print('ok')\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"


def test_make_tone():
    x = make_tone(1000.0, 0.03, 0.005, 0.5, 48000.0)
    assert x.dtype == np.float32 and x.shape == (1440,)
    assert np.max(np.abs(x)) <= 0.5 + 1e-6
    # Raised-cosine ramps: silent at the first sample, near full in the middle.
    assert x[0] == 0 and np.max(np.abs(x[600:840])) > 0.49
    # A ramp longer than half the burst is shortened, not an error.
    y = make_tone(50.0, 0.01, 0.05, 1.0, 1000.0)
    assert y.shape == (10,) and np.all(np.isfinite(y))
    assert KINDS == ("tone", "vibration")


@pytest.fixture(scope="module")
def player():
    pytest.importorskip("psychtoolbox")
    pytest.importorskip("pylsl")
    from cardioception.devices.tone_player import TonePlayer

    try:
        p = TonePlayer(volume=0.05, vib_volume=0.05)
    except Exception as err:  # no device, or it would not open
        pytest.skip(f"No audio device opened: {err}")
    yield p
    p.close()


def wait_onsets(player, handles, seconds=3.0):
    import time

    found = {}
    end = time.perf_counter() + seconds
    while len(found) < len(handles) and time.perf_counter() < end:
        found.update(player.poll_onsets())
        time.sleep(0.002)
    return found


def test_tone_player_onsets(player):
    import pylsl

    now = pylsl.local_clock()
    whens = [now + 0.1 + 0.35 * i for i in range(4)]
    handles = [player.schedule(w, "tone") for w in whens]
    # A vibration at the same moment as a tone: they overlap, both play.
    handles.append(player.schedule(whens[1], "vibration"))
    found = wait_onsets(player, handles)
    assert set(found) == set(handles)
    errors = [found[h] - w for h, w in zip(handles, whens + [whens[1]])]
    assert np.all(np.abs(errors) < 0.005), errors


def test_tone_player_stop_all(player):
    import pylsl

    h = player.schedule(pylsl.local_clock() + 1.0, "tone")
    assert player.busy
    player.stop_all()
    # Stopped, but its (NaN) onset not yet collected: still busy.
    assert player.busy
    found = wait_onsets(player, [h], seconds=0.5)
    assert math.isnan(found[h])
    assert not player.busy
