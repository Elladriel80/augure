> [Read in English](SECURITY.md)

# Sécurité & threat model — contracts Augure (Phase 1)

*Version 0.1 — 2026-05-09*

## 1. Périmètre

Ce document couvre la surface d'attaque on-chain des contracts Phase 1 (`AugPocToken`, `RoundRegistry`, `MonthlyMintCap`) déployés sur Arbitrum Sepolia.

Il **ne couvre pas** : l'intégrité de l'agent off-chain, la durabilité du pinning IPFS, les pratiques de gestion des clés des signataires Safe, ou le processus de challenge au niveau social. Chacun a son propre threat model et vit en dehors du code des contracts.

## 2. Actifs à protéger

| Actif | Pourquoi c'est critique |
|---|---|
| Intégrité de `AugPocToken.totalSupply` | Une inflation au-delà du cap mensuel de 10 % dilue chaque holder existant. |
| Enregistrements de rounds dans `RoundRegistry` | Un historique falsifié casse la responsabilité et l'audit trail. |
| `MINTER_ROLE` (et autres rôles privilégiés) | Autorité directe de mint. Compromis = inflation illimitée. |
| Allocations de mint aux bénéficiaires | Un round est censé minter vers les wallets ratifiés off-chain — pas vers des adresses contrôlées par un attaquant. |

## 3. Hypothèses de confiance (dans le périmètre)

- Les signataires du Safe multisig agissent honnêtement (ou, au minimum, le seuil de signataires ne peut pas comploter de manière malveillante).
- Le compilateur Solidity et OpenZeppelin v5.1.0 ne contiennent pas de backdoor.
- Arbitrum Sepolia (et la stack Arbitrum Nitro) ne censure pas et ne rejoue pas les transactions de manière adversariale.
- Le drift des timestamps de blocs reste inférieur à la granularité de la fenêtre mensuelle (quelques minutes sont sans impact sur une frontière d'1 mois).

## 4. Hors périmètre (reconnu mais pas défendu on-chain)

- **Compromis de la clé d'un signataire individuel** sous le seuil du Safe. La mitigation vit dans la configuration du Safe (M-sur-N + hardware wallets), pas dans le code des contracts.
- **MEV sur `executeRound`**. Front-runner une exécution ne permettrait pas à un attaquant de changer les bénéficiaires (le round a été committé à `proposeRound`). Pire cas : quelqu'un paie le gas avant le Safe — sans danger.
- **Agent off-chain produisant un rapport de valuation frauduleux.** Détecté par la review du founder et la fenêtre de challenge publique. Ce n'est pas le job du contract de détecter une fraude dans l'input.
- **Perte du pin IPFS.** Le contract stocke l'URI ; si le fichier est jamais perdu, le round reste on-chain (hash + montants + bénéficiaires) mais le rationnel humain devrait être republié. Pinata + pins redondants.

## 5. Surface d'attaque et mitigations

### 5.1 Compromis de rôle privilégié

| Menace | Mitigation |
|---|---|
| `MINTER_ROLE` accordé à une EOA | Le script de déploiement assert que `MINTER_ROLE` n'est détenu que par `RoundRegistry` (et que l'admin de `RoundRegistry` est le Safe). Test d'invariant post-deploy vérifie. |
| `DEFAULT_ADMIN_ROLE` conservé par l'EOA déployeur après handoff | Le script de déploiement transfère l'admin au Safe, puis l'EOA déployeur renounce. Le script post-deploy assert qu'aucun rôle n'est accordé au déployeur. |
| Seuil du Safe trop bas | Le Safe est créé avec M-sur-N où M ≥ 2. Vérifié hors-bande avant tout octroi de rôle. |

### 5.2 Inflation au-delà du cap mensuel de 10 %

| Menace | Mitigation |
|---|---|
| `executeRound` minte plus qu'autorisé pour le mois | `MonthlyMintCap` est une bibliothèque pure, fuzzée exhaustivement (M2). `RoundRegistry` revert sur excès de cap. Le test d'invariant impose la somme des mints exécutés ≤ cap chaque mois. |
| Manipulation de la frontière de mois | Le cap est calculé depuis `block.timestamp` aligné sur le début de mois UTC. Un drift de quelques minutes ne permet pas une fenêtre de mint additionnelle significative. |
| Snapshot du cap pris à l'execute au lieu du début du round | Spec : le snapshot du cap est `totalSupply` au début du mois UTC. Documenté dans le natspec de `MonthlyMintCap` ; testé dans la suite d'invariants. |

### 5.3 Abus du cycle de vie d'un round

| Menace | Mitigation |
|---|---|
| `executeRound` appelé avant l'expiration de la fenêtre de challenge | La fonction revert si `block.timestamp < proposedAt + challengeWindowDays * 1 days`. |
| `executeRound` appelé deux fois sur le même round | La fonction revert si `status != Proposed`. Après exécution, le status devient `Executed`. |
| `executeRound` appelé sur un round `Cancelled` | Même check de status. |
| `proposeRound` avec arrays beneficiaries / amounts non alignés | Check de longueur + chaque amount > 0 imposé. |
| `proposeRound` avec URI IPFS arbitraire | L'URI est informationnelle ; la confiance vient du processus de ratification off-chain, pas du fait que l'URI soit sur un provider spécifique. |
| Abus de `cancelRound` | Restreint au Safe (`DEFAULT_ADMIN_ROLE` ou rôle admin dédié). Documenté comme un break-glass pour les rounds invalides (ex. typo dans une adresse de bénéficiaire). |
| Reentrancy via `mint(beneficiary, amount)` si `beneficiary` est un contract malveillant | `ERC20.mint` d'OZ ne callback pas le receveur. Pas de reentrancy possible. `ReentrancyGuard` quand même appliqué à `executeRound` en défense en profondeur. |

### 5.4 Abus de signature / permit sur `AugPocToken`

| Menace | Mitigation |
|---|---|
| Replay d'une signature `ERC20Permit` cross-chain | OZ `ERC20Permit` inclut `chainid` dans le domain EIP-712. |
| Replay cross-déploiements | OZ utilise l'adresse du contract dans le domain separator. |
| Permit signé avec un `deadline` périmé | OZ impose le check de `deadline`. |

### 5.5 Abus de pause / unpause

| Menace | Mitigation |
|---|---|
| `PAUSER_ROLE` détenu par une seule clé, utilisé pour griefer les holders | `PAUSER_ROLE` détenu par le Safe, qui requiert le seuil multisig. |
| Pause utilisée pour geler le mint pendant qu'`executeRound` est en cours | La pause stoppe `transfer`, pas `mint`. Les chemins de mint dans `RoundRegistry` sont gardés séparément par la state machine du cycle de vie. |

## 6. Catégories de tests requises (Phase 1)

| Catégorie | Cible | Outillage |
|---|---|---|
| Unit | ≥ 95 % de couverture de lignes sur `AugPocToken`, `RoundRegistry`, `MonthlyMintCap` | `forge test`, `forge coverage` |
| Fuzz | 10 000 runs par défaut par test fuzz | `forge test --fuzz-runs 10000` |
| Invariants | Somme des mints exécutés dans le mois M ≤ cap(M) ; pas de round `Executed` sans `Proposed` + expiration de la fenêtre ; ensemble `MINTER_ROLE` détenu = {`RoundRegistry`} | tests d'invariant `forge test` |
| Analyse statique | Aucun warning Slither de niveau medium ou supérieur | `slither contracts/`, CI `fail-on: medium` |
| Format check | `forge fmt --check` clean | CI |

## 7. Plan d'audit

- **Interne :** continu (chaque PR fait tourner le pipeline CI complet).
- **Pré-mainnet :** au moins un parmi — Code4rena Arena-X, Sherlock Watson, peer review documentée par 2-3 ingénieurs Solidity reconnus. **Le déploiement mainnet est conditionné à cela.**
- **Bug bounty :** post-mainnet, scopé aux contracts de ce repo.

## 8. Disclosure

Les problèmes de sécurité ne doivent pas être ouverts en issues publiques. Reporter à `<contact sécurité à définir>` — à remplir avant le mainnet.
