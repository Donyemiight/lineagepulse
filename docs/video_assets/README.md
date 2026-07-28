# Video assets

The demo video is `lineagepulse-demo.mp4` (located in the parent `docs/`
folder) — 93 seconds, 1280×720, h264, ~630 KB.

The static frame thumbnails here are sample frames extracted from the
video for the README and Devpost submission.

To regenerate the video after editing the scene script:

```bash
python scripts/render_video.py
```

This will:

1. Read `scenes.json` (the scene definitions — title, problem, solution,
   architecture, demo, slack, doc, results, end)
2. Render each scene as a PNG via PIL
3. Concatenate them with `ffmpeg` into the final MP4

## Scene timings (total: 94 s)

| Scene | Duration | What it shows |
|---|---|---|
| 0 | 5 s | Title card with brand accent |
| 1 | 8 s | The problem (4 bullet points) |
| 2 | 7 s | The solution (4 bullet points) |
| 3 | 8 s | Architecture (Detector / Investigator / Responder) |
| 4 | 18 s | Live demo: running the agent in a terminal |
| 5 | 14 s | Slack notification mockup |
| 6 | 12 s | DataHub Document writeback mockup |
| 7 | 8 s | "Why we win" recap |
| 8 | 6 s | End card with GitHub URL |
