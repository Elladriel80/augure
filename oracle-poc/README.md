# Aratea Oracle POC — Reclaim + NWS

POC pour valider la **brique #1** de l'oracle météo Aratea (whitepaper v0.5 §5, Couche B) :
lire une observation officielle depuis l'API NWS, prouver cryptographiquement la lecture
via Reclaim Protocol (zkFetch), et stocker la valeur on-chain dans un contrat Solidity
sur Arbitrum Sepolia.

Spec complète + scope : [`SPEC.md`](./SPEC.md). Décisions techniques et limites : [`docs/POC-NOTES.md`](./docs/POC-NOTES.md).

## État

| Composant | Statut | Lien |
|---|---|---|
| Contrat `ReclaimWeatherSource` | **Live sur Arbitrum Sepolia** | [`0x6Bf18DF...502f`](https://sepolia.arbiscan.io/address/0x6Bf18DF23078f96d7FC035488e8C6fc68A4a502f#code) |
| Tests Foundry | 21/21 vert, incluant 2 fuzz × 1024 runs | [`contracts/test/`](./contracts/) |
| Keeper Node.js | Codé, à exécuter end-to-end avec credentials Reclaim | [`keeper/`](./keeper/) |

PR 1 (couche Solidity) mergée — [#76](https://github.com/Elladriel80/Aratea/pull/76). PR 2 (keeper) — cette PR.

---

## 1. Couche Solidity (`contracts/`)

### Prérequis

- **Foundry** récent (`forge --version` ≥ 1.0)
- Clé Arbitrum Sepolia funded (faucet : <https://www.alchemy.com/faucets/arbitrum-sepolia>)
- Optionnel : clé Etherscan pour la vérification (<https://etherscan.io/myapikey>)

### Installation

```bash
cd Aratea/oracle-poc/contracts
forge install --no-git foundry-rs/forge-std@v1.9.4
forge install --no-git OpenZeppelin/openzeppelin-contracts@v5.1.0
```

### Compiler et tester

```bash
forge fmt --check
forge build --sizes
forge test -vvv
```

Sortie attendue : **21 passed, 0 failed**.

### Re-déployer sur Arbitrum Sepolia (déjà fait, mais reproductible)

Convention Aratea : adresse déployeuse en `.env`, signer fourni au CLI. Voir
`Aratea/contracts/docs/DEPLOYMENT.fr.md` pour le pattern complet.

```bash
source ../../contracts/.env
export DEPLOYER_ADDRESS=$ADMIN_ADDRESS

forge script script/DeployPOC.s.sol:DeployPOC \
    --rpc-url $RPC_ARBITRUM_SEPOLIA \
    --ledger --sender $DEPLOYER_ADDRESS --hd-paths "m/44'/60'/0'/0/0" \
    --broadcast \
    --verify
```

Notes Ledger pour `oracle-poc/` spécifiquement (l'init code de `ReclaimWeatherSource` fait 4 332 bytes, plus gros que Phase 1) :

- Blind signing **activé** dans Settings → Ethereum sur le device
- Ajouter `--legacy` au `forge script` (force le format de tx pre-EIP-1559 que l'app Ethereum Ledger sait toujours parser)

### Vérifier l'état du contrat live

```bash
SOURCE=0x6Bf18DF23078f96d7FC035488e8C6fc68A4a502f

cast call $SOURCE "VERIFIER()(address)" --rpc-url $RPC_ARBITRUM_SEPOLIA
cast call $SOURCE "EXPECTED_LOCATION()(bytes32)" --rpc-url $RPC_ARBITRUM_SEPOLIA
cast call $SOURCE "EXPECTED_MEASUREMENT_TYPE()(bytes32)" --rpc-url $RPC_ARBITRUM_SEPOLIA
```

Pour lire la dernière mesure soumise (revertera tant qu'aucune n'est passée — c'est le rôle du keeper ci-dessous) :

```bash
cast call $SOURCE "getLatest(bytes32,bytes32)(int256,uint64,bytes32,bytes32)" \
    $(cast keccak "KJFK") \
    $(cast keccak "TEMP_C") \
    --rpc-url $RPC_ARBITRUM_SEPOLIA
```

---

## 2. Keeper Node.js (`keeper/`)

Daemon TypeScript qui poll NWS, génère une preuve Reclaim zkFetch, et la pousse on-chain.
Une itération toutes les 10 minutes par défaut. Log structuré JSON, signal handlers
SIGTERM/SIGINT pour shutdown propre.

### Prérequis

- **Node.js ≥ 20**
- Une clé privée Sepolia funded (≠ l'admin EOA, voir note sécurité plus bas)
- **Credentials Reclaim** (`APP_ID` + `APP_SECRET`) — voir [TODO HUMAIN](#todo-humain--sourcing-credentials-reclaim) ci-dessous

### Installation

```bash
cd Aratea/oracle-poc/keeper
npm install
```

Le script `postinstall` télécharge les fichiers ZK nécessaires à `@reclaimprotocol/zk-symmetric-crypto`. Si le download échoue (réseau, firewall), relance manuellement :

```bash
node node_modules/@reclaimprotocol/zk-symmetric-crypto/lib/scripts/download-files
```

### Configurer

Copier `.env.example` vers `.env` et remplir :

```bash
cp .env.example .env
# Édite .env avec tes valeurs : RECLAIM_APP_ID, RECLAIM_APP_SECRET, KEEPER_PRIVATE_KEY
```

L'adresse `RECLAIM_WEATHER_SOURCE_ADDRESS` est déjà pré-remplie sur l'instance live. Ne change rien sauf si tu redéploies un contrat à toi.

### Lancer

```bash
npm start
```

Sortie attendue (1 ligne JSON par événement) :

```json
{"ts":"2026-05-16T18:00:00.000Z","level":"info","event":"keeper_start","contractAddress":"0x6Bf18DF...","keeperAddress":"0x...","stationId":"KJFK","pollIntervalSeconds":600}
{"ts":"2026-05-16T18:00:01.000Z","level":"info","event":"iteration_start","stationId":"KJFK"}
{"ts":"2026-05-16T18:00:02.000Z","level":"info","event":"nws_observation","url":"https://api.weather.gov/stations/KJFK/observations/latest","temperatureMilliCelsius":23500,"timestampUnixSeconds":1747418400}
{"ts":"2026-05-16T18:00:06.000Z","level":"info","event":"proof_built","encodedBytes":4128}
{"ts":"2026-05-16T18:00:12.000Z","level":"info","event":"measurement_submitted","txHash":"0x...","blockNumber":"269...","gasUsed":"...","value":"23500","timestamp":"1747418400","submitter":"0x..."}
```

`Ctrl+C` ou `kill -TERM <pid>` pour shutdown propre.

### Vérifier que ça marche end-to-end

Après une itération réussie :

```bash
SOURCE=0x6Bf18DF23078f96d7FC035488e8C6fc68A4a502f

cast call $SOURCE "getLatest(bytes32,bytes32)(int256,uint64,bytes32,bytes32)" \
    $(cast keccak "KJFK") \
    $(cast keccak "TEMP_C") \
    --rpc-url $RPC_ARBITRUM_SEPOLIA
```

Devrait retourner `(value, timestamp, location, measurementType)` avec la dernière mesure
soumise. Si le keeper a tourné au moins une fois sans erreur, c'est le succès end-to-end.

### TODO HUMAIN — sourcing credentials Reclaim

`RECLAIM_APP_ID` et `RECLAIM_APP_SECRET` ne peuvent pas être générés automatiquement.
Étapes à faire manuellement (~10 min, gratuit) :

1. Aller sur <https://dev.reclaimprotocol.org> et créer un compte (Google ou email).
2. Cliquer **New Application** → nom libre (ex. `aratea-oracle-poc`).
3. Copier l'**Application ID** et l'**Application Secret** (le secret n'est affiché qu'une fois — bien le sauver).
4. **Critique** : dans l'app, onglet **Integration** → activer **zkFetch**. Sans ça, l'API renvoie 401 sans message d'erreur clair.
5. Coller les deux valeurs dans `.env` :

   ```bash
   RECLAIM_APP_ID=...
   RECLAIM_APP_SECRET=...
   ```

À ce stade-là le keeper peut tourner.

### Note sécurité — clé privée keeper

Le `KEEPER_PRIVATE_KEY` est stocké en clair dans `.env`. **Acceptable pour testnet POC**, jamais pour mainnet. Phase 2 / mainnet devra basculer vers :

- HSM (Ledger / Trezor) avec signing programmatique via Frame, ou
- KMS cloud (AWS KMS, Google Cloud KMS) avec signer custom viem, ou
- Multisig Safe avec keeper qui propose, signer humain qui valide

Le keeper EOA n'a aucun privilège on-chain — il paye juste le gas. Si la clé est compromise, le pire scénario sur Sepolia = quelqu'un soumet des fausses mesures avec d'autres proofs Reclaim valides. **Pour ce POC** : utilise une adresse jetable, **pas** ton admin EOA Phase 1.

---

## Structure du repo

```
oracle-poc/
├── README.md                          # ce fichier
├── SPEC.md                            # spec v2 figée
├── contracts/                         # Solidity (Foundry)
│   ├── src/
│   │   ├── interfaces/{IReclaim,IWeatherSource}.sol
│   │   └── sources/ReclaimWeatherSource.sol
│   ├── test/
│   │   ├── ReclaimWeatherSource.t.sol
│   │   └── mocks/MockReclaimVerifier.sol
│   ├── script/DeployPOC.s.sol
│   └── foundry.toml, remappings.txt, slither.config.json
├── keeper/                            # daemon Node.js TypeScript
│   ├── src/
│   │   ├── index.ts                   # poll loop + signal handlers
│   │   ├── nwsClient.ts               # NWS API + unitCode validation
│   │   ├── reclaimProof.ts            # zkFetch + verifyProof + transformForOnchain
│   │   └── chainSubmit.ts             # viem writeContract + event parse
│   ├── package.json, tsconfig.json
│   └── .env.example
└── docs/
    └── POC-NOTES.md                   # décisions, limites, mesures, TODOs Phase 2
```

## Lien avec le whitepaper

Ce POC implémente la **brique #1 de la Couche B** (whitepaper v0.5 §5). L'interface
`IWeatherSource` est conçue pour être consommée telle quelle par l'`OracleAggregator`
Phase 2 qui agrégera plusieurs sources (Reclaim + Chainlink + DePIN attestors).

## Adresses utiles

| Réseau | Reclaim verifier | Source |
|---|---|---|
| Arbitrum Sepolia | `0x4D1ee04EB5CeE02d4C123d4b67a86bDc7cA2E62A` | <https://docs.reclaimprotocol.org/onchain/solidity/supported-networks> |
| Arbitrum One | `0x9F0472FD02Ca1BC2d6C3A1702803Ba822C7C7E91` | idem (hors-scope POC) |

| Aratea | Adresse | Réseau |
|---|---|---|
| `ReclaimWeatherSource` (POC live) | [`0x6Bf18DF23078f96d7FC035488e8C6fc68A4a502f`](https://sepolia.arbiscan.io/address/0x6Bf18DF23078f96d7FC035488e8C6fc68A4a502f#code) | Arbitrum Sepolia |
