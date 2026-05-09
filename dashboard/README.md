> [Lire en français](README.fr.md)

# dashboard

Read-only dashboard for the Augure Phase 1 settlement layer. Shows the live state of
`AugPocToken` and `RoundRegistry` deployed on Arbitrum Sepolia (testnet).

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

## Why not server-render with caching?

Each page sets `export const dynamic = "force-dynamic"` so users always see fresh
on-chain state on a refresh. We deliberately avoid Next's ISR / cache layers here:
state changes are rare (one round per month), but when they happen we want them
visible immediately, not on whatever revalidation interval. The cost is one or two
RPC round-trips per page load, which is fine on a free RPC tier.

## License

Apache 2.0 — see [/LICENSE](../LICENSE).
