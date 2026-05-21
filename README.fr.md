> [Read in English](README.md)

# Aratea

**Marchés prédictifs météo et mutuelle paramétrique décentralisée, open-source.**

Aratea est en phase initiale. Sa première étape est de valider un edge prédictif sur les marchés météo Kalshi avant de construire l'infrastructure DAO pour la mutuelle paramétrique adossée à un pool de mutualisation.

> **Note importante** — Aratea n'est pas une assurance au sens du Code des assurances ni de Solvency II. C'est une **mutuelle discrétionnaire décentralisée** : les membres mutualisent un pool de capital, et l'exécution des indemnisations relève d'une mécanique paramétrique automatique adossée à des oracles, gouvernée par les holders. Cf. white paper, section 4.
>
> ---

> **Contributeurs bienvenus.** Aratea rémunère les contributeurs en tokens, valorisés en BTC via un rubric public, fact-only depuis Git.
> - **5 good-first-issues ouvertes maintenant** → [`docs/contributor-starter-issues.md`](docs/contributor-starter-issues.md)
> - **Comment marche le paiement** → [`docs/value_engine.md`](docs/value_engine.md)
> - **État actuel du projet** → [`STATUS.md`](STATUS.md)

---

## Structure du repo

Ce monorepo s'organise en quatre dossiers de premier niveau :

```
aratea/
├── predictor/      ← code de prédiction (Phase 1 : POC Kalshi)
├── contracts/      ← smart contracts (Phase 2+ : token, gouvernance, mutuelle)
├── rounds/         ← mécanique d'émission de tokens (live : mint AUG-POC valeur travail)
└── docs/           ← documents transverses (modèle token, architecture)
```

### `predictor/`
Le moteur de prédiction. Actuellement le POC Kalshi : méta-ensemble IA combinant ECMWF, GraphCast, GFS, JMA ; règles de résolution NWS ; analyse microstructure ; infrastructure backtest.

### `contracts/`
Smart contracts Solidity. **Phase 1 en cours** (mai 2026) : couche de règlement on-chain pour la mécanique de mint valeur-travail — `AugPocToken` (ERC-20 + AccessControl + Pausable) et `RoundRegistry` (cycle de vie propose / challenge / execute / cancel). Aucun cap d'émission n'est appliqué on-chain ; la qualité est garantie off-chain par le rubric de valuation, le vote pondéré au-delà de 0,01 BTC, le cooldown nouveaux entrants, le slashing et l'audit annuel (white paper §7.7). Foundry, Solidity 0.8.24, OpenZeppelin v5, cible Arbitrum Sepolia testnet. Voir [`contracts/README.fr.md`](contracts/README.fr.md) pour le statut et les jalons.

### `rounds/`
La mécanique vivante d'émission des tokens AUG-POC à toute personne apportant de la valeur travail au projet (code, recherche, donnée, design, capital). Contient le rubric public, la grille de taux horaires, le prompt de l'agent de valuation, les scripts d'automatisation, et les rapports historiques de valuation.

### `docs/`
Documentation transverse : modèle économique du token, spec du moteur de valuation, architecture projet.

## Phases

1. **POC Kalshi** *(en cours)* — valider l'edge prédictif. Critère go/no-go : ensemble IA bat le best single model et bat la climato sur N>50 events.
2. **DAO Aratea** — pool de mutualisation tokenisé façon Nexus Mutual, émission des contrats paramétriques via AMM/orderbook, pricing via le moteur prédictif.
3. **DePIN data layer** — stations météo physiques rémunérées en token (partenariat WeatherXM ou réseau propre).

## Modèle de token en une phrase

Un seul token (AUG-POC, puis ARA après lancement DAO). Une seule mécanique : chaque apport — cash ou travail — est valorisé en équivalent BTC et minté à la NAV. Pas de buckets pré-attribués, pas de bonus founder, pas de catégorie privilégiée. La cap table émerge des valuations accumulées. Détail dans [`docs/token_model.md`](docs/token_model.md).

## Comment participer

Commence ici :

1. **Choisis une issue de démarrage** → [`docs/contributor-starter-issues.md`](docs/contributor-starter-issues.md) (5 ouvertes, scopées sur 1 module chacune, pas de credentials)
2. **Comprends comment tu es payé** → [`docs/value_engine.md`](docs/value_engine.md) (fact-only Git, valuation en BTC, rubric public)
3. **Enregistre ton wallet** quand tu es prêt pour le round mensuel suivant → [`rounds/WALLETS.md`](rounds/WALLETS.md)
4. **Process complet** → [`CONTRIBUTING.md`](CONTRIBUTING.md)

DMs ouverts sur X : [@jsl_augure](https://x.com/jsl_augure) (handle en migration vers @jsl_aratea).

## Licence

[Apache 2.0](LICENSE).
