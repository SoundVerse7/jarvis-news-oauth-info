#!/usr/bin/env python3
"""Owner-authorized public-only YouTube publication handoff.

Runs only within an authenticated GitHub repository_dispatch workflow.
No OAuth, passwords, API keys, private video metadata, or visitor data are stored.
The JARVIS agent must independently verify the selected channel and public status
with YouTube before dispatching; this receiver never changes YouTube.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "jarvis_public.json"
NEWS_CHANNEL = "UCc3QJDTVAvImoGQSHOHTu3Q"
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
UTC = dt.timezone.utc


def validate(payload, now=None):
    if not isinstance(payload, dict):
        raise ValueError("Expected an object")
    if payload.get("channel_id") != NEWS_CHANNEL:
        raise ValueError("Channel mismatch: only Public Mind Report - World News is allowed")
    if payload.get("verified_channel_id") != NEWS_CHANNEL:
        raise ValueError("No matching YouTube channel confirmation")
    if payload.get("privacy_status") != "public" or payload.get("verified_public") is not True:
        raise ValueError("A public YouTube status read-back is required")
    vid = payload.get("video_id")
    if not isinstance(vid, str) or not VIDEO_ID.fullmatch(vid):
        raise ValueError("Invalid YouTube video ID")
    title = payload.get("title")
    if not isinstance(title, str):
        raise ValueError("Missing title")
    title = " ".join(title.split()).strip()
    if len(title) < 5 or len(title) > 150 or any(ord(c) < 32 for c in title):
        raise ValueError("Title is missing or too long")
    when = payload.get("published")
    if not isinstance(when, str):
        raise ValueError("Missing publication timestamp")
    try:
        published = dt.datetime.fromisoformat(when.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid publication timestamp") from exc
    if published.tzinfo is None:
        raise ValueError("Publication timestamp must include a timezone")
    published = published.astimezone(UTC)
    now = now or dt.datetime.now(UTC)
    if not (now - dt.timedelta(days=60) <= published <= now + dt.timedelta(minutes=5)):
        raise ValueError("Publication timestamp outside accepted 60-day window")
    return {
        "channel": "news",
        "channel_name": "PUBLIC MIND REPORT - WORLD NEWS",
        "video_id": vid,
        "title": title,
        "published": published.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "owner_confirmed_public",
    }


def ingest(payload, path=OUT, now=None):
    item = validate(payload, now=now)
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    all_items = [x for x in old.get("items", [])
                 if isinstance(x, dict) and x.get("channel") == "news"
                 and isinstance(x.get("video_id"), str) and VIDEO_ID.fullmatch(x["video_id"])
                 and x["video_id"] != item["video_id"]]
    all_items.append(item)
    all_items.sort(key=lambda x: x.get("published", ""), reverse=True)
    output = {"schema": 1,
              "updated_at": dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
              "items": all_items[:30]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return item


def main():
    # Authenticated GitHub workflow sets this from repository_dispatch.client_payload.
    payload = os.environ.get("JARVIS_PUBLIC_PAYLOAD")
    if not payload:
        raise SystemExit("No authenticated dispatch data was supplied")
    parsed = json.loads(payload)
    item = ingest(parsed)
    print("Accepted public-only JARVIS video notification:", item["video_id"])


if __name__ == "__main__":
    main()
