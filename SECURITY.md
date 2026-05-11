# Security policy

> [Lire en français](SECURITY.fr.md)

## Reporting a vulnerability

If you believe you have found a security vulnerability in this repository
— smart contracts, predictor, dashboard, or CI tooling — **please do not
open a public GitHub issue**.

Instead, email the maintainer directly:

- **Contact:** `jean-sebastien.lefevre@vasa.fr`
- **PGP key:** *(not yet published — request out-of-band if you need
  encrypted transport)*

Please include:

1. A description of the vulnerability and the affected component.
2. Steps to reproduce, or a proof-of-concept if available.
3. The impact you believe an attacker could achieve.
4. Any suggested remediation, if you have one.

We aim to acknowledge receipt within **3 working days** and to provide
an initial assessment within **10 working days**. Critical issues
affecting on-chain funds or user safety will be prioritised over
everything else.

## Disclosure policy

This project follows a **coordinated disclosure** model:

- We will work with you to confirm, reproduce, and triage the issue.
- We ask that you do **not** publicly disclose details until a fix is
  released or a mutually agreed timeline has elapsed (default: **90 days
  from initial report**).
- We will credit you in the release notes for the fix unless you
  request otherwise.

## Scope

| Area                    | In scope | Notes                                          |
|-------------------------|----------|------------------------------------------------|
| `contracts/`            | Yes      | Solidity sources, deploy scripts, foundry tests. See [`contracts/docs/SECURITY.md`](contracts/docs/SECURITY.md) for the on-chain threat model. |
| `predictor/`            | Yes      | Python code that fetches market and weather data, generates predictions, posts to Discord. |
| `dashboard/`            | Yes      | Read-only Next.js dashboard (no wallet, no signing). |
| `.github/`              | Yes      | Workflows, CI scripts, Dependabot config. Script injection issues are explicitly in scope. |
| Third-party services    | No       | Open-Meteo, Kalshi, Pinata, Vercel, Discord — report directly to the vendor. |
| Social engineering      | No       | Targeting the maintainer's accounts or contributors. |

## Out of scope

- Findings that require an attacker to already control the maintainer's
  EOA, Pinata account, or GitHub account.
- Denial-of-service via legitimate quota exhaustion on free-tier APIs.
- Best-practice nits (e.g. "missing X header") without a concrete
  exploit path. Open a regular issue or a PR instead.
- Anything on `main` that has not yet been deployed and is clearly a
  work in progress.

## Hardening already in place

- Solidity static analysis via Slither in CI (`fail-on: medium`).
- Forge unit tests + fuzz (10 000 runs) + invariants on the contracts.
- GitHub Dependabot weekly updates on `pip`, `npm`, `github-actions`.
- CodeQL static analysis on Python and JavaScript/TypeScript.
- `.gitignore` covers all known secret files; rotation procedure
  documented in [`docs/SECURITY-rotation-procedure.md`](docs/SECURITY-rotation-procedure.md)
  when present.

## Mainnet status

**Phase 1 contracts run on Arbitrum Sepolia testnet only.** Mainnet
deployment is gated on at least one community audit *and* the
establishment of a multisig Safe with separate signers per role. Until
then, no real value is at risk on-chain.
