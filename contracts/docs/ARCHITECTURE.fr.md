> [Read in English](ARCHITECTURE.md)

# Architecture — contracts Augure (Phase 1)

*Version 0.1 — 2026-05-09*

## 1. Objectif

Construire la plus petite couche on-chain possible qui ratifie et exécute les rounds mensuels de mint valeur-travail déjà produits off-chain dans [`/rounds/`](../../rounds/). Tout ce qui n'a **pas besoin** d'être on-chain reste off-chain.

## 2. Ce qui vit on-chain en Phase 1

Trois primitives :

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   AugPocToken          (ERC20 + AccessControl + Pausable)       │
│        ▲                                                        │
│        │ MINTER_ROLE                                            │
│        │                                                        │
│   RoundRegistry        (propose / challenge / execute / cancel) │
│        │                                                        │
│        │ utilise                                                │
│        ▼                                                        │
│   MonthlyMintCap       (bibliothèque pure — math du cap 10%)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

- **`AugPocToken`** est un ERC-20 OpenZeppelin standard avec `AccessControl`, `Pausable` et `ERC20Permit`. 18 décimales. Pas de `cap` fixe. Le seul `MINTER_ROLE` est attribué au `RoundRegistry` (pour qu'`executeRound()` puisse appeler `token.mint(...)`).
- **`RoundRegistry`** stocke des structs `Round`, expose les quatre fonctions de cycle de vie, et applique le cap mensuel de 10 % à chaque `executeRound()`. Il ne détient aucun fonds.
- **`MonthlyMintCap`** est une bibliothèque pure. À partir de `(supplyEnDébutDeMois, déjàMintéCeMois, mintDemandé)`, elle retourne si la demande passe et combien de marge il reste.

## 3. Ce qui reste off-chain en Phase 1

- **L'agent de valuation** — tourne chaque mois, lit les artefacts Git, produit `valuation_report.md`.
- **Le processus de challenge** — les challenges sont déposés on-chain (event), mais la **résolution** d'un round contesté (vote des Top-X holders) reste off-chain en Phase 1. Le Safe agit sur le résultat humain via `cancelRound` ou `executeRound`.
- **Le calcul de la NAV** — lu depuis le treasury + mark-to-market des positions, calculé off-chain chaque mois. Phase 2+ ajoutera un oracle.
- **Le pinning IPFS** — `RoundRegistry` ne stocke que l'URI IPFS sous forme de string. L'hébergement réel du fichier est fait par Pinata (ou tout service compatible CID).

## 4. Hypothèses de confiance

| Confiance placée dans | Pourquoi c'est acceptable en Phase 1 | Plan pour réduire la confiance |
|---|---|---|
| Signataires du Safe multisig | Petit ensemble de confiance (founder + 1-2 advisors) | Phase 2 : rotation vers un set de signataires élu communautairement ou contract Governor. |
| Ratification par l'agent off-chain | La discrétion du founder est documentée dans [`/rounds/RUBRIC.md`](../../rounds/RUBRIC.md) ; la fenêtre de challenge est ouverte à tous | Phase 2 : vote on-chain des Top-X holders. |
| Disponibilité du pinning IPFS | Plusieurs pins (Pinata + gateway publique IPFS + adressage par contenu) | Plusieurs providers de pinning ; redondance Filecoin à long terme. |
| Câblage des rôles du token au déploiement | Vérifié par le script de déploiement + test d'invariant post-deploy | Phase 2 : déploiement via CREATE2 déterministe + preuve de build reproductible. |

## 5. Pourquoi Foundry

- Tests fuzz + invariant natifs sans plugin.
- Boucle compile/test plus rapide que Hardhat.
- Standard pour les solo devs orientés sécurité et les audit firms (Code4rena, Spearbit, Trail of Bits).
- `forge fmt` supprime le débat de style et est imposé en CI.

## 6. Pourquoi Arbitrum (Sepolia en Phase 1)

- L2 mature, frais bas, large liquidité DeFi si la Phase 3 (pool de mutualisation) y est lancée.
- Éligible aux grants Arbitrum Foundation (STIP/LTIPP) accessibles à un solo dev.
- Tooling solide (Stylus optionnel, consensus Nitro, Arbiscan, bridge officiel).
- Fallback : rien en Phase 1 ne rend les contracts spécifiques à Arbitrum — le même bytecode tourne sur Optimism, Base ou tout L2 EVM si la décision de chain change plus tard.

## 7. Pourquoi pas d'upgradeabilité

- Réduit la surface d'attaque à "déploiement + rôles", ce qui est entièrement couvert par les tests et les invariants.
- Évite la complexité proxy / implementation slot qui a été à l'origine de plusieurs incidents très médiatisés (bugs de layout de storage, ré-entrée d'init, collisions du slot admin).
- Les bug fixes sont déployés comme un nouveau contract + une migration documentée. Le coût est une transaction Safe supplémentaire ; le bénéfice est l'absence de trappe d'upgrade qu'un attaquant pourrait jamais exploiter.
- Si à un jalon on conclut qu'un contract doit absolument être upgradeable, le prompt exige l'accord explicite du founder, le pattern UUPS, et un `TimelockController` d'au moins 48 h. La Phase 1 n'en a pas besoin.

## 8. Ce que le code des contracts ne fait *pas*

- **Ne calcule pas la NAV.** La NAV est off-chain ; le contract applique seulement le cap sur `totalSupply`.
- **Ne valorise pas les contributions.** C'est le job de l'agent. Le contract fait confiance aux paires `(beneficiary, amount)` fournies à `proposeRound`.
- **Ne gate pas les transferts.** `AugPocToken` est un ERC-20 librement transférable. Pas de KYC, pas d'allowlist, pas de fee de transfert.
- **Ne juge pas les challenges.** Il enregistre l'existence d'un challenge (event) et laisse le Safe résoudre via `cancelRound` ou en laissant la fenêtre expirer.

## 9. Pointeurs

- Détail du cycle de vie d'un round → [`ROUND-LIFECYCLE.fr.md`](ROUND-LIFECYCLE.fr.md)
- Threat model → [`SECURITY.fr.md`](SECURITY.fr.md)
- Flux de déploiement → [`DEPLOYMENT.fr.md`](DEPLOYMENT.fr.md)
- Modèle économique du token → [`/docs/token_model.md`](../../docs/token_model.md)
- Architecture niveau projet → [`/docs/architecture.md`](../../docs/architecture.md)
