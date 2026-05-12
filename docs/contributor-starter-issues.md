# Contributor starter issues

This file lists real, small tasks that can be opened as GitHub issues with the
`good-first-issue` label. They are intentionally scoped to one module and should
not require private credentials, wallet access, or production deployment rights.

## 1. Align predictor README command names with current scripts

**Module:** `predictor/`

**Why it is real:** `predictor/README.md` documents commands such as
`scripts/predict_climatology.py` and `scripts/score_resolved.py`, but the current
`predictor/scripts/` directory contains `predict.py`, `score_forward.py`,
`forward_predict.py`, and related entrypoints instead.

**Likely files:**

- `predictor/README.md`

**Acceptance criteria:**

- The documented pipeline references scripts that exist in `predictor/scripts/`.
- Any renamed or removed command is replaced with the current closest entrypoint.
- The PR states that no runtime behavior changed.

## 2. Add a dashboard environment variable quick reference

**Module:** `dashboard/`

**Why it is real:** `dashboard/.env.example` documents the required public
environment variables, while `dashboard/README.md` explains local development.
A compact table in the README would make first setup easier.

**Likely files:**

- `dashboard/README.md`
- `dashboard/.env.example` only if a variable is missing from the example

**Acceptance criteria:**

- `NEXT_PUBLIC_RPC_URL`, `NEXT_PUBLIC_CHAIN_ID`,
  `NEXT_PUBLIC_TOKEN_ADDRESS`, `NEXT_PUBLIC_REGISTRY_ADDRESS`,
  `NEXT_PUBLIC_DEPLOY_BLOCK`, and `NEXT_PUBLIC_EXPLORER_URL` are documented.
- The table clearly marks browser-exposed `NEXT_PUBLIC_` values as non-secret.
- No real endpoint key or private address is added.

## 3. Document static site local preview steps

**Module:** `site/`

**Why it is real:** `site/README.md` explains deployment and editing, but it does
not show a minimal local preview command for contributors who want to inspect
the single-file page before opening a PR.

**Likely files:**

- `site/README.md`

**Acceptance criteria:**

- The README includes at least one local preview option, for example
  `python -m http.server` from `site/`.
- The text explains that no build step is required.
- The change does not alter `site/index.html`.

## 4. Add a wallet registration PR example

**Module:** `rounds/`

**Why it is real:** `rounds/WALLETS.md` gives the required table and signature
procedure. A short example PR body would reduce ambiguity for first-time
contributors without changing the registry rules.

**Likely files:**

- `rounds/WALLETS.md`
- or a new short doc linked from `rounds/WALLETS.md`

**Acceptance criteria:**

- The example uses placeholder addresses only.
- It includes the signed message shape and where to paste the signature.
- It does not add a real contributor row.

## 5. Add a docs index for architecture and value-engine documents

**Module:** `docs/`

**Why it is real:** `docs/` contains architecture, token model, value engine, and
security handoff documents. A small `docs/README.md` would help reviewers find
the right document without scanning the folder.

**Likely files:**

- `docs/README.md`

**Acceptance criteria:**

- Each existing top-level docs file is linked with a one-line purpose.
- The index distinguishes product architecture, token economics, valuation, and
  security notes.
- No new claims are introduced beyond what the linked docs already state.
