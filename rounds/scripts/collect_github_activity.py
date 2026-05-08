"""
collect_github_activity.py — aggregate observable contributions from Git for a monthly round.

Usage:
    python scripts/collect_github_activity.py --month 2026-05 --repo augure-protocol/augure

Output:
    rounds/<month>/raw.json — per-contributor observable artifacts, ready for the valuation agent.

Hard rule: this script collects ONLY Git-observable facts. No declared hours, no submissions,
no narrative claims of any kind. If a contribution does not exist in Git, it does not exist.

MVP skeleton. To complete:
- pagination over GitHub Search API for merged PRs in the date range
- file diff stats per PR (additions, deletions, files changed)
- linked issues (closes #N detection)
- review activity given to others
- signed commits on `main` outside of PRs
- wallet resolution via WALLETS.md
- detection of likely auto-generated PRs (filter by committer, by labels)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import requests


GITHUB_API = "https://api.github.com"


@dataclass
class ObservableArtifact:
    """A single Git-observable fact attributed to a contributor."""
    type: str  # "merged_pr", "review_given", "signed_commit_main"
    ref: str  # PR number, review id, commit sha
    title: str
    url: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ContributorMonth:
    handle: str
    wallet: str
    artifacts: list[ObservableArtifact] = field(default_factory=list)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--month", required=True, help="YYYY-MM")
    p.add_argument("--repo", required=True, help="owner/name (Augure main repo)")
    p.add_argument("--rounds-dir", default="rounds")
    p.add_argument("--wallets", default="WALLETS.md")
    p.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    return p.parse_args()


def parse_wallets(path: Path) -> dict[str, str]:
    """Parse WALLETS.md -> {handle: wallet_address}."""
    handles = {}
    if not path.exists():
        return handles
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or "GitHub handle" in line or "---" in line:
            continue
        parts = [c.strip() for c in line.strip("|").split("|")]
        if len(parts) >= 2 and parts[0].startswith("@"):
            handle = parts[0].lstrip("@")
            address = parts[1]
            if address.startswith("0x"):
                handles[handle] = address
    return handles


def fetch_merged_prs(repo: str, since: str, until: str, token: str) -> list[dict]:
    """TODO: paginate GitHub search API q='repo:R is:pr is:merged merged:since..until'."""
    raise NotImplementedError


def fetch_reviews_given(repo: str, since: str, until: str, token: str) -> list[dict]:
    """TODO: per registered handle, list reviews submitted on PRs of the repo in date range."""
    raise NotImplementedError


def fetch_signed_main_commits(repo: str, since: str, until: str, token: str) -> list[dict]:
    """TODO: signed commits directly on main not associated with a merged PR."""
    raise NotImplementedError


def main() -> int:
    args = parse_args()

    if not args.token:
        print("ERROR: GITHUB_TOKEN required", file=sys.stderr)
        return 2

    month_start = datetime.strptime(args.month + "-01", "%Y-%m-%d")
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)

    wallets = parse_wallets(Path(args.wallets))
    print(f"Found {len(wallets)} registered wallets", file=sys.stderr)

    contributors: dict[str, ContributorMonth] = {
        handle: ContributorMonth(handle=handle, wallet=wallet)
        for handle, wallet in wallets.items()
    }

    # TODO: populate artifacts via GitHub API:
    #   - fetch_merged_prs -> attribute to author
    #   - fetch_reviews_given -> per reviewer
    #   - fetch_signed_main_commits -> per committer

    out_dir = Path(args.rounds_dir) / args.month
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "raw.json"
    payload = {
        "month": args.month,
        "repo": args.repo,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "fact_only_notice": (
            "This file contains only Git-observable artifacts. "
            "No declared hours, no narrative submissions. "
            "If a contribution is not here, it has zero value for this round."
        ),
        "contributors": {h: asdict(c) for h, c in contributors.items()},
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
