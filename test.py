from difflib import SequenceMatcher

from PIL import Image, ImageDraw, ImageFilter


def createimage():
    im1 = Image.open('data/pics/common.png')
    im2 = Image.open('data/pics/a_9bbb4144c63bd05e6e1b3cb229cfbdc9.gif')
    mask_im = Image.open('data/pics/mask.jpg')

    im2 = im2.resize((45, 45))
    mask_im = mask_im.resize((45, 45))
    back_im = im1.copy()
    back_im.paste(im2, (105, 68), mask_im)
    back_im.save('data/pics/test.png', quality=95)

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def equals_title(input):
    title_eng = "Pirates of the Caribbean: The Curse of the Black Pearl"
    title_ger = "Fluch der Karibik"

    perc_eng = similar(input, title_eng)
    perc_ger = similar(input, title_ger)

    print(f"Percentage: {max(perc_ger, perc_eng)}\n"
          f"Title (English): {title_eng}\n"
          f"Title (German): {title_ger}\n")


equals_title(input("Title:\n"))
