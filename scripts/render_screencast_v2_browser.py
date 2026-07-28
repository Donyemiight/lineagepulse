"""Phase 2: capture browser scenes for the LineagePulse screencast."""

from __future__ import annotations

import io
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "docs" / "screencast"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR = OUT_DIR / "frames_phase2"
FRAMES_DIR.mkdir(exist_ok=True)

W, H = 1280, 720
FPS = 30

LIVE_URL = "https://lineagepulse.onrender.com"
GH_URL = "https://github.com/Donyemiight/lineagepulse"

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
CODE_FONT = Image.open  # we'll only draw on captured images, not generate them

# Browser scenes
BROWSER_SCENES = [
    {
        "name": "open_live_demo",
        "url": LIVE_URL + "/",
        "duration_s": 5,
        "wait_for": 2.5,
        "scroll": [(0, 0), (4, 0)],
    },
    {
        "name": "scroll_home",
        "url": LIVE_URL + "/",
        "duration_s": 4,
        "wait_for": 1.5,
        "scroll": [(0, 0), (3, 250)],
    },
    {
        "name": "navigate_demo",
        "url": LIVE_URL + "/demo",
        "duration_s": 6,
        "wait_for": 2.5,
        "scroll": [(0, 0), (3, 200), (5, 400)],
    },
    {
        "name": "navigate_slack",
        "url": LIVE_URL + "/slack",
        "duration_s": 4,
        "wait_for": 2.0,
        "scroll": [(0, 0)],
    },
    {
        "name": "navigate_document",
        "url": LIVE_URL + "/document",
        "duration_s": 4,
        "wait_for": 2.0,
        "scroll": [(0, 0), (3, 200)],
    },
    {
        "name": "open_github",
        "url": GH_URL,
        "duration_s": 6,
        "wait_for": 4.0,
        "scroll": [(0, 0), (3, 250), (5, 500)],
    },
    {
        "name": "scroll_github",
        "url": GH_URL,
        "duration_s": 4,
        "wait_for": 1.0,
        "scroll": [(0, 500), (3, 800)],
    },
]


def add_url_bar(img: Image.Image, url: str) -> Image.Image:
    """Draw a Chrome-like URL bar on top of the screenshot."""
    from PIL import ImageDraw, ImageFont

    CODE_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono.ttf", 16)
    draw = ImageDraw.Draw(img)
    bar_h = 36
    draw.rectangle([(0, 0), (W, bar_h)], fill=(40, 44, 52))
    for i, color in enumerate([(248, 113, 113), (251, 191, 36), (34, 197, 94)]):
        cxd = 14 + i * 20
        cyd = bar_h // 2
        draw.ellipse([(cxd - 6, cyd - 6), (cxd + 6, cyd + 6)], fill=color)
    url_x = 80
    url_w = W - 100
    draw.rounded_rectangle(
        [(url_x, 6), (url_x + url_w, bar_h - 6)],
        radius=12,
        fill=(28, 32, 40),
        outline=(60, 64, 72),
        width=1,
    )
    draw.rounded_rectangle([(url_x + 12, 11), (url_x + 18, 15)], radius=2, fill=(120, 120, 120))
    draw.rectangle([(url_x + 13, 13), (url_x + 17, 19)], fill=(120, 120, 120))
    draw.text((url_x + 28, 10), url, font=CODE_FONT, fill=(220, 220, 220))
    return img


def add_caption(img: Image.Image, text: str) -> Image.Image:
    """Add a small caption at the top-right of the screen."""
    from PIL import ImageDraw, ImageFont

    SMALL_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 20)
    draw = ImageDraw.Draw(img)
    bar_h = 36
    bbox = draw.textbbox((0, 0), text, font=SMALL_FONT)
    tw = bbox[2] - bbox[0] + 24
    th = bbox[3] - bbox[1] + 12
    overlay = Image.new("RGBA", (tw, th), (15, 23, 42, 220))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([(0, 0), (tw, th)], radius=8, fill=(15, 23, 42, 220))
    od.text((12, 6), text, font=SMALL_FONT, fill=(56, 189, 248))
    img.paste(overlay, (W - tw - 16, bar_h + 12), overlay)
    return img


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        # Warm up render
        print("→ warming up render (free tier sleep)", flush=True)
        try:
            page.goto(LIVE_URL + "/health", wait_until="networkidle", timeout=90000)
        except Exception as exc:
            print(f"  warmup: {exc}", flush=True)

        frame_idx = 0
        for scene in BROWSER_SCENES:
            name = scene["name"]
            url = scene["url"]
            duration = scene["duration_s"]
            scroll = scene.get("scroll", [(0, 0)])

            print(f"→ {name}: {url} ({duration}s)", flush=True)
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as exc:
                print(f"  nav: {exc}", flush=True)
            time.sleep(scene.get("wait_for", 2.0))

            n_frames = int(duration * FPS)
            for i in range(n_frames):
                t_in_scene = i / FPS
                # Interpolate scroll position
                scroll_pos = 0
                for ts, sp in scroll:
                    if t_in_scene >= ts:
                        scroll_pos = sp
                # Apply scroll via JS
                try:
                    page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                except Exception:
                    pass
                # Take screenshot every 5 frames
                if i % 5 == 0:
                    try:
                        png_bytes = page.screenshot(full_page=False)
                        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
                    except Exception as exc:
                        print(f"  screenshot failed: {exc}", flush=True)
                        img = Image.new("RGB", (W, H), (13, 17, 23))
                else:
                    # Reuse last screenshot
                    if 'last_img' in dir():
                        img = last_img
                    else:
                        img = Image.new("RGB", (W, H), (13, 17, 23))
                last_img = img
                img = img.resize((W, H), Image.LANCZOS)
                img = add_url_bar(img, url)
                if name in ("open_live_demo", "scroll_home", "navigate_demo", "navigate_slack", "navigate_document"):
                    img = add_caption(img, "🌐  Live demo · lineagepulse.onrender.com")
                else:
                    img = add_caption(img, "📂  Source · github.com/Donyemiight/lineagepulse")
                path = FRAMES_DIR / f"f_{frame_idx:05d}.png"
                img.save(path, "PNG", optimize=False)
                frame_idx += 1
            print(f"  ✓ {name}: {n_frames} frames", flush=True)

        browser.close()

    # Encode
    list_path = OUT_DIR / "phase2.txt"
    out = OUT_DIR / "phase2.mp4"
    frames = sorted(FRAMES_DIR.glob("f_*.png"))
    print(f"→ {len(frames)} frames to encode", flush=True)
    with open(list_path, "w") as f:
        for p in frames:
            f.write(f"file '{p}'\n")
            f.write(f"duration {1.0 / FPS}\n")
        f.write(f"file '{frames[-1]}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "22",
        "-r", str(FPS), str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        print(r.stderr[-2000:])
        return 1
    print(f"✓ wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
        capture_output=True, text=True, check=False,
    )
    print(f"  duration: {probe.stdout.strip()}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
