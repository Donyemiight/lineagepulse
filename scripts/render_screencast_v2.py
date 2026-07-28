"""Render a professional screencast video for LineagePulse.

Two-phase rendering:
  Phase 1 (this file): animated terminal + title + end cards
  Phase 2 (browser): real browser captures

This file is responsible for phase 1 only. It's fast because it
doesn't need a browser.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "docs" / "screencast"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR = OUT_DIR / "frames_phase1"
FRAMES_DIR.mkdir(exist_ok=True)

W, H = 1280, 720
FPS = 30

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
TITLE_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 72)
SUBTITLE_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 32)
BULLET_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 28)
SMALL_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 22)
CODE_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono.ttf", 18)
CODE_FONT_LARGE = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono.ttf", 22)
CODE_FONT_SMALL = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono.ttf", 16)
BOLD_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 28)
BOLD_FONT_LARGE = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 22)
BOLD_TITLE_FONT = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 48)

BG = (15, 23, 42)
FG = (248, 250, 252)
ACCENT = (56, 189, 248)
MUTED = (100, 116, 139)
TERMINAL_BG = (2, 6, 23)
TERMINAL_FG = (226, 232, 240)
TERMINAL_GREEN = (74, 222, 128)
TERMINAL_RED = (248, 113, 113)
TERMINAL_YELLOW = (250, 204, 21)
TERMINAL_PURPLE = (167, 139, 250)
TERMINAL_CYAN = (34, 211, 238)
TERMINAL_MUTED = (113, 113, 122)
WHITE = (255, 255, 255)


# Animated terminal — shorter and tighter for the screencast feel
TERMINAL_SCENES = [
    {
        "name": "terminal_clone",
        "duration_s": 5.0,
        "lines_at_t": {
            0.0: ["$ git clone https://github.com/Donyemiight/lineagepulse.git"],
            0.8: [
                "$ git clone https://github.com/Donyemiight/lineagepulse.git",
                "Cloning into 'lineagepulse'...",
                "remote: Enumerating objects: 47, done.",
                "remote: Counting objects: 100% (47/47), done.",
            ],
            1.8: [
                "$ git clone https://github.com/Donyemiight/lineagepulse.git",
                "Cloning into 'lineagepulse'...",
                "remote: Enumerating objects: 47, done.",
                "remote: Counting objects: 100% (47/47), done.",
                "remote: Compressing objects: 100% (32/32), done.",
                "Receiving objects: 100% (47/47), 124.50 KiB | 1.85 MiB/s, done.",
                "Resolving deltas: 100% (12/12), done.",
                "$ cd lineagepulse",
            ],
            2.6: [
                "$ git clone https://github.com/Donyemiight/lineagepulse.git",
                "Cloning into 'lineagepulse'...",
                "remote: Enumerating objects: 47, done.",
                "remote: Counting objects: 100% (47/47), done.",
                "remote: Compressing objects: 100% (32/32), done.",
                "Receiving objects: 100% (47/47), 124.50 KiB | 1.85 MiB/s, done.",
                "Resolving deltas: 100% (12/12), done.",
                "$ cd lineagepulse",
                "$ pip install -r requirements.txt",
            ],
            3.4: [
                "$ git clone https://github.com/Donyemiight/lineagepulse.git",
                "Cloning into 'lineagepulse'...",
                "remote: Enumerating objects: 47, done.",
                "remote: Counting objects: 100% (47/47), done.",
                "remote: Compressing objects: 100% (32/32), done.",
                "Receiving objects: 100% (47/47), 124.50 KiB | 1.85 MiB/s, done.",
                "Resolving deltas: 100% (12/12), done.",
                "$ cd lineagepulse",
                "$ pip install -r requirements.txt",
                "Collecting acryl-datahub",
                "  Downloading acryl_datahub-1.6.0.6-py3-none-any.whl (4.2 MB)",
            ],
            4.4: [
                "$ git clone https://github.com/Donyemiight/lineagepulse.git",
                "Cloning into 'lineagepulse'...",
                "remote: Enumerating objects: 47, done.",
                "remote: Counting objects: 100% (47/47), done.",
                "remote: Compressing objects: 100% (32/32), done.",
                "Receiving objects: 100% (47/47), 124.50 KiB | 1.85 MiB/s, done.",
                "Resolving deltas: 100% (12/12), done.",
                "$ cd lineagepulse",
                "$ pip install -r requirements.txt",
                "Collecting acryl-datahub",
                "  Downloading acryl_datahub-1.6.0.6-py3-none-any.whl (4.2 MB)",
                "Installing collected packages: acryl-datahub, datahub-agent-context, langgraph, langchain, fastapi, uvicorn, slack-sdk, pydantic, rich, tenacity",
                "Successfully installed acryl-datahub-1.6.0.6 datahub-agent-context-1.6.0.16 fastapi-0.115.0 langchain-0.3.0 langgraph-0.2.0 pydantic-2.5.0 pydantic-settings-2.1.0 rich-13.7.0 slack-sdk-3.27.0 tenacity-8.2.0 uvicorn-0.30.0",
                "$ make test",
            ],
        },
    },
    {
        "name": "terminal_test",
        "duration_s": 5.0,
        "lines_at_t": {
            0.0: [
                "$ make test",
                "/workspace/.venv/bin/python -m pytest tests/ -v",
                "============================= test session starts ==============================",
                "platform linux -- Python 3.11.2, pytest-9.1.1",
                "collected 18 items",
            ],
            0.7: [
                "$ make test",
                "platform linux -- Python 3.11.2, pytest-9.1.1",
                "collected 18 items",
                "",
                "tests/test_agent.py::test_investigate_bumps_severity_when_ml_in_blast PASSED [  5%]",
                "tests/test_agent.py::test_respond_writes_document_and_dry_runs_slack PASSED [ 11%]",
            ],
            1.6: [
                "$ make test",
                "platform linux -- Python 3.11.2, pytest-9.1.1",
                "collected 18 items",
                "",
                "tests/test_agent.py::test_investigate_bumps_severity_when_ml_in_blast PASSED [  5%]",
                "tests/test_agent.py::test_respond_writes_document_and_dry_runs_slack PASSED [ 11%]",
                "tests/test_agent.py::test_handle_incident_full_loop PASSED             [ 16%]",
                "tests/test_agent.py::test_detect_incidents_calls_polling PASSED        [ 22%]",
                "tests/test_datahub_client.py::test_get_asset_uses_get_entities PASSED [ 27%]",
                "tests/test_datahub_client.py::test_get_lineage_walks_downstream PASSED [ 33%]",
            ],
            2.4: [
                "$ make test",
                "platform linux -- Python 3.11.2, pytest-9.1.1",
                "collected 18 items",
                "",
                "tests/test_agent.py::test_investigate_bumps_severity_when_ml_in_blast PASSED [  5%]",
                "tests/test_agent.py::test_respond_writes_document_and_dry_runs_slack PASSED [ 11%]",
                "tests/test_agent.py::test_handle_incident_full_loop PASSED             [ 16%]",
                "tests/test_agent.py::test_detect_incidents_calls_polling PASSED        [ 22%]",
                "tests/test_datahub_client.py::test_get_asset_uses_get_entities PASSED [ 27%]",
                "tests/test_datahub_client.py::test_get_lineage_walks_downstream PASSED [ 33%]",
                "tests/test_datahub_client.py::test_search_calls_search_tool PASSED    [ 38%]",
                "tests/test_datahub_client.py::test_write_incident_document_calls_save_document PASSED [ 44%]",
                "tests/test_datahub_client.py::test_dry_run_skips_writeback PASSED      [ 50%]",
                "tests/test_datahub_client.py::test_mutations_disabled_skips_writeback PASSED [ 55%]",
                "tests/test_datahub_client.py::test_fetch_failing_assertions_returns_incidents PASSED [ 61%]",
                "tests/test_datahub_client.py::test_available_returns_true_when_initialized PASSED [ 66%]",
                "tests/test_datahub_client.py::test_tools_summary PASSED                 [ 72%]",
            ],
            3.3: [
                "$ make test",
                "platform linux -- Python 3.11.2, pytest-9.1.1",
                "collected 18 items",
                "",
                "tests/test_agent.py::test_investigate_bumps_severity_when_ml_in_blast PASSED [  5%]",
                "tests/test_agent.py::test_respond_writes_document_and_dry_runs_slack PASSED [ 11%]",
                "tests/test_agent.py::test_handle_incident_full_loop PASSED             [ 16%]",
                "tests/test_agent.py::test_detect_incidents_calls_polling PASSED        [ 22%]",
                "tests/test_datahub_client.py::test_get_asset_uses_get_entities PASSED [ 27%]",
                "tests/test_datahub_client.py::test_get_lineage_walks_downstream PASSED [ 33%]",
                "tests/test_datahub_client.py::test_search_calls_search_tool PASSED    [ 38%]",
                "tests/test_datahub_client.py::test_write_incident_document_calls_save_document PASSED [ 44%]",
                "tests/test_datahub_client.py::test_dry_run_skips_writeback PASSED      [ 50%]",
                "tests/test_datahub_client.py::test_mutations_disabled_skips_writeback PASSED [ 55%]",
                "tests/test_datahub_client.py::test_fetch_failing_assertions_returns_incidents PASSED [ 61%]",
                "tests/test_datahub_client.py::test_available_returns_true_when_initialized PASSED [ 66%]",
                "tests/test_datahub_client.py::test_tools_summary PASSED                 [ 72%]",
                "tests/test_slack.py::test_render_blocks_has_required_structure PASSED  [ 77%]",
                "tests/test_slack.py::test_render_blocks_includes_ml_in_blast_radius PASSED [ 83%]",
                "tests/test_slack.py::test_post_incident_dry_run_returns_dry_run_marker PASSED [ 88%]",
                "tests/test_slack.py::test_post_incident_live_calls_requests PASSED    [ 94%]",
                "tests/test_slack.py::test_post_incident_no_webhook_returns_none PASSED [100%]",
                "",
                "============================== 18 passed in 2.93s ==============================",
                "$ make demo",
            ],
            4.0: [
                "$ make test",
                "platform linux -- Python 3.11.2, pytest-9.1.1",
                "collected 18 items",
                "",
                "tests/test_agent.py::test_investigate_bumps_severity_when_ml_in_blast PASSED [  5%]",
                "tests/test_agent.py::test_respond_writes_document_and_dry_runs_slack PASSED [ 11%]",
                "tests/test_agent.py::test_handle_incident_full_loop PASSED             [ 16%]",
                "tests/test_agent.py::test_detect_incidents_calls_polling PASSED        [ 22%]",
                "tests/test_datahub_client.py::test_get_asset_uses_get_entities PASSED [ 27%]",
                "tests/test_datahub_client.py::test_get_lineage_walks_downstream PASSED [ 33%]",
                "tests/test_datahub_client.py::test_search_calls_search_tool PASSED    [ 38%]",
                "tests/test_datahub_client.py::test_write_incident_document_calls_save_document PASSED [ 44%]",
                "tests/test_datahub_client.py::test_dry_run_skips_writeback PASSED      [ 50%]",
                "tests/test_datahub_client.py::test_mutations_disabled_skips_writeback PASSED [ 55%]",
                "tests/test_datahub_client.py::test_fetch_failing_assertions_returns_incidents PASSED [ 61%]",
                "tests/test_datahub_client.py::test_available_returns_true_when_initialized PASSED [ 66%]",
                "tests/test_datahub_client.py::test_tools_summary PASSED                 [ 72%]",
                "tests/test_slack.py::test_render_blocks_has_required_structure PASSED  [ 77%]",
                "tests/test_slack.py::test_render_blocks_includes_ml_in_blast_radius PASSED [ 83%]",
                "tests/test_slack.py::test_post_incident_dry_run_returns_dry_run_marker PASSED [ 88%]",
                "tests/test_slack.py::test_post_incident_live_calls_requests PASSED    [ 94%]",
                "tests/test_slack.py::test_post_incident_no_webhook_returns_none PASSED [100%]",
                "",
                "============================== 18 passed in 2.93s ==============================",
                "$ make demo",
                "✓ Synthesized incident: 38030bcb on taxi_trips",
                "  Severity: HIGH → bumped to CRITICAL (1 ML model in blast radius)",
                "✓ Bumped severity to CRITICAL (1 ML model(s) in blast radius)",
                "✓ Smoke test PASSED",
            ],
        },
    },
]


def render_terminal_frame(scene, t):
    """Render a single terminal frame at time t (seconds)."""
    lines = []
    last_t = -1
    for trigger_t, ls in sorted(scene["lines_at_t"].items()):
        if t >= trigger_t:
            lines = ls
            last_t = trigger_t

    in_progress = None
    if t < last_t + 0.5 and lines:
        last = lines[-1]
        if last.startswith("$"):
            chars_shown = min(len(last), int((t - last_t) * 32))
            in_progress = last[:chars_shown]
            lines = lines[:-1] + ([in_progress] if in_progress else [])

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    pad = 30
    cx, cy, cw, ch = pad, pad, W - 2 * pad, H - 2 * pad
    draw.rounded_rectangle([(cx, cy), (cx + cw, cy + ch)], radius=14, fill=TERMINAL_BG)

    title_h = 38
    draw.rectangle([(cx, cy), (cx + cw, cy + title_h)], fill=(24, 33, 50))
    for i, color in enumerate([(248, 113, 113), (251, 191, 36), (34, 197, 94)]):
        cxd = cx + 18 + i * 22
        cyd = cy + title_h // 2
        draw.ellipse([(cxd - 7, cyd - 7), (cxd + 7, cyd + 7)], fill=color)
    draw.text((cx + 100, cy + 10), "user@lineagepulse-demo: ~/lineagepulse", font=CODE_FONT, fill=TERMINAL_MUTED)

    content_y = cy + title_h + 14
    line_h = 26
    max_lines = (ch - title_h - 28) // line_h
    visible_lines = lines[-max_lines:] if len(lines) > max_lines else lines

    for i, line in enumerate(visible_lines):
        y = content_y + i * line_h
        color = TERMINAL_FG
        if line.startswith("$"):
            color = TERMINAL_GREEN
        elif "PASSED" in line:
            color = TERMINAL_GREEN
        elif "FAILED" in line or "Error" in line:
            color = TERMINAL_RED
        elif "==" in line or "platform" in line or line.startswith("Collecting"):
            color = TERMINAL_YELLOW
        elif line.startswith("Cloning") or "remote" in line or "Receiving" in line or "Resolving" in line:
            color = TERMINAL_MUTED
        elif "Successfully" in line:
            color = TERMINAL_CYAN
        elif line.startswith("Installing"):
            color = TERMINAL_PURPLE
        elif line.startswith("✓") or "Synthesized" in line or "Bumped" in line or "Smoke" in line:
            color = TERMINAL_GREEN
        elif "test" in line and "PASSED" not in line:
            color = TERMINAL_FG
        draw.text((cx + 24, y), line, font=CODE_FONT_LARGE, fill=color)

    if in_progress is not None:
        last_y = content_y + (len(visible_lines) - 1) * line_h
        cursor_x = cx + 24 + int(draw.textlength(in_progress, font=CODE_FONT_LARGE))
        if int(t * 2) % 2 == 0:
            draw.rectangle(
                [(cursor_x + 2, last_y + 2), (cursor_x + 12, last_y + 22)],
                fill=TERMINAL_GREEN,
            )
    elif lines and lines[-1].startswith("$") and t > last_t + 0.5 and int(t * 2) % 2 == 0:
        last = lines[-1]
        last_y = content_y + (len(visible_lines) - 1) * line_h
        cursor_x = cx + 24 + int(draw.textlength(last, font=CODE_FONT_LARGE))
        draw.rectangle(
            [(cursor_x + 4, last_y + 2), (cursor_x + 14, last_y + 22)],
            fill=TERMINAL_GREEN,
        )

    return img


def render_title_card(duration_s):
    """Title card with animated LineagePulse logo + tagline."""
    frames = []
    n = int(duration_s * FPS)
    for i in range(n):
        t = i / FPS
        progress = min(1.0, t / 1.0)
        pulse = 0.5 + 0.5 * math.sin(t * 2)

        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        bar_w = int(160 * progress)
        bar_x = W // 2 - bar_w // 2
        draw.rectangle([(bar_x, 280), (bar_x + bar_w, 290)], fill=ACCENT)
        bbox = draw.textbbox((0, 0), "LineagePulse", font=TITLE_FONT)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, 320), "LineagePulse", font=TITLE_FONT, fill=ACCENT)
        if progress > 0.3:
            sp = (progress - 0.3) / 0.7
            sub = "The first responder your data graph actually wakes up to"
            sub_color = (int(FG[0] * sp), int(FG[1] * sp), int(FG[2] * sp))
            bbox = draw.textbbox((0, 0), sub, font=SUBTITLE_FONT)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) // 2, 440), sub, font=SUBTITLE_FONT, fill=sub_color)
        footer = "DataHub Agent Hackathon · 2026"
        bbox = draw.textbbox((0, 0), footer, font=SMALL_FONT)
        tw = bbox[2] - bbox[0]
        footer_alpha = progress * (0.5 + 0.5 * pulse)
        footer_color = (int(MUTED[0] * footer_alpha), int(MUTED[1] * footer_alpha), int(MUTED[2] * footer_alpha))
        draw.text(((W - tw) // 2, 640), footer, font=SMALL_FONT, fill=footer_color)
        frames.append(img)
    return frames


def render_end_card(duration_s):
    frames = []
    n = int(duration_s * FPS)
    for i in range(n):
        t = i / FPS
        progress = min(1.0, t / 1.0)
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        bar_w = int(120 * progress)
        bar_x = W // 2 - bar_w // 2
        draw.rectangle([(bar_x, 230), (bar_x + bar_w, 238)], fill=ACCENT)
        bbox = draw.textbbox((0, 0), "LineagePulse", font=TITLE_FONT)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, 260), "LineagePulse", font=TITLE_FONT, fill=ACCENT)
        if progress > 0.3:
            sp = (progress - 0.3) / 0.7
            sub_color = (int(FG[0] * sp), int(FG[1] * sp), int(FG[2] * sp))
            sub = "Try it. Fork it. Beat it in production."
            bbox = draw.textbbox((0, 0), sub, font=SUBTITLE_FONT)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) // 2, 380), sub, font=SUBTITLE_FONT, fill=sub_color)
        if progress > 0.5:
            lp = (progress - 0.5) / 0.5
            link_color = (int(ACCENT[0] * lp), int(ACCENT[1] * lp), int(ACCENT[2] * lp))
            for j, url in enumerate([
                "🌐  lineagepulse.onrender.com",
                "📂  github.com/Donyemiight/lineagepulse",
                "📄  Apache 2.0 · Built for the DataHub Agent Hackathon",
            ]):
                y = 480 + j * 50
                bbox = draw.textbbox((0, 0), url, font=BULLET_FONT)
                tw = bbox[2] - bbox[0]
                draw.text(((W - tw) // 2, y), url, font=BULLET_FONT, fill=link_color)
        frames.append(img)
    return frames


def main():
    """Phase 1: render title + terminal + end card."""
    out_mp4 = OUT_DIR / "phase1.mp4"
    frames = []
    print("→ title card", flush=True)
    frames.extend(render_title_card(3))
    for ts in TERMINAL_SCENES:
        print(f"→ {ts['name']} ({ts['duration_s']}s)", flush=True)
        n = int(ts["duration_s"] * FPS)
        for i in range(n):
            frames.append(render_terminal_frame(ts, i / FPS))
    print("→ end card", flush=True)
    frames.extend(render_end_card(3))

    print(f"→ {len(frames)} frames to encode", flush=True)
    list_path = OUT_DIR / "phase1.txt"
    with open(list_path, "w") as f:
        for i, img in enumerate(frames):
            p = FRAMES_DIR / f"f_{i:05d}.png"
            img.save(p, "PNG", optimize=False)
            f.write(f"file '{p}'\n")
            f.write(f"duration {1.0 / FPS}\n")
            if i % 100 == 0:
                print(f"  saved {i}/{len(frames)}", flush=True)
        # Repeat last frame
        f.write(f"file '{FRAMES_DIR / f'f_{len(frames)-1:05d}.png'}'\n")

    print("→ ffmpeg", flush=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "22",
        "-r", str(FPS),
        str(out_mp4),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        print("FFMPEG STDERR (last 2000):")
        print(r.stderr[-2000:])
        return 1
    print(f"✓ wrote {out_mp4} ({out_mp4.stat().st_size / 1024:.0f} KB)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
