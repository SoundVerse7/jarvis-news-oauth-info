#!/usr/bin/env python3
"""Build short, source-attributed headline links from official RSS feeds.

- No paid API, third-party package, login, copyrighted photo or copied article body.
- Retains publication dates supplied by publishers; skips malformed/future/old items.
- Security: only accepts HTTPS links to known source domains and never renders HTML.
- Partial outages retain recent snapshots; complete outages preserve the last snapshot.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "headlines.json"
UTC = dt.timezone.utc

FEEDS = [
    ("UN News", "World", "https://news.un.org/feed/subscribe/en/news/all/rss.xml", "un.org"),
    ("Federal Reserve", "Economy", "https://www.federalreserve.gov/feeds/press_all.xml", "federalreserve.gov"),
    ("Bank of Canada", "Economy", "https://www.bankofcanada.ca/content_type/press/feed/", "bankofcanada.ca"),
    ("U.S. EIA", "Energy", "https://www.eia.gov/rss/todayinenergy.xml", "eia.gov"),
]


def clean_text(raw):
    value = html.unescape(re.sub(r"<[^>]*>", "", raw or ""))
    value = re.sub(r"\s+", " ", value).strip()
    return value[:185]


def https_source_link(raw, official_domain):
    try:
        u = urllib.parse.urlsplit((raw or "").strip())
        host = (u.hostname or "").lower()
        if u.scheme != "https" or u.username or u.password:
            return None
        if not (host == official_domain or host.endswith("." + official_domain)):
            return None
        return urllib.parse.urlunsplit(("https", u.netloc, u.path, u.query, ""))
    except (ValueError, TypeError):
        return None


def parse_date(raw):
    if not raw:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        try:
            parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def text_by_names(node, names):
    wanted = set(names)
    for element in node:
        name = element.tag.rsplit("}", 1)[-1]
        if name in wanted and element.text:
            return element.text.strip()
    return ""


def parse_feed(raw, name, category, domain, now):
    root = ET.fromstring(raw)
    raw_items = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] in ("item", "entry")]
    news = []
    for entry in raw_items[:60]:
        title = clean_text(text_by_names(entry, ("title",)))
        link = text_by_names(entry, ("link",))
        if not link:
            for el in entry:
                if el.tag.rsplit("}", 1)[-1] == "link":
                    link = el.attrib.get("href", "")
                    if link:
                        break
        date = parse_date(text_by_names(entry, ("pubDate", "published", "updated", "date")))
        url = https_source_link(link, domain)
        if not title or not url or not date or len(title) < 12:
            continue
        if date > now or date < now - dt.timedelta(days=14):
            continue
        news.append({
            "id": hashlib.sha256(url.encode("utf-8")).hexdigest()[:16],
            "title": title, "url": url, "source": name,
            "category": category,
            "published": date.isoformat(timespec="seconds").replace("+00:00", "Z")
        })
        if len(news) >= 18:
            break
    return news


def fetch(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "PublicMindReportHeadlines/1.0 (public-source RSS reader)",
                      "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml;q=0.9"})
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError("HTTP " + str(response.status))
        raw = response.read(1_050_000)
        if len(raw) > 1_000_000:
            raise ValueError("feed exceeds size limit")
        return raw


def main():
    now = dt.datetime.now(UTC)
    previous = {}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    articles, successful_sources = [], set()
    results = []
    for name, category, url, domain in FEEDS:
        try:
            chunk = parse_feed(fetch(url), name, category, domain, now)
            articles.extend(chunk)
            successful_sources.add(name)
            results.append({"source": name, "status": "ok", "recent_headlines": len(chunk)})
            print("OK:", name, len(chunk))
        except Exception as e:
            results.append({"source": name, "status": "unavailable"})
            print("UNAVAILABLE:", name, type(e).__name__, str(e)[:130], file=sys.stderr)

    # Keep recently observed items when a single publisher's feed is temporarily down.
    for item in previous.get("items", []):
        if item.get("source") in successful_sources:
            continue
        matching = next((f for f in FEEDS if f[0] == item.get("source")), None)
        if not matching:
            continue
        published = parse_date(item.get("published"))
        url = https_source_link(item.get("url"), matching[3])
        if published and url and now - dt.timedelta(days=7) <= published <= now:
            articles.append(item)

    # Never replace working data with an empty feed on an outage.
    if not articles and previous.get("items"):
        print("No valid fresh headlines; preserving the last working snapshot")
        return 0

    by_id = {}
    for item in articles:
        key = item["url"]
        if key not in by_id:
            by_id[key] = item
    grouped = {"World": [], "Economy": [], "Energy": []}
    for item in by_id.values():
        grouped[item["category"]].append(item)
    selected = []
    for category in grouped:
        selected.extend(sorted(grouped[category],
                               key=lambda x: x["published"], reverse=True)[:16])
    selected.sort(key=lambda x: x["published"], reverse=True)
    data = {"updated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "sources": results, "items": selected}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Total source-linked headlines:", len(selected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
