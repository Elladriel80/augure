# Contributing to Aratea

> [Lire en français](CONTRIBUTING.fr.md)

Aratea rewards labor value brought to the project, in any form: code, data, research, design, documentation, capital. The system is **fact-only**: only what is committed to Git counts.

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

## Local setup

Pick the module that matches your change and run only the relevant checks.

### Predictor

```bash
cd predictor
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate              # Linux / macOS
pip install -r requirements.lock --require-hashes
python scripts/test_ensemble.py
python scripts/test_resolution.py
python scripts/test_microstructure.py
```

### Contracts

```bash
cd contracts
forge install --no-commit foundry-rs/forge-std@v1.9.4 OpenZeppelin/openzeppelin-contracts@v5.1.0
forge build
forge test -vvv
```

### Dashboard

```bash
cd dashboard
cp .env.example .env.local
npm install
npm run typecheck
npm run build
```

### Static site and docs

No build step is required for `site/` or most Markdown-only changes. Use the
pre-commit hooks below for hygiene checks.

## Code style and safety checks

Before opening a PR:

```bash
pip install pre-commit
pre-commit run --all-files
```

The hooks run secret scanning and basic file hygiene checks. Do not bypass them
unless a maintainer explicitly asks you to do so and the reason is documented in
the PR.

Never commit real `.env` files, webhook URLs, private keys, RPC keys, wallet
seeds, API tokens, or private datasets. Use the `.env.example` files as
documentation only.

## How to propose a patch

1. Open or pick an issue before starting non-trivial work.
2. Keep the PR scoped to one module and one problem.
3. Link the issue in the PR description.
4. Explain the artifact value: what changed, why it matters, and how it can be
   verified from Git-visible evidence.
5. Include the commands you ran and their result.
6. If a command cannot be run locally, explain why and name the smallest
   reviewer-side check that would cover the change.

Good first issues are tracked in
[`docs/contributor-starter-issues.md`](docs/contributor-starter-issues.md).
The future bounty policy placeholder is
[`docs/bounty-mechanism.md`](docs/bounty-mechanism.md).

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
