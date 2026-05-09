> [Read in English](README.md)

# contracts

Smart contracts Solidity du protocole Augure. **Phase 1 en cours** — construction de la couche de règlement on-chain pour la mécanique de mint valeur-travail décrite dans [`/docs/token_model.md`](../docs/token_model.md).

## Statut

Phase 1 — *active*. Jalons M0 à M5. Voir [`/docs/architecture.md`](../docs/architecture.md) pour le phasage projet global.

## Périmètre Phase 1

Les primitives on-chain qui ratifient et exécutent les rounds mensuels déjà produits off-chain (voir [`/rounds/`](../rounds/)) :

1. **`AugPocToken`** — ERC-20 avec `AccessControl` et `Pausable`. 18 décimales (standard Ethereum). Pas de cap fixe — l'émission est régulée par `RoundRegistry` qui applique le cap mensuel de 10 %.
2. **`RoundRegistry`** — cycle de vie propose / challenge / execute / cancel des rounds mensuels de mint. Chaque round est ancré à son hash IPFS (le snapshot du `valuation_report.md` dans `/rounds/archives/<round-id>/`).
3. **`MonthlyMintCap`** — bibliothèque pure qui calcule le cap mensuel de 10 % à partir du supply circulant en début de mois calendaire (UTC).

Hors périmètre Phase 1 (scaffoldé, pas implémenté) : token de gouvernance `AUG` + `Governor`, oracle NAV automatisé, contrats paramétriques de mutuelle, vote on-chain des Top-X holders.

## Arborescence

```
contracts/
├── src/
│   ├── token/                      # M1 — AugPocToken
│   ├── rounds/                     # M2 (MonthlyMintCap) + M3 (RoundRegistry)
│   └── interfaces/                 # IAugPocToken, IRoundRegistry
├── test/
│   ├── unit/                       # ≥ 95 % de couverture sur la logique métier
│   ├── fuzz/                       # 10 000 runs par défaut
│   └── invariant/                  # invariants supply / cap / rôles
├── script/                         # M4 — scripts de déploiement + générateurs de calldata Safe
├── docs/                           # bilingue FR/EN — architecture, sécurité, déploiement, cycle de vie
├── foundry.toml
├── slither.config.json
├── remappings.txt
├── .env.example                    # placeholders pour Arbitrum Sepolia
└── README.md / README.fr.md
```

## Stack

- **Foundry** (forge, cast, anvil) — versions stables pinées via CI.
- **Solidity 0.8.24**, EVM `paris`, optimiseur 200 runs.
- **OpenZeppelin Contracts v5.1.0** pour chaque primitive (ERC20, AccessControl, Pausable, ReentrancyGuard, SafeERC20, ERC20Permit). Aucune réimplémentation maison.
- **`forge-std` v1.9.4** pour les tests et scripts.
- **Slither 0.10.4** pour l'analyse statique (la CI échoue à partir du niveau `medium`).
- **CI** dans `.github/workflows/contracts-ci.yml` — tourne à chaque push / PR qui touche à `contracts/**`.

## Chain cible

Arbitrum Sepolia (testnet) en Phase 1. Le déploiement mainnet est **bloqué** tant qu'au moins un audit communautaire (Code4rena Arena-X, Sherlock Watson, ou peer review documentée) n'est pas réalisé.

## Build & tests

> Foundry doit être installé localement. Voir [getfoundry.sh](https://book.getfoundry.sh/getting-started/installation).

```bash
# depuis contracts/
forge install --no-commit foundry-rs/forge-std@v1.9.4 OpenZeppelin/openzeppelin-contracts@v5.1.0
forge build
forge test -vvv
forge coverage --report summary
```

La CI exécute les mêmes commandes sur chaque PR — l'install local n'est nécessaire que pour le développement.

## Modèle de sécurité (version courte)

- Tous les rôles privilégiés (`MINTER_ROLE`, `PAUSER_ROLE`, `ROUND_PROPOSER_ROLE`, `ROUND_EXECUTOR_ROLE`) sont détenus par un multisig Safe sur Arbitrum Sepolia. **Jamais une EOA.**
- Pas d'upgradeabilité au démarrage. Les bug fixes sont déployés en tant que nouveaux contracts + migration.
- Pattern Checks-Effects-Interactions strict, `ReentrancyGuard` sur toutes les surfaces de transfert externe, `SafeERC20` pour toutes les interactions ERC20.
- Tests obligatoires à trois niveaux : unit (≥ 95 % de couverture), fuzz (10 000 runs), invariants sur les propriétés critiques (supply ≤ cap mensuel ; pas de mint sans fenêtre de challenge expirée ; `MINTER_ROLE` détenu uniquement par le Safe).

Threat model complet dans [`docs/SECURITY.fr.md`](docs/SECURITY.fr.md).

## Cycle de vie d'un round (Phase 1)

```
   ┌────────────────────┐
   │ Agent IA off-chain │  ───►  /rounds/archives/<round-id>/valuation_report.md
   │ produit le rapport │
   └─────────┬──────────┘
             │ founder ratifie + pin IPFS
             ▼
   ┌────────────────────┐
   │ Safe.proposeRound  │  ───►  RoundRegistry.proposeRound()
   │  (calldata)        │        émet l'event RoundProposed
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐         ┌─────────────────────┐
   │ Fenêtre challenge  │  ───►   │  challengeRound()    │  (n'importe qui)
   │ (7 j / 30 j genesis)│         │  → status Challenged │
   └─────────┬──────────┘         └─────────┬───────────┘
             │ fenêtre expirée + status == Proposed
             ▼                               │ Safe revoit le vote panel off-chain
   ┌────────────────────┐                    ▼
   │ Safe.executeRound  │              ┌─────────────────────┐
   │  → mint aux bens   │              │ Safe.cancelRound() │
   │  → check cap 10 %  │              └─────────────────────┘
   └────────────────────┘
```

Détail dans [`docs/ROUND-LIFECYCLE.fr.md`](docs/ROUND-LIFECYCLE.fr.md).

## Roadmap (jalons)

| Jalon | Périmètre | Statut |
|---|---|---|
| **M0** | Scaffold Foundry, CI, threat model, doc bilingue | ✅ fait |
| **M1** | `AugPocToken` (ERC20 + Permit + AccessControl + Pausable) | en attente |
| **M2** | Bibliothèque `MonthlyMintCap` + fuzzing exhaustif | en attente |
| **M3** | `RoundRegistry` (propose / challenge / execute / cancel) | en attente |
| **M4** | Scripts de déploiement Arbitrum Sepolia + intégration Safe | en attente |
| **M5** | Dashboard read-only (Next.js + viem) | en attente |

## Licence

Apache 2.0 — voir [/LICENSE](../LICENSE).
