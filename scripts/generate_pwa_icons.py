"""Recria os ícones do monograma do projeto, sem baixar imagens externas."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1] / 'static/icons'
root.mkdir(parents=True, exist_ok=True)
for name, size, padding in [('icon-192.png', 192, 0.14), ('icon-512.png', 512, 0.14), ('maskable-512.png', 512, 0.24)]:
    image = Image.new('RGB', (size, size), '#ae452c')
    draw = ImageDraw.Draw(image)
    margin = round(size * padding)
    draw.ellipse((margin, margin, size-margin, size-margin), fill='#fbf8f2')
    inset = round(size * (padding + .045))
    draw.ellipse((inset, inset, size-inset, size-inset), outline='#ae452c', width=max(2, size//100))
    font = ImageFont.load_default(size=round(size * .31))
    draw.text((size/2, size/2), 'm.', fill='#ae452c', font=font, anchor='mm')
    image.save(root / name)
