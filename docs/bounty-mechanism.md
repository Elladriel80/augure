# Future bounty mechanism

Aratea does not yet run a cash bounty program. This placeholder defines the
Phase 2 target shape so contributors know what will, and will not, be accepted
before the mechanism is activated.

## Current status

- The active contribution system is the Git-visible labor valuation process
  described in `rounds/RUBRIC.md` and `CONTRIBUTING.md`.
- A merged PR can be considered during the monthly valuation round.
- Open, abandoned, or closed-without-merge PRs have no valuation under the
  current rubric.

## Phase 2 bounty goals

When activated, bounties should:

- point to a specific GitHub issue;
- define a fixed acceptance criterion before work starts;
- require a merged PR or a maintainer-approved artifact;
- remain compatible with the fact-only valuation model;
- avoid off-Git promises, DMs, or unverifiable self-reported work.

## Non-goals

The bounty mechanism will not reward:

- spam PRs or duplicated low-quality submissions;
- private claims that are not visible in Git history;
- work that requires committing secrets, private keys, wallet seeds, or private
  datasets;
- attempts to game the valuation rubric by splitting or padding changes.

## Suggested lifecycle

1. Maintainer opens an issue with the `bounty` label and an explicit reward or
   valuation rule.
2. Contributor comments with a short implementation plan before starting.
3. Contributor opens a focused PR linked to the issue.
4. Maintainer reviews, requests changes if needed, and merges only if the
   acceptance criteria are met.
5. The merged artifact is included in the next valuation round or paid through
   the published bounty channel once that channel exists.

Until this process is ratified, this document is informational only.
