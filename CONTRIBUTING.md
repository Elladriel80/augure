# Contributing to Augure

> [Lire en français](CONTRIBUTING.fr.md)

Augure rewards labor value brought to the project, in any form: code, data, research, design, documentation, capital. The system is **fact-only**: only what is committed to Git counts.

## Steps to participate

1. **Read** [`README.md`](README.md), [`rounds/RUBRIC.md`](rounds/RUBRIC.md), and [`rounds/HOURLY_RATES.md`](rounds/HOURLY_RATES.md). The economic model is unconventional — make sure it suits you before investing time.
2. **Register your wallet** in [`rounds/WALLETS.md`](rounds/WALLETS.md) (signed PR).
3. **Bring value** in the relevant module:
   - **`predictor/`** — code, datasets, research RFCs about prediction.
   - **`contracts/`** — Solidity, specs, audits (Phase 2+).
   - **`rounds/`** — improvements to the rubric, prompt, scripts, automation.
   - **`docs/`** — architecture, token model, RFCs about the project itself.
   - **Cash** — BTC transfer to the published multisig address. Subscription window is monthly; cash is **subject to ratification** like any other contribution and may be refused with written rationale.
4. **Cooldown**: your first contribution must be merged > 30 days before you become eligible for mint. This filters drive-by participants.

## What is NOT valued

- Promises, intentions, brainstorms only.
- Open PRs that are not merged, or merged then reverted.
- Discord chat, DM debugging, hallway conversations: untraced in Git, not valued.
- Self-declared hours or narrative submissions: the system does not accept them.
- Auto-generated code without documented human curation.
- Visible gaming of metrics (split commits, padded diffs, sock-puppet reviews).

## Best practices

- **Open an issue before a large PR** to avoid wasted work that won't merge.
- **Link your PRs to issues** so impact is visible to the agent.
- **Write meaningful PR descriptions and commit messages.** They are the agent's primary input — sparse descriptions get valued at the floor.
- **Tests, docs, clean code increase your quality coefficient**, up to ×1.3.
- **Tech debt, regressions, incomplete work decrease it**, down to ×0.5.

## Challenge mechanism

If you believe your valuation in a monthly round is incorrect, file a **formal challenge** during the 7-day window:
- Comment on the round PR with the label `challenge`.
- Sign the comment with your registered wallet (signed message of the form `challenge-round-YYYY-MM-<your-handle>`).
- State precisely which valuation point you contest and why.

Filed challenges trigger a Top-X holder panel vote. The panel either ratifies the valuation as-is or returns it for revision with written instructions.

## Conduct

Standard: respect, intellectual honesty, transparency. Sanctioned (warning → exclusion → slashing by 67 % vote):

- Plagiarism or copying proprietary code without attribution / compatible license.
- Repeated submission of artifacts intentionally crafted to game the rubric.
- Manipulating challenges (sock puppets, intimidation).
- Hostile conduct toward other contributors.

## Questions

Project Discord: `<link to come>`. Forum: `<link to come>`.
