# Aratea Oracle POC — Reclaim + NWS

POC pour valider la **brique #1** de l'oracle météo Aratea (whitepaper v0.5 §5, Couche B) :
lire une observation officielle depuis l'API NWS, prouver cryptographiquement la lecture
via Reclaim Protocol (zkFetch), et stocker la valeur on-chain dans un contrat Solidity
sur Arbitrum Sepolia.

Lire la spec complète et le scope dans [`SPEC.md`](./SPEC.md).

## Livraison en deux PRs

| PR | Périmètre | Statut |
|---|---|---|
| **PR 1** | Couche Solidity : contrats + tests Foundry + script déploiement | En cours |
| **PR 2** | Keeper Node.js (zkFetch + viem) + complétion docs (`POC-NOTES.md`) | À venir |

Ce README ne couvre pour l'instant **que PR 1** (la section keeper sera ajoutée dans PR 2).

---

## Prérequis

- **Foundry** récent (`forge --version` ≥ 1.0). Install : <https://book.getfoundry.sh/getting-started/installation>
- Une clé privée Arbitrum Sepolia funded (faucet officiel : <https://www.alchemy.com/faucets/arbitrum-sepolia>)
- Optionnel pour la vérification on-chain : une clé Arbiscan (<https://arbiscan.io/myapikey>)

Aucun compte Reclaim n'est nécessaire pour PR 1 (les tests utilisent un mock du verifier).

---

## Installation

```bash
cd Aratea/oracle-poc/contracts
forge install --no-git foundry-rs/forge-std@v1.9.4
forge install --no-git OpenZeppelin/openzeppelin-contracts@v5.1.0
```

## Compiler et tester

```bash
forge fmt --check     # format check (formatte avec: forge fmt)
forge build --sizes   # build + affichage tailles bytecode
forge test -vvv       # 21 tests Foundry, dont 2 fuzz à 1024 runs
```

Sortie attendue : **21 passed, 0 failed**.

## Déployer sur Arbitrum Sepolia

Variables d'environnement (créer un `.env` à la racine de `oracle-poc/contracts/`, **ne pas committer**) :

```bash
RPC_ARBITRUM_SEPOLIA=https://sepolia-rollup.arbitrum.io/rpc
PRIVATE_KEY=0x...                                    # clé du déployeur (testnet uniquement)
ARBISCAN_API_KEY=...                                 # optionnel, pour --verify
# Optionnel : override des valeurs par défaut
# RECLAIM_VERIFIER_ADDRESS=0x4D1ee04EB5CeE02d4C123d4b67a86bDc7cA2E62A   # déjà défaut
# WEATHER_LOCATION_KEY=KJFK
# WEATHER_TYPE_KEY=TEMP_C
```

Charger et déployer :

```bash
source .env
forge script script/DeployPOC.s.sol \
    --rpc-url $RPC_ARBITRUM_SEPOLIA \
    --broadcast \
    --verify
```

L'adresse du `ReclaimWeatherSource` est loggée dans la sortie et inscrite dans
`broadcast/DeployPOC.s.sol/421614/run-latest.json`.

## Vérifier le déploiement

Une fois le contrat déployé, on peut lire les immutables avec `cast` :

```bash
SOURCE=0x...   # adresse retournée par forge script

cast call $SOURCE "VERIFIER()(address)"                  --rpc-url $RPC_ARBITRUM_SEPOLIA
cast call $SOURCE "EXPECTED_LOCATION()(bytes32)"         --rpc-url $RPC_ARBITRUM_SEPOLIA
cast call $SOURCE "EXPECTED_MEASUREMENT_TYPE()(bytes32)" --rpc-url $RPC_ARBITRUM_SEPOLIA
```

Pour lire la dernière mesure (revertera tant qu'aucune n'a été soumise — c'est le rôle de
PR 2 / le keeper) :

```bash
cast call $SOURCE "getLatest(bytes32,bytes32)" \
    $(cast keccak "KJFK") \
    $(cast keccak "TEMP_C") \
    --rpc-url $RPC_ARBITRUM_SEPOLIA
```

## Structure des contrats

```
contracts/
├── src/
│   ├── interfaces/
│   │   ├── IReclaim.sol            # interface minimale du verifier Reclaim upstream
│   │   └── IWeatherSource.sol      # interface modulaire Phase 2-ready
│   └── sources/
│       └── ReclaimWeatherSource.sol # implémentation : single-station, single-type
├── test/
│   ├── ReclaimWeatherSource.t.sol  # 21 tests (unit + fuzz + réentrance)
│   └── mocks/
│       └── MockReclaimVerifier.sol # double de test du verifier (verdict + revert + reenter)
├── script/
│   └── DeployPOC.s.sol             # déploiement Arbitrum Sepolia
├── foundry.toml
├── remappings.txt
└── slither.config.json
```

## Limites assumées de PR 1

Reprises de [`SPEC.md` §Ce que ce POC ne valide PAS](./SPEC.md). En résumé :

- Le contrat **fait confiance au keeper** pour déclarer une `value` et un `timestamp` qui
  correspondent au `context` du proof Reclaim. Le parsing on-chain du JSON `context` est
  Phase 2. Pour le POC, le keeper c'est nous.
- Single-station (KJFK), single-type (TEMP_C). Mapping shape déjà Phase 2-ready.
- Pas d'agrégation multi-sources (`OracleAggregator` Phase 2).
- Pas de dispute / slashing économique (Phase 3).
- Pas de gouvernance on-chain du choix de verifier (Phase 2).

## Lien avec le whitepaper

Ce POC implémente la **brique #1 de la Couche B** du whitepaper v0.5 §5. L'interface
`IWeatherSource` est conçue pour être consommée telle quelle par l'`OracleAggregator`
de Phase 2, qui agrégera plusieurs implémentations (Reclaim + Chainlink + DePIN attestors).

## Adresses utiles

| Réseau | Reclaim verifier | Source |
|---|---|---|
| Arbitrum Sepolia | `0x4D1ee04EB5CeE02d4C123d4b67a86bDc7cA2E62A` | <https://docs.reclaimprotocol.org/onchain/solidity/supported-networks> |
| Arbitrum One     | `0x9F0472FD02Ca1BC2d6C3A1702803Ba822C7C7E91` | idem (hors-scope POC) |

---

*PR 1 — couche Solidity. PR 2 ajoutera la section keeper + `docs/POC-NOTES.md` complet
avec mesures gas et coût Reclaim observées en live.*
