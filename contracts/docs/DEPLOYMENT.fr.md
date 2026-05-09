> [Read in English](DEPLOYMENT.md)

# Déploiement — contracts Augure (Phase 1)

*Version 1.0 — 2026-05-09*

Ce document couvre le déploiement de bout en bout de la couche de règlement
Phase 1 sur Arbitrum Sepolia : token + registry + câblage des rôles, vérification
post-deploy, vérification du code source sur Arbiscan, et le flux propose/execute
du round genesis. Les notes mainnet sont en bas — elles requièrent un Safe multisig.

## 1. Pré-requis

### Setup une fois

- **Foundry** installé localement — voir [getfoundry.sh](https://book.getfoundry.sh/getting-started/installation).
- **Dépendances Forge installées** dans `contracts/` :
  ```bash
  cd contracts
  forge install --no-git foundry-rs/forge-std@v1.9.4
  forge install --no-git OpenZeppelin/openzeppelin-contracts@v5.1.0
  ```
- **Clé API Arbiscan** (gratuite, 5 min) — créer un compte sur [arbiscan.io](https://arbiscan.io).
- **EOA fundée sur Arbitrum Sepolia** avec un peu d'ETH testnet :
  - Faucet : [faucet.quicknode.com/arbitrum/sepolia](https://faucet.quicknode.com/arbitrum/sepolia)
  - Ou bridge depuis Sepolia ETH : [bridge.arbitrum.io](https://bridge.arbitrum.io)
  - 0,01 ETH-Sepolia est largement suffisant pour tout le flux.
- **Compte Pinata** (gratuit, 1 GB) pour le pinning IPFS des rounds — créer sur [pinata.cloud](https://pinata.cloud).

### Setup par déploiement

- Copier `.env.example` vers `.env` et remplir :
  - `RPC_ARBITRUM_SEPOLIA` — ton endpoint RPC (le public par défaut marche).
  - `ADMIN_ADDRESS` — l'adresse qui détiendra `DEFAULT_ADMIN_ROLE`. En Phase 1 testnet,
    c'est l'EOA Ledger du founder.
  - `ETHERSCAN_API_KEY` — clé API V2 Etherscan (la clé unifiée fonctionne pour
    Arbitrum Sepolia aussi — plus besoin d'une clé Arbiscan séparée depuis l'API V2).

Le signataire est configuré via les flags CLI Foundry (`--ledger`, `--private-key`,
etc.) — pas via le fichier `.env`. Cela rend le script réutilisable avec un hardware
wallet, une clé hot, ou un multisig sans changement de code.

## 2. Déploiement

```bash
cd contracts
source .env

# Avec un Ledger (Phase 1 testnet) :
forge script script/DeployAugurePhase1.s.sol:DeployAugurePhase1 \
  --rpc-url $RPC_ARBITRUM_SEPOLIA \
  --ledger \
  --sender $ADMIN_ADDRESS \
  --hd-paths "m/44'/60'/0'/0/0" \
  --broadcast \
  --verify \
  --etherscan-api-key $ETHERSCAN_API_KEY \
  -vv
```

Si ton compte Ledger a été créé via Ledger Live, le path peut être
`m/44'/60'/<index>'/0/0` à la place (un path par compte). Si Foundry
n'arrive pas à dériver `ADMIN_ADDRESS` depuis le path fourni, il refusera
de broadcaster — essaie le path alternatif ou vérifie l'adresse importée.

```bash
# Avec une clé privée (CI / déploiement one-shot depuis un wallet hot) :
forge script script/DeployAugurePhase1.s.sol:DeployAugurePhase1 \
  --rpc-url $RPC_ARBITRUM_SEPOLIA \
  --private-key $DEPLOYER_PK \
  --sender $ADMIN_ADDRESS \
  --broadcast \
  --verify \
  --etherscan-api-key $ETHERSCAN_API_KEY \
  -vv
```

Dans tous les cas, attends-toi à **signer 7 transactions** d'affilée (1 deploy
token + 1 deploy registry + 5 grantRole). Sur un Ledger ça veut dire 7
confirmations physiques sur le device.

Le script affiche les deux adresses déployées. Note-les — tu en auras besoin pour
chaque étape suivante :

```
AugPocToken deployed at:    0x...
RoundRegistry deployed at:  0x...
```

Ce qu'il fait :
1. Déploie `AugPocToken` avec `ADMIN_ADDRESS` qui détient `DEFAULT_ADMIN_ROLE`.
2. Déploie `RoundRegistry` avec `ADMIN_ADDRESS` qui détient `DEFAULT_ADMIN_ROLE` et la
   référence vers le token figée immutablement.
3. Accorde `MINTER_ROLE` sur le token au registry (pour qu'`executeRound` puisse mint).
4. Accorde `PAUSER_ROLE` sur le token à l'admin.
5. Accorde `ROUND_PROPOSER_ROLE`, `ROUND_EXECUTOR_ROLE`, `ROUND_CANCELLER_ROLE` sur le
   registry à l'admin.
6. **`BURNER_ROLE` n'est PAS accordé** — réservé au futur contract `AugConverter` qui
   exécutera la conversion AUG-POC → AUG au lancement DAO Phase 2 (voir white paper §7.2).
7. Assert toutes les propriétés de câblage des rôles dans le script avant de retourner.

Le flag `--verify` utilise ta clé API Arbiscan pour uploader le code source, ainsi
l'onglet "Code" du contract sur Arbiscan affiche le source vérifié au lieu du bytecode.

## 3. Vérification post-deploy

Lance depuis un shell propre (ou une autre machine — utile comme check indépendant) :

```bash
export TOKEN_ADDRESS=0x... # depuis l'étape 2
export REGISTRY_ADDRESS=0x... # depuis l'étape 2
export ADMIN_ADDRESS=0x... # même que le deployer

forge script script/VerifyDeployment.s.sol:VerifyDeployment \
  --rpc-url $RPC_ARBITRUM_SEPOLIA
```

Si le script termine par `== All assertions passed ==`, l'état on-chain est exactement
ce qu'on attend. Tout revert signifie un problème de câblage et **tu ne dois PAS
poursuivre vers le genesis** tant que ce n'est pas résolu.

## 4. Pin du round genesis sur IPFS

```bash
# Pin tout le dossier 2026-05-genesis via l'UI web Pinata ou la CLI.
# L'approche recommandée est de pin le dossier lui-même, ainsi le CID résultant
# pointe vers le listing du dossier avec ses 4 fichiers.

# Une fois pinné, tu obtiens un CID type bafyXXX. L'URI IPFS à utiliser est :
#   ipfs://bafyXXX/valuation_report.md

# Sauve cette URI — c'est la var d'env GENESIS_IPFS_URI ci-dessous.
```

Le CID est ce qui lie le `roundHash` on-chain aux artefacts off-chain. Si le fichier
est jamais perdu de Pinata, l'enregistrement on-chain du round reste valide (hash +
montants + bénéficiaires sont immutables), mais le rationnel humain devrait être
republié.

## 5. Cycle de vie du round genesis

### 5.1 Propose

```bash
export REGISTRY_ADDRESS=0x... # depuis l'étape 2
export GENESIS_BENEFICIARY=0x... # EOA founder qui reçoit les 34 039 500 tokens
export GENESIS_IPFS_URI=ipfs://bafyXXX/valuation_report.md
export PROPOSER_ADDRESS=$ADMIN_ADDRESS # même EOA Ledger en Phase 1 testnet
export BROADCAST=true

forge script script/ProposeGenesisRound.s.sol:ProposeGenesisRound \
  --rpc-url $RPC_ARBITRUM_SEPOLIA \
  --ledger --sender $PROPOSER_ADDRESS --hd-paths "m/44'/60'/0'/0/0" \
  --broadcast \
  -vv
```

Le script affiche le `roundHash` calculé. **Sauve-le** — tu en auras besoin pour
exécuter ou annuler plus tard. Après cette étape, le round est live on-chain dans
l'état `Proposed` avec une fenêtre de challenge de 30 jours.

### 5.2 Attendre

La fenêtre de challenge genesis est de 30 jours (per white paper §11) — étendue depuis
les 7 jours réguliers pour donner aux investisseurs prospects le temps de revoir avant
de s'engager.

Pendant cette fenêtre, n'importe qui peut appeler `challengeRound(roundHash,
reasonIpfsUri)` publiquement pour signaler la valuation. Si un challenge est déposé :
- Le panel off-chain des Top-X holders (X = 5 en Phase 1) revoit et vote.
- Si le panel **valide** le challenge → lancer §5.3 (Cancel).
- Si le panel **rejette** le challenge → laisser simplement la fenêtre expirer, puis
  lancer §5.4 (Execute) — le contract exécute les rounds Challenged pareil que les
  Proposed une fois la fenêtre expirée.

### 5.3 Cancel (uniquement si un challenge est validé)

```bash
export ROUND_HASH=0x... # depuis l'étape 5.1
export REASON_IPFS_URI=ipfs://bafyYYY/cancel-rationale.md
export CANCELLER_ADDRESS=$ADMIN_ADDRESS
export BROADCAST=true

forge script script/CancelRound.s.sol:CancelRound \
  --rpc-url $RPC_ARBITRUM_SEPOLIA \
  --ledger --sender $CANCELLER_ADDRESS --hd-paths "m/44'/60'/0'/0/0" \
  --broadcast \
  -vv
```

Un round cancelled est permanent. Redémarrer le flux genesis requiert un nouveau
rapport de valuation sous un nouveau CID IPFS, ce qui produit un nouveau `roundHash`.

### 5.4 Execute (après 30 jours, si non cancelled)

```bash
export ROUND_HASH=0x... # depuis l'étape 5.1
export EXECUTOR_ADDRESS=$ADMIN_ADDRESS
export BROADCAST=true

forge script script/ExecuteRound.s.sol:ExecuteRound \
  --rpc-url $RPC_ARBITRUM_SEPOLIA \
  --ledger --sender $EXECUTOR_ADDRESS --hd-paths "m/44'/60'/0'/0/0" \
  --broadcast \
  -vv
```

Cela mint les 34 039 500 AUG-POC tokens vers l'EOA founder. Après exécution :
- Le statut du round devient `Executed` (terminal).
- `token.totalSupply()` devient `34_039_500 * 10^18`.
- Le snapshot du premier mois est capturé à `0` (exception genesis), donc
  `MonthlyMintCap` ne contraint pas pour ce mois. Dès le mois UTC suivant, le cap
  10 % s'applique normalement.

## 6. Flux mainnet (plus tard)

Le déploiement Phase 1 mainnet est **conditionné** à :
1. Un audit communautaire (Code4rena Arena-X, Sherlock Watson, ou peer review documentée
   par 2-3 ingénieurs Solidity reconnus — voir SECURITY.fr.md §7).
2. Un Safe multisig déployé sur Arbitrum mainnet avec au moins 2 signataires
   hardware-wallet, seuil M ≥ 2.

Le flux de déploiement diffère alors du §2 :
- `ADMIN_ADDRESS` est l'adresse du Safe multisig, PAS l'EOA déployeur.
- `DeployAugurePhase1.s.sol` refusera de tourner à cause de l'assertion
  `deployer == admin`. Utiliser le flux alternatif `WireRoles.s.sol` (prévu dans une
  PR de suivi) où le deploy et les étapes de role-granting sont séparés : le deploy
  est broadcast depuis l'EOA déployeur sans wiring de rôles, puis les grants de rôles
  sont exécutés par le Safe via l'UI Transaction Builder.
- Tous les scripts opérationnels (`ProposeGenesisRound`, `ExecuteRound`, `CancelRound`)
  ont par défaut `BROADCAST=false` et affichent le calldata Safe-compatible. Coller
  le calldata dans le Transaction Builder du Safe, obtenir les signatures multisig,
  broadcaster.

## 7. Rollback / break-glass

- Un round `Proposed` ou `Challenged` peut être cancelled par le rôle canceller à
  tout moment. La cancellation est permanente.
- Un bug découvert dans un contract déployé déclenche un nouveau déploiement + une
  migration documentée. Il n'y a pas de switch d'upgrade — voir white paper §7.2 et
  ARCHITECTURE.fr.md §7.
- La fonction pause sur le token bloque les transferts d'utilisateur à utilisateur
  mais **ne bloque pas** mint ni burn (intentionnel — voir SECURITY.fr.md §5.5).
  À utiliser uniquement comme mesure défensive durant un triage d'incident.
