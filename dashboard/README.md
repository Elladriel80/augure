> [Lire en français](README.fr.md)

# dashboard

Read-only dashboard for the Aratea Phase 1 settlement layer. Shows the live state of
`AugPocToken` and `RoundRegistry` deployed on Arbitrum Sepolia (testnet).

**Live:** [aratea-app.vercel.app](https://aratea-app.vercel.app/)

## Status

Phase 1 — *active*. Milestone M5. See [`/contracts/README.md`](../contracts/README.md)
for the on-chain pieces this dashboard reads.

## What it shows

- **Token page** (`/`): name, symbol, decimals, total supply, pause state, current
  month's 10% mint cap with consumption %, links to the contracts on Arbiscan.
- **Rounds page** (`/rounds`): every round committed to the registry, ordered by
  proposal date. Status pill (Proposed / Challenged / Executed / Cancelled),
  challenge window end, total amount, number of beneficiaries.
- **Round detail** (`/round/[hash]`): full metadata including the live countdown to
  the challenge window's end (when applicable), the IPFS link to the pinned
  `valuation_report.md`, and the per-beneficiary allocation breakdown.
- **Predictor page** (`/predictor`): predictor learning loop view — the latest
  training run's summary card with the test-Brier vs `kalshi_mid` verdict,
  the feature registry (every named hypothesis with its measured Brier
  contribution, clickable for full hypothesis + per-run history), the run
  history table, and the Brier trajectory chart across runs. Sourced
  entirely from a static manifest (`/predictor_manifest.json`) generated
  at build time — no API calls, no chain calls.

## What it does NOT do

- **No wallet connect.** Pure read-only by design — the dashboard never asks for a
  signature, never broadcasts a transaction, never holds a key. Operations
  (`proposeRound`, `executeRound`, `cancelRound`) are run via the Foundry scripts
  in [`/contracts/script/`](../contracts/script/), not this UI.
- **No backend, no database.** Every page server-renders by reading the chain
  directly through a public RPC endpoint. Hosting is static-friendly (Vercel,
  Netlify, Cloudflare Pages).

## Stack

- Next.js 15 (App Router) + React 19
- TypeScript strict
- viem 2.x (no wagmi — we don't need wallet plumbing)
- Tailwind CSS for styling
- No external CSS framework, no UI kit, no analytics

## Local development

### Prerequisites

- Node.js 20+ ([download](https://nodejs.org)).
- Optional but recommended: a free RPC endpoint URL from Alchemy, Infura, or Ankr
  for Arbitrum Sepolia. The default public endpoint works but is rate-limited.

### Run

```bash
cd dashboard
cp .env.example .env.local
# Fill in NEXT_PUBLIC_TOKEN_ADDRESS and NEXT_PUBLIC_REGISTRY_ADDRESS once the
# M4 deployment script has run on Arbitrum Sepolia. Until then the dashboard
# renders a "not yet deployed" notice.
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Environment Variables

> All `NEXT_PUBLIC_*` variables are exposed in the browser bundle. **These are not secrets** — they are public configuration values needed for the dashboard to connect to the chain.

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `NEXT_PUBLIC_RPC_URL` | ✅ | Arbitrum Sepolia RPC endpoint (public or private) | `https://sepolia-rollup.arbitrum.io/rpc` |
| `NEXT_PUBLIC_CHAIN_ID` | ✅ | Chain ID for the target network | `421614` (Arbitrum Sepolia) |
| `NEXT_PUBLIC_TOKEN_ADDRESS` | ✅ | Deployed `AugPocToken` contract address | `0x000...000` (unset) |
| `NEXT_PUBLIC_REGISTRY_ADDRESS` | ✅ | Deployed `RoundRegistry` contract address | `0x000...000` (unset) |
| `NEXT_PUBLIC_DEPLOY_BLOCK` | ✅ | Block number to start scanning events from | `0` |
| `NEXT_PUBLIC_EXPLORER_URL` | ❌ | Block explorer URL override | `https://sepolia.arbiscan.io` |

### Anvil (local fork)

For development against a local fork of Arbitrum Sepolia:

```bash
# In one terminal — fork the live testnet
anvil --fork-url https://sepolia-rollup.arbitrum.io/rpc

# In another — point the dashboard at it
NEXT_PUBLIC_CHAIN_ID=31337 \
NEXT_PUBLIC_RPC_URL=http://127.0.0.1:8545 \
NEXT_PUBLIC_TOKEN_ADDRESS=0x... \
NEXT_PUBLIC_REGISTRY_ADDRESS=0x... \
  npm run dev
```

## Deploying to Vercel

1. Connect the GitHub repo to a new Vercel project, set the root directory to
   `dashboard/`.
2. Set the environment variables under **Settings → Environment Variables**:
   - `NEXT_PUBLIC_RPC_URL` (recommended: a paid endpoint to avoid rate limits)
   - `NEXT_PUBLIC_CHAIN_ID=421614`
   - `NEXT_PUBLIC_TOKEN_ADDRESS` and `NEXT_PUBLIC_REGISTRY_ADDRESS` (from M4 deploy)
   - `NEXT_PUBLIC_DEPLOY_BLOCK` (the deployment tx's block number — speeds up event
     queries dramatically by skipping the early-chain history)
3. Deploy.

Vercel free tier is enough — every page is server-rendered, no edge functions, no
database.

## Predictor manifest pipeline

The `/predictor` page reads from `public/predictor_manifest.json`, an
aggregated snapshot of the off-chain predictor's state:

- every immutable training run under `predictor/runs_learning/<ts>/run.json`,
- the named-hypothesis registry in `predictor/src/learning/FEATURES.md`,
- aggregated counters from `predictor/data/ledger/paper_bets.csv` (no
  per-row data — only `n_open` / `n_resolved` / cumulative paper P&L).

The manifest is regenerated automatically by the `prebuild` (and `predev`)
npm hooks via `scripts/build-manifest.mjs`, which shells out to
`predictor/scripts/build_dashboard_manifest.py`. Vercel runs `npm run
build` so every deploy ships a fresh manifest. The shim tries `python3`
first (Linux/macOS/Vercel), then falls back to `python` (Windows).

To rebuild the manifest manually without a full Next.js build:

```bash
cd dashboard
npm run manifest
```

## Why not server-render with caching?

Each page sets `export const dynamic = "force-dynamic"` so users always see fresh
on-chain state on a refresh. We deliberately avoid Next's ISR / cache layers here:
state changes are rare (one round per month), but when they happen we want them
visible immediately, not on whatever revalidation interval. The cost is one or two
RPC round-trips per page load, which is fine on a free RPC tier.

## License

Apache 2.0 — see [/LICENSE](../LICENSE).
