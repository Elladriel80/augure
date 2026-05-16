# POC Oracle Reclaim — Spec v2

> **Statut** : spec corrigée après review critique + verdict provider Reclaim (16 mai 2026). À valider par JSL avant tout code.
>
> **Delta vs v1** : 3 bloqueurs résolus, 5 incohérences tranchées, stack côté keeper revue (zkFetch au lieu d'un provider Reclaim configuré). Voir section [Journal des changements](#journal-des-changements-vs-v1) en fin de doc.

---

## Contexte projet

Aratea — mutuelle paramétrique décentralisée pour les risques climatiques. Phase 1 valide l'edge prédictif via paper trading sur Kalshi ; la Phase 2 déploiera l'oracle météo on-chain qui alimentera les contrats de couverture paramétrique.

L'architecture oracle d'Aratea (whitepaper v0.5 §5, Couche B) est un **aggregator multi-sources gouverné par la DAO** :

- Phase 1-2 : consomme **Reclaim Protocol** (zkTLS) + **Chainlink Data Feeds**.
- Phase 3 : tracking accuracy on-chain, slashing économique, ouverture à des sources tierces.
- Phase 4 : réseau d'attestors météo Aratea natif (DePIN).
- Phase 5+ : devenir une brique consommable par d'autres protocoles climat.

Ce POC valide **la brique #1** : Reclaim → NWS → on-chain.

## Objectif du POC

Démontrer qu'on peut, de bout en bout :

1. Lire une donnée météo officielle depuis l'**API NWS** (`api.weather.gov`, JSON).
2. Générer un **zkProof** Reclaim via `zkFetch` attestant que cette donnée a été lue depuis la vraie URL HTTPS sans modification.
3. **Vérifier la preuve on-chain** dans un contrat Solidity sur Arbitrum Sepolia.
4. Exposer la valeur extraite via une interface `IWeatherSource` réutilisable en Phase 2.
5. Automatiser le tout via un **keeper Node.js** (poll → proof → tx on-chain).

## Stack technique (corrigée)

| Composant | Choix v2 | Pourquoi |
|---|---|---|
| Smart contracts | Foundry, Solidity 0.8.24 | Cohérent avec `Aratea/contracts/foundry.toml` existant |
| SDK Reclaim côté keeper | `@reclaimprotocol/zk-fetch` + `@reclaimprotocol/js-sdk` | zkFetch permet d'attester n'importe quelle URL HTTPS publique sans provider Reclaim pré-configuré (vérifié 2026-05-16 sur dev.reclaimprotocol.org : aucun provider météo dans le catalogue community) |
| SDK Reclaim on-chain | `reclaimprotocol/reclaim-solidity-sdk` (à installer via `forge install`) | SDK verifier officiel ; nom du repo et chemin précis à confirmer lors de l'install |
| Interactions on-chain | `viem` | Cohérent avec `dashboard/` |
| Runtime keeper | Node.js 20+, `npm` | Bun écarté à cause du bug `--compile` sur `$HOME` accentué (mémoire JSL) ; `pnpm` écarté pour rester sur le package manager déjà utilisé dans le repo |
| Tests Solidity | Foundry + mock du verifier Reclaim | Les attestors Reclaim sont des services externes vivants, mocker en CI est la seule voie viable |

**Pas de** : Web3.js, ethers.js, monorepo tooling lourd. Le POC reste autonome dans `oracle-poc/`.

## Architecture cible

```
Aratea/oracle-poc/
├── SPEC.md                            # ce fichier
├── README.md                          # install + run + critères validation
├── contracts/
│   ├── src/
│   │   ├── IWeatherSource.sol         # interface modulaire (Phase 2-ready)
│   │   └── ReclaimWeatherSource.sol   # implémentation Reclaim
│   ├── test/
│   │   ├── ReclaimWeatherSource.t.sol
│   │   └── mocks/
│   │       └── MockReclaimVerifier.sol
│   ├── script/
│   │   └── DeployPOC.s.sol
│   ├── foundry.toml
│   └── remappings.txt
├── keeper/
│   ├── src/
│   │   ├── index.ts                   # entry point : poll loop
│   │   ├── reclaimProof.ts            # zkFetch + transformForOnchain
│   │   ├── nwsClient.ts               # client NWS API
│   │   └── chainSubmit.ts             # push tx via viem
│   ├── package.json
│   ├── tsconfig.json
│   └── .env.example
└── docs/
    └── POC-NOTES.md                   # méthodo, résultats, limites, prochaines étapes
```

## Spec détaillée

### Interface `IWeatherSource.sol`

Modulaire, réutilisable en Phase 2.

```solidity
interface IWeatherSource {
    struct Measurement {
        int256 value;            // milliCelsius (ex: -50 000 = -50°C, +60 000 = +60°C)
        uint64 timestamp;        // unix epoch UTC du measurement (pas de la soumission)
        bytes32 location;        // hash de la station (ex: keccak256("KJFK"))
        bytes32 measurementType; // hash du type (ex: keccak256("TEMP_C"))
    }

    /// @notice Submit a verified measurement extracted from a Reclaim proof
    /// @dev The proof is verified by the Reclaim verifier set at construction.
    ///      Reverts if the proof is invalid, replayed, out of timestamp window,
    ///      or older than the currently stored measurement for the same (location, type).
    function submitMeasurement(bytes calldata proof) external;

    /// @notice Read latest measurement for a (location, type) pair
    /// @return The most recent Measurement; reverts if none exists
    function getLatest(bytes32 location, bytes32 measurementType)
        external view returns (Measurement memory);

    event MeasurementSubmitted(
        bytes32 indexed location,
        bytes32 indexed measurementType,
        int256 value,
        uint64 timestamp,
        address indexed submitter
    );
}
```

**Décisions tranchées (vs spec v1)** :

- **Unité** : milliCelsius (`int256`). Permet les négatifs sans gymnastique. `measurementType = keccak256("TEMP_C")` cohérent.
- **`address attestor` retiré de la struct** : la preuve Reclaim est validée cryptographiquement par le verifier, `msg.sender` n'a aucune autorité particulière. Conservé en event pour tracker qui a payé le gas, mais pas en storage.
- **`submitMeasurement` retourne `void`** au lieu de `Measurement memory` : économise du gas, le caller a déjà la donnée.

### `ReclaimWeatherSource.sol` — règles de validation

L'implémentation rejette une `submitMeasurement` dans les cas suivants :

| Cas | Comportement |
|---|---|
| Proof invalide (signature ou ZK) | `revert InvalidProof()` |
| Proof déjà soumise (replay) | `revert ProofAlreadyConsumed()` |
| `measurement.timestamp > block.timestamp + 5 minutes` | `revert FutureTimestamp()` |
| `measurement.timestamp < block.timestamp - 6 hours` | `revert StaleMeasurement()` |
| `measurement.timestamp <= storedMeasurement.timestamp` | `revert NotMoreRecent()` |
| Valeur hors plage `[-100_000, +70_000]` mC | `revert ValueOutOfRange()` |

**Décisions tranchées (vs v1)** :

- **Window timestamp** : `[block.timestamp - 6h, block.timestamp + 5min]` au lieu de `[-7j, +1h]`. Aligné avec la cadence keeper 10 min.
- **Anti-replay** : `mapping(bytes32 proofHash => bool consumed)`. 5 lignes, supprime la pollution des indexeurs.
- **Anti-ordonnancement** : reject si on tente d'overwrite une mesure plus récente avec une plus ancienne.
- **Sanity check valeur** : -100°C à +70°C en milliCelsius. Au-delà = bug du keeper ou donnée corrompue.

Pas de dispute / slashing pour ce POC, juste lecture validée par Reclaim. Cohérent avec scope Phase 1-2.

### Keeper Node.js

#### Dépendances

```json
{
  "dependencies": {
    "@reclaimprotocol/zk-fetch": "latest",
    "@reclaimprotocol/js-sdk": "latest",
    "viem": "^2.x",
    "dotenv": "^16.x"
  },
  "devDependencies": {
    "typescript": "^5.x",
    "tsx": "^4.x",
    "@types/node": "^20.x"
  },
  "scripts": {
    "start": "tsx src/index.ts",
    "build": "tsc"
  }
}
```

#### Workflow d'une itération keeper

1. `nwsClient.fetchLatestObservation('KJFK')` → confirme que NWS répond et identifie l'URL exacte (`https://api.weather.gov/stations/KJFK/observations/latest`).
2. `reclaimProof.generate(url)` :
   - `ReclaimClient(APP_ID, APP_SECRET).zkFetch(url, publicOptions, { responseRedactions: [{ jsonPath: '$.properties.temperature.value' }, { jsonPath: '$.properties.timestamp' }] })`
   - `verifyProof(proof, { dangerouslyDisableContentValidation: true })` localement
   - `transformForOnchain(proof)` → `{ claimInfo, signedClaim }`
   - Encode le tuple `(claimInfo, signedClaim)` au format attendu par le contrat
3. `chainSubmit.submit(encodedProof)` :
   - `viem.writeContract({ functionName: 'submitMeasurement', args: [encodedProof] })`
   - Wait receipt, log l'event `MeasurementSubmitted`
4. Sleep `POLL_INTERVAL_SECONDS`, recommence.

**Loop intentionnellement simple** : pas de retry sophistiqué, pas de queue. Si une itération échoue, on log et on attend la suivante. POC = robustesse minimum viable.

#### Variables d'environnement

```bash
# Reclaim (obtenus après création d'un compte sur dev.reclaimprotocol.org)
RECLAIM_APP_ID=
RECLAIM_APP_SECRET=
# IMPORTANT : activer "zkFetch" dans l'onglet Integration de l'app Reclaim
# (sans ça, l'API ne répond pas)

# Chaîne
ARBITRUM_SEPOLIA_RPC=https://sepolia-rollup.arbitrum.io/rpc
KEEPER_PRIVATE_KEY=
RECLAIM_WEATHER_SOURCE_ADDRESS=

# Cible NWS
NWS_STATION_ID=KJFK

# Cadence
POLL_INTERVAL_SECONDS=600
```

**Plus de `RECLAIM_PROVIDER_ID`** : zkFetch n'en a pas besoin. C'est l'URL passée à `zkFetch` qui définit la cible.

### Tests Foundry

Tous mockent le verifier Reclaim (les attestors sont des services externes vivants).

- `test_submitMeasurement_validProof_storesMeasurement`
- `test_submitMeasurement_invalidProof_reverts`
- `test_submitMeasurement_replay_reverts`
- `test_submitMeasurement_futureTimestamp_reverts`
- `test_submitMeasurement_staleTimestamp_reverts`
- `test_submitMeasurement_notMoreRecent_reverts`
- `test_submitMeasurement_valueOutOfRange_reverts`
- `test_getLatest_returnsLastSubmitted`
- `test_getLatest_noMeasurement_reverts`

### Script de déploiement

`script/DeployPOC.s.sol` déploie `ReclaimWeatherSource` sur Arbitrum Sepolia. L'adresse du verifier Reclaim officiel sur Arbitrum Sepolia est un constructor argument (à récupérer dans le repo `reclaim-solidity-sdk`).

## Contraintes éditoriales (cohérence projet)

- **Pas d'emojis** dans le code, commits, PRs.
- **Pas de signature AI** dans les commits.
- **Documentation FR** dans `docs/POC-NOTES.md` et `README.md`.
- **Commentaires code EN** (convention internationale).
- **Naming explicite** : pas de `tmp`/`misc`/`utils`.
- **Pas de terminologie "assurance"** : utiliser "mutuelle paramétrique" / "couverture paramétrique".

## Workflow Git

Branch protection active sur `main`. Workflow :

```bash
git checkout main
git pull --rebase origin main
git checkout -b feat/oracle-poc-reclaim
# travail
git add Aratea/oracle-poc/
git commit -m "feat(oracle-poc): Reclaim zkFetch POC for NWS weather data"
git push -u origin feat/oracle-poc-reclaim
gh pr create --fill --base main
# Self-approve + checks contracts/slither verts requis (ruleset main)
gh pr merge --squash --admin --delete-branch
```

**Note CI** : si le workflow GitHub `.github/workflows/contracts.yml` ne scanne pas déjà tout `**/contracts/`, il faudra l'étendre pour inclure `oracle-poc/contracts/`. **À traiter dans la PR** ou dans une PR de suivi immédiate.

## Critères d'acceptation

Le POC est validé si :

1. **Tests Foundry verts** : `forge test` passe dans `oracle-poc/contracts/`.
2. **Déploiement Sepolia réussi** : `forge script script/DeployPOC.s.sol --rpc-url $ARBITRUM_SEPOLIA_RPC --broadcast` retourne une adresse vérifiable sur arbiscan-sepolia.
3. **Keeper end-to-end** : `npm start` dans `oracle-poc/keeper/` se connecte à NWS, génère un proof zkFetch, push une tx, et le contrat émet l'event `MeasurementSubmitted` avec une valeur entre `-100 000` et `+70 000` milliCelsius.
4. **Lecture on-chain** : `cast call $RECLAIM_WEATHER_SOURCE_ADDRESS "getLatest(bytes32,bytes32)" $(cast keccak "KJFK") $(cast keccak "TEMP_C")` retourne la dernière valeur soumise.
5. **README.md d'install** : un dev externe peut suivre les instructions et faire tourner le POC en **moins de 60 minutes** (révisé de 30 à 60 min — création compte Reclaim + activation zkFetch + récupération credentials + provisionnement clé Sepolia funded prend du temps).

## Ce que ce POC ne valide PAS (section explicite)

Important pour ne pas créer l'illusion que l'oracle Phase 2 est prêt.

| Limite | Pourquoi pas dans le POC | Quand on l'adresse |
|---|---|---|
| **Agrégation multi-sources** | Whitepaper §5 décrit un aggregator Reclaim + Chainlink. Ce POC = source unique Reclaim. | Phase 2, `OracleAggregator.sol` |
| **Dispute & slashing économique des sources** | Pas de mécanisme on-chain de challenge. | Phase 3 |
| **Multi-stations simultanées** | Single-station (KJFK) pour focus. | Phase 2 (généralisation triviale via mapping) |
| **Cadence économique réaliste** | Poll 10 min = 144 tx/jour. Sur Sepolia gratuit, sur Arbitrum One = vrai coût gas + RECLAIM dev fees. | Phase 2 (event-driven : pull à l'instant du settlement uniquement) |
| **Robustesse keeper** | Pas de retry, queue, ou observabilité. | Phase 2 (production keeper avec Sentry/PagerDuty équivalent web3) |
| **Gestion clé keeper** | `.env` plain text = OK testnet. Mainnet = HSM ou multisig obligatoire. | Phase 3 (déploiement mainnet) |
| **Gouvernance de l'oracle** | Pas de DAO vote sur quel verifier Reclaim utiliser ni quel APP_ID. | Phase 2 (`GovernanceModule` du whitepaper) |
| **Coût opérationnel** | Pas d'estimation chiffrée du coût RECLAIM par proof à fréquence cible (flaggé dans `recherche-reclaim-2026-05-16.md` §7). | À mesurer pendant le POC et reporter dans `POC-NOTES.md` |

## Documentation à produire

### `oracle-poc/README.md`

Sections obligatoires :

- Objectif du POC (3 lignes)
- Prérequis : Foundry, Node 20+, compte dev.reclaimprotocol.org, clé Arbitrum Sepolia funded (faucet officiel)
- Étapes setup : clone, install, env, **activer zkFetch dans l'onglet Integration de l'app Reclaim**
- Étapes deployment : compile, deploy Sepolia
- Étapes run keeper : start, monitor logs
- Comment vérifier que ça marche (commande `cast call`)
- **TODO HUMAIN** dédié : sourcing des credentials Reclaim (procédure exacte sur dev.reclaimprotocol.org)

### `oracle-poc/docs/POC-NOTES.md`

- Décisions techniques prises (zkFetch vs provider configuré, mC vs mK, anti-replay design, etc.)
- Limites connues (recopier la section ci-dessus)
- Coût opérationnel mesuré : gas par tx, fees Reclaim, cadence raisonnable
- Prochaines étapes Phase 2 : intégration `IWeatherSource` dans `Aratea/contracts/`, ajout source Chainlink, `OracleAggregator`

## Hors-scope (à NE PAS faire dans ce POC)

- Pas d'intégration avec `PoolManager` ou `ContractFactory` de Phase 2.
- Pas de mécanisme de dispute on-chain (Phase 3).
- Pas de slashing économique sur les sources (Phase 3).
- Pas de support multi-stations (Phase 2).
- Pas de production-readiness.

## Si la stack zkFetch bloque

Hypothèses de risque résiduel :

1. **NWS retourne du chunked encoding** — la doc zkFetch fournit `decodeChunkedResponse()` en troubleshooting. Probablement OK.
2. **NWS exige un User-Agent custom** — politique connue de NWS (`User-Agent` obligatoire). À configurer dans `publicOptions.headers`.
3. **`dangerouslyDisableContentValidation: true`** — flag présent dans la doc Reclaim pour `verifyProof`. À comprendre AVANT de l'activer en production (semble OK pour POC mais à valider).
4. **TEE mode (Beta)** — Reclaim propose un mode TEE pour plus de sécurité. **Hors-scope POC** mais à noter pour Phase 2 (lien avec confiance dans l'attestor pour une mutuelle décentralisée).

Si zkFetch ne marche pas du tout sur NWS après une demi-journée de POC, fallback documenté dans `POC-NOTES.md` :
- Demande Telegram à l'équipe Reclaim ("Works out of the box guarantee" sur leur slogan)
- Ou bascule vers **Chainlink Functions** (TEE-based, alternative crédible pour Phase 2)

## Livraison finale attendue

Une PR ouverte sur `main` avec :

- Tout le contenu de `Aratea/oracle-poc/` committé
- Commit message clair (`feat(oracle-poc): Reclaim zkFetch POC for NWS weather data`)
- PR description FR : objectif, livrables, comment tester, limites connues, prochaines étapes
- Tests verts en local
- Adresse de déploiement Sepolia partagée dans la PR

---

## Journal des changements vs v1

| # | Sujet | v1 | v2 | Raison |
|---|---|---|---|---|
| 1 | SDK Reclaim côté keeper | `@reclaimprotocol/js-sdk` + provider configuré | `@reclaimprotocol/zk-fetch` (+ `js-sdk` pour transform onchain) | Aucun provider météo dans le catalogue Reclaim (vérifié 2026-05-16). zkFetch fait le job sans provider. |
| 2 | Nom SDK Solidity | `@reclaimprotocol/verifier-solidity-sdk` | `reclaimprotocol/reclaim-solidity-sdk` (à confirmer install) | Le bon nom selon `recherche-reclaim-2026-05-16.md`. |
| 3 | `RECLAIM_PROVIDER_ID` | obligatoire | supprimé | zkFetch n'en a pas besoin. |
| 4 | Unité de température | "milliKelvin pour précision int" + type `TEMP_C` (incohérent) | milliCelsius + type `TEMP_C` | Cohérence interne + lisibilité. |
| 5 | `address attestor` dans struct | présent | retiré (conservé en event) | `msg.sender` n'a aucune autorité cryptographique. |
| 6 | Retour `submitMeasurement` | `Measurement memory` | `void` | Économise du gas, caller a déjà la donnée. |
| 7 | Anti-replay | absent | `mapping(bytes32 proofHash => bool consumed)` | Évite pollution des indexeurs. |
| 8 | Window timestamp | `[-7 jours, +1h]` | `[-6h, +5min]` | Aligné avec cadence keeper 10 min. |
| 9 | Anti-ordonnancement | absent | reject si `newTs <= storedTs` | Évite l'overwrite d'une mesure récente par une ancienne. |
| 10 | Sanity check valeur | absent | reject hors `[-100 000, +70 000]` mC | Détection bug keeper / donnée corrompue. |
| 11 | Package manager keeper | `pnpm dev` (mentionné en critère) | `npm start` | Cohérence + Bun écarté (bug `$HOME` accentué). |
| 12 | Critère install README | "< 30 min" | "< 60 min" | Réaliste : créer compte Reclaim + activer zkFetch + funder clé Sepolia |
| 13 | Section "Ce que le POC ne valide PAS" | absente | section dédiée détaillée | Évite l'illusion que l'oracle Phase 2 est prêt (cohérence whitepaper §5). |
| 14 | CI slither sur `oracle-poc/contracts/` | non mentionné | flaggé comme PR de suivi | Ruleset main exige slither sur les contrats. |
| 15 | TEE mode Reclaim | non mentionné | flaggé comme à explorer Phase 2 | Pertinent pour confiance dans l'attestor d'une mutuelle décentralisée. |

---

*Spec v2 — 2026-05-16. À valider par JSL avant écriture de code.*
