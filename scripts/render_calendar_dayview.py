#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent / "tmp"
OUT_PATH = OUT_DIR / "sidecar_calendar_day_next.png"
SOURCE_PATH = OUT_DIR / "sidecar_calendar_day_source_next.png"
WIDTH = 800
HEIGHT = 480

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
ORANGE = (255, 128, 0)
PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN, ORANGE]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            pass
    return ImageFont.load_default()


def index_for_panel(img: Image.Image) -> Image.Image:
    palette_img = Image.new("P", (1, 1))
    flat = [c for rgb in PANEL_PALETTE for c in rgb]
    palette_img.putpalette(flat + [0] * (768 - len(flat)))
    return img.quantize(palette=palette_img, dither=Image.Dither.NONE)


def render(payload: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    f_title = font(24, bold=True)
    f_day_h = font(15, bold=True)
    f_time = font(16, bold=True)
    f_event = font(16)
    f_loc = font(13)
    f_empty = font(20, bold=True)

    days = payload.get("days", [])
    if not days:
        draw.text((WIDTH // 2, HEIGHT // 2), "No events this week", fill=BLACK, font=f_empty, anchor="mm")
        return img

    row_y = 0

    HEADER_H = 46
    draw.rectangle([(0, 0), (WIDTH, HEADER_H)], fill=BLACK)
    draw.text((WIDTH // 2, HEADER_H // 2), "Week Ahead", fill=WHITE, font=f_title, anchor="mm")
    row_y = HEADER_H + 4

    for day in days:
        day_name = day.get("day_name", "")
        date_str = day.get("date", "")[-5:]
        dt_str = f"{day_name} {date_str}"
        calendars = day.get("calendars", [])

        draw.text((16, row_y + 8), dt_str, fill=BLACK, font=f_day_h, anchor="lm")
        draw.line([(16, row_y + 20), (WIDTH - 16, row_y + 20)], fill=BLACK, width=2)
        row_y += 26

        for cal in calendars:
            cal_name = cal.get("name", "?")
            cal_color = tuple(cal.get("color", [128, 128, 128]))
            cal_events = cal.get("events", [])

            for ev in cal_events:
                start_s = ev.get("start", "")
                end_s = ev.get("end", "")
                all_day = ev.get("all_day", False)
                location = ev.get("location", "")

                if all_day:
                    time_label = "ALL DAY"
                else:
                    try:
                        st = datetime.fromisoformat(start_s.replace("Z", "+00:00"))
                        et = datetime.fromisoformat(end_s.replace("Z", "+00:00"))
                        time_label = f"{st.strftime('%H:%M')}-{et.strftime('%H:%M')}"
                    except (ValueError, TypeError):
                        time_label = ""

                ROW_H = 34
                draw.rectangle([(0, row_y), (14, row_y + ROW_H)], fill=cal_color)

                draw.text((22, row_y + 10), time_label, fill=BLACK, font=f_time, anchor="lm")

                tx = 130
                draw.text((tx, row_y + 8), ev.get("summary", "")[:45], fill=BLACK, font=f_event, anchor="lm")

                cal_pill_w = draw.textlength(cal_name, font=f_loc) + 12
                draw.rounded_rectangle([(tx, row_y + 20), (tx + cal_pill_w, row_y + 30)], 4, fill=cal_color)
                draw.text((tx + 6, row_y + 25), cal_name, fill=WHITE, font=f_loc, anchor="lm")

                if location:
                    lx = tx + cal_pill_w + 12
                    draw.text((lx, row_y + 25), location[:40], fill=(120, 120, 120), font=f_loc, anchor="lm")

                row_y += ROW_H + 3
                if row_y > HEIGHT - 10:
                    break
            if row_y > HEIGHT - 10:
                break
        if row_y > HEIGHT - 10:
            break

    return img


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path, default=None)
    args = parser.parse_args()

    if args.payload:
        p = Path(args.payload)
        with p.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from nango_calendar_fetch import fetch_payload
        payload = fetch_payload()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src = render(payload)
    src.save(str(SOURCE_PATH), "PNG")
    panel = index_for_panel(src)
    panel.save(str(OUT_PATH), "PNG")
    print(f"Source: {SOURCE_PATH}")
    print(f"Panel:  {OUT_PATH}")
    print(f"Size:   {panel.size[0]} x {panel.size[1]}, mode={panel.mode}")


if __name__ == "__main__":
    main()
