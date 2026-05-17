# POC oracle Reclaim — notes techniques

> Compagnon de [`SPEC.md`](../SPEC.md) (le quoi) et [`README.md`](../README.md) (le comment).
> Ce fichier capture les décisions techniques, les limites assumées, et les TODOs Phase 2.

---

## 1. Décisions techniques prises

### 1.1 zkFetch plutôt qu'un provider Reclaim configuré

Le catalogue Reclaim public ([dev.reclaimprotocol.org/explore](https://dev.reclaimprotocol.org/explore), vérifié 2026-05-16) ne contient **aucun provider météo officiel** :

- `nws`, `noaa`, `weather.gov`, `forecast`, `openweather`, `open-meteo`, `weatherxm` : 0 résultats
- `meteo` : 4 stubs marqués "University Provider" sans data fields utilisables
- Le catalogue est massivement orienté social/identity/KYC (GitHub, Gmail, LinkedIn, Twitter, Binance, Uber, etc.)

**Conséquence** : impossible d'utiliser le SDK Reclaim "user-facing" classique. Mais
`@reclaimprotocol/zk-fetch` permet d'attester n'importe quelle URL HTTPS publique
sans provider pré-configuré. C'est exactement ce qu'il faut pour une API REST
publique comme NWS.

Stack côté keeper :

- `@reclaimprotocol/zk-fetch` (génération de proof depuis URL arbitraire)
- `@reclaimprotocol/js-sdk` (`verifyProof` + `transformForOnchain` post-zkFetch)
- `viem` (interaction on-chain)

### 1.2 Unité = milliCelsius (`int256`)

`measurementType = keccak256("TEMP_C")` cohérent avec une valeur en **milliCelsius**.
Range stockable : `-100_000` à `+70_000` mC (record terrestre froid Vostok 1983 ~−89 °C,
chaud Death Valley 1913 ~+56,7 °C, marges généreuses).

Alternative écartée : milliKelvin. Aurait évité les négatifs mais perdu la lisibilité
on-chain (tout serait dans `[173_150, 333_150]`).

Le keeper convertit avec `Math.round(valueCelsius * 1000)` après avoir asserté que
`properties.temperature.unitCode === "wmoUnit:degC"`. **Pas de conversion auto-magique**
depuis degF / K : si NWS retourne un unitCode différent, le keeper reject l'observation
et log `wrong_temperature_unit`. C'est volontaire — la classe de bugs "j'ai mis la mauvaise
unité pendant 3 mois en silence" est éliminée.

### 1.3 Anti-replay via hash de la `Proof` complète

`_consumedProofs[keccak256(abi.encode(proof))] = true` après une `submitMeasurement`
réussie. Évite la pollution des indexeurs (même proof soumise 2× = 2× event).

Coût : 1 SSTORE (~20k gas la 1ère fois) + 1 SLOAD à chaque submit. Acceptable au POC.

### 1.4 Window timestamp `[block.timestamp − 6h, block.timestamp + 5min]`

Spec v1 disait `[−7 jours, +1h]`, trop laxiste pour une mesure "latest" d'une station
qui produit une observation toutes les ~10 min. La nouvelle window :

- `+5 min` futur : tolère skew d'horloge NWS / chaîne
- `−6h` passé : génère headroom pour outages keeper / NWS sans accepter d'observation arbitrairement vieille

Aligné avec la cadence keeper `POLL_INTERVAL_SECONDS=600` (10 min).

### 1.5 Anti-ordonnancement inverse

Si une mesure horodatée `t=12h` est déjà stockée et qu'on tente d'écrire `t=10h`, le
contrat reject (`NotMoreRecent`). Couvre aussi `t == storedTs` (deux observations à la
même seconde = anomalie, on garde la première). Test dédié `test_submit_sameTimestamp_reverts`.

### 1.6 ReentrancyGuard sur `submitMeasurement`

Le verifier Reclaim upstream est **UUPS-upgradeable** (`Reclaim.sol` hérite de
`UUPSUpgradeable`). En théorie un upgrade compromis pourrait faire que `verifyProof()`
réentre dans `ReclaimWeatherSource`. Le ReentrancyGuard d'OpenZeppelin v5 protège
contre ça. Test `test_submit_reentrancy_isBlocked` assert via un mock qui rappelle
`submitMeasurement` pendant `verifyProof`.

Coût : ~100 gas (1 SLOAD + 1 SSTORE par transition). Bargain pour la classe de bugs
éliminée.

### 1.7 Signer convention `DEPLOYER_ADDRESS` + CLI

Aligné avec `Aratea/contracts/script/DeployArateaPhase1.s.sol`. Aucune clé privée
plaintext dans `.env`. Signer fourni au CLI (`--ledger` / `--account` / `--private-key`).

### 1.8 `verifyProof` côté keeper sans flag de désactivation

Le SDK `@reclaimprotocol/js-sdk` v4+ expose `verifyProof(proof, allowAiWitness?): Promise<boolean>`.
L'ancien flag `dangerouslyDisableContentValidation` documenté sur docs.reclaimprotocol.org
**n'existe plus** dans les types actuels — la doc est en retard.

Ce que `verifyProof` v4 vérifie en pratique : recovery des signatures des witnesses sur
le hash du claim. Ce qu'il **ne fait pas** : re-fetch de l'URL upstream pour comparer
les bodies. C'est exactement le comportement qu'on veut (et NWS rate-limit agressivement
de toute façon).

### 1.9 Pin SDK Reclaim via npm `overrides` (anti-drift transitive)

`@reclaimprotocol/attestor-core@4.0.3` (consommé via `zk-fetch`) déclare sa dépendance
sur `@reclaimprotocol/tls` comme `"github:reclaimprotocol/tls"` **sans aucune version
ni commit pin**. Résultat : chaque `npm install` pioche le HEAD courant du `main`
de github.com/reclaimprotocol/tls, qui dérive dans le temps. Le 2026-05-17, le HEAD
ne contenait plus la fonction `strToUint8Array` que `attestor-core` utilise dans ses
binaires compilés → crash runtime immédiat au chargement de `http-parser.js`.

**Fix appliqué (fix #79)** :

1. Bump direct `@reclaimprotocol/zk-fetch` `^0.4.0` → `^0.8.0` (cette version pin
   `tls` à un commit précis : `github:reclaimprotocol/tls#8e0669a220341432673a20bb51f9339555701ef4`)
2. Ajout d'un bloc `overrides` dans `keeper/package.json` qui force le même commit
   au niveau racine, en défense en profondeur contre une future drift dans `zk-fetch` :

   ```json
   "overrides": {
       "@reclaimprotocol/tls": "github:reclaimprotocol/tls#8e0669a220341432673a20bb51f9339555701ef4"
   }
   ```

3. Smoke test CI ajouté (`oracle-poc-keeper-ci.yml`) : boote le keeper 10 s avec
   des env dummy, grep le log pour les signatures `TypeError | MODULE_NOT_FOUND |
   Cannot find module | is not a function`. Toute régression transitive future
   du même type fera fail le CI.

À monter à la Phase 2 (avant migration mainnet) : ouvrir un upstream issue / PR sur
`reclaimprotocol/attestor-core` pour pin sa dep tls proprement dans le package.json
plutôt que de compter sur notre override aval. Pas bloquant POC, mais propre pour
la communauté.

---

## 2. Limites assumées au POC (à transformer en TODO Phase 2)

### 2.1 [TODO Phase 2] Trust keeper sur `declaredValueMc` / `declaredTimestamp`

**Limite** : le contrat valide cryptographiquement la proof Reclaim, mais ne parse pas
le JSON `context.extractedParameters` qu'elle contient. Le keeper passe `declaredValueMc`
et `declaredTimestamp` à côté de la proof, et le contrat les croit sur parole.

Conséquence : un keeper compromis peut soumettre une proof Reclaim valide et déclarer
une valeur arbitraire qui n'a aucun rapport. Le contrat l'acceptera (modulo la window
de sanity).

**Acceptable au POC** parce que le keeper c'est nous (le projet). Mais Phase 2 industrialise
avec keeper potentiellement externe → bloquant.

**Remédiations possibles Phase 2** :

1. Parser le JSON `context.extractedParameters` on-chain via le helper
   `extractFieldFromContext(string, string)` exposé par `Reclaim.sol` (déjà déployé).
   Coûteux en gas (boucle bytes) mais self-contained.
2. Format de proof v2 où `claimInfo.parameters` expose des typed fields ABI-encodés
   plutôt qu'un JSON string. Demande un changement côté Reclaim, hors de notre contrôle.
3. Garder le trust keeper mais ajouter du **slashing économique** : keeper stake
   un collateral, déclarations incorrectes prouvables par challenge → slash.
   Cohérent avec Phase 3 du whitepaper.

### 2.2 [TODO Phase 2] Cohérence `proof.context` ↔ `EXPECTED_LOCATION` / `EXPECTED_MEASUREMENT_TYPE`

Corollaire du 2.1. Le contrat est instancié pour KJFK/TEMP_C mais ne vérifie pas que
la proof attestée concerne bien `api.weather.gov/stations/KJFK/observations/latest`.
Un keeper hostile pourrait soumettre une proof valide pour une URL `/stations/LAX/`
et le contrat stockerait la valeur sous la clé KJFK.

**Remédiation Phase 2** : extraire l'URL depuis `claimInfo.parameters` (qui est un JSON
contenant `{"url": "...", "method": "GET", ...}`) et asserter qu'elle matche un pattern
basé sur `EXPECTED_LOCATION`. Même outillage que 2.1.

### 2.3 [TODO Phase 2] Malléabilité signature ECDSA

`keccak256(abi.encode(proof))` inclut `signedClaim.signatures`. Les signatures ECDSA
standards ont une malléabilité connue (`s` vs `n-s` produit deux signatures valides
pour le même message).

Si Reclaim ne **canonicalise pas** ses signatures (force `s` dans la moitié basse), un
attaquant en possession d'une proof valide peut générer une signature alternative qui :

1. Vérifie tout aussi bien au niveau ECDSA
2. Produit un proof distinct au niveau bytes
3. Donc un `proofHash` différent
4. Donc passe l'anti-replay du contrat

L'attaquant pourrait soumettre 2× la "même" mesure. Risque mineur (il a besoin de
l'accès à la proof originale, et la 2ème submission consommerait juste plus de gas),
mais sale.

**Remédiation Phase 2** : hasher sur `signedClaim.claim.identifier` (qui est censé être
le hash du `claimInfo` côté Reclaim et donc canonique) plutôt que sur la proof complète.
Vérification supplémentaire requise : que `identifier` couvre bien tout ce qui doit être
unique. À auditer.

### 2.4 [RÉSOLU Phase 1] Drift transitive `@reclaimprotocol/tls` non pinné

**Découvert au premier `npm start` live (2026-05-17)** : `attestor-core@4.0.3` crash
au chargement avec `TypeError: (0 , tls_1.strToUint8Array) is not a function` parce
que sa dépendance `@reclaimprotocol/tls` est déclarée comme `github:reclaimprotocol/tls`
sans version ni commit pin. npm pioche le HEAD du `main` qui a, entre temps, renommé
la fonction (`strToUint8Array` → `asciiToUint8Array`).

**Remédiation** : voir §1.9. Fix appliqué dans PR #79 — bump zk-fetch + bloc `overrides`
dans `package.json` + smoke test CI. **Le TODO est traité en Phase 1**, pas reporté à
Phase 2, parce qu'il bloquerait toute exécution live du keeper.

À adresser en Phase 2 : upstream issue / PR sur `reclaimprotocol/attestor-core` pour
pin tls proprement côté package. Notre override est un workaround aval, pas une
solution structurelle.

---

## 3. Mesures gas et coûts

### 3.1 Déploiement

| Métrique | Valeur |
|---|---|
| Init code size | 4 332 bytes |
| Runtime size | 4 008 bytes |
| Gas utilisé au déploiement | 944 427 |
| Gas price observé | 0.020 gwei (Arbitrum Sepolia) |
| Coût total | 0.0000189 ETH (≈ $0.00006 testnet) |

### 3.2 `submitMeasurement` — TODO à mesurer en live

À remplir après le premier run live du keeper (PR 2 + credentials Reclaim). Champs
attendus :

| Cas | Gas estimé | À mesurer |
|---|---|---|
| 1ère submission (storage froid) | ~150–200k | TODO |
| Submissions suivantes (storage chaud) | ~80–120k | TODO |
| Revert anti-replay | ~30–35k | TODO |
| Revert window/range | ~25–30k | TODO |

### 3.3 Coût Reclaim par proof — TODO à mesurer en live

Reclaim facture les dapps en token RECLAIM pour chaque proof (cf. `recherche-reclaim-2026-05-16.md`).
Tarification exacte au volume cible (1 proof / 10 min = ~4 320/mois) à mesurer côté
dashboard Reclaim après quelques jours de run.

### 3.4 Cadence opérationnelle

Default `POLL_INTERVAL_SECONDS=600` (10 min) = ~144 tx/jour. Sur Sepolia : gratuit
(faucet). En extrapolation Phase 2 sur Arbitrum One avec gas réaliste, ça reste cheap
(~$0.01–$0.10/tx selon période), mais on devrait basculer vers **event-driven** :
ne soumettre que quand un settlement de couverture paramétrique le demande, pas en cron.

---

## 4. Prochaines étapes Phase 2

Dans l'ordre de priorité décroissante :

1. Adresser **TODO 2.1 et 2.2** (trust keeper) — bloquant pour keeper externe
2. Adresser **TODO 2.3** (malléabilité ECDSA) — défense en profondeur
3. Implémenter `OracleAggregator` consommant `IWeatherSource` × N (Reclaim + Chainlink Data Feeds + optionnellement WeatherXM)
4. Passer la cadence de submission de cron à event-driven
5. Industrialiser le signing keeper (HSM / KMS / multisig) pour mainnet
6. Ajouter de la gouvernance on-chain sur le choix de verifier / SDKs / locations supportées

Le whitepaper v0.5 §5 décrit la cible Couche B complète. Ce POC en valide la brique #1.
