> [Read in English](ROUND-LIFECYCLE.md)

# Cycle de vie d'un round — contracts Augure (Phase 1)

*Version 0.1 — 2026-05-09*

## 1. États d'un round

```
                ┌────────┐
                │  None  │  (hash non initialisé → pas d'enregistrement)
                └───┬────┘
                    │ proposeRound()
                    │ ROUND_PROPOSER_ROLE
                    ▼
                ┌──────────┐
        ┌──────▶│ Proposed │
        │       └────┬─────┘
        │            │
        │            │ challengeRound() (n'importe qui)   ┌──────────┐
        │            ├────────────────────────────────▶ │Challenged│
        │            │                                    └────┬─────┘
        │            │                                         │
        │            │                                         │ cancelRound()
        │            │                                         │ ADMIN_ROLE
        │            │                                         ▼
        │            │                                   ┌──────────┐
        │            │                                   │Cancelled │ (terminal)
        │            │                                   └──────────┘
        │            │
        │            │ block.timestamp ≥ proposedAt + challengeWindowDays
        │            │ ET status == Proposed
        │            │ executeRound() — ROUND_EXECUTOR_ROLE
        │            │ → mint vers les bénéficiaires
        │            │ → applique le cap mensuel 10 %
        │            ▼
        │       ┌──────────┐
        └──cancelRound()──│ Executed │ (terminal)
                          └──────────┘
```

## 2. Transitions d'état

| Depuis | Fonction | Appelant | Conditions | Vers |
|---|---|---|---|---|
| `None` | `proposeRound` | `ROUND_PROPOSER_ROLE` | `roundHash` unique ; `beneficiaries.length == amounts.length` ; chaque `amount > 0` ; `challengeWindowDays > 0` | `Proposed` |
| `Proposed` | `challengeRound` | n'importe qui | `block.timestamp < proposedAt + challengeWindowDays * 1 days` | `Challenged` |
| `Proposed` | `executeRound` | `ROUND_EXECUTOR_ROLE` | `block.timestamp ≥ proposedAt + challengeWindowDays * 1 days` ; cap 10 % non dépassé | `Executed` |
| `Proposed` | `cancelRound` | `ROUND_CANCELLER_ROLE` | toujours | `Cancelled` |
| `Challenged` | `cancelRound` | `ROUND_CANCELLER_ROLE` | toujours | `Cancelled` |
| `Challenged` | (aucune — le Safe doit `cancelRound` si le challenge est validé, sinon laisser la fenêtre expirer et `executeRound`) | — | — | — |
| `Executed`, `Cancelled` | (aucune — terminal) | — | — | — |

## 3. Struct Round (spec cible pour M3)

```solidity
struct Round {
    bytes32 roundHash;          // hash(beneficiaries, amounts, ipfsUri) — clé unique
    string  ipfsUri;            // pointeur IPFS vers le snapshot de /rounds/archives/<round-id>/valuation_report.md
    uint64  proposedAt;         // block.timestamp au proposeRound
    uint32  challengeWindowDays;// 7 par défaut ; 30 pour le genesis (override par round)
    RoundStatus status;
    address[] beneficiaries;
    uint256[] amounts;          // en unités de base du token (wei, 18 décimales)
}
```

`roundHash` est calculé off-chain (et vérifiable par n'importe qui) comme `keccak256(abi.encode(beneficiaries, amounts, ipfsUri))`. C'est l'identité canonique d'un round.

## 4. Events (spec cible pour M3)

```solidity
event RoundProposed(
    bytes32 indexed roundHash,
    string ipfsUri,
    uint64 proposedAt,
    uint32 challengeWindowDays,
    address[] beneficiaries,
    uint256[] amounts
);

event RoundChallenged(
    bytes32 indexed roundHash,
    address indexed challenger,
    string reasonIpfsUri
);

event RoundExecuted(
    bytes32 indexed roundHash,
    uint64 executedAt,
    uint256 totalMinted
);

event RoundCancelled(
    bytes32 indexed roundHash,
    address indexed canceller,
    string reasonIpfsUri
);
```

## 5. Timing de l'application du cap

Le cap mensuel de 10 % est vérifié **au moment de `executeRound`**, pas au moment de `proposeRound`. Raison :

- Un round peut être proposé en mois M-1 avec une fenêtre de challenge de 7 jours qui se ferme en mois M ; le supply pertinent pour le cap est celui du début **du mois pendant lequel le mint a lieu**.
- Plusieurs rounds proposés dans le même mois consomment dans le même bucket mensuel, dans l'ordre d'exécution.
- Un round dont l'exécution pousserait le mois au-delà du cap revert ; le Safe peut soit le cancel, soit attendre la frontière du mois suivant.

## 6. Cas spécial du round genesis

`2026-05-genesis` (34 039 500 tokens à `@Elladriel80`) part avec `challengeWindowDays = 30` au lieu du 7 par défaut. Le cap mensuel de 10 % n'est **pas applicable** au round genesis car `totalSupply` est 0 avant son exécution (tout mint est "100 % de zéro", ce que la math du cap traite comme une branche spéciale "premier round").

Pour la spec : `MonthlyMintCap` retourne "pas de cap qui contraint" quand `totalSupplyAtMonthStart == 0`. Le tout premier mint du protocole n'est pas contraint par cette règle. C'est intentionnel et c'est la seule exception.

## 7. Pont off-chain ↔ on-chain

```
/rounds/archives/<round-id>/         ──pin──▶  IPFS (Pinata)
                                                  │
                                                  │  CID = bafy...
                                                  ▼
                                          contract.proposeRound(
                                              roundHash,
                                              [beneficiaries...],
                                              [amounts...],
                                              "ipfs://bafy...",
                                              challengeWindowDays
                                          )
```

- L'artefact off-chain est le `valuation_report.md` (et le reste du dossier du round).
- Le hash lie ces artefacts à l'enregistrement on-chain.
- L'URI IPFS donne un pointeur de récupération stable.
- Un challenger peut recalculer le hash depuis les fichiers publiés et vérifier que l'enregistrement on-chain correspond.

## 8. Ce qui n'est intentionnellement PAS dans le cycle de vie

- **Pas de conversion automatique d'un round `Challenged` en vote panel.** Le vote a lieu off-chain ; le Safe agit sur le résultat. Cela passera on-chain en Phase 2.
- **Pas de chemin d'"appel" après `Cancelled`.** Un round cancelled est terminal. Pour le ressusciter, proposer un nouveau round avec un `roundHash` différent.
- **Pas d'exécution partielle.** Un round mint complètement à tous les bénéficiaires ou revert.
