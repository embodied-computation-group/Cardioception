# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Participant texts for the Phase Adjustment Task.

The instructions follow Hodgetts et al. (2026): move the beeps with the dial
until they fall on the heartbeat, explore freely, press space when they match,
then rate confidence from 1 (not at all) to 10 (extremely). Sit still, breathe
normally, do not tense the muscles, and attend to one place in the body. In the
exteroceptive task a vibration on the hand takes the place of the heartbeat.

The first live run showed that "turn the dial" was not enough: participants
need to hear that the beeps never change speed, that the wheel shifts each beep
within the beat, and which wheel that is.
"""

from typing import Any, Dict, Sequence


def english(
    device: str = "keyboard",
    extero: bool = False,
    confScale: Sequence[int] = (1, 10),
    showDial: bool = True,
) -> Dict[str, Any]:
    """Create the text dictionary with instructions in English.

    Parameters
    ----------
    device : str
        The confidence rating device, `"keyboard"` or `"mouse"`.
    extero : bool
        If `True`, the texts of the exteroceptive task (vibration instead of
        heartbeat).
    confScale : tuple of int
        Ends of the confidence scale.
    showDial : bool
        If `True`, the instructions describe the dial on the screen.

    Returns
    -------
    texts : dict

    """
    low, high = confScale
    if extero:
        each = "each vibration"  # one beep with ...
        per = "once per vibration"
        within = "compared to the vibration"
        feel = "the vibration"
        where = "where the vibration is"
    else:
        each = "each heartbeat"
        per = "once per heartbeat"
        within = "within the heartbeat"
        feel = "the heartbeat you feel"
        where = "where your heartbeat is"

    texts: Dict[str, Any] = {
        "done": "You have completed the task. Thank you for your participation.",
        "textNext": "Press SPACE to continue.",
        "textPracticeStart": "Now a few practice trials.\n\nPress SPACE to start.",
        "textTaskStart": "The main task starts now.\n\nPress SPACE to start.",
        "textNextTrial": "Press SPACE to start the next trial.",
        "textBreaks": "Take a short break.\n\nPress SPACE when you are ready to continue.",
        "Confidence": (
            "How confident are you that the beeps matched "
            f"{'the vibration' if extero else 'your heartbeat'}?"
        ),
        "VASlabels": ["Not at all", "Extremely"],
        "tooLate": "Too late",
        "waitingFirstTone": (
            "The beeps are starting ..."
            if extero
            else "Listening for your heartbeat ..."
        ),
    }
    if device == "keyboard":
        texts["ratingHelp"] = "LEFT and RIGHT to choose, SPACE to confirm."
    else:
        texts["ratingHelp"] = "Move the mouse to choose, click to confirm."

    if extero:
        intro = (
            "In this task you feel a short vibration on your hand, and hear a "
            f"short beep with {each}."
        )
        body = "Sit still, breathe normally and do not tense your muscles."
    else:
        intro = f"In this task you hear a short beep with {each}."
        body = (
            "Feel your heartbeat in one place in your body, and keep your "
            "attention there.\n\n"
            "Sit still, breathe normally and do not tense your muscles. Do not "
            "check your pulse with your fingers."
        )
    pages = [
        f"{intro}\n\nThe beeps always come {per}. They never speed up or slow down.",
        "Use the scroll wheel on the mouse, with your dominant hand.\n\n"
        f"Rolling the wheel moves each beep a little earlier or later {within}.",
        "When you roll the wheel, you hear one gap between beeps stretch or "
        "shrink. Then the rhythm settles again at the new position.",
        f"Keep adjusting until the beep lands on {feel}. Explore freely, both "
        "ways, as much as you like.\n\n"
        "When they match, press SPACE with your other hand.",
    ]
    if showDial:
        pages.append(
            "On the screen, a pointer on a circle shows how far you have rolled "
            "the wheel. It flashes with each beep.\n\n"
            f"It does not show {where}. Go by what you feel, and keep your eyes "
            "on the cross in the middle."
        )
    else:
        pages.append("During a trial, keep your eyes on the cross in the middle.")
    pages += [
        "After each trial, rate how confident you are that the beeps matched "
        f"{'the vibration' if extero else 'your heartbeat'}, from {low} (not at "
        f"all) to {high} (extremely).",
        body,
    ]
    texts["instructions"] = pages

    texts["tutorialIntro"] = (
        "Let's practise with the wheel. You will now hear the beeps."
    )
    texts["tutorialListen"] = f"Listen: one beep with {each}."
    texts["tutorialLater"] = (
        "Now roll the wheel AWAY from you a few notches, and listen: each beep "
        f"moves later {within}."
    )
    texts["tutorialEarlier"] = (
        "Now roll the wheel TOWARDS you a few notches, and listen: each beep "
        f"moves earlier {within}."
    )
    texts["tutorialFree"] = (
        f"Try to find the position where the beep falls on {feel}.\n\n"
        "Press SPACE when it does."
    )
    texts["tutorialEnd"] = (
        "If you have any questions, please ask the experimenter now.\n\n"
        "Otherwise, press SPACE to continue."
    )

    return texts


def danish(
    device: str = "keyboard",
    extero: bool = False,
    confScale: Sequence[int] = (1, 10),
    showDial: bool = True,
) -> Dict[str, Any]:
    """Create the text dictionary with instructions in Danish.

    Parameters
    ----------
    device : str
        The confidence rating device, `"keyboard"` or `"mouse"`.
    extero : bool
        If `True`, the texts of the exteroceptive task (vibration instead of
        heartbeat).
    confScale : tuple of int
        Ends of the confidence scale.
    showDial : bool
        If `True`, the instructions describe the dial on the screen.

    Returns
    -------
    texts : dict

    """
    low, high = confScale
    if extero:
        each = "hver vibration"  # et bip ved ...
        per = "én gang per vibration"
        within = "i forhold til vibrationen"
        feel = "vibrationen"
        match = "vibrationen"
        where = "hvor vibrationen er"
    else:
        each = "hvert hjerteslag"
        per = "én gang per hjerteslag"
        within = "i hjerteslaget"
        feel = "det hjerteslag, du mærker"
        match = "dit hjerteslag"
        where = "hvor dit hjerteslag er"

    texts: Dict[str, Any] = {
        "done": "Du har gennemført opgaven. Tak for din deltagelse.",
        "textNext": "Tryk på MELLEMRUM for at fortsætte.",
        "textPracticeStart": (
            "Nu kommer et par øvelsesrunder.\n\nTryk på MELLEMRUM for at starte."
        ),
        "textTaskStart": "Nu begynder hovedopgaven.\n\nTryk på MELLEMRUM for at starte.",
        "textNextTrial": "Tryk på MELLEMRUM for at starte næste runde.",
        "textBreaks": (
            "Hold en kort pause.\n\n"
            "Tryk på MELLEMRUM, når du er klar til at fortsætte."
        ),
        "Confidence": f"Hvor sikker er du på, at bippene passede med {match}?",
        "VASlabels": ["Slet ikke", "Ekstremt"],
        "tooLate": "For langsomt",
        "waitingFirstTone": (
            "Bippene starter ..." if extero else "Lytter efter dit hjerteslag ..."
        ),
    }
    if device == "keyboard":
        texts["ratingHelp"] = (
            "VENSTRE og HØJRE for at vælge, MELLEMRUM for at bekræfte."
        )
    else:
        texts["ratingHelp"] = "Flyt musen for at vælge, klik for at bekræfte."

    if extero:
        intro = (
            "I denne opgave mærker du en kort vibration på hånden og hører et kort "
            f"bip ved {each}."
        )
        body = "Sid stille, træk vejret normalt, og spænd ikke i musklerne."
    else:
        intro = f"I denne opgave hører du et kort bip ved {each}."
        body = (
            "Mærk dit hjerteslag ét sted i kroppen, og hold din opmærksomhed der.\n\n"
            "Sid stille, træk vejret normalt, og spænd ikke i musklerne. Mærk ikke "
            "efter din puls med fingrene."
        )
    pages = [
        f"{intro}\n\nBippene kommer altid {per}. De bliver aldrig hurtigere eller "
        "langsommere.",
        "Brug scroll-hjulet på musen med din dominante hånd.\n\n"
        f"Når du ruller på hjulet, flytter hvert bip sig lidt tidligere eller "
        f"senere {within}.",
        "Når du ruller på hjulet, hører du én pause mellem to bip blive længere "
        "eller kortere. Derefter falder rytmen til ro igen på den nye position.",
        f"Bliv ved med at justere, indtil bippet lander på {feel}. Udforsk frit, "
        "begge veje, så meget du vil.\n\n"
        "Når de passer sammen, så tryk på MELLEMRUM med den anden hånd.",
    ]
    if showDial:
        pages.append(
            "På skærmen viser en viser på en cirkel, hvor langt du har rullet "
            "hjulet. Den lyser op ved hvert bip.\n\n"
            f"Den viser ikke, {where}. Gå efter det, du mærker, og hold blikket "
            "på krydset i midten."
        )
    else:
        pages.append("Hold blikket på krydset i midten under hver runde.")
    pages += [
        "Efter hver runde angiver du, hvor sikker du er på, at bippene passede "
        f"med {match}, fra {low} (slet ikke) til {high} (ekstremt).",
        body,
    ]
    texts["instructions"] = pages

    texts["tutorialIntro"] = "Lad os øve med hjulet. Du hører nu bippene."
    texts["tutorialListen"] = f"Lyt: ét bip ved {each}."
    texts["tutorialLater"] = (
        "Rul nu hjulet et par hak VÆK fra dig, og lyt: hvert bip flytter sig "
        f"senere {within}."
    )
    texts["tutorialEarlier"] = (
        "Rul nu hjulet et par hak IND mod dig, og lyt: hvert bip flytter sig "
        f"tidligere {within}."
    )
    texts["tutorialFree"] = (
        f"Prøv at finde den position, hvor bippet falder på {feel}.\n\n"
        "Tryk på MELLEMRUM, når det gør."
    )
    texts["tutorialEnd"] = (
        "Hvis du har spørgsmål, så spørg forsøgslederen nu.\n\n"
        "Ellers tryk på MELLEMRUM for at fortsætte."
    )

    return texts
