#!/usr/bin/env python3
"""post_to_discord.py — manual Discord webhook poster.

Use this when you want to post a run update without pushing a Git tag —
typically for pre-run signal (before a market is opened) or
post-resolution P&L (after the market resolves but before the next
tag-driven release announce). The tag-driven path lives in
.github/workflows/announce-release.yml; this script is the manual
escape hatch.

Usage
-----

    python predictor/scripts/post_to_discord.py \\
        --channel predictions \\
        --file predictor/runs/002/PRE_RUN.md

The channel name is mapped to an environment variable:

    --channel predictions
        → reads DISCORD_WEBHOOK_PREDICTIONS from the env

The variable's value must be a full Discord webhook URL of the form
"https://discord.com/api/webhooks/<id>/<token>". Set them either in a
local predictor/.env (gitignored) or export them before running:

    export DISCORD_WEBHOOK_PREDICTIONS="https://discord.com/api/webhooks/..."

The conventional channels for Phase 1 are listed in
predictor/.env.example. Quick reference:

    --channel predictions   → DISCORD_WEBHOOK_PREDICTIONS   (#🎯-predictions, run open)
    --channel pnl-tracker   → DISCORD_WEBHOOK_PNL_TRACKER   (#💰-pnl-tracker, resolution)
    --channel build-log     → DISCORD_WEBHOOK_BUILD_LOG     (#🛠-build-log, post-mortem)

Channel-name to env-var mapping rules:
    - lowercase, hyphens, dots  → uppercase, underscores
    - so "pnl-tracker"   → DISCORD_WEBHOOK_PNL_TRACKER
    - and "kalshi.runs"  → DISCORD_WEBHOOK_KALSHI_RUNS

Discord enforces a 2000-character limit per message. Longer content is
truncated to 1990 chars + an ellipsis. If the file you want to send
is longer, split it into multiple files and post them in sequence.

No external dependencies. Pure Python 3.9+ stdlib.

Exit code: 0 on success, 1 on any failure (missing env, HTTP error,
file not found).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Windows defaults stdout to cp1252; emojis and non-ASCII content in
# templates would otherwise raise UnicodeEncodeError on --dry-run.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DISCORD_LIMIT = 2000
SAFETY_LIMIT = 1990  # leave room for the ellipsis


def channel_to_env_var(channel: str) -> str:
    """`product-updates` → `DISCORD_WEBHOOK_PRODUCT_UPDATES`."""
    normalised = channel.strip().upper().replace("-", "_").replace(".", "_")
    return f"DISCORD_WEBHOOK_{normalised}"


def truncate(content: str, limit: int = SAFETY_LIMIT) -> str:
    if len(content) <= limit:
        return content
    return content[: limit - 1].rstrip() + "…"


def post(webhook_url: str, content: str) -> None:
    payload = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"Discord webhook rejected the post (HTTP {e.code}): {body[:500]}"
        )
    except urllib.error.URLError as e:
        raise SystemExit(f"Could not reach Discord webhook: {e.reason}")

    # Discord returns 204 No Content on success for plain webhooks,
    # 200 OK for `?wait=true` flavoured ones.
    if status not in (200, 204):
        raise SystemExit(
            f"Discord webhook returned unexpected status {status}: {body[:500]}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Post a markdown file to a Discord channel via webhook."
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Channel slug. Mapped to env var DISCORD_WEBHOOK_<UPPER>.",
    )
    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to the markdown file to post.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be posted, do not actually call the webhook.",
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 1

    content = args.file.read_text(encoding="utf-8")
    content = truncate(content)

    env_var = channel_to_env_var(args.channel)
    webhook_url = os.environ.get(env_var)

    if args.dry_run:
        print(f"[dry-run] channel: {args.channel}")
        print(f"[dry-run] env var resolved to: {env_var}")
        print(f"[dry-run] webhook set: {bool(webhook_url)}")
        print(f"[dry-run] content length: {len(content)} / {DISCORD_LIMIT}")
        print("[dry-run] content:")
        print("---")
        print(content)
        print("---")
        return 0

    if not webhook_url:
        print(
            f"error: env var {env_var} is not set. "
            "Set it to the Discord webhook URL for this channel.",
            file=sys.stderr,
        )
        return 1

    post(webhook_url, content)
    print(f"posted {args.file} to channel {args.channel} ({len(content)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
