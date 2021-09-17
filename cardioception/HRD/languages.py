# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>


def english(device: str, setup: str, exteroception: bool):
    """Create the text dictionary with instruction in Danish

    Parameters
    ----------
    device : str
    setup : str
    ExteroCondition : str

    Returns
    -------
    texts : dict

    """
    btnext = "press SPACE" if device == "keyboard" else "click the mouse"
    texts = {
        "done": "You have completed the task. Thank you for your participation.",
        "slower": "Slower",
        "faster": "Faster",
        "checkOximeter": "Please make sure the oximeter is correctly clipped to your finger.",
        "stayStill": "Please stay still during the recording",
        "tooLate": "Too late",
        "correctResponse": "Correct",
        "incorrectResponse": "False",
        "VASlabels": ["Guess", "Certain"],
        "textHeartListening": "Listen to your heart",
        "textToneListening": "Listen to the tones",
        "textTaskStart": "The task is now going to start, get ready.",
        "textBreaks": f"Break. You can rest as long as you want. Just {btnext} when you want to resume the task.",
        "textNext": f"Please {btnext} to continue",
        "textWaitTrigger": "Waiting for fMRI trigger...",
        "Decision": {
            "Intero": """Are these beeps faster or slower than your heart?""",
            "Extero": """Are these beeps faster or slower than the previous?""",
        },
        "Confidence": """How confident are you in your choice?""",
    }

    if device == "keyboard":
        texts["responseText"] = "Use DOWN key for slower - UP key for faster."
    elif device == "mouse":
        texts["responseText"] = "Use LEFT button for slower - RIGHT button for faster."

    texts[
        "Tutorial1"
    ] = """During this experiment, we will record your pulse and play beeps based on your heart rate.

You will only be allowed to focus on the internal sensations of your heartbeats, but not to measure your heart rate by any other means (e.g. checking pulse at your wrist or your neck).
        """
    if setup != "fmri":

        texts[
            "pulseTutorial1"
        ] = "Please place the pulse oximeter on your forefinger. Use your non-dominant hand as depicted in this schema."

        texts[
            "pulseTutorial2"
        ] = "If you can feel your heartbeats when you have the pulse oximeter in your forefinger, try to place it on another finger."

        texts[
            "pulseTutorial3"
        ] = "You can test different configurations until you find the finger which provides you with the less sensory input about your heart rate."

        texts[
            "pulseTutorial4"
        ] = "Please enter the number of the finger corresponding to the finger where you decided to place the pulse oximeter."

    texts[
        "Tutorial2"
    ] = "When you see this icon, try to focus on your heartbeat for 5 seconds. Try not to move, as we are recording your pulse in this period"

    moreResp = "UP key" if device == "keyboard" else "RIGHT mouse button"
    lessResp = "DOWN key" if device == "keyboard" else "LEFT mouse button"
    texts[
        "Tutorial3_icon"
    ] = """After this 'heart listening' period, you will see the same icon and hear a series of beeps."""
    texts[
        "Tutorial3_responses"
    ] = f"""As quickly and accurately as possible, you will listen to these beeps and decide if they are faster ({moreResp}) or slower ({lessResp}) than your own heart rate.

The beeps will ALWAYS be slower or faster than your heart. Please guess, even if you are unsure."""

    if exteroception is True:
        texts[
            "Tutorial3bis"
        ] = """For some trials, instead of seeing the heart icon, you will see a listening icon. You will then have to listen to a first set of beeps, instead of your heart."""

        texts[
            "Tutorial3ter"
        ] = f"""After these first beeps, you will see the response icons appear, and a second set of beeps will play.

As quickly and accurately as possible, you will listen to these beeps and decide if they are faster ({moreResp}) or slower ({lessResp}) than the first set of beeps.

The second series of beeps will ALWAYS be slower or faster than the first series. Please guess, even if you are unsure."""

    texts[
        "Tutorial4"
    ] = """Once you have provided your decision, you will also be asked to rate how confident you feel in your decision.

Here, the maximum rating (100) means that you are totally certain in your choice, and the smallest rating (0) means that you felt that you were guessing.

You should use mouse to select your rating"""

    texts[
        "Tutorial5"
    ] = """This sequence will be repeated during the task.

At times the task may be very difficult; the difference between your true heart rate and the presented beeps may be very small.

This means that you should try to use the entire length of the confidence scale to reflect your subjective uncertainty on each trial.

As the task difficulty will change over time, it is rare that you will be totally confident or totally uncertain."""

    texts[
        "Tutorial6"
    ] = """This concludes the tutorial. If you have any questions, please ask the experimenter now.
Otherwise, you can continue to the main task."""

    return texts


def danish(device: str, setup: str, exteroception: bool):
    """Create the text dictionary with instruction in Danish

    Parameters
    ----------
    device : str
    setup : str
    ExteroCondition : str

    Returns
    -------
    texts : dict

    """

    btnext = "tryk på mellemrumstasten" if device == "keyboard" else "click på musen"
    texts = {
        "done": "Du har genemført opgaven. Tak for din deltagalse.",
        "slower": "Langsommere",
        "faster": "Hurtigere",
        "checkOximeter": "Sørg venligst for, at pulsoximeteret sidder rigtigt på din finger.",
        "stayStill": "Sid venglist rogligt under målingen",
        "tooLate": "For langsomt",
        "correctResponse": "Rigtigt",
        "incorrectResponse": "Forkert",
        "VASlabels": ["Gæt", "Helt sikker"],
        "textHeartListening": "Mærk din hjertrytme",
        "textToneListening": "Lyt til tonerne",
        "textTaskStart": "Opgaven begynder nu, gør dig klar.",
        "textBreaks": f"Pause. Du kan tage så lang en pause, som du har brug for. Bare {btnext} når du vil fortsætte opgaven.",
        "textNext": f"Venligst, {btnext} for at fortsætte",
        "textWaitTrigger": "Venter på fMRI-udløseren...",
        "Decision": {
            "Intero": """Er disse bib-lyde hurtigere eller langsommere end dit hjerte?""",
            "Extero": """Er disse bib-lyde hurtigere eller langsommere end den de forrige? """,
        },
        "Confidence": """Hvor sikker er du på dit svar?""",
    }

    if device == "keyboard":
        texts[
            "responseText"
        ] = "Brug NED tasten for langsommere - OP tasten for hurtigere."
    elif device == "mouse":
        texts[
            "responseText"
        ] = "Brug VENSTRE museknap for langsommere - HØJRE museknap for hurtigere."

    texts[
        "Tutorial1"
    ] = """I dette forsøg vil vi registrere din puls og afspille bib-lyde baseret på din hjerterytme.

Du må kun fokusere på din indre følelse af din hjerterytme. Du må altså ikke måle din hjerterytme på andre måder (fx ved at tjekke din puls på dit håndled eller din hals).
        """
    if setup != "fmri":

        texts[
            "pulseTutorial1"
        ] = "Placer venligst puls oximeteret på din pegefinger. Brug din ikke-dominante hånd som beskrevet i dette skema."

        texts[
            "pulseTutorial2"
        ] = "Hvis du kan mærke din hjerterytme, når du har puls oximeteret på din pegefinger, så prøv at placere det på en anden finger."

        texts[
            "pulseTutorial3"
        ] = "Du kan teste forskellige fingre indtil du finder den finger, der giver dig mindst sensorisk indput omkring din hjerterytme."

        texts[
            "pulseTutorial4"
        ] = "Indtast venligt nummeret på den finger, som du besluttede at placere puls oximeteret på."

    texts[
        "Tutorial2"
    ] = "Når du ser dette ikon, forsøg da at fokusere på din hjerterytme i 5 sekunder. Prøv ikke at bevæge dig, da vi registrere din puls i dette tidsrum"

    moreResp = "OP tasten" if device == "keyboard" else "HØJRE mussetast"
    lessResp = "NED tasten" if device == "keyboard" else "VENSTRE mussetast"
    texts[
        "Tutorial3_icon"
    ] = """Efter tidsrummet hvor du har lyttet til dit hjerte, vil du se det samme ikon og høre en række bib-lyde."""
    texts[
        "Tutorial3_responses"
    ] = f"""Det følgende skal du gøre så hurtigt og præcist som muligt: Du vil lytte til disse bib-lyde og beslutte om de er hurtigere ({moreResp}) eller langsommere ({lessResp}) end din egen hjerterytme.

Bib-lydene vil ALTID være langsommere eller hurtigere end dit hjerte. Gæt venligst selvom du er usikker."""

    if exteroception is True:
        texts[
            "Tutorial3bis"
        ] = """I nogle runder vil du se et lytteikon i stedet for et hjerteikon. Her vil du skulle lytte til et sæt af bib-lyde i stedet for dit hjerte."""

        texts[
            "Tutorial3ter"
        ] = f"""Efter dette sæt af bib-lyde vil du se, at svarikonet dukker op, og et andet sæt af bib-lyde vil blive afspillet.

Det følgende skal du gøre så hurtigt og præcist som muligt: Du vil lytte til det sidste sæt af bib-lyde og beslutte om de er hurtigere ({moreResp}) eller langsommere ({lessResp}) end det første sæt af bib-lyde.

Det andet sæt af bib-lyde vil ALTID være langsommere eller hurtigere end det første sæt. Gæt venligst selvom du er usikker."""

    texts[
        "Tutorial4"
    ] = """Når du har svaret, vil du også blive bedt om at angive hvor sikker du er på din beslutning.

Her betyder den højeste score (100) at du er helt sikker på dit valg, og den mindste score (0) betyder, at du følte, at du gættede.

Du skal bruge musen til at vælge en score."""

    texts[
        "Tutorial5"
    ] = """Denne sekvens vil blive gentaget igennem opgaven.

Nogle gange kan opgaven være virkelig svær; forskellen mellem din faktiske hjerterytme og bib-lydene kan være meget små.

Dette betyder, at du skal forsøge at bruge hele skalaens længde til at angive din subjektive usikkerhed i hver runde.

Da opgavens sværhedsgrad ændrer sig over tid, er det sjældent at du vil være totalt sikker eller totalt usikker."""

    texts[
        "Tutorial6"
    ] = """Dette er slutningen på vejledningen. Hvis du har noget spørgsmål, så spørg endelig en forsker nu.
Ellers kan du fortsætte til hovedopgaven."""

    return texts
