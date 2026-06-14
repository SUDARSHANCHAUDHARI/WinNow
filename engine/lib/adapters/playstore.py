"""Play Store reviews via the batchexecute RPC (UsvDTd).

Probed live: the endpoint returns HTTP 200 with a wrb.fr envelope. This is
the gap that matters most for an indie Android dev. Topic is a package id
(e.g. com.whatsapp). Best-effort parser: returns [] on any shape mismatch
rather than crashing, so a Play Store template change degrades gracefully
(fixing last30days loophole #2 — no hard dependency on undocumented markup).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from .. import http
from ..schema import Item

_RPC = "https://play.google.com/_/PlayStoreUi/data/batchexecute?hl={hl}&gl={gl}"
_SEARCH = "https://play.google.com/store/search?q={q}&c=apps&hl={hl}&gl={gl}"
# A package id: dotted, lowercase-ish reverse-domain (e.g. com.whatsapp).
_PACKAGE_RE = re.compile(r"^[A-Za-z][\w]*(\.[A-Za-z0-9_]+)+$")
_DETAILS_RE = re.compile(r"store/apps/details\?id=([A-Za-z0-9._]+)")


def resolve_package_id(name: str, *, hl: str = "en", gl: str = "us") -> str | None:
    """Resolve a free-text app name to the top Play Store package id."""
    if _PACKAGE_RE.match(name.strip()):
        return name.strip()
    url = _SEARCH.format(q=http.urllib.parse.quote(name), hl=hl, gl=gl)
    try:
        html_text = http.get(url)
    except http.HTTPError:
        return None
    m = _DETAILS_RE.search(html_text)
    return m.group(1) if m else None


def _build_freq(app_id: str, count: int, sort: int = 2) -> str:
    # sort: 1=relevant, 2=newest. Inner payload is itself JSON-encoded.
    inner = json.dumps(
        [None, None, [2, sort, [count, None, None], None, [None, None]], [app_id, 7]]
    )
    return json.dumps([[["UsvDTd", inner, None, "generic"]]])


def fetch(topic: str, *, lookback_days: int = 30, limit: int = 50,
          hl: str = "en", gl: str = "us") -> list[Item]:
    app_id = resolve_package_id(topic, hl=hl, gl=gl)
    if not app_id:
        return []
    url = _RPC.format(hl=hl, gl=gl)
    body = "f.req=" + http.urllib.parse.quote(_build_freq(app_id, limit))
    try:
        raw = http.post(url, body,
                        headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    except http.HTTPError:
        return []

    reviews = _extract_reviews(raw)
    items: list[Item] = []
    for r in reviews[:limit]:
        items.append(
            Item(
                source="playstore",
                item_id=str(r.get("id", "")),
                title="",
                text=r.get("text", ""),
                url=f"https://play.google.com/store/apps/details?id={app_id}",
                author=r.get("author", ""),
                published_at=r.get("date"),
                rating=r.get("rating"),
                engagement=float(r.get("helpful", 0) or 0),
                metadata={"app_id": app_id, "version": r.get("version", "")},
            )
        )
    return items


def _extract_reviews(raw: str) -> list[dict]:
    """Dig review tuples out of the nested wrb.fr envelope. Defensive."""
    raw = raw.lstrip()
    if raw.startswith(")]}'"):
        raw = raw.split("\n", 1)[-1]
    out: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            envelope = json.loads(line)
        except ValueError:
            continue
        for frame in envelope:
            if not (isinstance(frame, list) and frame and frame[0] == "wrb.fr"):
                continue
            payload_str = frame[2] if len(frame) > 2 else None
            if not isinstance(payload_str, str):
                continue
            try:
                payload = json.loads(payload_str)
            except ValueError:
                continue
            out.extend(_walk_review_rows(payload))
    return out


def _walk_review_rows(payload) -> list[dict]:
    rows: list[dict] = []
    # Review rows look like: [review_id, [author, ...], rating, ..., text, ...]
    if not isinstance(payload, list):
        return rows
    # Review row layout (verified against live com.whatsapp response 2026-06):
    #   [0] id  [1] [author, ...]  [2] rating  [4] text  [5] [epoch_s, nanos]
    #   [6] helpful-count  [10] app version
    for row in payload[0] if (payload and isinstance(payload[0], list)) else []:
        try:
            review_id = row[0]
            author = row[1][0] if isinstance(row[1], list) and row[1] else ""
            rating = row[2] if isinstance(row[2], (int, float)) else None
            text = row[4] if len(row) > 4 and isinstance(row[4], str) else ""
            ts = None
            if len(row) > 5 and isinstance(row[5], list) and row[5] and isinstance(row[5][0], int):
                ts = datetime.fromtimestamp(row[5][0], tz=timezone.utc)
            helpful = row[6] if len(row) > 6 and isinstance(row[6], int) else 0
            version = row[10] if len(row) > 10 and isinstance(row[10], str) else ""
            rows.append({"id": review_id, "author": author, "rating": rating,
                         "text": text, "date": ts, "helpful": helpful, "version": version})
        except (IndexError, TypeError):
            continue
    return rows
