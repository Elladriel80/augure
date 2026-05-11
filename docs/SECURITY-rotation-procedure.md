# Secret rotation procedure

> Runbook for rotating every credential the Augure stack depends on.
> Used routinely (quarterly) and after any suspected exposure.

## When to rotate

- **Routine:** every 90 days, calendar-driven. Set a reminder.
- **On any of the following events:**
  - A `.env` file is suspected to have been read by a process you don't
    control (extension install, npm postinstall, supply-chain incident).
  - Push protection or `gitleaks` flags a near-miss in CI.
  - A laptop holding the secrets is lost, sold, or sent for repair.
  - A contributor with read access leaves the project.

## What to rotate

| Secret                       | Where it lives                          | Rotation procedure                            |
|------------------------------|------------------------------------------|------------------------------------------------|
| Pinata JWT                   | `contracts/.env` (`PINATA_JWT`)          | See [Pinata](#pinata-jwt) below.               |
| Etherscan V2 API key         | `contracts/.env` (`ETHERSCAN_API_KEY`, `ARBISCAN_API_KEY`) | See [Etherscan](#etherscanarbiscan-api-key). |
| Discord webhooks (×3)        | `predictor/.env` (`DISCORD_WEBHOOK_*`)   | See [Discord](#discord-webhooks).              |
| X / Twitter API + access tokens | GitHub Actions secrets (5 secrets)    | See [X](#x--twitter-api-credentials).          |
| GitHub Actions `DISCORD_WEBHOOK_URL` | GitHub repo secret               | Same channel as Discord above; reset on both ends. |
| Admin EOA private key        | Hardware wallet only — never on disk     | If compromised: deploy a new key on mainnet, transfer admin via on-chain handover, deprecate the old EOA. Testnet: just generate a new EOA. |

## Pinata JWT

1. Sign in at [pinata.cloud](https://app.pinata.cloud/) → **Developers
   → API Keys**.
2. Click **New Key**. Set:
   - Key name: `augure-ci-YYYYMMDD`.
   - Permissions: only `pinFileToIPFS`, `pinList`. Leave `unpin`
     **unchecked** unless you specifically need to remove pins from CI.
   - Expiration: **90 days**.
3. Copy the JWT into `contracts/.env` locally **and** into GitHub
   Actions secrets (`Settings → Secrets and variables → Actions →
   PINATA_JWT`).
4. Test the new key with a small `pinFileToIPFS` call.
5. Go back to the **API Keys** page and **revoke the old key**.
6. **Enable 2FA on the Pinata account** if not already done.

## Etherscan/Arbiscan API key

1. Sign in at [etherscan.io](https://etherscan.io/myapikey) → **My API
   Keys**.
2. Add a new key (the V2 API uses one key across all supported chains
   including Arbiscan).
3. Copy it into `contracts/.env` for both `ETHERSCAN_API_KEY` and
   `ARBISCAN_API_KEY`. If you prefer two distinct keys for blast-radius
   reduction, generate a second key and put it under
   `ARBISCAN_API_KEY`.
4. Verify a contract on Arbiscan with the new key to confirm it works.
5. Delete the old key from the Etherscan dashboard.

## Discord webhooks

For each of the three webhooks in `predictor/.env`
(`DISCORD_WEBHOOK_BUILD_LOG`, `DISCORD_WEBHOOK_PREDICTIONS`,
`DISCORD_WEBHOOK_PNL_TRACKER`) **and** the CI webhook
(`DISCORD_WEBHOOK_URL` repo secret):

1. Open the target channel in Discord → **Edit Channel → Integrations →
   Webhooks**.
2. Click the existing webhook → **Reset Webhook URL**. Discord
   immediately invalidates the old URL.
3. Copy the new URL into the local `.env` (or the GitHub repo secret).
4. Smoke-test:
   ```bash
   python predictor/scripts/post_to_discord.py \
     --channel predictions --dry-run \
     --file predictor/runs/002/PRE_RUN.md
   # Remove --dry-run to actually post once dry-run is happy.
   ```

## X / Twitter API credentials

1. Sign in to the [developer portal](https://developer.x.com/).
2. **Regenerate** the consumer keys (API key + secret) and the access
   token (user access token + secret). Note that regenerating user
   tokens may force re-auth of any other application using them.
3. Update the four secrets in the GitHub Actions repo settings:
   `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`,
   `X_ACCESS_TOKEN_SECRET`.
4. Trigger the `Announce Release` workflow in **dry-run mode** to
   validate the new tokens without spamming the channel.

## Post-rotation checklist

- [ ] Old credentials revoked at the provider (not just rotated
      locally).
- [ ] New credentials present in every consumer: local `.env`, GitHub
      Actions secrets, any deployed Vercel project env, anywhere
      automation reaches.
- [ ] Smoke test passed for every rotated credential.
- [ ] If on-chain admin EOA was rotated: contract `admin()` returns
      the new address, the old EOA returns no permissions.
- [ ] Log the rotation in `docs/SECURITY-rotation-log.md` (date,
      credential, reason). Keeps a paper trail for audit.
