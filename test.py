from PIL import Image, ImageDraw, ImageFilter

im1 = Image.open('data/pics/common.png')
im2 = Image.open('data/pics/a_9bbb4144c63bd05e6e1b3cb229cfbdc9.gif')
mask_im = Image.open('data/pics/mask.jpg')

im2 = im2.resize((45, 45))
mask_im = mask_im.resize((45, 45))
back_im = im1.copy()
back_im.paste(im2, (105, 68), mask_im)
back_im.save('data/pics/test.png', quality=95)
