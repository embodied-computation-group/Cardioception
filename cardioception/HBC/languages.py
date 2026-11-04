# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University
from typing import Dict, List, Union


def english() -> Dict[str, Union[str, List[str]]]:
    """Create the text dictionary with instruction in English

    Returns
    -------
    texts : dict
        The texts presented during the task and the tutorial. The `"labelsRating"`
        entry holds the two labels of the confidence rating scale.

    """
    texts: Dict[str, Union[str, List[str]]] = dict()

    # Confidence rating scale
    texts["labelsRating"] = ["Guess", "Certain"]

    # Task instructions
    texts["Rest"] = "Please sit quietly until the next session"
    texts["Count"] = (
        "After you hear START, try to count your heartbeats"
        " by concentrating on your body feelings."
        " Stop counting when you hear STOP"
    )
    texts["Training"] = (
        "After you hear START, try to count your heartbeats"
        " by concentrating on your body feelings"
        " Stop counting when you hear STOP"
    )
    texts["nCount"] = (
        "How many heartbeats did you count?"
        " Write a number and press ENTER to validate."
    )
    texts["confidence"] = (
        "How confident are you about your count?"
        "Use the RIGHT/LEFT keys to select and the DOWN key to confirm"
    )

    # Tutorial instructions
    texts["Tutorial1"] = (
        "During this experiment, we will ask you to silently"
        " count your heartbeats for different intervals of time."
    )
    texts["Tutorial2"] = (
        'When you see this "heart" icon, you will silently count your'
        " heartbeats by focusing on your body sensations."
    )
    texts["Tutorial3"] = (
        'Sometime, you will also encounter this "rest" icon.'
        " In this case your task will just be to sit quietly until the next"
        " session."
    )
    texts["Tutorial4"] = (
        "The beginning and the end of the task will be signalled when you hear"
        " the words 'START'' and 'STOP'. While counting your heartbeats, you"
        " may close your eyes if you find that helpful. Please keep your hand"
        " still during the counting period, to avoid interfering with"
        " the heartbeat recording."
    )
    texts["Tutorial5"] = (
        "After the counting part of the task, you will be asked to report the"
        " exact number of heartbeats you felt during the interval between"
        " 'START' and 'STOP'. Please do not try to estimate the number of"
        " heartbeats, but instead only report the heartbeats you actually felt"
        " during the interval. You will input your response using the number"
        " pad and press return when done. You can also correct your response"
        " using backspace."
    )
    texts["Tutorial6"] = (
        "Once you have made your response, you will estimate your subjective"
        " feeling of confidence in how accurate your count was"
        " for that interval. A large number here means that you are totally"
        " certain you counted the exact number of heartbeats that occured,"
        " and a small number means that you are totally uncertain or felt that"
        " you were guessing about the"
        " number of heartbeats. You should use the RIGHT and LEFT"
        " key to select your response and the DOWN key to confirm."
    )
    texts["Tutorial7"] = (
        "Before the main task begins there is a short resting period of"
        " several minutes, during which we will calibrate the heartbeat"
        " recording. During this period, please sit quietly with your"
        " hands still to avoid interfering with the calibration."
        " Afterwards, the counting task will begin, and will take about"
        " 6 minutes in total."
    )
    texts["Tutorial8"] = (
        "You will now complete a short practice task."
        " Please ask the experimenter if you have any questions before"
        " continuing to the main experiment."
    )
    texts["Tutorial9"] = (
        "Good job! If you have any question, ask the experimenter now,"
        " otherwise press SPACE to continue to the experiment."
    )

    return texts


def german() -> Dict[str, Union[str, List[str]]]:
    """Create the text dictionary with instruction in German

    The participant is addressed with the formal "Sie" throughout. The words
    START and STOP are kept as they are, because they refer to the recorded
    start and stop sounds played by the task.

    Returns
    -------
    texts : dict
        The texts presented during the task and the tutorial. The `"labelsRating"`
        entry holds the two labels of the confidence rating scale.

    """
    texts: Dict[str, Union[str, List[str]]] = dict()

    # Confidence rating scale
    texts["labelsRating"] = ["Geraten", "Sicher"]

    # Task instructions
    texts["Rest"] = "Bitte sitzen Sie ruhig bis zum nächsten Abschnitt"
    texts["Count"] = (
        "Wenn Sie START hören, versuchen Sie, Ihre Herzschläge zu zählen,"
        " indem Sie sich auf Ihre Körperempfindungen konzentrieren."
        " Hören Sie auf zu zählen, wenn Sie STOP hören"
    )
    texts["Training"] = (
        "Wenn Sie START hören, versuchen Sie, Ihre Herzschläge zu zählen,"
        " indem Sie sich auf Ihre Körperempfindungen konzentrieren."
        " Hören Sie auf zu zählen, wenn Sie STOP hören"
    )
    texts["nCount"] = (
        "Wie viele Herzschläge haben Sie gezählt?"
        " Geben Sie eine Zahl ein und bestätigen Sie mit ENTER."
    )
    texts["confidence"] = (
        "Wie sicher sind Sie sich bei Ihrer Zählung?"
        " Wählen Sie mit den Tasten RECHTS/LINKS aus und bestätigen Sie mit"
        " der Taste NACH UNTEN"
    )

    # Tutorial instructions
    texts["Tutorial1"] = (
        "In diesem Experiment bitten wir Sie, Ihre Herzschläge über"
        " unterschiedlich lange Zeitabschnitte still für sich zu zählen."
    )
    texts["Tutorial2"] = (
        'Wenn Sie dieses "Herz"-Symbol sehen, zählen Sie still Ihre'
        " Herzschläge, indem Sie sich auf Ihre Körperempfindungen konzentrieren."
    )
    texts["Tutorial3"] = (
        'Manchmal sehen Sie auch dieses "Ruhe"-Symbol.'
        " In diesem Fall besteht Ihre Aufgabe nur darin, bis zum nächsten"
        " Abschnitt ruhig sitzen zu bleiben."
    )
    texts["Tutorial4"] = (
        "Beginn und Ende jedes Zählabschnitts werden durch die Wörter 'START'"
        " und 'STOP' angekündigt. Während Sie Ihre Herzschläge zählen, können"
        " Sie die Augen schließen, wenn Ihnen das hilft. Bitte halten Sie Ihre"
        " Hand während des Zählens still, damit die Aufzeichnung des"
        " Herzschlags nicht gestört wird."
    )
    texts["Tutorial5"] = (
        "Nach dem Zählen werden Sie gebeten, die genaue Anzahl der Herzschläge"
        " anzugeben, die Sie zwischen 'START' und 'STOP' gespürt haben. Bitte"
        " schätzen Sie die Anzahl nicht, sondern geben Sie nur die Herzschläge"
        " an, die Sie in diesem Zeitraum tatsächlich gespürt haben. Geben Sie"
        " Ihre Antwort über den Ziffernblock ein und drücken Sie anschließend"
        " die Eingabetaste. Mit der Rücktaste können Sie Ihre Antwort"
        " korrigieren."
    )
    texts["Tutorial6"] = (
        "Nach Ihrer Antwort schätzen Sie ein, wie sicher Sie sich sind, dass"
        " Ihre Zählung für diesen Abschnitt genau war. Ein hoher Wert bedeutet,"
        " dass Sie sich vollkommen sicher sind, genau die Anzahl der"
        " tatsächlichen Herzschläge gezählt zu haben. Ein niedriger Wert"
        " bedeutet, dass Sie sich vollkommen unsicher sind oder das Gefühl"
        " hatten, die Anzahl der Herzschläge zu raten. Wählen Sie Ihre Antwort"
        " mit den Tasten RECHTS und LINKS aus und bestätigen Sie mit der Taste"
        " NACH UNTEN."
    )
    texts["Tutorial7"] = (
        "Vor Beginn der Hauptaufgabe gibt es eine kurze Ruhephase von einigen"
        " Minuten, in der wir die Aufzeichnung des Herzschlags kalibrieren."
        " Bitte sitzen Sie in dieser Zeit ruhig und halten Sie Ihre Hände"
        " still, damit die Kalibrierung nicht gestört wird. Danach beginnt die"
        " Zählaufgabe, die insgesamt etwa 6 Minuten dauert."
    )
    texts["Tutorial8"] = (
        "Sie absolvieren nun eine kurze Übungsaufgabe."
        " Wenn Sie Fragen haben, wenden Sie sich bitte an die Versuchsleitung,"
        " bevor Sie mit dem Hauptexperiment fortfahren."
    )
    texts["Tutorial9"] = (
        "Gut gemacht! Wenn Sie Fragen haben, wenden Sie sich bitte jetzt an die"
        " Versuchsleitung. Andernfalls drücken Sie die LEERTASTE, um mit dem"
        " Experiment fortzufahren."
    )

    return texts
