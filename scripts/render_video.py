"""Render the LineagePulse demo video using PIL + ffmpeg.

Generates a 90-second screencast-style video with static scenes (one
PNG per scene) and uses ffmpeg to control duration. Much faster than
frame-by-frame animation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "docs" / "video_assets"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR = OUT_DIR / "frames"
FRAMES_DIR.mkdir(exist_ok=True)

W, H = 1280, 720
FPS = 24

# Color palette
BG = (15, 23, 42)
FG = (248, 250, 252)
ACCENT = (56, 189, 248)
DANGER = (239, 68, 68)
WARN = (251, 191, 36)
GOOD = (34, 197, 94)
MUTED = (100, 116, 139)
TERMINAL_BG = (2, 6, 23)
TERMINAL_FG = (226, 232, 240)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
TITLE_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 72)
SUBTITLE_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 36)
BULLET_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 30)
CODE_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono.ttf", 22)
CODE_FONT_SMALL = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono.ttf", 20)
SMALL_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 24)


def draw_text_centered(draw, text, font, y, fill=FG):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    x = (W - w) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return y + font.size + 20


def draw_text_wrapped(draw, text, font, x, y, max_w, fill=FG, line_spacing=8):
    words = text.split(" ")
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_w and current:
            lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)
    for i, line in enumerate(lines):
        draw.text((x, y + i * (font.size + line_spacing)), line, font=font, fill=fill)
    return y + len(lines) * (font.size + line_spacing)


def render_title_card(scene: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    # Accent bar
    draw.rectangle([(W // 2 - 150, 180), (W // 2 + 150, 195)], fill=ACCENT)
    # Title
    y = draw_text_centered(draw, scene["title"], TITLE_FONT, 220, ACCENT)
    if "subtitle" in scene:
        y += 20
        for line in scene["subtitle"].split("\n"):
            y = draw_text_centered(draw, line, SUBTITLE_FONT, y, FG)
            y += 20
    if "footer" in scene:
        draw_text_centered(draw, scene["footer"], SMALL_FONT, 620, MUTED)
    return img


def render_bullets_card(scene: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_text_centered(draw, scene["title"], TITLE_FONT, 100, ACCENT)
    y = 240
    for bullet in scene["bullets"]:
        # Strip leading ✓ if present so we control the icon
        clean = bullet.lstrip("✓").lstrip()
        is_results = "result" in scene.get("title", "").lower() or "win" in scene.get("title", "").lower()
        icon = "✓" if is_results else "→"
        icon_color = GOOD if is_results else ACCENT
        draw.text((140, y), icon, font=SUBTITLE_FONT, fill=icon_color)
        y = draw_text_wrapped(draw, clean, BULLET_FONT, 220, y + 6, W - 360, fill=FG)
        y += 25
    return img


def render_terminal_card(scene: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_text_centered(draw, scene["title"], SUBTITLE_FONT, 30, ACCENT)
    # Terminal window
    pad = 40
    term_x = pad
    term_y = 90
    term_w = W - 2 * pad
    term_h = H - 130
    draw.rounded_rectangle(
        [(term_x, term_y), (term_x + term_w, term_y + term_h)],
        radius=10,
        fill=TERMINAL_BG,
    )
    # Title bar
    draw.rectangle([(term_x, term_y), (term_x + term_w, term_y + 36)], fill=(30, 41, 59))
    for i, color in enumerate([(248, 113, 113), (251, 191, 36), (34, 197, 94)]):
        cx = term_x + 20 + i * 20
        cy = term_y + 18
        draw.ellipse([(cx - 6, cy - 6), (cx + 6, cy + 6)], fill=color)
    draw.text((term_x + 100, term_y + 8), "demo_runbook.py", font=CODE_FONT_SMALL, fill=MUTED)

    # Lines
    y = term_y + 60
    for line in scene["terminal_lines"]:
        color = TERMINAL_FG
        if line.startswith("$"):
            color = GOOD
        elif "→" in line and "Synthesized" in line:
            color = ACCENT
        elif line.startswith("  ✓"):
            color = GOOD
        elif line.startswith("──"):
            color = WARN
        elif "CRITICAL" in line:
            color = DANGER
        draw.text((term_x + 24, y), line, font=CODE_FONT, fill=color)
        y += 36
    return img


def render_slack_card(scene: dict) -> Image.Image:
    import re

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_text_centered(draw, scene["title"], SUBTITLE_FONT, 30, ACCENT)

    pad = 60
    card_x = pad
    card_y = 100
    card_w = W - 2 * pad
    card_h = H - 140
    draw.rounded_rectangle(
        [(card_x, card_y), (card_x + card_w, card_y + card_h)],
        radius=10,
        fill=(40, 42, 54),
        outline=(79, 84, 105),
        width=2,
    )
    # Avatar
    draw.ellipse([(card_x + 20, card_y + 20), (card_x + 64, card_y + 64)], fill=ACCENT)
    draw.text((card_x + 28, card_y + 26), "LP", font=SUBTITLE_FONT, fill=BG)
    draw.text((card_x + 80, card_y + 22), "LineagePulse", font=SUBTITLE_FONT, fill=FG)
    name_w = draw.textlength("LineagePulse", font=SUBTITLE_FONT)
    draw.text((card_x + 80 + int(name_w) + 16, card_y + 30), "APP", font=CODE_FONT_SMALL, fill=MUTED)

    bold = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", SMALL_FONT.size)
    regular = SMALL_FONT

    def draw_inline_slack(x, y, text, fill, base_font=regular, bold_font=bold):
        """Render slack mrkdwn: *bold* segments."""
        # Slack uses *bold* (single asterisk) and ~strike~ and `code`
        # Split by *...*
        parts = re.split(r"(\*[^*]+\*)", text)
        cx = x
        for part in parts:
            if part.startswith("*") and part.endswith("*") and len(part) > 2:
                draw.text((cx, y), part[1:-1], font=bold_font, fill=fill)
                cx += int(draw.textlength(part[1:-1], font=bold_font))
            elif part:
                draw.text((cx, y), part, font=base_font, fill=fill)
                cx += int(draw.textlength(part, font=base_font))
        return cx

    y = card_y + 100
    for block in scene.get("slack_blocks", []):
        btype = block.get("type")
        text = block.get("text", "")
        if btype == "header":
            draw.text((card_x + 24, y), text, font=SUBTITLE_FONT, fill=DANGER)
            y += 56
        elif btype == "summary":
            y = draw_text_wrapped(draw, text, SMALL_FONT, card_x + 24, y, card_w - 48, fill=FG)
            y += 18
        elif btype == "fields":
            # Render each line separately for proper line breaks
            for line in text.split("\n"):
                draw_inline_slack(card_x + 24, y, line, FG)
                y += SMALL_FONT.size + 6
            y += 8
        elif btype in ("root_cause", "fix"):
            for line in text.split("\n"):
                draw_inline_slack(card_x + 24, y, line, FG)
                y += SMALL_FONT.size + 6
            y += 8
        elif btype == "context":
            draw.text((card_x + 24, y), text, font=SMALL_FONT, fill=MUTED)
            y += 30
    return img


def render_doc_card(scene: dict) -> Image.Image:
    import re

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_text_centered(draw, scene["title"], SUBTITLE_FONT, 30, ACCENT)

    pad = 60
    card_x = pad
    card_y = 100
    card_w = W - 2 * pad
    card_h = H - 140
    draw.rounded_rectangle(
        [(card_x, card_y), (card_x + card_w, card_y + card_h)],
        radius=10,
        fill=(255, 255, 255),
    )
    draw.rectangle([(card_x, card_y), (card_x + 5, card_y + card_h)], fill=ACCENT)

    def draw_inline(x, y, text, font, fill):
        """Render text with **bold** segments."""
        # Split by **...** segments
        parts = re.split(r"(\*\*[^*]+\*\*)", text)
        cx = x
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                # Bold
                f = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono-Bold.ttf", font.size)
                draw.text((cx, y), part[2:-2], font=f, fill=fill)
                cx += int(draw.textlength(part[2:-2], font=f))
            elif part:
                draw.text((cx, y), part, font=font, fill=fill)
                cx += int(draw.textlength(part, font=font))
        return cx

    y = card_y + 24
    for line in scene.get("document_body", []):
        if line.startswith("# "):
            draw.text((card_x + 30, y), line[2:], font=SUBTITLE_FONT, fill=(15, 23, 42))
            y += 55
        elif line.startswith("## "):
            y += 12
            draw.text((card_x + 30, y), line[3:], font=BULLET_FONT, fill=ACCENT)
            y += 45
        elif line.startswith("- "):
            draw_inline(card_x + 30, y, line, CODE_FONT, (51, 65, 85))
            y += 32
        elif line.strip() == "":
            y += 12
        else:
            draw_inline(card_x + 30, y, line, CODE_FONT, (51, 65, 85))
            y += 32
    return img


def render_scene(scene: dict) -> Image.Image:
    stype = scene.get("scene")
    if stype in ("title", "end"):
        return render_title_card(scene)
    if stype in ("problem", "solution", "architecture", "results"):
        return render_bullets_card(scene)
    if stype == "demo_1":
        return render_terminal_card(scene)
    if stype == "demo_slack":
        return render_slack_card(scene)
    if stype == "demo_doc":
        return render_doc_card(scene)
    return Image.new("RGB", (W, H), BG)


def main() -> int:
    scenes_path = OUT_DIR / "scenes.json"
    scenes = json.loads(scenes_path.read_text())

    pngs: list[Path] = []
    durations: list[float] = []
    for sidx, scene in enumerate(scenes):
        img = render_scene(scene)
        path = FRAMES_DIR / f"scene_{sidx:02d}.png"
        img.save(path, "PNG", optimize=True)
        pngs.append(path)
        durations.append(scene["duration"])
        print(f"  ✓ scene {sidx} ({scene['scene']}): {scene['duration']}s")

    # Write concat list
    list_path = OUT_DIR / "concat.txt"
    lines = []
    for p, d in zip(pngs, durations):
        lines.append(f"file '{p}'")
        lines.append(f"duration {d}")
    # Last entry must be repeated for ffmpeg concat demuxer
    lines.append(f"file '{pngs[-1]}'")
    list_path.write_text("\n".join(lines) + "\n")

    out_mp4 = REPO / "docs" / "lineagepulse-demo.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "23",
        "-r", str(FPS),
        str(out_mp4),
    ]
    print("→ running ffmpeg…")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FFMPEG STDERR:")
        print(r.stderr[-2000:])
        return 1
    print(f"  ✓ wrote {out_mp4}")
    print(f"  size: {out_mp4.stat().st_size / 1024:.1f} KB")
    # Get duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(out_mp4)],
        capture_output=True, text=True,
    )
    print(f"  duration: {probe.stdout.strip()}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
