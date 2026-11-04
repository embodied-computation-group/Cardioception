# Copyright (C) 2020-2026 Micah G Allen and the Embodied Computation Group, Aarhus University
"""TonePlayer on the real sound card, and the sound it makes.

The live tests skip when PsychToolbox or pylsl is missing, or no audio
device opens.
"""

import logging
import math
import subprocess
import sys
import types

import numpy as np
import pytest

from cardioception.devices.tone_player import (
    KINDS,
    TONE_CLEARANCE,
    make_tone,
    min_tone_spacing,
)


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


class FakeSlave:
    """A PsychPortAudio slave that never finishes: everything stays in flight."""

    def __init__(self, *args, **kwargs):
        self.status = {"StartTime": 0.0, "State": 1}
        self.starts = []

    def fill_buffer(self, data):
        pass

    def start(self, repetitions=1, when=0, wait_for_start=0):
        self.starts.append(when)

    def stop(self):
        return (0.0, 0, 0, 0)

    def close(self):
        pass


class FakeStream:
    handle = 1

    def __init__(self, *args, **kwargs):
        self.status = {"SampleRate": 48000.0, "OutDeviceIndex": 0}

    def start(self, **kwargs):
        pass

    def stop(self):
        pass

    def close(self):
        pass


@pytest.fixture
def silent_player(monkeypatch):
    """A TonePlayer on a fake PsychToolbox, whose clock is GetSecs itself."""
    now = [100.0]
    audio = types.SimpleNamespace(
        verbosity=lambda level: None, Stream=FakeStream, Slave=FakeSlave
    )
    ptb = types.SimpleNamespace(GetSecs=lambda: now[0], audio=audio)
    monkeypatch.setitem(sys.modules, "psychtoolbox", ptb)
    monkeypatch.setitem(sys.modules, "psychtoolbox.audio", audio)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    from cardioception.devices.tone_player import TonePlayer

    player = TonePlayer(duration=0.03, vib_duration=0.05, clock=lambda: now[0])
    assert player.offset == 0.0
    yield player, now
    player.close()


def test_player_refuses_a_tone_that_would_play_late(silent_player, caplog):
    """A tone less than its duration plus 0.05 s from another in flight is
    not played: it is logged and its onset is NaN. Other kinds are not
    affected, and a tone far enough away is queued."""
    player, now = silent_player
    assert min_tone_spacing(0.03) == pytest.approx(0.03 + TONE_CLEARANCE)
    first = player.schedule(101.0, "tone")
    with caplog.at_level(logging.WARNING, logger="cardioception"):
        late = player.schedule(101.05, "tone")
        early = player.schedule(100.95, "tone")
    assert sum("would play late" in r.getMessage() for r in caplog.records) == 2
    # Vibration and tone are separate tracks, and may overlap.
    vibration = player.schedule(101.0, "vibration")
    queued = player.schedule(101.09, "tone")
    # Spacing is checked against the queue too, not only the sound playing.
    behind = player.schedule(101.12, "tone")
    onsets = dict(player.poll_onsets())
    assert set(onsets) == {late, early, behind}
    assert all(math.isnan(v) for v in onsets.values())
    tone = player._tracks["tone"]
    assert tone.active is not None and tone.active[1] == first
    assert [h for _, h in tone.queue] == [queued]
    assert player._tracks["vibration"].active[1] == vibration


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
