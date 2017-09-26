from PIL import Image
import random

ascii_char = list(" . ")
wide_chars = "?6$+<"
chars = list("![" + wide_chars)


def get_char(r, g, b, a=256):
	if a == 0:
		return ' '
	length = len(ascii_char)
	gray = int(0.2126 * r + 0.7152 * g + 0.0722 * b)

	unit = (256.0 + 1) / length
	return ascii_char[int(gray / unit)]


def get_txt(img_path):
	select = random.randint(0, len(chars)-1)
	ascii_char[0] = chars[select]
	txt_lis = []
	im = Image.open(img_path)
	bbox = im.getbbox()
	im = im.resize((bbox[2], int(bbox[3]*0.51)), Image.NEAREST)
	bbox = im.getbbox()
	for i in range(bbox[3]):
		for j in range(bbox[2]):
			c = get_char(*im.getpixel((j, i)))
			txt_lis.append(c if c in wide_chars else 2*c)
		txt_lis.append('\n')
	txt = ''.join(txt_lis)
	return txt
