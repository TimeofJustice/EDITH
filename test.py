import os
import re
from difflib import SequenceMatcher
from PIL import Image, ImageDraw, ImageFilter
import enchant


def createimage():
    im1 = Image.open('data/pics/common.png')
    im2 = Image.open('data/pics/a_9bbb4144c63bd05e6e1b3cb229cfbdc9.gif')
    mask_im = Image.open('data/pics/mask.jpg')

    im2 = im2.resize((45, 45))
    mask_im = mask_im.resize((45, 45))
    back_im = im1.copy()
    back_im.paste(im2, (105, 68), mask_im)
    back_im.save('data/pics/test.png', quality=95)


def equals_title(input):
    title_eng = "Pirates of the Caribbean: The Curse of the Black Pearl"
    title_ger = "Fluch der Karibik"

    perc_eng = similar(input, title_eng)
    perc_ger = similar(input, title_ger)

    print(f"Percentage: {max(perc_ger, perc_eng)}\n"
          f"Title (English): {title_eng}\n"
          f"Title (German): {title_ger}\n")


def similar(a, b):
    return SequenceMatcher(None, a.lower().replace(" ", ""), b.lower().replace(" ", "")).ratio()


def get_level(xp, base_xp=1000, xp_multiplier=1.1):
    """
    Gibt das Level und die benötigte XP bis zum nächsten Level zurück, basierend auf einer gegebenen Menge an XP.

    :param xp: Die Menge an XP, für die das Level berechnet werden soll.
    :param base_xp: Die Basis-XP, die für das Erreichen des Level 1 benötigt werden. Standardmäßig 1000.
    :param xp_multiplier: Der Multiplikator, der bestimmt, wie viel XP für jedes Level benötigt werden. Standardmäßig 1.1.
    :return: Ein Tupel aus dem aktuellen Level und der benötigten XP bis zum nächsten Level.
    """
    # Initialisiere das Level auf 0
    level = 0

    # Schleife durch jedes Level, beginnend bei Level 1
    while xp >= base_xp:
        # Erhöhe das Level um 1
        level += 1

        # Subtrahiere die Basis-XP des aktuellen Levels von der gegebenen XP-Menge
        xp -= base_xp

        # Berechne die benötigte XP für das nächste Level
        base_xp = round(base_xp * xp_multiplier)

    # Berechne die benötigte XP bis zum nächsten Level
    next_level_xp = base_xp - xp

    # Gib das Level und die benötigte XP bis zum nächsten Level zurück
    return level, next_level_xp


def get_valid_word_percentage(string, dictionaries=None):
    """
    Ermittelt den Prozentsatz, zu dem ein String aus tatsächlich existierenden Wörtern besteht, unter Verwendung
    einer oder mehrerer Wörterbücher.

    :param string: Der zu überprüfende String.
    :param dictionaries: Eine Liste von Wörterbüchern.
    :return: Der Prozentsatz, zu dem der String aus tatsächlich existierenden Wörtern besteht.
    """
    if dictionaries is None:
        # Wenn keine Wörterbücher angegeben sind, verwende alle verfügbaren Wörterbücher
        dictionaries = enchant.list_languages()

    # Erstelle eine Liste von Wörterbuch-Objekten
    dictionary_objects = [enchant.Dict(d) for d in dictionaries]

    # Entferne alle Satzzeichen und Zahlen aus dem String
    cleaned_string = re.sub(r'[^\w\s]', '', string)

    # Teile den String in Wörter auf
    words = cleaned_string.split()

    # Zähle, wie viele Wörter in den Wörterbüchern enthalten sind
    valid_word_count = sum(1 for word in words if any(d.check(word.lower()) for d in dictionary_objects))

    # Berechne den Prozentsatz der gültigen Wörter
    valid_word_percentage = valid_word_count / len(words) * 100

    # Gib den Prozentsatz zurück
    return valid_word_percentage


print(get_valid_word_percentage("Hallo"))

for element in None:
    print(element)
