from io import BytesIO
from aiogram.types import BufferedInputFile
from PIL import Image, ImageDraw, ImageFont


def build_invite_card(title: str, subtitle: str, lines: list[str]) -> BufferedInputFile:
    width, height = 1080, 1350
    bg_color = (18, 16, 14)      
    accent_color = (218, 178, 106) 
    text_color = (242, 238, 230)
    muted_color = (165, 158, 145)

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Рамка картки
    draw.rounded_rectangle(
        [48, 48, width - 48, height - 48],
        radius=36,
        outline=(75, 63, 42),
        width=2,
    )

    font_title = ImageFont.load_default(size=54)
    font_sub = ImageFont.load_default(size=30)
    font_body = ImageFont.load_default(size=34)

    draw.text((100, 140), title, fill=accent_color, font=font_title)
    draw.text((100, 220), subtitle, fill=muted_color, font=font_sub)

    y = 340
    for line in lines:
        draw.text((100, y), line, fill=text_color, font=font_body)
        y += 72

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return BufferedInputFile(buf.read(), filename="invite_card.png")