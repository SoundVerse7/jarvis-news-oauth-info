#!/usr/bin/env python3
"""Snapshot the owner's public YouTube video titles and links via free Atom feeds.

Does not use OAuth, YouTube API quota, third-party packages, or private user data.
It does not publish, modify or connect to either YouTube account.
"""
from __future__ import annotations

import datetime as dt
import json
import re
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
    if channel_id != channel["id"]:
        raise ValueError("RSS channel identity mismatch")
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
    with urllib.request.urlopen(req, timeout=22) as response:
        data = response.read(260_000)
        if len(data) >= 260_000:
            raise ValueError("Too much RSS data")
        return data


def main():
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    records = []
    status = []
    for channel in CHANNELS:
        try:
            latest = parse_channel(fetch(channel["id"]), channel)
            status.append({"channel": channel["key"], "status": "ok", "videos": len(latest)})
            records.extend(latest)
            print(channel["key"], len(latest), "public videos")
        except Exception as exc:
            # Keep last cached public videos when a feed is temporarily unavailable.
            previous = [x for x in old.get("items", []) if x.get("channel") == channel["key"]
                        and VIDEO_ID.fullmatch(str(x.get("video_id", ""))) and x.get("title")]
            records.extend(previous[:12])
            status.append({"channel": channel["key"], "status": "unavailable"})
            print(channel["key"], "RSS unavailable:", type(exc).__name__, str(exc)[:100])
    records.sort(key=lambda x: x.get("published", ""), reverse=True)
    result = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "channels": CHANNELS, "status": status, "items": records[:24]
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Video items:", len(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
