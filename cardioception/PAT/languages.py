# Copyright (C) 2020-2026 Micah Allen, Embodied Computation Group, Aarhus University
"""Participant texts for the Phase Adjustment Task.

The instructions follow Hodgetts et al. (2026): turn the dial until the tones
are simultaneous with the heartbeat, explore freely, press space when they
match, then rate confidence from 1 (not at all) to 10 (extremely). Sit still,
breathe normally and do not tense the muscles. In the exteroceptive task a
vibration on the hand takes the place of the heartbeat.
"""

from typing import Any, Dict, Sequence


def english(
    device: str = "keyboard",
    extero: bool = False,
    confScale: Sequence[int] = (1, 10),
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

    Returns
    -------
    texts : dict

    """
    low, high = confScale
    target = "the vibration" if extero else "your heartbeat"

    texts: Dict[str, Any] = {
        "done": "You have completed the task. Thank you for your participation.",
        "textNext": "Press SPACE to continue.",
        "textPracticeStart": "First, a few practice trials.\n\nPress SPACE to start.",
        "textTaskStart": "The main task starts now.\n\nPress SPACE to start.",
        "textNextTrial": "Press SPACE to start the next trial.",
        "textBreaks": "Take a short break.\n\nPress SPACE when you are ready to continue.",
        "Confidence": f"How confident are you that you matched the tones to {target}?",
        "VASlabels": ["Not at all", "Extremely"],
        "tooLate": "Too late",
    }
    if device == "keyboard":
        texts["ratingHelp"] = "LEFT and RIGHT to choose, SPACE to confirm."
    else:
        texts["ratingHelp"] = "Move the mouse to choose, click to confirm."

    if extero:
        intro = (
            "In this task you will feel a short vibration on your hand, and hear a "
            "short tone with each vibration.\n\n"
            "You can move the tones earlier or later by turning the mouse wheel."
        )
        body = "Sit still, breathe normally and do not tense your muscles."
    else:
        intro = (
            "In this task you will hear a short tone with each of your heartbeats.\n\n"
            "You can move the tones earlier or later by turning the mouse wheel."
        )
        body = (
            "Try to feel your heartbeat in one place in your body, and keep your "
            "attention there.\n\n"
            "Sit still, breathe normally and do not tense your muscles. Do not "
            "check your pulse with your fingers."
        )
    texts["instructions"] = [
        intro,
        f"Your goal: turn the wheel until the tones happen at the same time as "
        f"{target}.\n\n"
        "Explore freely. Turn the wheel both ways, as much as you like. When the "
        f"tones and {target} feel at the same time, press SPACE.",
        "After each trial, rate how confident you are that you matched the tones "
        f"to {target}, from {low} (not at all) to {high} (extremely).",
        body,
        "Turn the wheel with your dominant hand, and press SPACE with your other "
        "hand.\n\n"
        "During a trial you will only see a cross on the screen. Keep your eyes on "
        "it.",
    ]

    texts["tutorialDial"] = (
        "Let's try the wheel. You will now hear the tones.\n\n"
        f"Turn the wheel and listen to how the tones move compared to {target}."
    )
    texts["tutorialRunning"] = (
        "Turn the wheel and listen.\n\nPress SPACE when you are done."
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

    Returns
    -------
    texts : dict

    """
    low, high = confScale
    target = "vibrationen" if extero else "dine hjerteslag"

    texts: Dict[str, Any] = {
        "done": "Du har gennemført opgaven. Tak for din deltagelse.",
        "textNext": "Tryk på MELLEMRUM for at fortsætte.",
        "textPracticeStart": (
            "Først kommer et par øvelsesrunder.\n\nTryk på MELLEMRUM for at starte."
        ),
        "textTaskStart": "Nu begynder hovedopgaven.\n\nTryk på MELLEMRUM for at starte.",
        "textNextTrial": "Tryk på MELLEMRUM for at starte næste runde.",
        "textBreaks": (
            "Hold en kort pause.\n\n"
            "Tryk på MELLEMRUM, når du er klar til at fortsætte."
        ),
        "Confidence": (
            f"Hvor sikker er du på, at du fik tonerne til at passe med {target}?"
        ),
        "VASlabels": ["Slet ikke", "Ekstremt"],
        "tooLate": "For langsomt",
    }
    if device == "keyboard":
        texts["ratingHelp"] = (
            "VENSTRE og HØJRE for at vælge, MELLEMRUM for at bekræfte."
        )
    else:
        texts["ratingHelp"] = "Flyt musen for at vælge, klik for at bekræfte."

    if extero:
        intro = (
            "I denne opgave mærker du en kort vibration på hånden og hører en kort "
            "tone ved hver vibration.\n\n"
            "Du kan flytte tonerne tidligere eller senere ved at dreje på musehjulet."
        )
        body = "Sid stille, træk vejret normalt, og spænd ikke i musklerne."
    else:
        intro = (
            "I denne opgave hører du en kort tone ved hvert af dine hjerteslag.\n\n"
            "Du kan flytte tonerne tidligere eller senere ved at dreje på musehjulet."
        )
        body = (
            "Prøv at mærke dit hjerteslag ét sted i kroppen, og hold din "
            "opmærksomhed der.\n\n"
            "Sid stille, træk vejret normalt, og spænd ikke i musklerne. Mærk ikke "
            "efter din puls med fingrene."
        )
    texts["instructions"] = [
        intro,
        f"Dit mål: drej på hjulet, indtil tonerne kommer samtidig med {target}.\n\n"
        "Udforsk frit. Drej hjulet begge veje, så meget du vil. Når tonerne og "
        f"{target} føles samtidige, så tryk på MELLEMRUM.",
        "Efter hver runde angiver du, hvor sikker du er på, at du fik tonerne til "
        f"at passe med {target}, fra {low} (slet ikke) til {high} (ekstremt).",
        body,
        "Drej på hjulet med din dominante hånd, og tryk på MELLEMRUM med den anden "
        "hånd.\n\n"
        "Under en runde ser du kun et kryds på skærmen. Hold blikket på det.",
    ]

    texts["tutorialDial"] = (
        "Lad os prøve hjulet. Du hører nu tonerne.\n\n"
        "Drej på hjulet, og lyt til, hvordan tonerne flytter sig i forhold til "
        f"{target}."
    )
    texts["tutorialRunning"] = (
        "Drej på hjulet, og lyt.\n\nTryk på MELLEMRUM, når du er færdig."
    )
    texts["tutorialEnd"] = (
        "Hvis du har spørgsmål, så spørg forsøgslederen nu.\n\n"
        "Ellers tryk på MELLEMRUM for at fortsætte."
    )

    return texts
