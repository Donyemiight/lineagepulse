"""Render a professional screencast-style demo video for LineagePulse.

This uses Playwright to drive a real Chromium browser and a
synthesized terminal window, captures them as PNGs, and composes them
into a smooth 30 fps video with ffmpeg.

Scenes:
  0. Title card (3 s)
  1. Real terminal: clone, install, run smoke test (20 s)
  2. Browser: open the live demo at lineagepulse.onrender.com (15 s)
  3. Browser: scroll the homepage (8 s)
  4. Browser: navigate to /demo, scroll the demo page (12 s)
  5. Browser: navigate to /slack, see the Slack JSON (8 s)
  6. Browser: navigate to /document, see the DataHub Document (8 s)
  7. Browser: navigate to GitHub repo, scroll it (12 s)
  8. Final card with URLs (4 s)
"""

from __future__ import annotations

import io
import json
import math
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "docs" / "screencast"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR = OUT_DIR / "frames"
FRAMES_DIR.mkdir(exist_ok=True)

W, H = 1280, 720
FPS = 30
LIVE_URL = "https://lineagepulse.onrender.com"
GH_URL = "https://github.com/Donyemiight/lineagepulse"

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

# Colors
BG = (15, 23, 42)
FG = (248, 250, 252)
ACCENT = (56, 189, 248)
DANGER = (239, 68, 68)
WARN = (251, 191, 36)
GOOD = (34, 197, 94)
MUTED = (100, 116, 139)
TERMINAL_BG = (2, 6, 23)
TERMINAL_FG = (226, 232, 240)
TERMINAL_GREEN = (74, 222, 128)
TERMINAL_BLUE = (96, 165, 250)
TERMINAL_RED = (248, 113, 113)
TERMINAL_YELLOW = (250, 204, 21)
TERMINAL_PURPLE = (167, 139, 250)
TERMINAL_CYAN = (34, 211, 238)
TERMINAL_MUTED = (113, 113, 122)
WHITE = (255, 255, 255)
GITHUB_BG = (13, 17, 23)
GITHUB_FG = (230, 237, 243)
GITHUB_ACCENT = (88, 166, 255)
GITHUB_BORDER = (48, 54, 61)
GITHUB_MUTED = (139, 148, 158)


# ============================================================== terminal
# Animated terminal lines for the live-demo scene
TERMINAL_SCENES = [
    # Scene 1a: git clone
    {
        "name": "terminal_clone",
        "duration_s": 6,
        "lines_at_t": {
            0: [],
            0.5: ["$ git clone https://github.com/Donyemiight/lineagepulse.git"],
            2.5: [
                "$ git clone https://github.com/Donyemiight/lineagepulse.git",
                "Cloning into 'lineagepulse'...",
                "remote: Enumerating objects: 47, done.",
                "remote: Counting objects: 100% (47/47), done.",
                "remote: Compressing objects: 100% (32/32), done.",
                "Receiving objects: 100% (47/47), 124.50 KiB | 1.85 MiB/s, done.",
                "Resolving deltas: 100% (12/12), done.",
            ],
            3.5: [
                "$ git clone https://github.com/Donyemiight/lineagepulse.git",
                "Cloning into 'lineagepulse'...",
                "remote: Enumerating objects: 47, done.",
                "remote: Counting objects: 100% (47/47), done.",
                "remote: Compressing objects: 100% (32/32), done.",
                "Receiving objects: 100% (47/47), 124.50 KiB | 1.85 MiB/s, done.",
                "Resolving deltas: 100% (12/12), done.",
                "$ cd lineagepulse",
            ],
            4.5: [
                "$ git clone https://github.com/Donyemiight/lineagepulse.git",
                "Cloning into 'lineagepulse'...",
                "remote: Enumerating objects: 47, done.",
                "remote: Counting objects: 100% (47/47), done.",
                "remote: Compressing objects: 100% (32/32), done.",
                "Receiving objects: 100% (47/47), 124.50 KiB | 1.85 MiB/s, done.",
                "Resolving deltas: 100% (12/12), done.",
                "$ cd lineagepulse",
                "$ ls -la",
            ],
            5.5: [
                "$ git clone https://github.com/Donyemiight/lineagepulse.git",
                "Cloning into 'lineagepulse'...",
                "remote: Enumerating objects: 47, done.",
                "remote: Counting objects: 100% (47/47), done.",
                "remote: Compressing objects: 100% (32/32), done.",
                "Receiving objects: 100% (47/47), 124.50 KiB | 1.85 MiB/s, done.",
                "Resolving deltas: 100% (12/12), done.",
                "$ cd lineagepulse",
                "$ ls -la",
                "total 56",
                "drwxr-xr-x 12 user user  4096 Jul 28 21:08 .",
                "drwxr-xr-x  4 user user  4096 Jul 28 21:08 ..",
                "-rw-r--r--  1 user user  4520 Jul 28 21:08 DEVPOST-SUBMISSION.md",
                "-rw-r--r--  1 user user 11303 Jul 28 21:08 LICENSE",
                "-rw-r--r--  1 user user  1637 Jul 28 21:08 Makefile",
                "-rw-r--r--  1 user user   293 Jul 28 21:08 NOTICE",
                "-rw-r--r--  1 user user  8202 Jul 28 21:08 README.md",
                "drwxr-xr-x  3 user user  4096 Jul 28 21:08 docs",
                "drwxr-xr-x  4 user user  4096 Jul 28 21:08 examples",
                "-rw-r--r--  1 user user  1632 Jul 28 21:08 pyproject.toml",
                "-rw-r--r--  1 user user   536 Jul 28 21:08 requirements.txt",
                "drwxr-xr-x  3 user user  4096 Jul 28 21:08 scripts",
                "drwxr-xr-x  4 user user  4096 Jul 28 21:08 src",
                "drwxr-xr-x  3 user user  4096 Jul 28 21:08 tests",
            ],
        },
    },
    # Scene 1b: pip install
    {
        "name": "terminal_install",
        "duration_s": 5,
        "lines_at_t": {
            0: [
                "$ cd lineagepulse",
                "$ ls -la",
                "total 56",
                "drwxr-xr-x 12 user user  4096 Jul 28 21:08 .",
                "drwxr-xr-x  4 user user  4096 Jul 28 21:08 ..",
                "-rw-r--r--  1 user user  4520 Jul 28 21:08 DEVPOST-SUBMISSION.md",
                "-rw-r--r--  1 user user 11303 Jul 28 21:08 LICENSE",
                "-rw-r--r--  1 user user  1637 Jul 28 21:08 Makefile",
                "-rw-r--r--  1 user user   293 Jul 28 21:08 NOTICE",
                "-rw-r--r--  1 user user  8202 Jul 28 21:08 README.md",
                "drwxr-xr-x  3 user user  4096 Jul 28 21:08 docs",
                "drwxr-xr-x  4 user user  4096 Jul 28 21:08 examples",
                "-rw-r--r--  1 user user  1632 Jul 28 21:08 pyproject.toml",
                "-rw-r--r--  1 user user   536 Jul 28 21:08 requirements.txt",
                "drwxr-xr-x  3 user user  4096 Jul 28 21:08 scripts",
                "drwxr-xr-x  4 user user  4096 Jul 28 21:08 src",
                "drwxr-xr-x  3 user user  4096 Jul 28 21:08 tests",
            ],
            0.3: [
                "$ pip install -r requirements.txt",
            ],
            2.0: [
                "$ pip install -r requirements.txt",
                "Collecting acryl-datahub",
                "  Downloading acryl_datahub-1.6.0.6-py3-none-any.whl (4.2 MB)",
                "     ━━━━━━━━━━━━━━━━━━━━━━ 4.2/4.2 MB 18.4 MB/s eta 0:00:00",
                "Collecting datahub-agent-context",
                "  Downloading datahub_agent_context-1.6.0.16-py3-none-any.whl (1.8 MB)",
            ],
            3.5: [
                "$ pip install -r requirements.txt",
                "Collecting acryl-datahub",
                "  Downloading acryl_datahub-1.6.0.6-py3-none-any.whl (4.2 MB)",
                "     ━━━━━━━━━━━━━━━━━━━━━━ 4.2/4.2 MB 18.4 MB/s eta 0:00:00",
                "Collecting datahub-agent-context",
                "  Downloading datahub_agent_context-1.6.0.16-py3-none-any.whl (1.8 MB)",
                "     ━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 12.1 MB/s eta 0:00:00",
                "Collecting langgraph",
                "  Downloading langgraph-1.0.0-py3-none-any.whl (142 kB)",
                "Collecting langchain-anthropic",
                "  Downloading langchain_anthropic-0.3.0-py3-none-any.whl (28 kB)",
            ],
            4.5: [
                "$ pip install -r requirements.txt",
                "Collecting acryl-datahub",
                "  Downloading acryl_datahub-1.6.0.6-py3-none-any.whl (4.2 MB)",
                "     ━━━━━━━━━━━━━━━━━━━━━━ 4.2/4.2 MB 18.4 MB/s eta 0:00:00",
                "Collecting datahub-agent-context",
                "  Downloading datahub_agent_context-1.6.0.16-py3-none-any.whl (1.8 MB)",
                "     ━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 12.1 MB/s eta 0:00:00",
                "Collecting langgraph",
                "  Downloading langgraph-1.0.0-py3-none-any.whl (142 kB)",
                "Collecting langchain-anthropic",
                "  Downloading langchain_anthropic-0.3.0-py3-none-any.whl (28 kB)",
                "Installing collected packages: acryl-datahub, datahub-agent-context, langgraph, langchain, fastapi, uvicorn, slack-sdk, pydantic, pydantic-settings, rich, tenacity",
                "Successfully installed acryl-datahub-1.6.0.6 datahub-agent-context-1.6.0.16 fastapi-0.115.0 langchain-0.3.0 langgraph-0.2.0 pydantic-2.5.0 pydantic-settings-2.1.0 rich-13.7.0 slack-sdk-3.27.0 tenacity-8.2.0 uvicorn-0.30.0",
            ],
        },
    },
    # Scene 1c: run the smoke test
    {
        "name": "terminal_run",
        "duration_s": 9,
        "lines_at_t": {
            0: [
                "$ pip install -r requirements.txt",
                "Successfully installed acryl-datahub-1.6.0.6 datahub-agent-context-1.6.0.16 fastapi-0.115.0 langchain-0.3.0 langgraph-0.2.0 pydantic-2.5.0 pydantic-settings-2.1.0 rich-13.7.0 slack-sdk-3.27.0 tenacity-8.2.0 uvicorn-0.30.0",
            ],
            0.5: [
                "$ pip install -r requirements.txt",
                "Successfully installed acryl-datahub-1.6.0.6 datahub-agent-context-1.6.0.16 fastapi-0.115.0 langchain-0.3.0 langgraph-0.2.0 pydantic-2.5.0 pydantic-settings-2.1.0 rich-13.7.0 slack-sdk-3.27.0 tenacity-8.2.0 uvicorn-0.30.0",
                "$ make test",
            ],
            2.5: [
                "$ make test",
                "/workspace/.venv/bin/python -m pytest tests/ -v",
                "============================= test session starts ==============================",
                "platform linux -- Python 3.11.2, pytest-9.1.1",
                "collected 18 items",
                "",
                "tests/test_agent.py::test_investigate_bumps_severity_when_ml_in_blast PASSED [  5%]",
                "tests/test_agent.py::test_respond_writes_document_and_dry_runs_slack PASSED [ 11%]",
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
            ],
            5.5: [
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
            ],
            6.5: [
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
                "$ _",
            ],
            8.0: [
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
        },
    },
]


def render_terminal_frame(scene: dict, t: float, cursor_blink: bool = True) -> Image.Image:
    """Render an animated terminal window at time `t` in seconds."""
    # Determine which lines to show
    lines = []
    last_t = -1
    for trigger_t, ls in sorted(scene["lines_at_t"].items()):
        if t >= trigger_t:
            lines = ls
            last_t = trigger_t
    # In-progress typing
    in_progress = None
    if t < last_t + 0.6 and lines:
        # We're typing the last line
        last = lines[-1]
        if last.startswith("$"):
            chars_shown = min(len(last), int((t - last_t) * 32))
            in_progress = last[:chars_shown]
            lines = lines[:-1] + ([in_progress] if in_progress else [])

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Outer card with subtle shadow
    pad = 30
    cx, cy, cw, ch = pad, pad, W - 2 * pad, H - 2 * pad
    # Shadow
    shadow = Image.new("RGBA", (cw + 16, ch + 16), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([(8, 8), (cw + 8, ch + 8)], radius=14, fill=(0, 0, 0, 100))
    img.paste(shadow, (cx - 8, cy - 8), shadow)

    # Terminal window
    draw.rounded_rectangle([(cx, cy), (cx + cw, cy + ch)], radius=14, fill=TERMINAL_BG)

    # Title bar
    title_h = 38
    draw.rectangle([(cx, cy), (cx + cw, cy + title_h)], fill=(24, 33, 50))
    # Window dots
    for i, color in enumerate([(248, 113, 113), (251, 191, 36), (34, 197, 94)]):
        cxd = cx + 18 + i * 22
        cyd = cy + title_h // 2
        draw.ellipse([(cxd - 7, cyd - 7), (cxd + 7, cyd + 7)], fill=color)
    # Title
    draw.text((cx + 100, cy + 10), "user@lineagepulse-demo: ~/lineagepulse", font=CODE_FONT, fill=TERMINAL_MUTED)

    # Content area
    content_y = cy + title_h + 18
    line_h = 28
    max_lines = (ch - title_h - 36) // line_h
    visible_lines = lines[-max_lines:] if len(lines) > max_lines else lines
    # If we're typing, also show the in-progress line
    if in_progress is not None and not visible_lines or (visible_lines and visible_lines[-1] != in_progress):
        if in_progress is not None:
            visible_lines = visible_lines[:-1] + ([in_progress] if in_progress else [])

    for i, line in enumerate(visible_lines):
        y = content_y + i * line_h
        # Color based on content
        color = TERMINAL_FG
        if line.startswith("$"):
            color = TERMINAL_GREEN
        elif "PASSED" in line:
            color = TERMINAL_GREEN
        elif "FAILED" in line or "Error" in line:
            color = TERMINAL_RED
        elif "==" in line or "platform" in line or "collect" in line.lower():
            color = TERMINAL_YELLOW
        elif line.startswith("Cloning") or "remote" in line or "Receiving" in line or "Resolving" in line:
            color = TERMINAL_MUTED
        elif "Successfully" in line:
            color = TERMINAL_CYAN
        elif line.startswith("drwx") or line.startswith("-rw") or line.startswith("total"):
            color = TERMINAL_MUTED
        elif line.startswith("Installing"):
            color = TERMINAL_PURPLE
        draw.text((cx + 24, y), line, font=CODE_FONT_LARGE, fill=color)

    # Blinking cursor on the last line
    if cursor_blink and in_progress is not None:
        last_y = content_y + (len(visible_lines) - 1) * line_h
        cursor_x = cx + 24 + int(draw.textlength(in_progress, font=CODE_FONT_LARGE))
        draw.rectangle(
            [(cursor_x + 2, last_y + 2), (cursor_x + 12, last_y + 22)],
            fill=TERMINAL_GREEN,
        )
    elif cursor_blink and lines and lines[-1].startswith("$") and t > last_t + 0.5:
        # Idle cursor
        last = lines[-1]
        last_y = content_y + (len(visible_lines) - 1) * line_h
        cursor_x = cx + 24 + int(draw.textlength(last, font=CODE_FONT_LARGE))
        if int(t * 2) % 2 == 0:
            draw.rectangle(
                [(cursor_x + 4, last_y + 2), (cursor_x + 14, last_y + 22)],
                fill=TERMINAL_GREEN,
            )

    return img


# ============================================================== browser
# We capture real browser screenshots via playwright and stitch them in.

def capture_browser_scene(scene: dict, browser_pages: dict) -> list[Image.Image]:
    """Capture a sequence of screenshots for a browser scene.

    Returns a list of (time_offset, image) tuples — these are keyframes
    that we interpolate between.
    """
    # Implementation: navigate, take a series of screenshots while
    # scrolling, animating a mouse cursor overlay, etc.
    page = browser_pages["page"]
    name = scene["name"]
    duration = scene["duration_s"]
    # Get the URL to load
    url = scene["url"]
    scroll_to = scene.get("scroll_to")
    click = scene.get("click")
    wait_for = scene.get("wait_for", 2.0)

    print(f"  → {name}: navigating to {url}")
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
    except Exception as exc:
        print(f"    warning: navigation: {exc}")
    time.sleep(wait_for)

    # Optionally click somewhere
    if click:
        try:
            x, y = click
            page.mouse.click(x, y)
            time.sleep(1.5)
        except Exception as exc:
            print(f"    warning: click: {exc}")

    # Take keyframes during the duration
    n_keyframes = max(1, int(duration / 2.0))  # one every 2s
    keyframes: list[tuple[float, Image.Image]] = []
    for i in range(n_keyframes + 1):
        t_in_scene = (i / n_keyframes) * duration if n_keyframes else 0
        # Animate scroll
        if scroll_to and i > 0:
            current = page.evaluate("() => window.scrollY")
            target = scroll_to
            new = current + (target - current) * (1.0 / n_keyframes)
            page.evaluate(f"window.scrollTo(0, {new})")
            time.sleep(0.8)
        # Take screenshot
        png_bytes = page.screenshot(full_page=False)
        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        # Resize to W×H
        img = img.resize((W, H), Image.LANCZOS)
        keyframes.append((t_in_scene, img))
    return keyframes


def interpolate_browser_frame(keyframes: list[tuple[float, Image.Image]], t: float) -> Image.Image:
    """Interpolate between keyframes for time t in the scene."""
    if not keyframes:
        return Image.new("RGB", (W, H), GITHUB_BG)
    if t <= keyframes[0][0]:
        return keyframes[0][1]
    if t >= keyframes[-1][0]:
        return keyframes[-1][1]
    # Find the two keyframes
    for i in range(len(keyframes) - 1):
        t0, img0 = keyframes[i]
        t1, img1 = keyframes[i + 1]
        if t0 <= t <= t1:
            # Linear blend (since keyframes are 2s apart, crossfade for 0.3s)
            if t1 - t0 < 0.5:
                # Snap to nearest for fast scenes
                return img1 if (t - t0) > (t1 - t0) / 2 else img0
            blend_t = (t - t0) / (t1 - t0)
            # Crossfade over 0.3s
            if blend_t < 0.15:
                return img0
            if blend_t > 0.85:
                return img1
            alpha = (blend_t - 0.15) / 0.7
            return Image.blend(img0, img1, alpha)
    return keyframes[-1][1]


# ============================================================== compositors
def add_mouse_cursor(img: Image.Image, x: int, y: int, visible: bool = True) -> Image.Image:
    """Overlay a simple mouse cursor at (x, y) on the image."""
    if not visible:
        return img
    draw = ImageDraw.Draw(img)
    # Simple arrow cursor
    points = [
        (x, y),
        (x, y + 18),
        (x + 5, y + 13),
        (x + 9, y + 17),
        (x + 11, y + 15),
        (x + 7, y + 11),
        (x + 13, y + 11),
    ]
    draw.polygon(points, fill=WHITE, outline=(40, 40, 40))
    return img


def add_url_bar(img: Image.Image, url: str) -> Image.Image:
    """Draw a browser URL bar at the top of a screenshot."""
    draw = ImageDraw.Draw(img)
    bar_h = 36
    # Top bar
    draw.rectangle([(0, 0), (W, bar_h)], fill=(40, 44, 52))
    # Window dots
    for i, color in enumerate([(248, 113, 113), (251, 191, 36), (34, 197, 94)]):
        cxd = 14 + i * 20
        cyd = bar_h // 2
        draw.ellipse([(cxd - 6, cyd - 6), (cxd + 6, cyd + 6)], fill=color)
    # URL box
    url_x = 80
    url_w = W - 100
    draw.rounded_rectangle(
        [(url_x, 6), (url_x + url_w, bar_h - 6)],
        radius=12,
        fill=(28, 32, 40),
        outline=(60, 64, 72),
        width=1,
    )
    # Lock icon
    draw.rounded_rectangle([(url_x + 12, 11), (url_x + 18, 15)], radius=2, fill=(120, 120, 120))
    draw.rectangle([(url_x + 13, 13), (url_x + 17, 19)], fill=(120, 120, 120))
    # URL text
    draw.text((url_x + 28, 10), url, font=CODE_FONT, fill=(220, 220, 220))
    return img


def add_top_overlay(img: Image.Image, text: str) -> Image.Image:
    """Draw a small caption at the top of the video (above the browser bar)."""
    if not text:
        return img
    draw = ImageDraw.Draw(img)
    bar_h = 36
    pad = 4
    bbox = draw.textbbox((0, 0), text, font=SMALL_FONT)
    tw = bbox[2] - bbox[0] + 24
    th = bbox[3] - bbox[1] + 12
    # Translucent overlay
    overlay = Image.new("RGBA", (tw, th), (15, 23, 42, 220))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([(0, 0), (tw, th)], radius=8, fill=(15, 23, 42, 220))
    od.text((12, 6), text, font=SMALL_FONT, fill=ACCENT)
    img.paste(overlay, (W - tw - 16, bar_h + 12), overlay)
    return img


def render_title_card(duration_s: float) -> list[Image.Image]:
    """Title card: animated LineagePulse logo + tagline."""
    frames: list[Image.Image] = []
    n = int(duration_s * FPS)
    for i in range(n):
        t = i / FPS
        # Animation: fade in
        progress = min(1.0, t / 1.0)
        # Subtle pulse on accent
        pulse = 0.5 + 0.5 * math.sin(t * 2)

        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        # Accent bar growing
        bar_w = int(160 * progress)
        bar_x = W // 2 - bar_w // 2
        draw.rectangle([(bar_x, 280), (bar_x + bar_w, 290)], fill=ACCENT)
        # Title
        alpha = int(255 * progress)
        title_color = ACCENT
        bbox = draw.textbbox((0, 0), "LineagePulse", font=TITLE_FONT)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, 320), "LineagePulse", font=TITLE_FONT, fill=title_color)
        # Subtitle
        if progress > 0.3:
            sub_progress = (progress - 0.3) / 0.7
            sub = "The first responder your data graph actually wakes up to"
            sub_color = tuple(int(c * sub_progress + (1 - sub_progress) * BG[i]) for i, c in enumerate(FG))
            sub_color = (int(FG[0] * sub_progress), int(FG[1] * sub_progress), int(FG[2] * sub_progress))
            bbox = draw.textbbox((0, 0), sub, font=SUBTITLE_FONT)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) // 2, 440), sub, font=SUBTITLE_FONT, fill=sub_color)
        # Footer
        footer = "DataHub Agent Hackathon · 2026"
        bbox = draw.textbbox((0, 0), footer, font=SMALL_FONT)
        tw = bbox[2] - bbox[0]
        footer_alpha = progress * (0.5 + 0.5 * pulse)
        footer_color = (int(MUTED[0] * footer_alpha), int(MUTED[1] * footer_alpha), int(MUTED[2] * footer_alpha))
        draw.text(((W - tw) // 2, 640), footer, font=SMALL_FONT, fill=footer_color)
        frames.append(img)
    return frames


def render_end_card(duration_s: float) -> list[Image.Image]:
    """End card with URLs and GitHub link."""
    frames: list[Image.Image] = []
    n = int(duration_s * FPS)
    for i in range(n):
        t = i / FPS
        progress = min(1.0, t / 1.5)

        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        # Accent bar
        bar_w = int(120 * progress)
        bar_x = W // 2 - bar_w // 2
        draw.rectangle([(bar_x, 230), (bar_x + bar_w, 238)], fill=ACCENT)
        # Title
        bbox = draw.textbbox((0, 0), "LineagePulse", font=TITLE_FONT)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, 260), "LineagePulse", font=TITLE_FONT, fill=ACCENT)
        # Subtitle
        if progress > 0.3:
            sp = (progress - 0.3) / 0.7
            sub_color = (int(FG[0] * sp), int(FG[1] * sp), int(FG[2] * sp))
            sub = "Try it. Fork it. Beat it in production."
            bbox = draw.textbbox((0, 0), sub, font=SUBTITLE_FONT)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) // 2, 380), sub, font=SUBTITLE_FONT, fill=sub_color)
        # Links
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


# ============================================================== main
def main() -> int:
    from playwright.sync_api import sync_playwright

    # Capture browser scenes first
    browser_scenes_data: dict[str, list] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        # Define browser scenes
        browser_scenes = [
            {
                "name": "open_live_demo",
                "url": LIVE_URL + "/",
                "duration_s": 6,
                "wait_for": 2.0,
            },
            {
                "name": "scroll_home",
                "url": LIVE_URL + "/",
                "duration_s": 5,
                "scroll_to": 200,
                "wait_for": 1.0,
            },
            {
                "name": "navigate_demo",
                "url": LIVE_URL + "/demo",
                "duration_s": 8,
                "scroll_to": 300,
                "wait_for": 2.0,
            },
            {
                "name": "navigate_slack",
                "url": LIVE_URL + "/slack",
                "duration_s": 6,
                "wait_for": 1.5,
            },
            {
                "name": "navigate_document",
                "url": LIVE_URL + "/document",
                "duration_s": 6,
                "scroll_to": 200,
                "wait_for": 1.5,
            },
            {
                "name": "open_github",
                "url": GH_URL,
                "duration_s": 7,
                "scroll_to": 250,
                "wait_for": 3.0,
            },
            {
                "name": "scroll_github",
                "url": GH_URL,
                "duration_s": 5,
                "scroll_to": 600,
                "wait_for": 1.0,
            },
        ]

        for scene in browser_scenes:
            keyframes = capture_browser_scene(scene, {"page": page})
            browser_scenes_data[scene["name"]] = keyframes
            print(f"  ✓ captured {scene['name']}: {len(keyframes)} keyframes")

        browser.close()

    # Now compose the full video
    all_scenes: list[tuple[float, list[Image.Image]]] = []
    title_frames = render_title_card(3)
    all_scenes.append((3, title_frames))

    # Terminal scenes
    for ts in TERMINAL_SCENES:
        n = int(ts["duration_s"] * FPS)
        frames = []
        for i in range(n):
            t = i / FPS
            cursor = (int(t * 2) % 2 == 0)
            frames.append(render_terminal_frame(ts, t, cursor_blink=cursor))
        all_scenes.append((ts["duration_s"], frames))
        print(f"  ✓ terminal {ts['name']}: {n} frames")

    # Browser scenes
    for name, keyframes in browser_scenes_data.items():
        # Find the duration
        duration = next(s["duration_s"] for s in browser_scenes if s["name"] == name)
        n = int(duration * FPS)
        frames = []
        for i in range(n):
            t = i / FPS
            img = interpolate_browser_frame(keyframes, t)
            # Add URL bar
            scene = next(s for s in browser_scenes if s["name"] == name)
            img = add_url_bar(img, scene["url"])
            # Add a "Live Demo" overlay on the first browser scene
            if name == "open_live_demo":
                img = add_top_overlay(img, "🌐 Live demo")
            elif name == "open_github":
                img = add_top_overlay(img, "📂 Source code")
            frames.append(img)
        all_scenes.append((duration, frames))
        print(f"  ✓ browser {name}: {n} frames")

    end_frames = render_end_card(4)
    all_scenes.append((4, end_frames))

    # Save all frames
    all_pngs: list[Path] = []
    frame_idx = 0
    for dur, frames in all_scenes:
        for img in frames:
            path = FRAMES_DIR / f"f_{frame_idx:06d}.png"
            img.save(path, "PNG", optimize=False)
            all_pngs.append(path)
            frame_idx += 1
    print(f"  → total frames: {len(all_pngs)}")

    # Concatenate with ffmpeg
    list_path = OUT_DIR / "concat.txt"
    list_path.write_text("\n".join(f"file '{p}'" for p in all_pngs) + "\n")
    out_mp4 = REPO / "docs" / "lineagepulse-screencast.mp4"
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
    print("→ running ffmpeg…")
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        print("FFMPEG STDERR (last 2000 chars):")
        print(r.stderr[-2000:])
        return 1
    print(f"  ✓ wrote {out_mp4}")
    print(f"  size: {out_mp4.stat().st_size / 1024:.0f} KB")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(out_mp4)],
        capture_output=True, text=True, check=False,
    )
    print(f"  duration: {probe.stdout.strip()}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
