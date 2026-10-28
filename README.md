# PUBLIC MIND REPORT — News Site & Two YouTube Channels

**Public website:** https://soundverse7.github.io/jarvis-news-oauth-info/

A free public static newsroom with a source-linked world/economy/energy headline feed and original explainers. The website directs visitors to **two distinct YouTube channels**, with no login or user account required.

## Follow both channels

| Channel | Handle | Purpose |
|---|---|---|
| Public Mind Report | [@PUBLICMINDREPORT](https://www.youtube.com/@PUBLICMINDREPORT) | Commentary, podcasts and analysis of world affairs and the economy |
| Public Mind Report - World News | [@PublicMindReportNews](https://www.youtube.com/@PublicMindReportNews) | World news, updates and Shorts |

The old channel ID `UCAVVVfl6qdT1JZsndhyhetA` and the news channel ID `UCc3QJDTVAvImoGQSHOHTu3Q` remain separate. Neither is altered or uploaded to by this website.

## Pages

- `index.html` — homepage, both channel links, source-attributed headlines, latest public videos
- `channels.html` — both YouTube channels, two subscribe links, recent public videos
- `videos.html` — searchable recent video library with per-channel filters, video thumbnails and direct YouTube links
- `insights.html` — original explainers about oil, interest rates and verifying footage
- `editorial.html` — editorial and correction policies
- `app.html` — desktop JARVIS News Autopilot Google OAuth application information
- `privacy.html` and `terms.html` — site and desktop app policies
- `support.html` — old URL now redirected to `channels.html`
- `sitemap.xml` and `robots.txt` — discoverable site pages

## Automated feeds (public data only)

The free GitHub Actions workflow `.github/workflows/refresh-headlines.yml` runs on an hourly schedule and on manual request. It refreshes:

- `data/headlines.json`, from public RSS feeds by UN News, Federal Reserve, Bank of Canada, U.S. EIA. Original headlines and publication dates link directly to official publishers; no article bodies or source pictures copied.
- `data/videos.json`, from publicly accessible YouTube Atom feeds for both channels. Only public video IDs, titles and dates are recorded; video previews link to YouTube. YouTube's public feeds are subject to service availability; temporary errors keep the last known public videos instead of deleting them. The video index is limited to recent public feed entries, not the entire YouTube back catalogue.

The homepage and video-library pages use the public GitHub Contents API to read current snapshots, with a Pages-hosted JSON fallback. GitHub Actions may not publish updates exactly on the hour, and video availability depends on YouTube public feeds. No API credentials are embedded in the website. The website does **not** auto-publish any videos or access private analytics.

## Safety & deployment

- Publish with **GitHub Pages → Deploy from main branch, root folder**.
- Do not upload OAuth client JSON files, API keys, passwords, encrypted tokens, private analytics or local footage to this public repository.
- The actual JARVIS News Autopilot software is in a separate **private** repository and is not affected.
- Google OAuth branding may use the dedicated app homepage: https://soundverse7.github.io/jarvis-news-oauth-info/app.html
- Public website privacy and terms: https://soundverse7.github.io/jarvis-news-oauth-info/privacy.html and https://soundverse7.github.io/jarvis-news-oauth-info/terms.html
- This public informational site does not automatically satisfy Google's domain-ownership or OAuth verification requirements.
