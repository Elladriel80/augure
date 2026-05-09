# Release Announcements — Setup Guide

This repo posts an English announcement to **Discord** and **X** every time a release tag is pushed. The workflow lives in `.github/workflows/announce-release.yml`.

## How it triggers

The job runs when:
- A tag matching `v*.*.*` (or `v*.*.*-anything`) is pushed: `git tag v0.1.0 && git push origin v0.1.0`
- You manually trigger it from the **Actions** tab → **Announce Release** → **Run workflow** (handy to backfill or to test in dry-run mode).

## Required GitHub secrets

Set these in **Settings → Secrets and variables → Actions → New repository secret**.

| Secret | What it is | Where to get it |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | A Discord webhook URL for the channel you want announcements in | Discord channel → ⚙️ → Integrations → Webhooks → New Webhook → copy URL |
| `X_API_KEY` | App consumer key | X Developer Portal → your app → Keys and tokens → "API Key" |
| `X_API_SECRET` | App consumer secret | Same place — "API Key Secret" |
| `X_ACCESS_TOKEN` | User access token (the account that will tweet) | Same page — "Access Token" (regenerate if you only have the truncated value) |
| `X_ACCESS_TOKEN_SECRET` | User access token secret | Same place — "Access Token Secret" |

> ⚠️ The X access token must come from an **app with Read+Write permissions** attached to a **Project**. If your app is "standalone" (legacy), the v2 endpoint will return 401 even with valid keys. The fix is in the dev portal: User authentication settings → set permissions to "Read and write" → regenerate the access token.

## Optional repository variables

Set these in **Settings → Secrets and variables → Actions → Variables**.

| Variable | Purpose | Default |
|---|---|---|
| `PROJECT_NAME` | Display name in messages | `Augure` |
| `PROJECT_TAGLINE` | One-line tagline appended to Discord messages | `Decentralized prediction markets for weather risk` |
| `ANNOUNCE_DRY_RUN` | Set to `true` to skip actual posting (logs only) | unset |
| `ANNOUNCE_DISABLE_DISCORD` | Set to `true` to skip Discord posting | unset |
| `ANNOUNCE_DISABLE_X` | Set to `true` to skip X posting | unset |

> Tip: while X API keys are pending, set `ANNOUNCE_DISABLE_X=true` so Discord still posts on every tag without the X step failing the run.

## X API tier — what you can actually use

| Tier | Cost (May 2026) | Tweet limit | Verdict |
|---|---|---|---|
| Free | $0 | ~50 tweets / 24h, ~1500 / month | OK for tagged releases. Subject to silent rate limits. |
| Basic | $200/month | 3000 tweets / month | Recommended once you have weekly+ cadence. |
| Pro | $5000/month | 300k / month | Overkill. |

> Pricing has changed several times since 2023. Check [developer.twitter.com/en/products/x-api](https://developer.twitter.com/en/products/x-api) before relying on these numbers.

## Discord webhook setup

1. Go to the Discord channel where you want releases announced.
2. Click the gear icon (Edit Channel) → **Integrations** → **Webhooks**.
3. Click **New Webhook**, name it `Augure Releases`, optionally set an avatar.
4. Copy the webhook URL.
5. Paste it into the `DISCORD_WEBHOOK_URL` secret on GitHub.

> The bot will never @everyone or @here — `allowed_mentions` is locked down in the script (`post-discord.mjs`). If you want pings, edit that file to remove the lockdown for specific roles.

## How the message gets built

`.github/scripts/build-announcement.mjs` looks for content in this priority order:

1. **Annotated tag message** — if you pushed the tag with `git tag -a v0.1.0 -m "..."`, that text is used verbatim. **This is the recommended path** because it lets you write the message at tag time.
2. **CHANGELOG.md section** — if there's a heading matching the version (`## v0.1.0` or `## 0.1.0`), the body of that section is used.
3. **Conventional commit summary** — falls back to `git log` between the previous tag and this one, grouped by `feat:` / `fix:` / `refactor:` / `docs:`.

### Recommended workflow

```bash
# Write the announcement at tag time — it shows up everywhere consistently.
git tag -a v0.1.0 -m "Kalshi fetcher + climatology baseline + ECMWF/GFS blend predictor are live. Backtest on April markets next."
git push origin v0.1.0
```

The first line of the tag message becomes the X tweet body. The full message is the Discord post.

## Testing without polluting Discord/X

Two ways:

**A. Use the manual trigger with dry-run.**
1. Actions tab → **Announce Release** → **Run workflow**.
2. Tag: `v0.0.1-test`
3. Dry run: ✅
4. Inspect the artifact uploaded by the run (`announcement-v0.0.1-test`) — it contains the exact files that *would* have been posted.

**B. Set the variable.**
Set `ANNOUNCE_DRY_RUN=true` repository variable. All future runs print to logs but don't post. Remove it when ready to go live.

## What to do if a post fails

- **Discord 401/404** → webhook URL was deleted or revoked. Recreate, update the secret.
- **X 401** → app permissions are wrong or the access token was generated before Read+Write was set. Regenerate the access token in the dev portal.
- **X 403** → most often: duplicate tweet (X blocks identical content within ~24h), or the API tier no longer permits writes. Check the response body in the run logs.
- **X 429** → rate limited. Wait and re-run from the Actions tab.

When auto-posting fails, fall back to **`ANNOUNCE_TEMPLATES.md`** for ready-to-paste copy in the same voice.

## Weekly recap (FR) — automatic Sunday post

A second workflow, `weekly-recap.yml`, posts a French recap to Discord every **Sunday around 8 PM Paris time**, summarizing what changed in the repo over the last 7 days.

### Schedule

Cron: `30 18 * * 0` = Sunday 18:30 UTC.
- **Summer** (CEST, UTC+2): 20:30 Paris ✅
- **Winter** (CET, UTC+1): 19:30 Paris ⚠️ (one hour earlier)

GitHub Actions cron has no DST awareness. If the winter time bothers you, edit the cron in `weekly-recap.yml`:
- Year-round 20:00 Paris in summer only → keep `30 18 * * 0`
- Year-round 19:30 Paris in winter only → change to `30 19 * * 0`
- A run that fires both at 17:30 UTC and 18:30 UTC with a guard on the wall-clock hour (more complex, not provided by default).

> Note: GitHub may delay scheduled runs by 5–15 minutes during peak load. For a weekly recap, that's fine.

### How the content is built

`build-weekly-recap.mjs` runs `git log --since="7 days ago" --no-merges --name-only`, drops noise commits (`chore:`, `release:`, `bump:`, `style:`, `wip:`, `typo:`), then:

1. Buckets each commit by **module** based on the paths of files it touched:
   `predictor/` → Predictor, `contracts/` (excluding `lib/`) → Contracts, `site/` → Site, `docs/` → Docs, `rounds/` → Rounds, `.github/` → CI / Infra, `discord*` files → Discord, audit/checklist/contacts files → Comm / Process, other markdown → Docs, anything else → Divers.
2. Sub-buckets within each module by conventional-commit type: `feat:` items appear first, `fix:` items prefixed with "Correctif :", everything else after.
3. Lists tags created in the same window in a "Releases taguées cette semaine" section.
4. Adds a French tagline as footer.

If there are no meaningful commits, the script writes `recap.empty` instead of `recap.discord.md` and the workflow skips the Discord post (silence > empty posts). To force a post on a quiet week, run the workflow manually with **Force post: ✅**.

### Optional repo variables for the recap

| Variable | Purpose | Default |
|---|---|---|
| `PROJECT_TAGLINE_FR` | Tagline appended to the recap | `Marchés prédictifs décentralisés pour le risque météo` |
| `RECAP_LOOKBACK_DAYS` | Days to scan back | `7` |
| `RECAP_SKIP_IF_EMPTY` | Set to `false` to always post even on quiet weeks | `true` |

### Testing manually

Actions tab → **Weekly Recap (FR)** → **Run workflow**:
- **Lookback days**: keep `7`, or bump to `14` if you've just installed it and want a 2-week recap for the first run.
- **Dry run**: ✅ to see what would be posted without actually posting.
- **Force post**: ✅ to post even when the script considers the week empty.

The artifact `weekly-recap-<run-id>` always contains the generated `recap.discord.md` (or `recap.empty` with the reason) — useful for previewing copy before going live.

## What to do if a post fails

- **Discord 401/404** → webhook URL was deleted or revoked. Recreate, update the secret.
- **X 401** → app permissions are wrong or the access token was generated before Read+Write was set. Regenerate the access token in the dev portal.
- **X 403** → most often: duplicate tweet (X blocks identical content within ~24h), or the API tier no longer permits writes. Check the response body in the run logs.
- **X 429** → rate limited. Wait and re-run from the Actions tab.
- **Weekly recap silently skipped** → expected behavior on a quiet week. Check the run summary; you should see "Recap is empty — skipping Discord post" with a reason. To override, run manually with Force post.

When auto-posting fails, fall back to **`ANNOUNCE_TEMPLATES.md`** for ready-to-paste copy in the same voice.

## Files in this system

```
augure/.github/
├── workflows/
│   ├── announce-release.yml          # release announcement on tag push (EN)
│   └── weekly-recap.yml              # weekly recap, every Sunday ~20:00 Paris (FR)
├── scripts/
│   ├── build-announcement.mjs        # generates Discord + X messages from the tag
│   ├── build-weekly-recap.mjs        # generates the FR Sunday recap from git log
│   ├── post-discord.mjs              # POSTs to Discord webhook (shared)
│   └── post-x.mjs                    # POSTs to X v2 with OAuth 1.0a
├── ANNOUNCE_SETUP.md                 # this file
└── ANNOUNCE_TEMPLATES.md             # manual fallback copy
```

No npm dependencies — pure Node 20 stdlib (`fetch`, `node:crypto`).
