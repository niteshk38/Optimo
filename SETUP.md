# Setup & Configuration — one page

Everything you need to configure after cloning. **Every key below is free**, and
each user runs with their **own** keys, so there are no shared quotas or costs.

The app runs out of the box with **zero keys** (RemoteOK jobs + keyword ranking).
Keys only *add* things: AI reasoning, and more job sources.

---

## 1. Install

```bash
git clone https://github.com/niteshk38/Optimo.git
cd Optimo
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # your keys go here (gitignored — never committed)
```

Run it:
```bash
streamlit run app/streamlit_app.py     # web UI
# or the CLI:
python cli.py search --query "python backend" --location India
```

---

## 2. Where things go

| File | Contains | Committed? |
|------|----------|-----------|
| `.env` | **secrets** — all API keys | ❌ gitignored |
| `config.yaml` | **settings** — which sources, how many results, ranking weights | ❌ gitignored (copy of `config.example.yaml`) |
| `config.example.yaml` | the default settings the app falls back to | ✅ yes |

Rule: **API keys only ever go in `.env`.** Never in `config.yaml` or code.

---

## 3. The AI (pick ONE — both free)

The app works without AI (keyword ranking), but AI adds fit scoring with reasons,
resume understanding, and cover-letter/bullet tailoring.

### Option A — Ollama (local, free, private, offline)
Best for a single user on a capable machine. Your resume never leaves your computer.
1. Install [Ollama](https://ollama.com).
2. `ollama pull llama3.1`
3. Done — it's the default (`http://localhost:11434`). Nothing to put in `.env`.

### Option B — Groq (free hosted API, no GPU needed)
Best if your machine can't run a local model. Sign up (no credit card):
1. Get a key at <https://console.groq.com> → **API Keys**.
2. In `.env`:
   ```
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_MODEL=llama-3.3-70b-versatile
   LLM_API_KEY=gsk_your_key
   ```
   (`70b-versatile` gives clearly better fit reasoning than small models;
   `llama-3.1-8b-instant` is faster/higher-limit if you prefer. Model names change —
   see <https://console.groq.com/docs/models>.)

Any other OpenAI-compatible provider (OpenAI, Together, etc.) works the same way —
just change those three values.

---

## 4. Job sources

Enable/disable and tune these in `config.yaml`. Each source **disables itself
silently** if its key is missing, so you can add them one at a time.

| Source | Gets you | Key(s) in `.env` | Free? |
|--------|----------|------------------|-------|
| **remoteok** | Remote tech jobs | none | ✅ works instantly |
| **jsearch** | **LinkedIn, Indeed, Glassdoor** | `RAPIDAPI_KEY` | ✅ ~200 requests/mo |
| **websearch** | **Instahyre, LinkedIn, Naukri** (links) | `SERPER_API_KEY` (or Google CSE) | ✅ ~2,500 free searches |
| **adzuna** | Multi-country listings | `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` | ✅ free tier |
| **greenhouse** | Specific company boards | none (list boards in config) | ✅ |

### 4a. jsearch → LinkedIn / Indeed (recommended)
1. Sign up at <https://rapidapi.com>.
2. Open **JSearch**: <https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch>
3. **Pricing** tab → **Subscribe** to **Basic ($0/month)**. *(You must subscribe —
   copying the key is not enough.)*
4. Copy your key (the `X-RapidAPI-Key` in the code snippet) → `.env`:
   ```
   RAPIDAPI_KEY=your_key
   ```
- Cost per search = `num_pages` requests (default 3 → ~66 searches/month). Lower
  `num_pages` in `config.yaml` to stretch the free quota; raise it (max 20) for more
  LinkedIn results. Resets monthly.

### 4b. websearch → Instahyre / LinkedIn / Naukri
Returns result *links* (title + snippet), not full descriptions. There are two
backends; the app auto-uses whichever key is present, with **Serper preferred**.

**Option 1 — Serper (recommended — one key, no hassle):**
1. Sign up at <https://serper.dev> (Google login; free tier ~2,500 searches).
2. Dashboard → **API Key** → copy it → `.env`:
   ```
   SERPER_API_KEY=your_key
   ```
Done. No Google Cloud setup.

**Option 2 — Google Custom Search (fallback only):**
1. Enable **Custom Search API** at
   <https://console.cloud.google.com/apis/library/customsearch.googleapis.com>,
   then create an **API key** in that **same project**.
2. Create an engine at <https://programmablesearchengine.google.com/controlpanel/create>,
   add `linkedin.com/jobs`, `instahyre.com`, `naukri.com` under **"Sites to search"**,
   copy the **Search engine ID**.
3. In `.env`: `GOOGLE_CSE_KEY=...` and `GOOGLE_CSE_CX=...`
   > ⚠️ Brand-new Google Cloud projects can take up to ~1 hr to activate, and some
   > accounts gate the API entirely. **Serper avoids all of this** — prefer it.

Which sites are searched is set by `websearch.sites` in `config.yaml`.

### 4c. adzuna (optional)
Free `app_id` / `app_key` from <https://developer.adzuna.com> → `.env` as
`ADZUNA_APP_ID` / `ADZUNA_APP_KEY`. Set the country in `config.yaml`.

---

## 5. Full `.env` reference

```env
# --- AI (leave blank to use local Ollama) ---
LLM_BASE_URL=
LLM_MODEL=
LLM_API_KEY=

# --- Jobs: LinkedIn/Indeed/Glassdoor ---
RAPIDAPI_KEY=

# --- Jobs: Instahyre/LinkedIn/Naukri links (websearch) ---
# Preferred: Serper (one key). Or Google CSE as a fallback (needs BOTH keys).
SERPER_API_KEY=
GOOGLE_CSE_KEY=
GOOGLE_CSE_CX=

# --- Jobs: Adzuna (optional) ---
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
```

## 6. Key `config.yaml` settings

```yaml
sources:
  jsearch:
    enabled: true
    country: in          # us, gb, in, ...
    num_pages: 3         # results ≈ 10 × num_pages; each page = 1 request
  websearch:
    enabled: true
    sites: [instahyre.com, linkedin.com/jobs, naukri.com]

matcher:
  llm_weight: 0.7        # 0..1 — how much the AI score counts vs keywords
  rerank_k: 15           # how many top jobs the AI re-scores (more = more ✅/⚠️, more LLM calls)
```

---

## 7. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| jsearch returns nothing | Not subscribed to JSearch on RapidAPI (step 4a.3), or monthly quota used up (resets monthly). |
| "No LLM reachable" in Tailor | Start Ollama, or set the Groq `LLM_*` keys in `.env`. |
| Few LinkedIn jobs | Raise `num_pages` in `config.yaml`. |
| websearch off | Set `SERPER_API_KEY` (easiest), or **both** `GOOGLE_CSE_KEY` and `GOOGLE_CSE_CX`. |
| websearch: "project does not have access to Custom Search JSON API" | A Google-CSE-only problem: enable Custom Search API on the **same project** as your key (new projects take up to ~1 hr; some accounts gate it). **Just use `SERPER_API_KEY` instead** — no Google Cloud needed. |
| no ✅/⚠️ on lower jobs | Only the top `rerank_k` jobs get AI reasons/concerns — raise it in `config.yaml`. |
| Changed `.env` but nothing happened | Restart the app — keys are read once at startup. |
