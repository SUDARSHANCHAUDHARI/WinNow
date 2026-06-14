"""Config loading: process env + an optional repo-root .env, with placeholder
detection so dormant keys never trigger a broken API call.

A value is treated as UNSET when it is empty or looks like a placeholder
(your_..., changeme, placeholder, xxx). This lets us ship .env.example with
obvious dummies and have the engine cleanly fall back to keyless paths.
"""

from __future__ import annotations

import os
from pathlib import Path

_PLACEHOLDER_MARKERS = ("your_", "changeme", "placeholder", "xxx", "<", "todo")


def _is_placeholder(value: str) -> bool:
    v = value.strip().lower()
    if not v:
        return True
    return any(m in v for m in _PLACEHOLDER_MARKERS)


def load(start: Path | None = None) -> dict[str, str]:
    """Merge a repo-root .env under process env (process env wins)."""
    config: dict[str, str] = {}
    root = (start or Path(__file__).resolve()).parents[2]  # engine/lib/env.py -> repo root
    env_file = root / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            config[key.strip()] = val.strip().strip('"').strip("'")
    config.update({k: v for k, v in os.environ.items()})
    return config


def get(config: dict[str, str], key: str) -> str | None:
    """Return a usable value, or None if missing/placeholder."""
    val = config.get(key, "")
    return None if _is_placeholder(val) else val


def reddit_creds(config: dict[str, str]) -> tuple[str, str, str] | None:
    """(client_id, client_secret, user_agent) or None when not configured."""
    cid = get(config, "REDDIT_CLIENT_ID")
    secret = get(config, "REDDIT_CLIENT_SECRET")
    if not cid or not secret:
        return None
    ua = get(config, "REDDIT_USER_AGENT") or "winnow/0.1 (authenticity research)"
    return cid, secret, ua
