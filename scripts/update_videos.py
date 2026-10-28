#!/usr/bin/env python3
"""Snapshot the owner's public YouTube video titles and links via free Atom feeds.

Does not use OAuth, YouTube API quota, third-party packages, or private user data.
It does not publish, modify or connect to either YouTube account.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "videos.json"
ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"
CHANNELS = [
    {"key": "original", "name": "PUBLIC MIND REPORT", "id": "UCAVVVfl6qdT1JZsndhyhetA", "handle": "@PUBLICMINDREPORT"},
    {"key": "news", "name": "PUBLIC MIND REPORT - WORLD NEWS", "id": "UCc3QJDTVAvImoGQSHOHTu3Q", "handle": "@PublicMindReportNews"},
]
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def parse_channel(feed_bytes, channel):
    root = ET.fromstring(feed_bytes)
    channel_id = root.findtext(YT + "channelId", "").strip()
    if not channel_id:
        atom_id = root.findtext(ATOM + "id", "").strip()
        if atom_id.startswith("yt:channel:"):
            channel_id = atom_id.removeprefix("yt:channel:")
    # YouTube Atom feed identifiers may omit the leading UC prefix used by channel URLs.
    if channel_id not in (channel["id"], channel["id"][2:]):
        raise ValueError(f"RSS channel identity mismatch: expected {channel['id']}; got {channel_id!r}; root: {root.tag}")
    items = []
    now = dt.datetime.now(dt.timezone.utc)
    for entry in root.findall(ATOM + "entry"):
        vid = entry.findtext(YT + "videoId", "").strip()
        title = " ".join((entry.findtext(ATOM + "title") or "").split())[:170]
        published = entry.findtext(ATOM + "published")
        if not VIDEO_ID.fullmatch(vid) or not title or not published:
            continue
        try:
            stamp = dt.datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=dt.timezone.utc)
        if stamp > now:
            continue
        items.append({
            "channel": channel["key"], "channel_name": channel["name"],
            "video_id": vid, "title": title,
            "published": stamp.isoformat(timespec="seconds").replace("+00:00", "Z")
        })
    return sorted(items, key=lambda x: x["published"], reverse=True)[:12]


def fetch(channel_id):
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; PublicMindReportSite/1.0)",
        "Accept": "application/atom+xml,application/xml;q=0.9"
    })
    # Public YouTube Atom feeds occasionally give a transient 404/429/5xx.
    # Retry only once, politely; never bypass a block or request private data.
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=22) as response:
                data = response.read(260_000)
                if len(data) >= 260_000:
                    raise ValueError("Too much RSS data")
                return data
        except urllib.error.HTTPError as exc:
            if attempt == 0 and exc.code in (404, 429, 500, 502, 503, 504):
                time.sleep(2)
                continue
            raise


def main():
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    records = []
    status = []
    attempted_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    prior_status = {s.get("channel"): s for s in old.get("status", []) if isinstance(s, dict)}
    for channel in CHANNELS:
        try:
            latest = parse_channel(fetch(channel["id"]), channel)
            status.append({"channel": channel["key"], "status": "ok", "videos": len(latest),
                           "last_success_at": attempted_at})
            records.extend(latest)
            print(channel["key"], len(latest), "public videos")
        except Exception as exc:
            # Keep last cached public videos when a feed is temporarily unavailable.
            previous = [x for x in old.get("items", []) if x.get("channel") == channel["key"]
                        and VIDEO_ID.fullmatch(str(x.get("video_id", ""))) and x.get("title")]
            records.extend(previous[:12])
            earlier = prior_status.get(channel["key"], {})
            # Only claim a previously confirmed refresh time. Never use this
            # attempt's timestamp as the last successful YouTube update.
            previous_success = earlier.get("last_success_at")
            if not previous_success and earlier.get("status") == "ok":
                previous_success = old.get("updated_at")
            status.append({"channel": channel["key"], "status": "unavailable",
                           "videos": len(previous), "last_success_at": previous_success})
            print(channel["key"], "RSS unavailable:", type(exc).__name__, str(exc)[:100])
    records.sort(key=lambda x: x.get("published", ""), reverse=True)
    result = {
        "updated_at": attempted_at,
        "channels": CHANNELS, "status": status, "items": records[:24]
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Video items:", len(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
