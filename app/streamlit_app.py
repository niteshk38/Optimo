"""Streamlit UI for Optimo.

Run from the project root:  streamlit run app/streamlit_app.py

The same jobagent core powers this and the CLI — this file is only glue and
widgets.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make the `jobagent` package importable when Streamlit runs this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import streamlit.components.v1 as components

from jobagent.config import Config
from jobagent.models import Application, Profile
from jobagent.matcher import rank
from jobagent.pipeline import build_llm, fetch_jobs
from jobagent.resume import build_profile, read_resume_bytes
from jobagent.tailor import cover_letter, tailored_bullets
from jobagent.tracker import Tracker

st.set_page_config(page_title="Optimo", page_icon="🚀", layout="wide")

# On Streamlit Community Cloud there is no .env — secrets live in st.secrets.
# Mirror any top-level string secrets into the environment so the framework-free
# jobagent.config (which reads os.getenv) picks them up. setdefault means a local
# .env still wins locally; on the cloud (no .env) the secrets fill the gap. This
# is a no-op when no secrets are configured.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

config = Config.load()
tracker = Tracker(config.preferences.get("db_path", "data/applications.db"))

# --- Futuristic theme -------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    :root {
        --cyan: #22d3ee;
        --violet: #a855f7;
        --pink: #f472b6;
        --ink: #e8eeff;
        --muted: #9fb0da;
        --glass: rgba(24, 26, 33, 0.62);
        --glass-2: rgba(30, 33, 42, 0.78);
        --brd: rgba(150, 160, 190, 0.15);
        --brd-hi: rgba(34, 211, 238, 0.5);
    }

    html, body, [class*="css"] { font-family: 'Space Grotesk', system-ui, sans-serif; }

    /* App background: sleek near-black charcoal with faint accent glows */
    .stApp {
        background:
            radial-gradient(900px 600px at 8% -14%, rgba(34,211,238,0.10), transparent 60%),
            radial-gradient(820px 620px at 100% 2%, rgba(168,85,247,0.10), transparent 55%),
            linear-gradient(160deg, #0a0b0f 0%, #0e1014 55%, #111318 100%);
        color: var(--ink);
    }
    .stApp::before {
        content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
        background-image:
            linear-gradient(rgba(150,160,190,0.035) 1px, transparent 1px),
            linear-gradient(90deg, rgba(150,160,190,0.035) 1px, transparent 1px);
        background-size: 46px 46px;
        mask-image: radial-gradient(circle at 50% 25%, black, transparent 88%);
    }

    /* Kill Streamlit's top bar + stop it swallowing clicks on our header */
    [data-testid="stHeader"] { background: transparent !important; pointer-events: none; }
    [data-testid="stToolbar"] { right: .5rem; pointer-events: auto; }

    .block-container {
        position: relative; z-index: 1; padding-top: 7rem; padding-bottom: 4rem;
        max-width: 1180px;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 11px; height: 11px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--cyan), var(--violet));
        border-radius: 99px; border: 3px solid transparent; background-clip: padding-box;
    }

    /* Fixed, centered hero bar */
    .hero-bar {
        position: fixed; top: 0; left: 0; right: 0; z-index: 2147483000;
        display: flex; flex-direction: column; align-items: center;
        padding: .6rem 1rem .55rem;
        background: linear-gradient(180deg, rgba(10,11,15,0.88), rgba(10,11,15,0.32) 70%, transparent);
        backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
        border-bottom: 1px solid rgba(150,160,190,0.12);
        pointer-events: none;
    }
    .hero-bar::after {
        content: ""; position: absolute; left: 0; right: 0; bottom: -1px; height: 1px;
        background: linear-gradient(90deg, transparent, var(--cyan), var(--violet), var(--pink), transparent);
        opacity: .8;
    }
    .hero { display: flex; align-items: center; justify-content: center; gap: 1.1rem; flex-wrap: wrap; }
    .hero-title {
        font-family: 'Orbitron', sans-serif; font-weight: 900;
        font-size: clamp(1.7rem, 3.8vw, 2.7rem); letter-spacing: 1px; line-height: 1.05;
        background: linear-gradient(92deg, var(--cyan), var(--violet) 48%, var(--pink), var(--cyan));
        background-size: 250% auto;
        -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
        animation: bh-shimmer 7s linear infinite;
        filter: drop-shadow(0 0 26px rgba(124,58,237,0.5));
    }
    @keyframes bh-shimmer { to { background-position: 250% center; } }
    .hero-sub {
        font-size: .82rem; font-weight: 500; color: var(--muted); text-align: center;
        letter-spacing: 2px; text-transform: uppercase; margin-top: .15rem;
    }
    .hero-sub .dot { color: var(--cyan); }

    /* LinkedIn badge */
    .li-badge {
        pointer-events: auto;
        position: absolute; top: .85rem; right: 1.2rem;  /* pinned to the corner */
        display: inline-flex; align-items: center; gap: .5rem;
        padding: .48rem .95rem; border-radius: 999px; text-decoration: none;
        font-weight: 600; font-size: .92rem; color: #eaf1ff !important;
        background: linear-gradient(135deg, rgba(10,102,194,0.45), rgba(34,211,238,0.22));
        border: 1px solid rgba(34,211,238,0.5);
        box-shadow: 0 0 20px rgba(10,102,194,0.4);
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .li-badge:hover { transform: translateY(-2px); box-shadow: 0 0 30px rgba(34,211,238,0.7); }
    .li-badge svg { fill: #eaf1ff; }

    /* Glass cards (bordered containers) with animated gradient edge + hover lift */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        position: relative;
        background: linear-gradient(180deg, var(--glass), var(--glass-2)) !important;
        border: 1px solid var(--brd) !important;
        border-radius: 18px !important;
        box-shadow: 0 10px 44px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06);
        backdrop-filter: blur(12px);
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-3px);
        border-color: var(--brd-hi) !important;
        box-shadow: 0 16px 54px rgba(0,0,0,0.55), 0 0 30px rgba(34,211,238,0.18);
    }

    /* Buttons */
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        font-family: 'Space Grotesk', sans-serif; font-weight: 700; letter-spacing: .4px;
        border-radius: 12px; border: 1px solid rgba(34,211,238,0.55); color: #05070f;
        background: linear-gradient(135deg, var(--violet), var(--cyan));
        box-shadow: 0 6px 20px rgba(124,58,237,0.35);
        transition: transform .12s ease, box-shadow .12s ease, filter .12s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-1px); filter: brightness(1.1); color: #05070f;
        box-shadow: 0 0 26px rgba(34,211,238,0.6);
    }
    /* Secondary (non-primary) buttons: outlined glass */
    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.03); color: var(--ink);
        border: 1px solid var(--brd); box-shadow: none;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--brd-hi); color: var(--cyan);
        box-shadow: 0 0 18px rgba(34,211,238,0.25);
    }

    /* Widget labels */
    .stTextInput label, .stTextArea label, .stSelectbox label, .stRadio label,
    .stCheckbox label, .stFileUploader label {
        color: #c7d3f5 !important; font-weight: 600 !important; letter-spacing: .2px;
    }

    /* Inputs */
    .stTextInput input, .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(9,13,28,0.75) !important;
        border: 1px solid var(--brd) !important;
        border-radius: 11px !important; color: var(--ink) !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--cyan) !important;
        box-shadow: 0 0 0 3px rgba(34,211,238,0.22) !important;
    }

    /* File uploader dropzone */
    [data-testid="stFileUploaderDropzone"] {
        background: rgba(9,13,28,0.6) !important;
        border: 1.5px dashed rgba(34,211,238,0.4) !important; border-radius: 14px !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover { border-color: var(--cyan) !important; }

    /* Tabs as glowing pills */
    .stTabs [data-baseweb="tab-list"] {
        gap: .5rem; border-bottom: none; padding: .3rem;
        background: rgba(9,13,28,0.5); border: 1px solid var(--brd);
        border-radius: 14px; width: fit-content;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: .9rem;
        letter-spacing: .3px; color: var(--muted); border-radius: 10px;
        padding: .35rem 1rem;
    }
    .stTabs [data-baseweb="tab"]:hover { color: var(--ink); }
    .stTabs [aria-selected="true"] {
        color: #05070f !important;
        background: linear-gradient(135deg, var(--cyan), var(--violet));
        box-shadow: 0 0 18px rgba(34,211,238,0.45);
    }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

    /* Progress (fit score) bar */
    .stProgress > div > div > div { background: rgba(255,255,255,0.06) !important; border-radius: 99px; }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, var(--cyan), var(--violet), var(--pink)) !important;
        border-radius: 99px;
    }

    /* Inline code (used for job.source) -> neon pill */
    code {
        background: rgba(34,211,238,0.12) !important; color: #7fe9ff !important;
        border: 1px solid rgba(34,211,238,0.3); border-radius: 7px;
        padding: .05rem .45rem !important; font-size: .8rem;
    }
    a { color: var(--cyan) !important; }

    /* Alerts / status -> tinted glass */
    [data-testid="stAlert"], [data-testid="stNotification"] {
        border-radius: 12px !important; backdrop-filter: blur(8px);
        border: 1px solid var(--brd) !important;
    }
    [data-testid="stExpander"] details {
        background: var(--glass) !important; border: 1px solid var(--brd) !important;
        border-radius: 12px !important;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] { border: 1px solid var(--brd); border-radius: 12px; }

    /* Job cards */
    .job-title {
        font-family: 'Space Grotesk', system-ui, sans-serif; font-weight: 700;
        font-size: 1.18rem; color: #f4f8ff; line-height: 1.35; margin-bottom: .12rem;
        letter-spacing: .1px;
    }
    .job-company {
        font-family: 'Space Grotesk', system-ui, sans-serif; color: var(--cyan);
        font-weight: 600; font-size: .98rem; margin-bottom: .1rem;
    }
    .pill-row { display: flex; flex-wrap: wrap; gap: .4rem; margin: .55rem 0 .35rem; }
    .pill {
        font-size: .74rem; font-weight: 600; padding: .18rem .6rem; border-radius: 999px;
        border: 1px solid var(--brd); color: #c7d3f5; background: rgba(255,255,255,0.04);
    }
    .pill.remote { color: #6ee7b7; border-color: rgba(110,231,183,.4); background: rgba(16,185,129,.12); }
    .pill.src   { color: #7fe9ff; border-color: rgba(34,211,238,.35); background: rgba(34,211,238,.10); }
    .pill.sal   { color: #fde68a; border-color: rgba(251,191,36,.4); background: rgba(251,191,36,.12); }
    .pill.tracked {
        color: #c4b5fd; border-color: rgba(167,139,250,.5); background: rgba(139,92,246,.16);
        font-size: .68rem; vertical-align: middle;
    }
    a.pill { text-decoration: none !important; }
    a.pill:hover { border-color: var(--cyan); color: #bff3ff !important; }
    /* Fit score — donut ring gauge (fill % + color set inline per card) */
    .fit-ring {
        width: 78px; height: 78px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        margin: .1rem auto .35rem;
    }
    .fit-ring-inner {
        width: 60px; height: 60px; border-radius: 50%;
        background: #15171d;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Space Grotesk', system-ui, sans-serif; font-weight: 700;
        font-size: 1.4rem; letter-spacing: -.5px; color: #eef3ff;
        font-variant-numeric: tabular-nums;
    }
    .fit-label {
        text-align: center; font-family: 'Space Grotesk', sans-serif; font-weight: 600;
        font-size: .68rem; letter-spacing: 1px; text-transform: uppercase; opacity: .9;
        margin-bottom: .5rem;
    }
    .reason, .concern {
        font-family: 'Space Grotesk', system-ui, sans-serif; font-size: .94rem;
        line-height: 1.45; margin: .15rem 0;
    }
    .reason { color: #b6f5d6; } .concern { color: #ffdfb0; }

    /* Footer */
    .app-footer {
        position: relative; max-width: 640px; margin: 4rem auto 1.5rem;
        padding-top: 1.9rem; text-align: center;
        font-family: 'Space Grotesk', system-ui, sans-serif;
    }
    .app-footer::before {   /* glowing gradient hairline instead of a flat rule */
        content: ""; position: absolute; top: 0; left: 50%; transform: translateX(-50%);
        width: 200px; height: 2px; border-radius: 2px;
        background: linear-gradient(90deg, transparent, var(--cyan), var(--violet), transparent);
        box-shadow: 0 0 14px rgba(34, 211, 238, .55);
    }
    .app-footer .ft-tag { color: #c3cdea; font-size: .95rem; font-weight: 500; margin-bottom: .55rem; }
    .app-footer .ft-meta { color: var(--muted); font-size: .82rem; letter-spacing: .3px; }
    .app-footer a { color: var(--cyan) !important; text-decoration: none; font-weight: 600; }
    .app-footer a:hover { text-decoration: underline; }
    .app-footer .sep { opacity: .35; margin: 0 .55rem; }

    h1, h2, h3, h4 { font-family: 'Orbitron', sans-serif; color: #eef3ff; letter-spacing: .5px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Fixed header + cursor-reactive particle background ---------------------
# Both are injected via a same-origin components iframe rather than st.markdown.
# The header MUST live at document.body level: rendered through st.markdown it
# gets trapped inside Streamlit's block-container stacking context and sits
# UNDER the app header, so its LinkedIn link can't be clicked. Injected at the
# top level with a max z-index, the badge is reliably clickable. The <style>
# rules for .hero-bar / .li-badge (above) already live in the parent <head>.
components.html(
    """
    <script>
    (function () {
      const pdoc = window.parent.document;
      const LI_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"'
        + ' width="20" height="20"><path d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04'
        + '-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64'
        + '-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.45v6.29zM5.34 7.43a2.07 2.07 0 1 1 0'
        + '-4.14 2.07 2.07 0 0 1 0 4.14zm1.78 13.02H3.56V9h3.56v11.45zM22.22 0H1.77C.79'
        + ' 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1'
        + '.73C24 .77 23.2 0 22.22 0z"/></svg>';
      const old = pdoc.getElementById('nitesh-header');
      if (old) old.remove();
      const bar = pdoc.createElement('div');
      bar.id = 'nitesh-header';
      bar.className = 'hero-bar';
      bar.innerHTML =
        '<a class="li-badge" href="https://www.linkedin.com/in/niteshk38/"'
        + ' target="_blank" rel="noopener noreferrer">' + LI_SVG
        + '<span>Connect on LinkedIn</span></a>'
        + '<div class="hero">'
        + '<div class="hero-title">🚀 Optimo</div>'
        + '</div>'
        + '<div class="hero-sub">AI-powered <span class="dot">&middot;</span>'
        + ' find &amp; rank jobs <span class="dot">&middot;</span> tailor applications'
        + ' <span class="dot">&middot;</span> track progress</div>';
      pdoc.body.appendChild(bar);
    })();
    </script>
    <script>
    (function () {
      const pwin = window.parent, pdoc = pwin.document;
      if (pwin.__niteshBg) {
        try {
          cancelAnimationFrame(pwin.__niteshBg.raf);
          pwin.__niteshBg.canvas.remove();
          pwin.removeEventListener('mousemove', pwin.__niteshBg.onMove);
          pwin.removeEventListener('resize', pwin.__niteshBg.onResize);
        } catch (e) {}
      }
      const host = pdoc.querySelector('.stApp') || pdoc.body;
      const canvas = pdoc.createElement('canvas');
      Object.assign(canvas.style, {
        position: 'fixed', top: '0', left: '0', width: '100%', height: '100%',
        zIndex: '0', pointerEvents: 'none'
      });
      host.prepend(canvas);
      const ctx = canvas.getContext('2d');
      const mouse = { x: -999, y: -999 };
      let W, H, dots;

      function resize() {
        W = canvas.width = pwin.innerWidth;
        H = canvas.height = pwin.innerHeight;
        const n = Math.max(40, Math.min(120, Math.floor(W * H / 15000)));
        dots = Array.from({ length: n }, () => ({
          x: Math.random() * W, y: Math.random() * H,
          vx: (Math.random() - .5) * .45, vy: (Math.random() - .5) * .45
        }));
      }
      const onMove = e => { mouse.x = e.clientX; mouse.y = e.clientY; };
      const onResize = () => resize();
      resize();
      pwin.addEventListener('mousemove', onMove);
      pwin.addEventListener('resize', onResize);

      function frame() {
        ctx.clearRect(0, 0, W, H);
        for (const p of dots) {
          p.x += p.vx; p.y += p.vy;
          if (p.x < 0 || p.x > W) p.vx *= -1;
          if (p.y < 0 || p.y > H) p.vy *= -1;
          const dx = mouse.x - p.x, dy = mouse.y - p.y, d = Math.hypot(dx, dy);
          if (d < 170) { p.x += dx * 0.012; p.y += dy * 0.012; }  // drawn toward cursor
        }
        for (let i = 0; i < dots.length; i++) {
          const a = dots[i];
          for (let j = i + 1; j < dots.length; j++) {
            const b = dots[j], d = Math.hypot(a.x - b.x, a.y - b.y);
            if (d < 120) {
              ctx.strokeStyle = 'rgba(45,212,191,' + (1 - d / 120) * 0.22 + ')';
              ctx.lineWidth = 1;
              ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
            }
          }
          const md = Math.hypot(a.x - mouse.x, a.y - mouse.y);
          if (md < 190) {
            ctx.strokeStyle = 'rgba(56,130,246,' + (1 - md / 190) * 0.5 + ')';
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke();
          }
        }
        for (const p of dots) {
          ctx.fillStyle = 'rgba(190,225,255,0.85)';
          ctx.beginPath(); ctx.arc(p.x, p.y, 1.6, 0, 6.283); ctx.fill();
        }
        if (mouse.x > 0) {
          const g = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 150);
          g.addColorStop(0, 'rgba(45,212,191,0.17)');
          g.addColorStop(1, 'rgba(45,212,191,0)');
          ctx.fillStyle = g;
          ctx.fillRect(mouse.x - 150, mouse.y - 150, 300, 300);
        }
        pwin.__niteshBg.raf = pwin.requestAnimationFrame(frame);
      }
      pwin.__niteshBg = { canvas, onMove, onResize, raf: 0 };
      frame();
    })();
    </script>
    """,
    height=0,
)

_PORTAL_PRETTY = {"remoteok": "RemoteOK", "adzuna": "Adzuna", "greenhouse": "Greenhouse"}

# Collapse country/subdomains and publisher variants to one brand, so
# 'web:in.linkedin.com', 'web:sg.linkedin.com' and 'jsearch:LinkedIn' all
# become a single "LinkedIn" in the filter and pills.
_PORTAL_BRANDS = [
    ("linkedin", "LinkedIn"),
    ("instahyre", "Instahyre"),
    ("naukri", "Naukri"),
    ("indeed", "Indeed"),
    ("glassdoor", "Glassdoor"),
    ("foundit", "Foundit"),
]


def portal_name(source: str) -> str:
    """Clean portal label for display/filtering: 'jsearch:LinkedIn' and
    'web:in.linkedin.com' both -> 'LinkedIn'; 'remoteok' -> 'RemoteOK'."""
    name = source.split(":", 1)[1] if ":" in source else source
    low = name.lower()
    for needle, brand in _PORTAL_BRANDS:
        if needle in low:
            return brand
    return _PORTAL_PRETTY.get(low, name)


def job_age_days(posted_at) -> int | None:
    """Age of a posting in days, or None if it has no parseable date."""
    if not posted_at:
        return None
    try:
        dt = datetime.fromisoformat(str(posted_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max((datetime.now(timezone.utc) - dt).days, 0)
    except (ValueError, TypeError):
        return None


# Freshness options -> (jsearch date_posted param, client-side max age in days)
FRESHNESS = {
    "Any time": ("all", None),
    "Past 24 hours": ("today", 1),
    "Past 3 days": ("3days", 3),
    "Past week": ("week", 7),
    "Past month": ("month", 31),
}


search_tab, tailor_tab, tracker_tab = st.tabs(["🔎 Search", "✍️ Tailor", "📋 Tracker"])


# --- Search ----------------------------------------------------------------

with search_tab:
    col1, col2 = st.columns([2, 1])
    with col1:
        query = st.text_input("Search", value="Software Development Engineer in Test (SDET)")
        location = st.text_input("Location", value="")
    with col2:
        freshness = st.selectbox("Posted", list(FRESHNESS), index=0,
                                 help="Filters LinkedIn/Indeed by post date.")
        remote = st.checkbox("Remote only", value=False)
        use_llm = st.checkbox("Use LLM re-ranking", value=True,
                              help="Needs Ollama or an API key configured.")
    MAX_RESUME_MB = 10
    resume_file = st.file_uploader(
        "Attach your resume (PDF, TXT or MD) — optional, improves ranking & enables tailoring",
        type=["pdf", "txt", "md"],
        help=f"Max {MAX_RESUME_MB} MB.",
    )
    resume_text = ""  # populated from the attached file below

    if resume_file is not None and resume_file.size > MAX_RESUME_MB * 1024 * 1024:
        st.error(f"{resume_file.name} is {resume_file.size / 1024 / 1024:.1f} MB — "
                 f"please attach a resume under {MAX_RESUME_MB} MB.")
        resume_file = None
    if resume_file is not None:
        try:
            extracted = read_resume_bytes(resume_file.name, resume_file.getvalue())
            if extracted.strip():
                resume_text = extracted
            else:
                st.warning(f"Couldn't extract text from {resume_file.name} "
                           "(is it a scanned image?). Try a text-based PDF or a .txt/.md file.")
        except Exception as exc:
            st.error(f"Could not read {resume_file.name}: {exc}")

    # Remember the resume (and where it came from) across tabs/reruns so Tailor
    # can use it even if you haven't clicked Search since attaching it.
    if resume_text and resume_text.strip():
        st.session_state["resume_text"] = resume_text
        st.session_state["resume_name"] = (
            resume_file.name if resume_file is not None else "pasted resume"
        )

    if st.button("Search", type="primary"):
        # Broken into visible steps so a slow local model reads as "working",
        # not "hung". Each step reports what it's doing and whether AI is on.
        with st.status("Working…", expanded=True) as status:
            llm = build_llm(config)
            llm_ok = llm.available  # 3s reachability check; avoids 120s hangs below
            if use_llm and not llm_ok:
                st.info("LLM re-ranking is on but no model is reachable — using "
                        "keyword ranking. Start Ollama or set LLM_* in .env.")

            if resume_text:
                status.write("📄 Reading your resume "
                             + ("with AI…" if llm_ok else "(keywords — no LLM)…"))
                profile = build_profile(raw_text=resume_text,
                                        preferences=config.preferences,
                                        llm=llm if llm_ok else None)
            else:
                profile = build_profile(raw_text="", preferences=config.preferences)
            st.session_state["profile"] = profile

            # Freshness: server-side date filter for jsearch + remember the window
            # so we can also drop stale dated jobs from other sources client-side.
            date_posted, max_age = FRESHNESS[freshness]
            config.sources.setdefault("jsearch", {})["date_posted"] = date_posted
            st.session_state["max_age_days"] = max_age

            status.write("🔎 Fetching jobs from sources…")
            jobs = fetch_jobs(config, query, location=location or None,
                              remote=remote or None)
            status.write(f"Found **{len(jobs)}** jobs.")

            use_ai = use_llm and llm_ok
            if jobs and use_ai:
                k = min(len(jobs), int(config.matcher.get("rerank_k", 8)))
                is_local = "localhost" in llm.base_url or "127.0.0.1" in llm.base_url
                speed = " — local model, can take ~20s" if is_local else ""
                status.write(f"✨ Scoring the top {k} with AI ({llm.model}{speed})…")
            elif jobs:
                status.write("Scoring by keyword overlap…")

            st.session_state["results"] = rank(
                profile, jobs, llm=llm if use_ai else None,
                llm_weight=float(config.matcher.get("llm_weight", 0.7)),
                rerank_k=int(config.matcher.get("rerank_k", 8)),
            )
            status.update(
                label=f"Done — {len(st.session_state['results'])} matches.",
                state="complete", expanded=False,
            )

    results = st.session_state.get("results", [])
    if results:
        portals = sorted({portal_name(r.job.source) for r in results})
        # Keep any prior selection valid as portals change between searches.
        if "portal_filter" not in st.session_state:
            st.session_state["portal_filter"] = portals
        else:
            st.session_state["portal_filter"] = [
                p for p in st.session_state["portal_filter"] if p in portals
            ]

        # Jobs already in the tracker -> {job_id: status} for "Saved/Applied" badges.
        tracked = {row["job_id"]: row["status"] for row in tracker.list()}

        fcol, bcol, scol = st.columns([3, 1.2, 1])
        with bcol:
            st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
            b_all, b_clear = st.columns(2)
            # Set state BEFORE the multiselect is instantiated below, then rerun.
            if b_all.button("All", use_container_width=True):
                st.session_state["portal_filter"] = portals
                st.rerun()
            if b_clear.button("Clear", use_container_width=True):
                st.session_state["portal_filter"] = []
                st.rerun()
        selected = fcol.multiselect("Filter by portal", portals, key="portal_filter",
                                    help="Show only jobs from these portals.")
        sort_by = scol.selectbox("Sort by", ["Best fit", "Portal"])

        opt1, opt2 = st.columns(2)
        min_salary = opt1.number_input("Min salary (0 = any)", min_value=0, value=0, step=10000,
                                       help="Hides jobs whose listed salary is below this. "
                                            "Jobs with no salary listed are kept.")
        hide_tracked = opt2.checkbox("Hide jobs I've already saved/applied", value=False)

        max_age = st.session_state.get("max_age_days")
        shown = []
        for r in results:
            if portal_name(r.job.source) not in selected:
                continue
            if hide_tracked and r.job.id in tracked:
                continue
            if max_age is not None:
                age = job_age_days(r.job.posted_at)
                if age is not None and age > max_age:   # drop stale dated jobs; keep undated
                    continue
            if min_salary:
                top = r.job.salary_max or r.job.salary_min
                if top is not None and top < min_salary:  # drop below floor; keep unsalaried
                    continue
            shown.append(r)
        if sort_by == "Portal":
            shown = sorted(shown, key=lambda r: (portal_name(r.job.source).lower(), -r.score))

        note = "grouped by portal" if sort_by == "Portal" else "best first"
        st.markdown(f"### ⚡ {len(shown)} matches <span style='color:#9fb0da;font-size:.8rem;"
                    f"font-family:Space Grotesk'>· {note}</span>", unsafe_allow_html=True)
        for r in shown[:25]:
            with st.container(border=True):
                head, side = st.columns([5, 1])

                loc = r.job.location or ("Remote" if r.job.remote else "Location N/A")
                pills = f'<span class="pill">📍 {loc}</span>'
                if r.job.remote:
                    pills += '<span class="pill remote">🌐 Remote</span>'
                pills += f'<span class="pill src">🛰️ {portal_name(r.job.source)}</span>'
                # Salary (when the source provides it)
                if r.job.salary_min or r.job.salary_max:
                    lo, hi = r.job.salary_min, r.job.salary_max
                    if lo and hi:
                        sal = f"{lo:,.0f}–{hi:,.0f}"
                    else:
                        sal = f"{(lo or hi):,.0f}"
                    pills += f'<span class="pill sal">💰 {sal}</span>'
                # Freshness (when the posting has a date)
                age = job_age_days(r.job.posted_at)
                if age is not None:
                    fresh = "today" if age == 0 else (f"{age}d ago")
                    pills += f'<span class="pill">🕒 {fresh}</span>'
                # Already in the tracker?
                status_badge = ""
                if r.job.id in tracked:
                    status_badge = f'<span class="pill tracked">✓ {tracked[r.job.id].title()}</span>'
                if r.job.url:
                    pills += (f'<a class="pill src" href="{r.job.url}" target="_blank"'
                              f' rel="noopener">↗ Open on {portal_name(r.job.source)}</a>')
                reasons = "".join(f'<div class="reason">✅ {x}</div>' for x in r.reasons)
                concerns = "".join(f'<div class="concern">⚠️ {x}</div>' for x in r.concerns)
                head.markdown(
                    f'<div class="job-title">{r.job.title} {status_badge}</div>'
                    f'<div class="job-company">{r.job.company or "—"}</div>'
                    f'<div class="pill-row">{pills}</div>'
                    f'{reasons}{concerns}',
                    unsafe_allow_html=True,
                )
                head.progress(min(r.score / 100, 1.0), text=f"AI fit score · {r.score:.0f}/100")

                deg = round(min(r.score, 100) / 100 * 360)
                if r.score >= 70:
                    col, lab = "#34d399", "Strong match"
                elif r.score >= 40:
                    col, lab = "#22d3ee", "Good match"
                else:
                    col, lab = "#8ea0d0", "Fair match"
                side.markdown(
                    f'<div class="fit-ring" style="background:conic-gradient('
                    f'{col} {deg}deg, rgba(255,255,255,0.08) {deg}deg);">'
                    f'<div class="fit-ring-inner">{r.score:.0f}</div></div>'
                    f'<div class="fit-label" style="color:{col}">{lab}</div>',
                    unsafe_allow_html=True,
                )
                if r.job.id in tracked:
                    side.button("✓ Saved", key=f"save_{r.job.id}", disabled=True,
                                use_container_width=True)
                elif side.button("💾 Save", key=f"save_{r.job.id}",
                                 use_container_width=True):
                    tracker.save_job(r.job)
                    st.toast(f"Saved {r.job.title}")
                    st.rerun()


# --- Tailor ----------------------------------------------------------------

with tailor_tab:
    results = st.session_state.get("results", [])
    profile: Profile | None = st.session_state.get("profile")
    resume_text = st.session_state.get("resume_text", "")

    # Tailoring runs off your attached/pasted resume. If the current profile has
    # no resume text yet (e.g. you searched before attaching one), build it from
    # the remembered resume now so Tailor still works without re-running Search.
    if resume_text and (profile is None or not profile.raw_text):
        profile = build_profile(raw_text=resume_text, preferences=config.preferences)
        st.session_state["profile"] = profile

    if not results:
        st.info("Run a search first, then come back to tailor an application.")
    elif not profile or not profile.raw_text:
        st.warning("Attach your resume on the Search tab so tailoring "
                   "has something to work from.")
    else:
        resume_name = st.session_state.get("resume_name", "your resume")
        st.success(f"📄 Tailoring from **{resume_name}** "
                   f"({len(profile.raw_text):,} characters)")
        labels = [f"{r.job.title} — {r.job.company}" for r in results[:25]]
        choice = st.selectbox("Which job?", range(len(labels)),
                              format_func=lambda i: labels[i])
        job = results[choice].job
        kind = st.radio("Generate", ["Cover letter", "Resume bullets"], horizontal=True)
        if st.button("Generate", type="primary"):
            llm = build_llm(config)
            if not llm.available:
                st.error("No LLM reachable. Start Ollama or set LLM_BASE_URL/LLM_API_KEY in .env.")
            else:
                with st.spinner("Drafting..."):
                    if kind == "Cover letter":
                        st.write(cover_letter(profile, job, llm))
                    else:
                        for bullet in tailored_bullets(profile, job, llm):
                            st.markdown(f"- {bullet}")


# --- Tracker ---------------------------------------------------------------

with tracker_tab:
    rows = tracker.list()
    if not rows:
        st.info("Nothing tracked yet. Save jobs from the Search tab.")
    else:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.subheader("Update status")
        by_label = {f"{r['title']} @ {r['company']}": r["job_id"] for r in rows}
        pick = st.selectbox("Application", list(by_label))
        new_status = st.selectbox("Status", list(Application.VALID_STATUSES))
        if st.button("Update"):
            tracker.set_status(by_label[pick], new_status)
            st.rerun()

        csv_path = tracker.export_csv("applications.csv")
        st.download_button("⬇️ Export CSV", data=csv_path.read_bytes(),
                           file_name="applications.csv", mime="text/csv")


# --- Footer (shown on every tab) -------------------------------------------
st.markdown(
    """
    <div class="app-footer">
        <div class="ft-tag">Let AI find, rank &amp; tailor your next role — you make the call.</div>
        <div class="ft-meta">
            Built by <a href="https://www.linkedin.com/in/niteshk38/" target="_blank"
            rel="noopener noreferrer">Nitesh</a>
            <span class="sep">·</span>
            <a href="https://github.com/niteshk38/Optimo" target="_blank"
            rel="noopener noreferrer">Open-source</a>
            <span class="sep">·</span> © 2026
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
