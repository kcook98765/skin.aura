#!/usr/bin/env python3
"""Reproduce simple Aura title/fallback artwork. These images are not screenshots.

New geometric/typographic composition: kcook98765 Aura continuation, CC BY-NC-SA
4.0, like the skin. Uses bundled Apache-2.0 Roboto Condensed, without altering it.
Pillow is a development-only dependency; generated images alone enter the ZIP.
"""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]


def background(size, phase=0):
    width, height = size
    image = Image.new('RGB', size)
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            glow = max(0, 1 - math.hypot(x / width - .25 - phase / 35, y / height - .6))
            pixels[x, y] = (int(14 + 12 * glow), int(18 + 22 * glow), int(28 + 35 * glow))
    return image


def title(path, size):
    image = background(size)
    draw = ImageDraw.Draw(image)
    width, height = size
    main = ImageFont.truetype(str(ROOT / 'fonts/RobotoCondensed-Light.ttf'), int(height * .25))
    small = ImageFont.truetype(str(ROOT / 'fonts/RobotoCondensed-Regular.ttf'), int(height * .042))
    draw.text((width / 2, height * .44), 'Aura', anchor='mm', font=main, fill='#f6f7fb')
    draw.text((width / 2, height * .65), 'OMEGA  |  2.1.0 ALPHA', anchor='mm', font=small, fill='#a6c4dd')
    image.save(ROOT / path, **({'quality': 95, 'subsampling': 0} if path.endswith('.jpg') else {}))


if __name__ == '__main__':
    title('icon.png', (512, 512))
    title('fanart.jpg', (1920, 1080))
    for index in range(10):
        image = background((500, 500), index)
        draw = ImageDraw.Draw(image)
        for offset in range(4):
            start = 40 + offset * 35
            draw.rounded_rectangle((start, start, 500 - start, 500 - start), 18,
                                   outline=(44 + index * 3, 70 + offset * 4, 94 + index * 2), width=3)
        image.save(ROOT / f'extras/albumbacks/{index}.jpg', quality=95, subsampling=0)
