> [Read in English](README.md)

# contracts

Smart contracts Solidity du protocole Augure. **Vide pour l'instant** — le dossier porte la roadmap architecturale jusqu'à ce que le POC predictor valide le cas pour passer aux composants on-chain.

## Statut

Phase 2+ — *non démarré*.

La Phase 1 (POC Kalshi) tourne entièrement off-chain. Les smart contracts ne démarrent qu'après le go/no-go du POC (méta-ensemble bat best single model et climato sur N>50 events). Jusque-là, ce dossier existe pour signaler l'intention et permettre aux contributeurs de proposer des specs.

## Modules prévus

```
contracts/
├── token/          ← ERC-20 AUG-POC et AUG, avec mint/burn guards
├── rounds/         ← module mint ratifié multisig (subscription + redemption)
├── governance/     ← panel Top-X holders, votes, slashing
└── mutual/         ← (Phase 3) contracts paramétriques météo + oracles
```

### `token/`
ERC-20 avec 8 décimales (aligné BTC). Deux phases :
- **AUG-POC** : token de la phase POC, mintable uniquement via le module `rounds/` après ratification multisig. Inclut logique de redemption window et hooks de slashing.
- **AUG** : token de la phase DAO. Mécanisme de conversion depuis AUG-POC selon un ratio voté par les holders (seuil ≥ 67 %) au lancement DAO.

### `rounds/`
Module mint ratifié multisig. Reçoit les rapports de valuation ratifiés depuis l'agent off-chain + ratificateur (ou post-DAO depuis le vote on-chain du panel holders). Mint des tokens à la NAV courante vers les wallets spécifiés dans le rapport. Applique les caps durs (10 % mensuel, 30 % par contributeur).

### `governance/`
Phase 1 : multisig simple (founder + 2 advisors).
Phase 2 : panel on-chain composé des Top-X holders en tokens, chacun ayant une voix (non pondéré par stake). Utilisé pour ratifier les rounds de valuation contestés.
Phase 3 : DAO complète avec votes token-weighted pour les changements paramétriques (rubric, taux, fees), avec règles de quorum et seuils.

### `mutual/`
Phase 3+. Contracts paramétriques de mutuelle météo. Les membres apportent du collatéral au pool de mutualisation ; les acheteurs souscrivent à des payouts paramétriques déclenchés par event. Pricing calculé off-chain par le predictor, résolution oracle via Chainlink Custom au-dessus des feeds NOAA/NWS.

> Augure n'opère **pas** comme assureur réglementé. Cf. white paper, section 4.

## Toolchain

**Foundry** *(prévu)*. Justification : cycle compile + test plus rapide, fuzzing intégré, tooling Solidity moderne, audité et forké largement. Hardhat pourra être ajouté plus tard si un workflow de déploiement spécifique en a besoin.

Version Solidity : ≥ 0,8,20.
Chain cible : à trancher (candidats : Base, Arbitrum, Optimism). Critères : coût gaz, compatibilité EVM, écosystème de contributeurs DeFi / risk-pool, options de custody pour le bankroll.

## Specs à écrire avant tout code

- Spec token AUG-POC (mint guard, surface slashing, lock de transferabilité)
- Spec module mint des rounds (format des preuves de ratification, signatures multisig)
- Spec adresse subscription pending (flux de remboursement en cas de refus du round)
- Spec queue de redemption (window, gate, lockup, oracle NAV)

Contributions bienvenues sur les PRs de spec (voir [`/CONTRIBUTING.fr.md`](../CONTRIBUTING.fr.md)).
