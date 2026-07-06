# 🚀 Optimo

_An open-source, AI-powered job search agent._

An open-source, LLM-powered assistant for the job hunt. It pulls real listings
from legitimate sources, ranks them against your resume with explanations, helps
you tailor each application, and tracks your pipeline — all locally, with a human
in the loop.

Works fully **offline and free** with a local model via [Ollama](https://ollama.com),
or plug in any OpenAI-compatible API.

---

## What it does

| Capability | What you get |
|---|---|
| 🔎 **Find & rank** | Fetches jobs from **LinkedIn, Indeed, Glassdoor** (JSearch), **Instahyre, Naukri** (web search), RemoteOK, Adzuna, and Greenhouse boards — de-duplicated and ranked by fit with a score + reasons. |
| ✍️ **Tailor** | Drafts a grounded cover letter and rewrites resume bullets for a specific role — using only what's actually on your resume. |
| 📋 **Track** | Saves applications to a local SQLite database, moves them through statuses, and exports to CSV. |

Two ways to use it: a **CLI** for speed and a **Streamlit web UI** for a friendly, visual workflow. Both share the same core.

Runs out of the box with **zero keys** (RemoteOK + keyword ranking). Add free keys to unlock AI ranking and more sources — see **[SETUP.md](SETUP.md)**.

---

## Quickstart

```bash
git clone https://github.com/niteshk38/Optimo.git
cd Optimo
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

```bash
cp .env.example .env    # put your free keys here later
```

**That's enough to run** — you'll get RemoteOK jobs with keyword ranking.

To unlock **AI ranking** and **LinkedIn / Instahyre / Indeed** sources, add free keys.
Every step (Groq or Ollama for AI, RapidAPI for LinkedIn, Serper for Instahyre) is
on one page: **👉 [SETUP.md](SETUP.md)**.

### Run the CLI

```bash
python cli.py search --query "python backend" --location London --resume resume.txt
python cli.py save   --rank 1
python cli.py tailor --rank 1 --kind cover
python cli.py track  list
python cli.py track  status --job-id <id> --to applied
python cli.py track  export --out applications.csv
```

No model running? Add `--no-llm` to `search` for keyword-only ranking.

### Run the web UI

```bash
streamlit run app/streamlit_app.py
```

---

## How ranking works

Every job gets a fast **keyword-overlap** score against your skills and preferences,
so ranking works even with no model at all. When an LLM is reachable, the top
`rerank_k` candidates are **re-scored with reasoning** (fit score, why it fits, and
honest concerns), and the two scores are blended (`matcher.llm_weight`). Tune both in
`config.yaml`.

## Configuration

All configuration — every free key, where it goes, and every `config.yaml` setting —
is documented on one page: **[SETUP.md](SETUP.md)**.

In short: secrets live in `.env` (gitignored), settings live in `config.yaml`. If
`config.yaml` is absent, `config.example.yaml` is used so the project runs out of the box.

## Project layout

```
jobagent/
  config.py      # config.yaml + .env
  llm.py         # OpenAI-compatible client (Ollama by default)
  models.py      # Job, Profile, MatchResult, Application
  resume.py      # resume -> Profile (LLM, with a heuristic fallback)
  matcher.py     # keyword score + optional LLM re-rank
  tailor.py      # cover letters + resume bullets
  tracker.py     # SQLite tracking + CSV export
  pipeline.py    # orchestration shared by both UIs
  sources/       # remoteok, jsearch, websearch, adzuna, greenhouse (+ your own)
app/streamlit_app.py
cli.py
tests/
```

Adding a job source is a ~40-line file — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

- [ ] More sources (USAJOBS, Lever, "Who is hiring")
- [ ] Embedding-based matching option
- [ ] Resume gap analysis ("skills this role wants that you don't list")
- [ ] Optional export to Notion / Google Sheets

## A note on scope

This tool **does not auto-apply** to jobs. Mass auto-submission is spammy, usually
violates site terms, and can hurt your reputation with recruiters. It helps you find
and prepare — you stay in control of what actually gets sent. LinkedIn/Indeed listings
come only through legitimate, publicly documented APIs — an aggregator (JSearch) and
official search (Google Custom Search) — never by scraping sites whose terms forbid it.

## Contributing

PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Please run `pytest` first.

## License

[MIT](LICENSE) — free to use, modify, and share.
