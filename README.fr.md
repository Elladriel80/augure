> [Read in English](README.md)

# Augure

**Prediction markets météo et assurance paramétrique décentralisée, open-source.**

Augure est en phase initiale. Sa première étape est de valider un edge prédictif sur les marchés météo Kalshi avant de construire l'infrastructure DAO pour l'assurance paramétrique adossée à un risk pool.

## Structure du repo

Ce monorepo s'organise en quatre dossiers de premier niveau :

```
augure/
├── predictor/      ← code de prédiction (Phase 1 : POC Kalshi)
├── contracts/      ← smart contracts (Phase 2+ : token, gouvernance, assurance)
├── rounds/         ← mécanique d'émission de tokens (live : mint AUG-POC valeur travail)
└── docs/           ← documents transverses (modèle token, architecture)
```

### `predictor/`
Le moteur de prédiction. Actuellement le POC Kalshi : méta-ensemble IA combinant ECMWF, GraphCast, GFS, JMA ; règles de résolution NWS ; analyse microstructure ; infrastructure backtest.

### `contracts/`
Smart contracts Solidity. Actuellement une roadmap (pas encore de contracts live). Hébergera le token ERC-20 AUG-POC, le module mint des rounds, la gouvernance par panel, et (Phase 3+) les contracts paramétriques d'assurance et oracles météo.

### `rounds/`
La mécanique vivante d'émission des tokens AUG-POC à toute personne apportant de la valeur travail au projet (code, recherche, donnée, design, capital). Contient le rubric public, la grille de taux horaires, le prompt de l'agent de valuation, les scripts d'automatisation, et les rapports historiques de valuation.

### `docs/`
Documentation transverse : modèle économique du token, spec du moteur de valuation, architecture projet.

## Phases

1. **POC Kalshi** *(en cours)* — valider l'edge prédictif. Critère go/no-go : ensemble IA bat le best single model et bat la climato sur N>50 events.
2. **DAO Augure** — risk pool tokenisé façon Nexus Mutual, émission des contrats via AMM/orderbook, pricing via le moteur prédictif.
3. **DePIN data layer** — stations météo physiques rémunérées en token (partenariat WeatherXM ou réseau propre).

## Modèle de token en une phrase

Un seul token (AUG-POC, puis AUG après lancement DAO). Une seule mécanique : chaque apport — cash ou travail — est valorisé en équivalent BTC et minté à la NAV. Pas de buckets pré-attribués, pas de bonus founder, pas de catégorie privilégiée. La cap table émerge des valuations accumulées. Détail dans [`docs/token_model.md`](docs/token_model.md).

## Comment participer

Voir [`CONTRIBUTING.fr.md`](CONTRIBUTING.fr.md). En résumé : enregistre ton wallet, livre des artefacts visibles dans Git (code, donnée, RFCs) sur le module pertinent, fais-toi évaluer chaque mois par le rubric, reçois des tokens AUG-POC.

## Licence

[Apache 2.0](LICENSE).
