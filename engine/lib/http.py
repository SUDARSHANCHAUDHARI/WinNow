"""Minimal stdlib HTTP. Zero third-party deps (the last30days discipline)."""

from __future__ import annotations

import json as _json
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_UA = "Mozilla/5.0 (Winnow research engine)"
DEFAULT_TIMEOUT = 15


class HTTPError(Exception):
    pass


def get(url: str, *, headers: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise HTTPError(f"GET {url} failed: {exc}") from exc


def get_json(url: str, *, headers: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    raw = get(url, headers=headers, timeout=timeout)
    # Strip XSSI guard prefixes like )]}' used by some Google endpoints.
    raw = raw.lstrip()
    if raw.startswith(")]}'"):
        raw = raw.split("\n", 1)[-1]
    return _json.loads(raw)


def post(url: str, data: dict | str, *, headers: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data.encode()
    req = urllib.request.Request(url, data=body, headers={"User-Agent": DEFAULT_UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise HTTPError(f"POST {url} failed: {exc}") from exc
