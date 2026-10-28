#!/usr/bin/env python3
"""Quick CI checks for public website, two-channel ID safety and feed parsing."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("videos", ROOT / "scripts" / "update_videos.py")
videos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(videos)

handoff_spec = importlib.util.spec_from_file_location("handoff", ROOT / "scripts" / "ingest_publication.py")
handoff = importlib.util.module_from_spec(handoff_spec)
handoff_spec.loader.exec_module(handoff)

merge_spec = importlib.util.spec_from_file_location("merge_snapshots", ROOT / "scripts" / "merge_snapshots.py")
merge_snapshots = importlib.util.module_from_spec(merge_spec)
merge_spec.loader.exec_module(merge_snapshots)


class WebsiteChecks(unittest.TestCase):
    def test_correct_distinct_youtube_channels(self):
        channels = {x["key"]: x for x in videos.CHANNELS}
        self.assertEqual(channels["original"]["id"], "UCAVVVfl6qdT1JZsndhyhetA")
        self.assertEqual(channels["news"]["id"], "UCc3QJDTVAvImoGQSHOHTu3Q")
        self.assertNotEqual(channels["original"]["id"], channels["news"]["id"])

    def test_atom_channel_identity_and_valid_video(self):
        channel = videos.CHANNELS[1]
        published = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).isoformat()
        xml = f'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
  <yt:channelId>{channel["id"][2:]}</yt:channelId>
  <entry><yt:videoId>UdsaqB9anuo</yt:videoId><title>News story</title>
  <published>{published}</published></entry>
</feed>'''
        result = videos.parse_channel(xml.encode(), channel)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["video_id"], "UdsaqB9anuo")
        self.assertEqual(result[0]["channel"], "news")

    def test_atom_rejects_other_channel(self):
        other = videos.CHANNELS[0]
        xml = f'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
  <yt:channelId>{other["id"]}</yt:channelId></feed>'''
        with self.assertRaises(ValueError):
            videos.parse_channel(xml.encode(), videos.CHANNELS[1])

    def test_at_least_one_public_video_link_per_channel(self):
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        library = (ROOT / "videos.html").read_text(encoding="utf-8")
        for channel in videos.CHANNELS:
            url = "https://www.youtube.com/" + channel["handle"]
            with self.subTest(channel=channel["key"]):
                self.assertIn(url, homepage)
                self.assertIn(url, library)

    def test_video_library_in_sitemap_and_homepage(self):
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("/videos.html", sitemap)
        ET.fromstring(sitemap)
        self.assertIn('href="videos.html"', (ROOT / "index.html").read_text(encoding="utf-8"))

    def test_json_snapshots_have_expected_structure(self):
        for filename in ("headlines.json", "videos.json"):
            with self.subTest(snapshot=filename):
                data = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
                self.assertIn("items", data)
                self.assertIsInstance(data["items"], list)

    def test_website_discloses_generic_channel_links(self):
        script = (ROOT / "assets" / "newsroom.js").read_text(encoding="utf-8")
        self.assertIn("YouTube video with similar title keywords", script)
        self.assertIn("Explore our World News channel", script)
        self.assertIn("Explore our Economy & Commentary videos", script)
        self.assertIn("shared >= 2", script)
        self.assertIn("Similar words do not establish", script)

    def test_outage_keeps_video_and_last_success(self):
        original = videos.CHANNELS[0]
        prior = {
            "updated_at": "2026-10-27T21:00:00Z",
            "items": [{"channel":"original","channel_name":original["name"],
                       "video_id":"HjEuopztg3I","title":"Public sample","published":"2026-10-24T23:59:07Z"}],
            "status": [{"channel":"original","status":"ok","videos":1,
                        "last_success_at":"2026-10-27T19:00:00Z"}]
        }
        with tempfile.TemporaryDirectory() as tempdir:
            path = pathlib.Path(tempdir) / "videos.json"
            path.write_text(json.dumps(prior), encoding="utf-8")
            with mock.patch.object(videos, "OUT", path):
                with mock.patch.object(videos, "fetch", side_effect=OSError("Temporary public feed outage")):
                    self.assertEqual(videos.main(), 0)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["items"]), 1)
            original_status = next(x for x in data["status"] if x["channel"] == "original")
            self.assertEqual(original_status["status"], "unavailable")
            self.assertEqual(original_status["last_success_at"], "2026-10-27T19:00:00Z")
            self.assertNotEqual(original_status["last_success_at"], data["updated_at"])

    @staticmethod
    def public_news_payload():
        now = dt.datetime.now(dt.timezone.utc)
        return {
            "channel_id": "UCc3QJDTVAvImoGQSHOHTu3Q",
            "verified_channel_id": "UCc3QJDTVAvImoGQSHOHTu3Q",
            "privacy_status": "public",
            "verified_public": True,
            "video_id": "AbC123defG_",
            "title": "Example verified public video",
            "published": (now - dt.timedelta(minutes=5)).isoformat()
        }

    def test_handoff_rejects_wrong_channel_and_private_video(self):
        good = self.public_news_payload()
        self.assertEqual(handoff.validate(good)["channel"], "news")
        for changes in (
            {"channel_id":"UCAVVVfl6qdT1JZsndhyhetA"},
            {"verified_channel_id":"UCAVVVfl6qdT1JZsndhyhetA"},
            {"privacy_status":"private"},
            {"verified_public":False},
            {"video_id":"bad id"},
            {"published":"2020-01-01T00:00:00Z"},
            {"published":"not a timestamp"}
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                handoff.validate({**good, **changes})

    def test_handoff_is_deduplicated_and_preserves_channel(self):
        with tempfile.TemporaryDirectory() as folder:
            file = pathlib.Path(folder) / "jarvis_public.json"
            payload = self.public_news_payload()
            handoff.ingest(payload, path=file)
            handoff.ingest(payload, path=file)
            saved = json.loads(file.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["items"]), 1)
            self.assertEqual(saved["items"][0]["video_id"], payload["video_id"])
            self.assertEqual(saved["items"][0]["channel"], "news")
            self.assertEqual(saved["items"][0]["source"], "owner_confirmed_public")

    def test_public_handoff_appears_when_rss_is_unavailable(self):
        with tempfile.TemporaryDirectory() as folder:
            base = pathlib.Path(folder)
            payload = self.public_news_payload()
            handoff.ingest(payload, path=base / "jarvis_public.json")
            with mock.patch.object(videos, "OUT", base / "videos.json"):
                with mock.patch.object(videos, "fetch", side_effect=OSError("RSS outage")):
                    self.assertEqual(videos.main(), 0)
            snapshot = json.loads((base / "videos.json").read_text(encoding="utf-8"))
            matches = [x for x in snapshot["items"] if x["video_id"] == payload["video_id"]]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["channel"], "news")
            self.assertEqual(snapshot["owner_confirmed_added"], 1)

    def test_public_snapshot_merge_preserves_all_owner_events(self):
        with tempfile.TemporaryDirectory() as folder:
            base = pathlib.Path(folder)
            stage, remote = base / "stage", base / "remote"
            stage.mkdir()
            remote.mkdir()
            now = dt.datetime.now(dt.timezone.utc)
            early = (now - dt.timedelta(minutes=6)).isoformat()
            late = (now - dt.timedelta(minutes=2)).isoformat()
            first = handoff.validate(self.public_news_payload())
            second = dict(first, video_id="ZyX987uvwQ_", title="Another public news video")
            def save(folder, name, data):
                (folder / name).write_text(json.dumps(data), encoding="utf-8")
            save(stage, "jarvis-new.json", {"schema":1,"updated_at":early,"items":[first]})
            save(remote, "jarvis_public.json", {"schema":1,"updated_at":late,"items":[second]})
            save(stage, "headlines-new.json", {"updated_at":early,"items":[{"id":"old"}]})
            save(remote, "headlines.json", {"updated_at":late,"items":[{"id":"newer"}]})
            save(stage, "videos-new.json", {"updated_at":early,"items":[]})
            save(remote, "videos.json", {"updated_at":late,
                "items":[{"channel":"original","video_id":"HjEuopztg3I",
                          "title":"Original public video","published":early}]})
            changes = merge_snapshots.merge(stage, remote)
            self.assertIn("jarvis_public", changes)
            owner = json.loads((remote / "jarvis_public.json").read_text())
            self.assertEqual(set(x["video_id"] for x in owner["items"]),
                             {first["video_id"], second["video_id"]})
            news = json.loads((remote / "videos.json").read_text())
            self.assertEqual(set(x["video_id"] for x in news["items"]),
                             {"HjEuopztg3I", first["video_id"], second["video_id"]})
            headlines = json.loads((remote / "headlines.json").read_text())
            self.assertEqual(headlines["items"][0]["id"], "newer")

    def test_no_public_payment_promotions(self):
        for page in ("index.html", "channels.html", "videos.html"):
            content = (ROOT / page).read_text(encoding="utf-8").lower()
            for word in ("sponsorship", "donate now", "buy now", "paid memberships"):
                self.assertNotIn(word, content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
