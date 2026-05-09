> [Read in English](DEPLOYMENT.md)

# Déploiement — contracts Augure (Phase 1)

*Version 0.1 — 2026-05-09 — placeholder, sera détaillé au jalon M4.*

## 1. Cible

La Phase 1 déploie sur **Arbitrum Sepolia testnet uniquement**. Le déploiement mainnet est conditionné à un audit communautaire (voir [`SECURITY.fr.md`](SECURITY.fr.md) §7).

## 2. Pré-requis (rempli en M4)

Avant de lancer les scripts de déploiement, le founder doit avoir :

- Une EOA fundée sur Arbitrum Sepolia (quelques ETH-Sepolia depuis un faucet — gas uniquement).
- Un multisig Safe déployé sur Arbitrum Sepolia (M-sur-N, signataires hardware-wallet, seuil M ≥ 2).
- Une clé API Arbiscan (gratuite).
- Une clé API Pinata (pour le pinning IPFS des rounds en M5+).
- Un `.env` rempli depuis `.env.example`.

## 3. Flux de déploiement (haut niveau)

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│ EOA déployeur│───▶│ Deploy AugPoc    │───▶│ Deploy           │───▶│ Câble les rôles :  │
│ (admin temp) │    │ Token            │    │ RoundRegistry    │    │ - Token MINTER →   │
└──────────────┘    └──────────────────┘    └──────────────────┘    │   RoundRegistry    │
                                                                     │ - Token PAUSER →   │
                                                                     │   Safe             │
                                                                     │ - Registry admin → │
                                                                     │   Safe             │
                                                                     └─────────┬──────────┘
                                                                               │
                                                                               ▼
                                                                     ┌────────────────────┐
                                                                     │ Transfère le       │
                                                                     │ DEFAULT_ADMIN_ROLE │
                                                                     │ au Safe sur chaque │
                                                                     │ contract           │
                                                                     └─────────┬──────────┘
                                                                               │
                                                                               ▼
                                                                     ┌────────────────────┐
                                                                     │ L'EOA déployeur    │
                                                                     │ renounce tous ses  │
                                                                     │ rôles              │
                                                                     └─────────┬──────────┘
                                                                               │
                                                                               ▼
                                                                     ┌────────────────────┐
                                                                     │ Verify sur Arbiscan│
                                                                     └─────────┬──────────┘
                                                                               │
                                                                               ▼
                                                                     ┌────────────────────┐
                                                                     │ Tests d'invariants │
                                                                     │ post-deploy sur le │
                                                                     │ déploiement live   │
                                                                     └────────────────────┘
```

## 4. Scripts (remplis en M4)

| Script | Fonction | Appelant |
|---|---|---|
| `script/DeployToken.s.sol` | Déploie `AugPocToken`, accorde les rôles initiaux à l'EOA déployeur | EOA déployeur |
| `script/DeployRegistry.s.sol` | Déploie `RoundRegistry`, câble le `MINTER_ROLE` depuis le token | EOA déployeur |
| `script/HandoffToSafe.s.sol` | Transfère l'admin au Safe, renounce sur le déployeur | EOA déployeur |
| `script/ProposeRound.s.sol` | Génère le calldata Safe Transaction Builder pour `proposeRound` | Helper off-chain (founder) |
| `script/ExecuteRound.s.sol` | Génère le calldata Safe Transaction Builder pour `executeRound` | Helper off-chain (founder) |

Les actions privilégiées (`proposeRound`, `executeRound`, `cancelRound`) ne sont **jamais** exécutées depuis une EOA. Les scripts émettent du calldata que le Safe signe et broadcast.

## 5. Vérification post-deploy

Un script Foundry `script/VerifyDeployment.s.sol` tourne contre le déploiement testnet live et assert :

- `token.MINTER_ROLE()` n'est détenu que par `RoundRegistry`.
- `token.DEFAULT_ADMIN_ROLE()` n'est détenu que par le Safe.
- `registry.DEFAULT_ADMIN_ROLE()` n'est détenu que par le Safe.
- L'EOA déployeur détient **zéro** rôle sur les deux contracts.

## 6. Exécution du round genesis (M5)

Une fois le déploiement vérifié, le round genesis (`2026-05-genesis`, 34 039 500 tokens vers le wallet de `@Elladriel80`) est exécuté via :

1. Le founder pin `valuation_report.md` sur IPFS (Pinata).
2. Le founder lance `script/ProposeRound.s.sol` pour générer le calldata, avec `challengeWindowDays = 30`.
3. Le Safe exécute `proposeRound` — le statut du round devient `Proposed`.
4. 30 jours passent. Si aucun challenge n'est déposé et que le Safe juge le processus off-chain propre, le calldata d'`executeRound` est généré et signé.
5. Le mint a lieu vers le wallet du bénéficiaire. `totalSupply` devient 34 039 500 × 10^18.

## 7. Rollback / break-glass

- Un round `Proposed` peut être cancelled par le Safe à tout moment pendant la fenêtre de challenge via `cancelRound`.
- Un round `Challenged` peut être cancelled par le Safe sur la base du résultat du vote panel off-chain.
- Un bug découvert dans un contract déployé déclenche un nouveau déploiement + une migration. Il n'y a pas de switch d'upgrade.
