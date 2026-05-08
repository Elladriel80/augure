# Augure — architecture overview

*Date : 2026-05-08 — version 0.1*

## Vision

Augure est un protocole décentralisé d'assurance paramétrique météo, alimenté par un moteur prédictif communautaire. Trois piliers :

1. **Moteur prédictif** : méta-ensemble de modèles météo IA + données crowdsourcées. Open-source, contributif, mesuré sur Kalshi en phase POC.
2. **DAO d'assurance** : risk pool tokenisé façon Nexus Mutual. Stakers underwrite, payouts paramétriques déclenchés par oracles météo.
3. **DePIN data layer** : stations physiques rémunérées en token. Améliore la résolution locale et réduit la dépendance aux feeds gouvernementaux.

Les trois piliers se renforcent : meilleure prédiction → meilleur pricing → plus de contrats vendus → plus de stakers attirés → financement de plus de capteurs DePIN → meilleure prédiction.

## Phases

### Phase 1 — POC Kalshi *(en cours)*

Objectif : démontrer que le moteur prédictif a un edge mesurable. Pas de produit final, pas de smart contract, pas de risk pool. Le critère go/no-go est strictement quantitatif : ensemble IA bat best single model et bat climatologie sur N>50 events forward-testés (sans data leakage).

Code : `predictor/`. Off-chain entièrement. Bankroll de trading sur Kalshi finance la suite.

### Phase 2 — DAO Augure (token + gouvernance)

Démarre une fois la Phase 1 validée. Objectifs :
- Déployer l'ERC-20 AUG-POC sur Base/Arbitrum/Optimism (chain à trancher).
- Activer le module mint via les rounds mensuels existants (déjà testés en off-chain).
- Mettre en place la gouvernance par panel Top-X holders.
- Convertir AUG-POC vers AUG (token DAO final) par vote ≥ 67 %.

Code : `contracts/token/`, `contracts/rounds/`, `contracts/governance/`.

### Phase 3 — Assurance paramétrique

Démarre une fois la DAO opérationnelle et le predictor démontré en live. Objectifs :
- Risk pool : stakers déposent USDC/BTC, perçoivent les primes des contrats vendus.
- Pricing : moteur prédictif (off-chain) émet des prix de contrat, signés et postés on-chain.
- Résolution : Chainlink Custom au-dessus des feeds NOAA/NWS (et DePIN propre quand disponible).
- Catégories initiales : température extrême, précipitations cumulées, événements vent.

Code : `contracts/insurance/`, `predictor/oracle/` (signature des prix), pipeline de résolution dans `predictor/scripts/`.

### Phase 4 — DePIN data layer

Stations physiques (partenariat WeatherXM ou réseau propre, à arbitrer). Récompense en token AUG basée sur :
- Disponibilité de la station (uptime).
- Qualité des données (cohérence avec voisins, validation par modèles, pas d'outliers manuels).
- Densité géographique (bonus pour les zones sous-couvertes).

Le module rounds gère la valuation de ces apports comme tout autre travail (non-code).

## Composants transverses

### Modèle économique du token

Voir [`token_model.md`](token_model.md) — un seul token, valeur travail comme principe unifiant, mint à NAV, refusabilité symétrique entre apports cash et travail, gouvernance Top-X holders.

### Moteur de valuation

Voir [`value_engine.md`](value_engine.md) — agent IA fact-only sur artefacts Git, rubric et grille de taux publics et versionnés, fenêtre de challenge 7 jours, ratification par panel des Top-X holders en cas de contestation.

### Oracles météo

Phase 3+. Architecture cible :
1. Source primaire : NOAA / NWS pour les marchés US (résolutions Kalshi-compatibles).
2. Source secondaire : ECMWF / Météo-France / DWD pour les marchés européens à venir.
3. Cross-validation : DePIN stations propres pour résolution locale haute fréquence.

Le module `predictor/src/kalshi/resolution.py` actuel sert de prototype : règles précises de mapping station ↔ market, gestion des arrondis, conventions Trace. Sera ré-utilisé et étendu pour l'oracle on-chain.

### Stack data

- Forecasts : Open-Meteo (gratuit, multi-modèle) en POC. Aurora/Pangu/FourCastNet/GenCast via HuggingFace + GPU cloud en Phase A.2.
- Historical : ERA5 via Open-Meteo.
- Markets Kalshi : API REST publique (lecture). Intégration write API quand DAO active si élargissement à d'autres prediction markets.
- Crowdsourced : à intégrer (PWS, Twitter, traffic cams).

## Décisions ouvertes

- **Chain de déploiement** : Base / Arbitrum / Optimism. Critères : gas, écosystème DeFi/insurance, custody options.
- **Stable de bankroll** : USDC, EURC, multi-stable. Impact : frais conversion Kalshi (USD only).
- **Custody Kalshi POC** : compte personnel JS, structure intermédiaire LLC US, foundation. Détermine la structure juridique amont.
- **Toolchain smart contracts** : Foundry retenu, à graver dans `contracts/README.md`.
- **Wallet registry** : fichier signé en Phase 1 (`rounds/WALLETS.md`), registry on-chain à partir de Phase 2.
