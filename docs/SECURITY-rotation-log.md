# Rotation log

Append-only paper trail of secret rotations. Each row documents what was
rotated, when, and why. Required by `docs/SECURITY-rotation-procedure.md`
post-rotation checklist. Old credentials are listed by name + provider only
— never by value.

## Format

Each rotation gets one entry:

```
## YYYY-MM-DD — <credential category>

- **Reason:** <routine / suspected exposure / contributor offboarding / etc.>
- **Old credential:** <provider — name or short identifier>
- **New credential:** <provider — name>
- **Consumers updated:** <list of files / secrets stores>
- **Smoke test:** <PASS/FAIL + brief result>
- **Old credential revoked:** <YES/NO> at <provider URL>
- **Operator:** Elladriel80
```

---

## 2026-05-12 — Initial post-audit rotation (3 categories)

Following the security audit dated 2026-05-11 (`AUDIT-SECURITE-AUGURE.md`,
later renamed for the Aratea project), all three on-disk credential
categories were rotated as defense-in-depth. No leak was proven in git
history (`git log --all` returned clean on all `.env` paths and on the
literal credential values), but the credentials had lived on disk in a
synced workspace folder for several weeks — long enough to be considered
potentially read by any process with filesystem access. Rotation cost was
minimal relative to the impact of an unproven leak materialising later.

### Pinata JWT

- **Reason:** routine + defense-in-depth post-audit
- **Old credential:** Pinata — scoped key issued 2026-05-10, expiry 2027-05
- **New credential:** Pinata — `aratea-ci-20260512`, expiry 90 days
- **Permissions trimmed to:** `pinFileToIPFS`, `pinList` (no `unpin`, no V3
  resources, no admin)
- **Consumers updated:** `contracts/.env` line `PINATA_JWT=`
- **Smoke test:** PASS — `GET /data/pinList` returned the genesis
  `valuation_report.md` CID (`bafybeih5jb2vk577w57uw62m4j7opyke4poryrphscydhzmd3htvm2ug7u`)
- **Old credential revoked:** YES at https://app.pinata.cloud/developers/api-keys
- **Account hardening:** 2FA enabled on the Pinata account
- **Operator:** Elladriel80

### Discord webhooks (×4)

- **Reason:** routine + defense-in-depth post-audit + rebrand alignment
  (renamed all webhooks from `augure-*` to `aratea-*`)
- **Old credentials:** 3 webhooks issued 2026-05-10 in channels
  `#🛠-build-log`, `#🎯-predictions`, `#💰-pnl-tracker`. A 4th channel
  `#🌱-product-updates` had no webhook prior to this rotation.
- **New credentials:** 4 fresh webhooks via delete+create:
  - `aratea-build-log` in `#🛠-build-log`
  - `aratea-predictions` in `#🎯-predictions`
  - `aratea-pnl-tracker` in `#💰-pnl-tracker`
  - `aratea-product-updates` in `#🌱-product-updates` (new)
- **Consumers updated:**
  - `predictor/.env` lines `DISCORD_WEBHOOK_BUILD_LOG`,
    `DISCORD_WEBHOOK_PREDICTIONS`, `DISCORD_WEBHOOK_PNL_TRACKER`,
    `DISCORD_WEBHOOK_PRODUCT_UPDATES` (new line added)
  - GitHub Actions repository secret `DISCORD_WEBHOOK_URL` (pointing to the
    `aratea-build-log` webhook, per Option A — release announces and weekly
    recaps continue to land in the dev channel)
- **Smoke test:** PASS — direct POST to each webhook returned 204 and the
  test message appeared in the correct channel for all 4 (visual verification
  in Discord)
- **Old credentials revoked:** YES — automatic upon delete+create of each
  webhook (Discord invalidates the old URL the moment the webhook is deleted)
- **Operator:** Elladriel80

### Etherscan V2 API key

- **Reason:** routine + defense-in-depth post-audit
- **Old credential:** Etherscan V2 — single key shared for Etherscan and
  Arbiscan in `contracts/.env`
- **New credential:** Etherscan V2 — `aratea-ci-20260512` (34 chars)
- **Consumers updated:** `contracts/.env` lines `ETHERSCAN_API_KEY=` and
  `ARBISCAN_API_KEY=` (same key value reused on both, consistent with the
  V2 unified API; deferred to a future rotation if blast-radius separation
  becomes desirable)
- **Smoke test:** PASS — `eth_getCode` against the deployed `AugPocToken`
  (`0x56a754632f19996649E78818BcD8ee388D2871Ee` on Arbitrum Sepolia, chainid
  421614) returned the expected `0x6080604052...` bytecode
- **Old credential revoked:** YES at https://etherscan.io/myapikey
- **Operator:** Elladriel80

### X / Twitter API credentials — deleted, not rotated

- **Reason:** auto-posting to X is disabled (`ANNOUNCE_DISABLE_X=true` repo
  variable) and not planned to be re-enabled in the short term. Rather than
  rotating dormant secrets, the 4 secrets were deleted outright to reduce
  attack surface to zero. If X auto-posting is reactivated later, new
  credentials will be issued fresh.
- **Old credentials:** GitHub Actions repository secrets `X_API_KEY`,
  `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- **Action:** all 4 secrets deleted from
  `Settings → Secrets and variables → Actions`
- **Workflow impact:** none. `post-x.mjs` lines 33-37 implement a soft-skip
  when any of the 4 env vars is missing (`process.exit(0)`). The
  `announce-release` workflow continues to succeed on tag pushes, just
  without the X-post step.
- **At-rest credentials at X side:** the upstream X developer app tokens
  remain valid at X — they were not regenerated on the X developer portal.
  To fully neutralise the tokens, regenerate them on
  https://developer.x.com/. Deferred unless we believe they leaked.
- **Operator:** Elladriel80

### Not rotated this round

- **Admin EOA** (`0x9a94552DCB67F036af6eccc9111b749856ab8EEA`): never on
  disk, key material in hardware wallet only. No rotation needed until
  mainnet migration to a Safe multisig.

---

## Next rotation due

Quarterly cadence — next due **2026-08-12** (or earlier on any suspected
exposure event per `docs/SECURITY-rotation-procedure.md`).
