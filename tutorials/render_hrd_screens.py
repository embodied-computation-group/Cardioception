"""Render the HRD screens shown in panel a of the HRD overview figure.

Each screen is drawn with the task's own drawing code and saved from the back
buffer. No session runs and no sound is created or played. Needs PsychoPy, so
run it in a Cardioception environment::

    python tutorials/render_hrd_screens.py

The PNGs land in ``docs/source/images/hrd_screens/``; ``plot_hrd_overview.py``
composes them into the figure.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from psychopy import visual

from cardioception._screens import fixation as fixation_cross
from cardioception._screens import text
from cardioception._session import confidence_rating
from cardioception.HRD.parameters import getParameters

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "source" / "images" / "hrd_screens"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp()
    p = getParameters(
        participant="screens",
        session="figure",
        setup="test",
        fullscr=False,
        resultPath=tmp,
        nTrials=2,
    )
    win, t = p["win"], p["texts"]

    def save(name: str, *stims) -> None:
        for stim in stims:
            stim.draw()
        win._getFrame(buffer="back").save(OUT / f"{name}.png")
        win.flip()

    try:
        save("fixation", fixation_cross(p))
        save(
            "intero_listen",
            text(p, t["textHeartListening"], pos=(0.0, 0.2)),
            p["heartLogo"],
        )
        save(
            "extero_listen",
            text(p, t["textToneListening"], pos=(0.0, 0.2)),
            p["listenLogo"],
        )
        # The decision screen as task.trial and responseDecision draw it with
        # the default mouse device.
        for modality, logo in (("Intero", "heartLogo"), ("Extero", "listenLogo")):
            save(
                f"{modality.lower()}_decision",
                p[logo],
                text(p, t["Decision"][modality], pos=(0, 0.4)),
                text(p, t["responseText"], pos=(0.0, -0.4)),
                text(p, t["slower"], pos=(-0.2, 0.2), color="white"),
                text(p, t["faster"], pos=(0.2, 0.2), color="white"),
            )

        # The confidence scale is drawn inside its own loop, so capture one of
        # its frames and let it time out.
        original_flip = visual.Window.flip
        state = {"n": 0}

        def flip(self, *args, **kwargs):
            state["n"] += 1
            if state["n"] == 20:
                self._getFrame(buffer="back").save(OUT / "confidence.png")
            return original_flip(self, *args, **kwargs)

        visual.Window.flip = flip
        p["maxRatingTime"], p["minRatingTime"] = 1.0, 0.0
        try:
            confidence_rating(p)
        finally:
            visual.Window.flip = original_flip
    finally:
        win.close()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
