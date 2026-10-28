#!/usr/bin/env python3
"""Conflict-safe merge of public feed snapshots in a disposable GitHub runner.

This never checks out or modifies the owner's Windows PC, private JARVIS
repository or OAuth credentials. It takes data JSON prepared by the current
run, compares it with the most recent public GitHub branch and merges owner-
confirmed publication notices by immutable YouTube video IDs.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys

UTC = dt.timezone.utc
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
NEWS_CHANNEL = "news"
CHANNELS = ("original", "news")


def read(path):
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError):
        return {}


def stamp(obj):
    value = obj.get("updated_at")
    return value if isinstance(value, str) else ""


def write_if_changed(path, obj):
    output = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == output:
        return False
    path.write_text(output, encoding="utf-8")
    return True


def valid_owner_item(item):
    if not isinstance(item, dict):
        return False
    if item.get("channel") != NEWS_CHANNEL or item.get("source") != "owner_confirmed_public":
        return False
    vid, title = item.get("video_id"), item.get("title")
    if not isinstance(vid, str) or not VIDEO_ID.fullmatch(vid):
        return False
    if not isinstance(title, str) or not 5 <= len(title) <= 150:
        return False
    try:
        published = dt.datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
    except (KeyError, AttributeError, ValueError):
        return False
    if published.tzinfo is None:
        return False
    now = dt.datetime.now(UTC)
    return now - dt.timedelta(days=60) <= published <= now + dt.timedelta(minutes=5)


def merge_owner(remote, staged):
    by_id = {}
    # Later snapshot wins the duplicate if title metadata was corrected.
    for snapshot in sorted((remote, staged), key=stamp):
        for item in snapshot.get("items", []):
            if valid_owner_item(item):
                by_id[item["video_id"]] = item
    items = sorted(by_id.values(), key=lambda x: x["published"], reverse=True)[:30]
    return {
        "schema": 1,
        "updated_at": max(stamp(remote), stamp(staged)) or None,
        "items": items,
    }


def merge_video_items(snapshot, handoff):
    result = dict(snapshot) if snapshot else {}
    current = [x for x in result.get("items", [])
               if isinstance(x, dict) and x.get("channel") in CHANNELS
               and isinstance(x.get("video_id"), str) and VIDEO_ID.fullmatch(x["video_id"])
               and isinstance(x.get("title"), str)]
    by_id = {x["video_id"]: x for x in current}
    added = 0
    for item in handoff["items"]:
        if item["video_id"] not in by_id:
            by_id[item["video_id"]] = item
            added += 1
    selected = []
    for channel in CHANNELS:
        subset = [x for x in by_id.values() if x["channel"] == channel]
        subset.sort(key=lambda x: x.get("published", ""), reverse=True)
        selected.extend(subset[:20])
    selected.sort(key=lambda x: x.get("published", ""), reverse=True)
    result["items"] = selected
    if added:
        result["owner_confirmed_added"] = added
    return result


def merge(staging, destination):
    staging, destination = pathlib.Path(staging), pathlib.Path(destination)
    # For data fetched from public RSS, keep the newest complete snapshot.
    feed = {}
    for name in ("headlines", "videos"):
        remote = read(destination / (name + ".json"))
        staged = read(staging / (name + "-new.json"))
        feed[name] = staged if stamp(staged) > stamp(remote) else remote
    owner = merge_owner(read(destination / "jarvis_public.json"),
                        read(staging / "jarvis-new.json"))
    # Every authenticated owner-confirmed published video is visible promptly,
    # even if a different workflow updated the RSS snapshot concurrently.
    feed["videos"] = merge_video_items(feed["videos"], owner)
    changes = []
    for name, obj in (("headlines", feed["headlines"]),
                      ("videos", feed["videos"]),
                      ("jarvis_public", owner)):
        if obj and write_if_changed(destination / (name + ".json"), obj):
            changes.append(name)
    return changes


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python scripts/merge_snapshots.py STAGING_DIR DATA_DIR")
    changed = merge(sys.argv[1], sys.argv[2])
    print("Snapshots refreshed:", ", ".join(changed) if changed else "no changes")
