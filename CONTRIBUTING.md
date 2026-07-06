# Contributing

Thanks for your interest in improving Optimo! Contributions of all
sizes are welcome — bug fixes, new job sources, docs, tests.

## Getting set up

```bash
git clone https://github.com/niteshk38/Optimo.git
cd Optimo
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env          # optional; fill in keys you have
pytest
```

## Adding a new job source

1. Create `jobagent/sources/<name>.py` with a class that subclasses `JobSource`
   and returns a `list[Job]` from `search(...)`.
2. Register it in `jobagent/sources/__init__.py`.
3. Add a config block to `config.example.yaml`.
4. Add a small test (network calls should be mocked).

That's it — the CLI and the web UI pick it up automatically.

## Guidelines

- Keep dependencies minimal; prefer the standard library.
- Only use publicly documented APIs. Do **not** add scrapers for sites whose
  terms prohibit it (e.g. LinkedIn, Indeed) — it breaks for users and is a legal
  and ethical problem.
- This tool keeps a human in the loop. We don't build features that auto-submit
  applications on someone's behalf.
- Run `pytest` before opening a PR and describe what you changed and why.
