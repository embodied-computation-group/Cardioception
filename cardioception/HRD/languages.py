# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University
from typing import Collection, Dict


def english(device: str, setup: str, exteroception: bool) -> Dict[str, Collection[str]]:
    """Create the text dictionary with instruction in Danish

    Parameters
    ----------
    device : str
        Can be `"keyboard"` or `"mouse"`.
    setup : str
        The experimental setup. Can be `"behavioral"` or `"test"`.
    exteroception : bool
        If `True`, the task includes and exteroceptive control condition.

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
    texts[
        "pulseTutorial1"
    ] = "Please place the pulse oximeter on your forefinger. Use your non-dominant hand as depicted in this schema."

    texts[
        "pulseTutorial2"
    ] = "If you can feel your heartbeats when you have the pulse oximeter on your forefinger, try to place it on another finger."

    texts[
        "pulseTutorial3"
    ] = "You can test different configurations until you find the finger which provides you with the least sensory input about your heart rate."

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


def danish(device: str, setup: str, exteroception: bool) -> Dict[str, Collection[str]]:
    """Create the text dictionary with instruction in Danish

    Parameters
    ----------
    device : str
        Can be `"keyboard"` or `"mouse"`.
    setup : str
        The experimental setup. Can be `"behavioral"` or `"test"`.
    exteroception : bool
        If `True`, the task includes and exteroceptive control condition.

    Returns
    -------
    texts : dict

    """

    btnext = "tryk på mellemrumstasten" if device == "keyboard" else "klik på musen"
    texts = {
        "done": "Du har gennemført opgaven. Tak for din deltagelse.",
        "slower": "Langsommere",
        "faster": "Hurtigere",
        "checkOximeter": "Sørg venligst for at pulsoximeteret sidder rigtigt på din finger.",
        "stayStill": "Sid venligst roligt under målingen",
        "tooLate": "For langsomt",
        "correctResponse": "Rigtigt",
        "incorrectResponse": "Forkert",
        "VASlabels": ["Gæt", "Helt sikker"],
        "textHeartListening": "Mærk din hjerterytme",
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
    ] = "Indtast venligt nummeret på den finger som du besluttede at placere puls oximeteret på."

    texts[
        "Tutorial2"
    ] = "Når du ser dette ikon, forsøg da at fokusere på din hjerterytme i 5 sekunder. Prøv ikke at bevæge dig, da vi registrere din puls i dette tidsrum"

    moreResp = "OP tasten" if device == "keyboard" else "HØJRE mussetast"
    lessResp = "NED tasten" if device == "keyboard" else "VENSTRE mussetast"
    texts[
        "Tutorial3_icon"
    ] = """Efter tidsrummet hvor du har forsøgt at mærke dit hjerte, vil du se det samme ikon og høre en række bib-lyde."""
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
    ] = """Dette er slutningen på vejledningen. Hvis du har nogen spørgsmål, så spørg endelig en forsker nu.
Ellers kan du fortsætte til hovedopgaven."""

    return texts


def danish_children(
    device: str, setup: str, exteroception: bool
) -> Dict[str, Collection[str]]:
    """Create the text dictionary with instruction in Danish (simplified version for
    children).

    Parameters
    ----------
    device : str
        Can be `"keyboard"` or `"mouse"`.
    setup : str
        The experimental setup. Can be `"behavioral"` or `"test"`.
    exteroception : bool
        If `True`, the task includes and exteroceptive control condition.

    Returns
    -------
    texts : dict

    """

    btnext = "tryk på mellemrumstasten" if device == "keyboard" else "klik på musen"
    texts = {
        "done": "Du har gennemført opgaven. Tak for din deltagelse.",
        "slower": "Langsommere",
        "faster": "Hurtigere",
        "checkOximeter": "Spørg forskningsassistensen om, hvordan du skal placere fingerklemmen.",
        "stayStill": "Sid venligst roligt under målingen",
        "tooLate": "For langsomt",
        "correctResponse": "Rigtigt",
        "incorrectResponse": "Forkert",
        "VASlabels": ["Slet ikke sikker", "Helt sikker"],
        "textHeartListening": "Mærk din indre puls",
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
    ] = """Instruktion 1
        """
    texts["pulseTutorial1"] = "Udstyr."

    texts["pulseTutorial2"] = ""

    texts["pulseTutorial3"] = ""

    texts[
        "pulseTutorial4"
    ] = "Indtast venligt nummeret på den finger som du besluttede at placere fingerklemmen på."

    texts[
        "Tutorial2"
    ] = "Når du ser dette ikon, forsøg da at fokusere på din indre puls i 5 sekunder. Prøv ikke at bevæge dig, da vi måler din puls i dette tidsrum"

    moreResp = "OP tasten" if device == "keyboard" else "HØJRE mussetast"
    lessResp = "NED tasten" if device == "keyboard" else "VENSTRE mussetast"
    texts[
        "Tutorial3_icon"
    ] = """Efter du har forsøgt at mærke din indre puls, vil du se det samme ikon og høre en række bib-lyde."""
    texts["Tutorial3_responses"] = """Instruktion 2"""

    if exteroception is True:
        texts[
            "Tutorial3bis"
        ] = """I nogle runder vil du se et lytteikon i stedet for et hjerteikon. Her vil du skulle lytte til et sæt af bib-lyde i stedet for dit hjerte."""

        texts[
            "Tutorial3ter"
        ] = f"""Efter dette sæt af bib-lyde vil du se, at svarikonet dukker op, og et andet sæt af bib-lyde vil blive afspillet.

Det følgende skal du gøre så hurtigt og præcist som muligt: Du vil lytte til det sidste sæt af bib-lyde og beslutte om de er hurtigere ({moreResp}) eller langsommere ({lessResp}) end det første sæt af bib-lyde.

Det andet sæt af bib-lyde vil ALTID være langsommere eller hurtigere end det første sæt. Gæt venligst selvom du er usikker."""

    texts["Tutorial4"] = """Instruktion 3"""

    texts["Tutorial5"] = """Instruktion 4"""

    texts[
        "Tutorial6"
    ] = """Dette er slutningen på øve-runden. Hvis du har nogen spørgsmål, så spørg en forsker nu.
Ellers kan du fortsætte til opgaven."""

    return texts


def french(device: str, setup: str, exteroception: bool) -> Dict[str, Collection[str]]:
    """Create the text dictionary with instruction in french

    Parameters
    ----------
    device : str
        Can be `"keyboard"` or `"mouse"`.
    setup : str
        The experimental setup. Can be `"behavioral"` or `"test"`.
    exteroception : bool
        If `True`, the task includes and exteroceptive control condition.

    Returns
    -------
    texts : dict

    """
    btnext = (
        "appuyez sur la barre espace"
        if device == "keyboard"
        else "cliquez sur la souris"
    )
    texts = {
        "done": "Vous avez terminé la tâche. Merci pour votre participation.",
        "slower": "Plus lent",
        "faster": "Plus rapide",
        "checkOximeter": "Assurez-vous que l'oxymètre est bien attaché à votre doigt.",
        "stayStill": "Veuillez ne pas bouger pendant l'enregistrement",
        "tooLate": "Trop tard",
        "correctResponse": "Correct",
        "incorrectResponse": "Faux",
        "VASlabels": ["Incertain", "Tout à fait sûr"],
        "textHeartListening": "Ecoutez votre coeur",
        "textToneListening": "Ecoutez les sons",
        "textTaskStart": "La tâche va débuter, tenez-vous prêt.",
        "textBreaks": f"Pause. Vous pouvez vous reposer aussi longtemps que vous le souhaitez. Simplement {btnext} quand vous désirez rependre la tâche.",
        "textNext": f"S'il vous plaît {btnext} pour continuer",
        "textWaitTrigger": "Attendez pour le déclencheur IRMf...",
        "Decision": {
            "Intero": """Est-ce que ces sons sont plus rapides ou plus lents que votre coeur?""",
            "Extero": """Est-ce que ces sons sont plus rapides ou plus lents que les précédents?""",
        },
        "Confidence": """Etes-vous sûr de votre choix?""",
    }

    if device == "keyboard":
        texts[
            "responseText"
        ] = "Appuyez sur la flèche vers le BAS pour plus lent - vers le HAUT pour plus rapide."
    elif device == "mouse":
        texts[
            "responseText"
        ] = "Appuyez sur le clic GAUCHE pour plus lent - clic DROIT pour plus rapide."

    texts[
        "Tutorial1"
    ] = """Durant cette tâche, nous allons enregistrer vos pulsations et jouer des sons basés sur votre rythme cardiaque.

Vous serez uniquement autorisés à vous concentrer sur vos sensations internes de vos battements cardiaques, mais ne mesurez pas votre rythme cardiaque par d'autres moyens (ex. vérification du pouls au poignet ou au cou).
        """
    texts[
        "pulseTutorial1"
    ] = "Veuillez placer l'oxymètre de pouls sur votre index. Utilisez votre main non-dominante comme illustré sur ce schéma."

    texts[
        "pulseTutorial2"
    ] = "Si vous pouvez sentir vos battements de coeur quand vous portez l'oxymètre de pouls sur votre index, essayez de le placer sur un autre doigt."

    texts[
        "pulseTutorial3"
    ] = "Vous pouvez essayer différentes configurations jusqu'à ce que vous trouviez le doigt qui provoque le moins de sensations de battements cardiaques."

    texts[
        "pulseTutorial4"
    ] = "Veuillez entrer le numéro du doigt correspondant au doigt sur lequel vous avez décidé de placer l'oxymètre de pouls."

    texts[
        "Tutorial2"
    ] = "Quand vous voyez cette icône, essayez de vous concentrer sur vos battements cardiaques durant 5 secondes. Essayez de ne pas bouger, car nous enregistrons votre pouls durant cette période."

    moreResp = "flèche vers le HAUT" if device == "keyboard" else "clic DROIT"
    lessResp = "flèche vers le BAS" if device == "keyboard" else "clic GAUCHE"
    texts[
        "Tutorial3_icon"
    ] = """Après cette période d'écoute du coeur, vous verrez la même icône and entendrez une série de bips."""
    texts[
        "Tutorial3_responses"
    ] = f"""Aussi rapidement et précisément possible, vous écouterez ces bips et déciderez s'ils sont plus rapides ({moreResp}) ou plus lents ({lessResp}) que votre propre rythme cardiaque.

Les bips seront TOUJOURS plus lents ou plus rapides que votre coeur. Veuillez faire une estimation, même si vous n'est pas sûr."""

    if exteroception is True:
        texts[
            "Tutorial3bis"
        ] = """Pour certains essais, au lieu de voir une icône de coeur, vous verrez une icône d'écoute. Vous devrez alors écouter une première série de bips, au lieu de votre coeur."""

        texts[
            "Tutorial3ter"
        ] = f"""Après ce premier bip, vous verrez l'icône de réponse apparaître, et une seconde série de bip sera joué.

Aussi rapidement et précisément possible, vous entendrez ces bips et déciderez s'ils sont plus rapides ({moreResp}) ou plus lents ({lessResp}) que la première série de bips.

La seconde série de bips sera TOUJOURS plus lente ou rapide que la première série. Veuillez faire une estimation, même si vous n'êtes pas sûr."""

    texts[
        "Tutorial4"
    ] = """Une fois que vous avez donné votre réponse, il vous sera également demandé d'estimer votre degré de confiance dans votre réponse.

Ici, le score maximum (100) signifie que vous êtes totalement certain de votre choix, et le score minimum (0) signifie que vous devinez.

Vous devez utiliser la souris pour sélectionner votre score"""

    texts[
        "Tutorial5"
    ] = """Cette séquence sera répétée durant la tâche.

Par moment la tâche peut être très difficile ; la différence entre votre propre rythme cardiaque et les bips présentés peut être très petite.

Cela signifie que vous devez essayer d'utiliser toute la longueur de l'échelle de confiance pour refléter votre incertitude subjective sur chaque essai.

Comme la difficulté de la tâche évolue avec le temps, il est rare que vous soyez totalement confiant ou totalement incertain."""

    texts[
        "Tutorial6"
    ] = """Ceci conclut le tutoriel. Si vous avez des questions, veuillez les poser maintenant à l'expérimentateur.
Sinon, vous pouvez continuer avec la tâche principale."""

    return texts
