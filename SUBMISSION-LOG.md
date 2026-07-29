# DataHub Agent Hackathon — Submission Log

**Submitted:** 2026-07-29
**User:** Donyemiight (GitHub: Donyemiight / ademidun)

## Submission URLs

- **Live demo:** https://lineagepulse.onrender.com
- **GitHub repo:** https://github.com/Donyemiight/lineagepulse
- **YouTube demo:** (unlisted, screencast)
- **Project URL on Devpost:** https://devpost.com/software/lineagepulse
- **Hackathon:** https://datahub.devpost.com

## Form fields filled in

1. **Project name:** LineagePulse
2. **Elevator pitch:** "Multi-agent incident response for DataHub. Detects failing assertions, walks the lineage blast radius, writes a structured incident back to the graph, and notifies owners in one Slack message."
3. **Sub-challenge:** Agents That Do Real Work
4. **About the project:** [long markdown with inspiration, what it does, how we built it, challenges, what we learned, what's next]
5. **Built with tags:** Python, LangGraph, LangChain, Anthropic Claude, FastAPI, Render, Apache 2.0, DataHub, DataHub Agent Context Kit, DataHub MCP Server, DataHub Skills Registry, Slack, GitHub, multi-agent, lineage, ML metadata, incident response, data engineering, MLOps, observability
6. **Try it out links:** Live demo + GitHub repo
7. **Image gallery:** 7 images with professional captions
8. **Video demo:** YouTube unlisted link
9. **Code repository URL:** https://github.com/Donyemiight/lineagepulse
10. **Project URL:** https://lineagepulse.onrender.com
11. **Examples URL:** https://github.com/Donyemiight/lineagepulse/tree/main/examples
12. **DataHub technologies used:** DataHub Agent Context Kit, MCP Server, Skills Registry
13. **DataHub contributions during hackathon:** No new core contributions; future plans to PR Slack notifier
14. **Country:** Nigeria
15. **Newly created during submission period:** Yes
16. **Pre-existing code:** No
17. **Feedback Prize:** Yes
18. **Polished/Useful:** Detailed answer about Agent Context Kit
19. **Where stuck:** RPC cache lag + PAT workflow scope
20. **If unlimited time:** Activity feed + severity-bump policy engine
21. **Bugs/Errors:** acryl-datahub PKG-INFO + Render auto-deploy

## Accomplishments

Closed the read-write loop on DataHub. ML-aware severity bump. Three independent agents. Real production shape (Apache 2.0, 18 tests, Dockerfile, CI, live demo, screencast). Zero required credentials.

## Status

- ✅ Submitted on 2026-07-29
- ⏳ Judging: Aug 17 - Aug 31, 2026
- ⏳ Winners announced: Sept 8, 2026 (2:00 PM ET)

## Things to watch

- **Email** — DataHub may email about the feedback survey or the result
- **Devpost notifications** — for judging feedback
- **GitHub issues / stars** — judges may star or file issues
- **Slack #agent-hackathon** — official channel for status updates

## If we win

- Grand Prize = $6,000 + Town Hall presentation
- Challenge Winner = $3,000
- Honourable Mention = $1,000
- Feedback Prize = $50 × 10

## Backup plan if a judge can't run the live demo

The repo has full demo runbooks that work offline:
```bash
git clone https://github.com/Donyemiight/lineagepulse.git
cd lineagepulse
pip install -e .
python scripts/smoke_test.py
python scripts/demo_runbook.py
```

The `examples/demo_output/` folder has the exact Slack JSON and DataHub Document MD outputs a judge would see.
