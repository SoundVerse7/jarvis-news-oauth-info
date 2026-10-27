# Public Mind Report – World News

**Free, public news and explainer site:** https://soundverse7.github.io/jarvis-news-oauth-info/

Built as a free, static site using GitHub Pages. It has **no paid hosting, paid APIs, tracking pixels, ad codes, card collection, public logins or customer data processing**.

## Editorial website
- `index.html` — branded news homepage, safe filtered/searchable headline cards, source attribution and YouTube links
- `insights.html` — three original explainers on oil, interest rates and news-video verification
- `editorial.html` — source standards, accuracy, corrections and automation disclosures
- `support.html` — subscriber growth, sharing and a public sponsorship-inquiry route; no fake payment buttons
- `assets/newsroom.css` and `assets/newsroom.js` — responsive frontend and safe headline rendering
- `sitemap.xml`, `robots.txt` — public search discoverability

## Automated news links
- `scripts/update_headlines.py` reads **headlines + URLs + source names + publication dates only** from UN News, Federal Reserve, Bank of Canada and U.S. EIA feeds.
- `.github/workflows/refresh-headlines.yml` performs a free scheduled refresh every 3 hours, with a manual-run option. Schedules may be delayed or disabled by GitHub.
- `data/headlines.json` holds a public feed snapshot. A public GitHub Contents API request gives site visitors the latest Git branch contents even when GitHub Pages isn't rebuilt by commits pushed with `GITHUB_TOKEN`. The static JSON is the fallback if the API fails. The unauthenticated GitHub API can be rate-limited; no credential is shipped to visitors.
- Source lists are **not independently fact-checked news stories**. No photos, body copies or unlicensed RSS summaries are republished. Future-dated releases are excluded.

## Google OAuth information
- `app.html` — original official JARVIS News Autopilot Desktop App information page
- `privacy.html` — privacy policy
- `terms.html` — terms

**For Google's OAuth Branding > Application homepage**, the most accurately focused URL is `https://soundverse7.github.io/jarvis-news-oauth-info/app.html`. The publicly accessible privacy and terms URLs remain unchanged.

This site does not automatically satisfy OAuth domain ownership, verification, sensitive scope review, Google quota review, or YouTube API-project audit requirements.

## Monetization without pretending income exists
- The website links to the correct YouTube channel: https://www.youtube.com/channel/UCc3QJDTVAvImoGQSHOHTu3Q .
- A sponsorship inquiry route is available under `support.html` (public GitHub issues; **no confidential details**).
- Direct donations, advertising networks and affiliate programs **are not connected or collecting money**. They need user-owned, verified payment or advertising accounts, and a policy-compatible hosting plan. YouTube's Partner Program is subject to eligibility and acceptance.
- GitHub Pages is **not intended as free commercial store hosting or a payment gateway**. Keep the publication/news resources as the primary function.
- Clearly disclose sponsorships and affiliate links if added later.

## Deployment
- GitHub Pages: **Settings → Pages → Deploy from a branch → main → /(root)**.
- Workflows: **Actions → Refresh public headline links → Run workflow** for an immediate refresh.
- Workflow token needs `contents:write` to update `data/headlines.json`.
- Action-generated commits do not necessarily trigger Pages rebuilds (documented GitHub behavior); the browser reads the public Contents API with static Pages fallback.
- The app's **private code is in a different repository**. Never put Google OAuth JSON files, refresh tokens, source footage, passwords or local databases in this public site.
