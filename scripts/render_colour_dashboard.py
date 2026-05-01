from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path(__file__).resolve().parent / "tmp"
OUT_PATH = OUT_DIR / "sidecar_colour_dashboard.png"
WIDTH = 800
HEIGHT = 480


PANEL_PALETTE = [
    (0, 0, 0),        # black
    (255, 255, 255),  # white
    (255, 0, 0),      # red
    (255, 255, 0),    # yellow
    (0, 0, 255),      # blue
    (0, 255, 0),      # green
    (255, 128, 0),    # orange
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, fill=(0, 0, 0), bold=False) -> None:
    draw.text(xy, value, font=font(size, bold), fill=fill)


def centered_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], value: str, size: int, fill=(0, 0, 0), bold=False) -> None:
    f = font(size, bold)
    bb = draw.textbbox((0, 0), value, font=f)
    x = box[0] + (box[2] - box[0] - (bb[2] - bb[0])) // 2
    y = box[1] + (box[3] - box[1] - (bb[3] - bb[1])) // 2
    draw.text((x, y), value, font=f, fill=fill)


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill, outline=(0, 0, 0), width=2) -> None:
    draw.rounded_rectangle(box, radius=8, fill=fill, outline=outline, width=width)


def icon_home(draw: ImageDraw.ImageDraw, x: int, y: int, fill=(0, 0, 0)) -> None:
    draw.polygon([(x, y + 18), (x + 18, y), (x + 36, y + 18)], fill=fill)
    draw.rectangle((x + 6, y + 18, x + 30, y + 38), fill=fill)
    draw.rectangle((x + 16, y + 25, x + 24, y + 38), fill=(255, 255, 255))


def icon_sun_cloud(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 20, y, x + 58, y + 38), fill=(255, 255, 0), outline=(0, 0, 0), width=2)
    for dx, dy in [(39, -10), (39, 48), (5, 19), (73, 19), (14, -4), (64, -4)]:
        draw.line((x + 39, y + 19, x + dx, y + dy), fill=(0, 0, 0), width=2)
    draw.ellipse((x + 5, y + 28, x + 45, y + 65), fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    draw.ellipse((x + 35, y + 22, x + 82, y + 66), fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    draw.rectangle((x + 16, y + 44, x + 76, y + 67), fill=(255, 255, 255))
    draw.arc((x + 5, y + 28, x + 45, y + 65), 180, 360, fill=(0, 0, 0), width=2)
    draw.arc((x + 35, y + 22, x + 82, y + 66), 180, 360, fill=(0, 0, 0), width=2)
    draw.line((x + 15, y + 66, x + 75, y + 66), fill=(0, 0, 0), width=2)


def icon_bulb(draw: ImageDraw.ImageDraw, x: int, y: int, on=True) -> None:
    fill = (255, 255, 0) if on else (255, 255, 255)
    draw.ellipse((x + 8, y, x + 42, y + 34), fill=fill, outline=(0, 0, 0), width=2)
    draw.rectangle((x + 18, y + 33, x + 32, y + 47), fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    draw.line((x + 14, y + 50, x + 36, y + 50), fill=(0, 0, 0), width=2)
    if on:
        for x1, y1, x2, y2 in [
            (x + 25, y - 8, x + 25, y - 18),
            (x + 2, y + 14, x - 8, y + 10),
            (x + 48, y + 14, x + 58, y + 10),
        ]:
            draw.line((x1, y1, x2, y2), fill=(0, 0, 0), width=2)


def icon_drop(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 9, y + 24, x + 39, y + 54), fill=(0, 0, 255), outline=(0, 0, 0), width=2)
    draw.polygon([(x + 24, y), (x + 9, y + 34), (x + 39, y + 34)], fill=(0, 0, 255), outline=(0, 0, 0))


def icon_lock(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.arc((x + 8, y, x + 42, y + 36), 180, 360, fill=(0, 0, 0), width=5)
    draw.rectangle((x + 5, y + 25, x + 45, y + 58), fill=(0, 0, 0))
    draw.ellipse((x + 22, y + 36, x + 30, y + 44), fill=(255, 255, 255))


def icon_thermo(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.rounded_rectangle((x + 18, y, x + 32, y + 42), radius=7, fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    draw.ellipse((x + 10, y + 34, x + 40, y + 64), fill=(255, 0, 0), outline=(0, 0, 0), width=2)
    draw.rectangle((x + 21, y + 14, x + 29, y + 48), fill=(255, 0, 0))


def metric(draw: ImageDraw.ImageDraw, box, title, value, detail, fill, icon_fn) -> None:
    card(draw, box, fill=fill)
    icon_fn(draw, box[0] + 14, box[1] + 18)
    text(draw, (box[0] + 90, box[1] + 16), title, 16, bold=True)
    text(draw, (box[0] + 90, box[1] + 43), value, 27, bold=True)
    text(draw, (box[0] + 90, box[1] + 78), detail, 13)


def control(draw: ImageDraw.ImageDraw, box, title, value, fill, icon_fn) -> None:
    card(draw, box, fill=fill)
    centered_text(draw, (box[0], box[1] + 8, box[2], box[1] + 32), title, 15, bold=True)
    icon_fn(draw, box[0] + 38, box[1] + 40)
    centered_text(draw, (box[0], box[3] - 30, box[2], box[3] - 8), value, 15)


def build() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), (250, 248, 239))
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, WIDTH, 54), fill=(255, 255, 255))
    icon_home(draw, 24, 10)
    text(draw, (74, 16), "Home Assistant", 24, bold=True)
    text(draw, (626, 6), "10:30", 40, bold=True)
    text(draw, (654, 40), "Fri, 24 May 2024", 13)
    draw.line((22, 56, 778, 56), fill=(0, 0, 0), width=2)

    metric(draw, (24, 76, 212, 174), "Weather", "24.5", "Partly cloudy", (255, 255, 210), icon_sun_cloud)
    metric(draw, (226, 76, 384, 174), "Humidity", "48%", "Living room", (210, 230, 255), icon_drop)
    metric(draw, (398, 76, 556, 174), "Thermostat", "22.0 C", "Heating", (255, 220, 205), icon_thermo)
    metric(draw, (570, 76, 776, 174), "Front door", "Locked", "Nuki secure", (220, 255, 220), icon_lock)

    controls = [
        ((24, 192, 144, 306), "Living", "On", (255, 245, 180), lambda d, x, y: icon_bulb(d, x, y + 4, True)),
        ((158, 192, 278, 306), "Bedroom", "Off", (235, 235, 235), lambda d, x, y: icon_bulb(d, x, y + 4, False)),
        ((292, 192, 412, 306), "Kitchen", "On", (255, 245, 180), lambda d, x, y: icon_bulb(d, x, y + 4, True)),
        ((426, 192, 546, 306), "Blinds", "Open", (220, 255, 220), lambda d, x, y: centered_text(d, (x - 2, y + 4, x + 52, y + 54), "|||", 34, bold=True)),
        ((560, 192, 680, 306), "Washer", "Done", (210, 230, 255), lambda d, x, y: d.rounded_rectangle((x + 6, y + 4, x + 46, y + 58), radius=4, fill=(255, 255, 255), outline=(0, 0, 0), width=3)),
        ((694, 192, 776, 306), "Sonos", "Idle", (255, 220, 205), lambda d, x, y: centered_text(d, (x, y + 2, x + 48, y + 56), "♪", 34, bold=True)),
    ]
    for args in controls:
        control(draw, *args)

    card(draw, (24, 328, 244, 424), (220, 255, 220))
    text(draw, (44, 344), "People", 18, bold=True)
    text(draw, (44, 374), "David: Home", 22, bold=True)
    text(draw, (44, 400), "Jennifer: Away", 18)

    card(draw, (264, 328, 536, 424), (210, 230, 255))
    text(draw, (284, 344), "Media", 18, bold=True)
    text(draw, (284, 374), "Living Room", 22, bold=True)
    text(draw, (284, 400), "Paused - no active playback", 17)

    card(draw, (556, 328, 776, 424), (255, 245, 180))
    text(draw, (576, 344), "Energy", 18, bold=True)
    for i, h in enumerate([18, 28, 24, 40, 56, 74]):
        x = 590 + i * 26
        draw.rectangle((x, 408 - h, x + 16, 408), fill=(0, 0, 255), outline=(0, 0, 0))
    text(draw, (690, 374), "8.2 kWh", 22, bold=True)

    draw.rectangle((0, 442, WIDTH, 480), fill=(120, 168, 150))
    for i, label in enumerate(["Home", "Rooms", "Lights", "Climate", "Security", "More"]):
        x = 54 + i * 126
        fill = (255, 255, 255) if i == 0 else (0, 0, 0)
        centered_text(draw, (x - 44, 448, x + 44, 474), label, 15, fill=fill, bold=i == 0)

    return img


def remap_to_panel_palette(img: Image.Image) -> Image.Image:
    palette = Image.new("P", (1, 1))
    flat = []
    for rgb in PANEL_PALETTE:
        flat.extend(rgb)
    flat.extend([0, 0, 0] * (256 - len(PANEL_PALETTE)))
    palette.putpalette(flat)
    return img.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = build()
    source.save(OUT_DIR / "sidecar_colour_dashboard_source.png")
    remapped = remap_to_panel_palette(source)
    remapped.save(OUT_PATH, optimize=True)
    colors = remapped.convert("RGB").getcolors(maxcolors=256) or []
    print(f"Wrote {OUT_PATH}")
    print("Palette use:")
    for count, rgb in sorted(colors, reverse=True):
        print(f"  #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}: {count}")


if __name__ == "__main__":
    main()
