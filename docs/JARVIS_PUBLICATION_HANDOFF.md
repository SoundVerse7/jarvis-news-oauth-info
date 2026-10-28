# JARVIS → Public Mind Report website: public publication handoff

**Status:** public website receiver implemented and tested locally in CI; **not yet connected to the private JARVIS installation**. This document is a handoff specification for the developer working on JARVIS. Do not install or authorize any new token without the owner's separate approval.

## What this does

After the private JARVIS app **successfully publishes** a video, it may notify the website so the public video library updates promptly even when YouTube's public RSS feed is temporarily unavailable. This does **not** upload a video, edit YouTube, disclose private metadata, or authorize JARVIS to manage the old channel.

- Original Public Mind Report: @PUBLICMINDREPORT, ID \`UCAVVVfl6qdT1JZsndhyhetA\` — **not allowed in this dispatch**. It continues through public RSS.
- JARVIS News: @PublicMindReportNews, ID \`UCc3QJDTVAvImoGQSHOHTu3Q\` — **only accepted channel**.

## Security/approval prerequisites

1. Ask the owner to authorize this integration separately; no token or permission is preapproved by preparing this website receiver.
2. Use a short-lived **fine-grained GitHub token** or GitHub App access token restricted to the *single public repository* \`SoundVerse7/jarvis-news-oauth-info\` with **Contents: write** only, which GitHub requires to create a repository dispatch event. Do not use the owner’s general-purpose GitHub token.
3. Store the token locally on the PC in encrypted, gitignored storage. Never put it in YouTube descriptions, the public GitHub repository, a website HTML/JavaScript file, a CLI argument that would be logged, or the dispatch JSON.
4. On each public upload, confirm through Google's authorized API **that YouTube read-back says \`privacyStatus=public\` and the video belongs to exactly \`UCc3QJDTVAvImoGQSHOHTu3Q\`**. Require that JARVIS's channel lock passed in the same session.
5. Never send an event for a draft, scheduled-private video, failed upload, a merely submitted upload, or another channel.
6. If the notification fails, preserve the normal YouTube publication and queue a safe, idempotent retry. Never reupload the video just to notify the website.

## Notification contract

Endpoint (GitHub REST API):

\`POST https://api.github.com/repos/SoundVerse7/jarvis-news-oauth-info/dispatches\`

Headers: \`Authorization: Bearer [OWNER-APPROVED-LOCAL-TOKEN]\`, \`Accept: application/vnd.github+json\`, \`Content-Type: application/json\`.

Request body example (substitute **actual, verified values**):

\`\`\`json
{
  "event_type": "jarvis_public_video",
  "client_payload": {
    "channel_id": "UCc3QJDTVAvImoGQSHOHTu3Q",
    "verified_channel_id": "UCc3QJDTVAvImoGQSHOHTu3Q",
    "privacy_status": "public",
    "verified_public": true,
    "video_id": "UdsaqB9anuo",
    "title": "DOJ takes steps to charge James Comey again - what we know",
    "published": "2026-10-27T21:08:29Z"
  }
}
\`\`\`

The JSON must contain **only public information**. The endpoint should return HTTP \`204 No Content\` for an accepted dispatch request, meaning GitHub queued an event (not that the website has already published it). The GitHub Actions run must then complete successfully.

GitHub docs: https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event

## Public receiver, validation and publication

- Workflow: \`.github/workflows/refresh-headlines.yml\` receives only \`repository_dispatch\` type \`jarvis_public_video\`.
- Validator: \`scripts/ingest_publication.py\` rejects any ID other than the News channel, any item lacking the exact public status and read-back flags, malformed video IDs, missing titles, dates older than 60 days or future-dated claims.
- Accepted public metadata goes to \`data/jarvis_public.json\`, up to 30 recent entries.
- \`scripts/update_videos.py\` merges this list with the two official YouTube RSS feeds and de-duplicates by video ID. The library has a per-channel quota so World News cannot bury the original channel.
- The public website reads \`data/videos.json\` through GitHub's public Contents API with a GitHub Pages fallback.
- No sensitive Google permissions, app tokens, personal analytics, private videos or drafts enter the public website.
- Public RSS can fail or lag. A JARVIS-reported publicly published video is owner-confirmed, not independently reverified by the website. If a video later becomes unavailable, visitors may temporarily see a dead YouTube link until the next review or cache expiry.

## Rollout/quality gates

1. Keep the private JARVIS repo unchanged until the developer is authorized.
2. Simulate a valid and invalid event *locally* using \`scripts/test_site.py\`; reject wrong-channel and private events.
3. With the owner’s approval, configure a limited token on the PC and perform **one real GitHub dispatch for an already-public News video**.
4. Verify the GitHub Actions run reports success and that the website shows the proper title, thumbnail and News-channel attribution.
5. Test duplicate dispatches (one video only), token revocation, wrong channel and an unavailable video.
6. Preserve existing JARVIS automatic publishing decisions and permissions; this notification is supplementary.

Nothing in this public site grants permission to change the original Public Mind Report channel.
