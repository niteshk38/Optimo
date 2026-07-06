"""Configuration: non-secret settings live in config.yaml, secrets live in .env.

If config.yaml is missing we fall back to config.example.yaml so the project
runs out of the box. Secrets are read from the environment and never stored in
YAML.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

try:  # optional: load a local .env if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a convenience, not required
    pass


ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    llm: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    matcher: dict = field(default_factory=dict)
    preferences: dict = field(default_factory=dict)
    secrets: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | os.PathLike | None = None) -> "Config":
        chosen = _resolve_config_path(path)
        raw = yaml.safe_load(chosen.read_text()) if chosen and chosen.exists() else {}
        raw = raw or {}

        llm = raw.get("llm", {}) or {}
        # Environment overrides win, so hosted keys never need to touch YAML.
        llm.setdefault("base_url", "http://localhost:11434/v1")
        llm.setdefault("model", "llama3.1")
        if os.getenv("LLM_BASE_URL"):
            llm["base_url"] = os.environ["LLM_BASE_URL"]
        if os.getenv("LLM_MODEL"):
            llm["model"] = os.environ["LLM_MODEL"]

        secrets = {
            "adzuna_app_id": os.getenv("ADZUNA_APP_ID", ""),
            "adzuna_app_key": os.getenv("ADZUNA_APP_KEY", ""),
            "rapidapi_key": os.getenv("RAPIDAPI_KEY", ""),
            "google_cse_key": os.getenv("GOOGLE_CSE_KEY", ""),
            "google_cse_cx": os.getenv("GOOGLE_CSE_CX", ""),
            "serper_api_key": os.getenv("SERPER_API_KEY", ""),
            "llm_api_key": os.getenv("LLM_API_KEY", ""),
        }

        return cls(
            llm=llm,
            sources=raw.get("sources", {}) or {},
            matcher=raw.get("matcher", {}) or {},
            preferences=raw.get("preferences", {}) or {},
            secrets=secrets,
        )


def _resolve_config_path(path: str | os.PathLike | None) -> Path | None:
    if path:
        return Path(path)
    user_cfg = ROOT / "config.yaml"
    if user_cfg.exists():
        return user_cfg
    example = ROOT / "config.example.yaml"
    return example if example.exists() else None
