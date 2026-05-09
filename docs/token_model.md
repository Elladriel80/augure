# Modèle de tokens — Augure POC

*Date : 2026-05-08 — version 0.3, monorepo*

> Ce document est la version canonique du modèle de tokens, hébergée dans le repo public Augure. Une version de travail est conservée dans le workspace local du founder.

## 1. Principe fondateur

**Un seul type d'apporteur : la valeur travail.**

Le cash est du travail déjà cristallisé sous forme monétaire. Le code, la donnée, l'expertise sont du travail en cours de cristallisation. Tous les apports convergent sur la même unité de mesure et reçoivent le même traitement.

Le token AUG-POC représente une part de la valeur travail accumulée dans le projet. Pas de catégorie privilégiée, pas de pré-allocation. La cap table émerge de qui a apporté combien.

## 2. Token AUG-POC

- **Standard :** ERC-20 sur Arbitrum (cible retenue 2026-05-09 ; Sepolia testnet en Phase 1, mainnet conditionné à un audit communautaire).
- **Décimales :** 18 (standard Ethereum). Choix retenu 2026-05-09 pour la compatibilité maximale avec l'écosystème Web3 (DEX, indexeurs, wallets). L'unité de compte fonctionnelle reste le **sat** : la convention 1 sat = 1 token est imposée par construction au mint au NAV initial, indépendamment du nombre de décimales du contract ERC-20.
- **Unité de compte :** BTC. Tous les calculs internes (NAV, taux horaires, valuations) sont en BTC ou sats.
- **NAV initiale :** **1 sat = 1 token** (atomique, validé 2026-05-08). Aucune conversion mentale nécessaire — le nombre de tokens détenu lit directement la valeur travail apportée en sats.
- **Convertibilité future :** mécanisme de conversion AUG-POC → AUG (DAO Augure) inscrit dans le contract dès le départ. Ratio voté à 67 % par les holders au moment du lancement DAO.

## 3. Le mint, mécanique unifiée

Le projet n'accepte qu'**un seul type d'input** au moteur de valuation : un **fait observable**.

- Pour le cash : un dépôt on-chain (BTC, ou USDC convertis au spot du jour de subscription). Envoyé à une adresse multisig "subscription pending", non automatiquement intégré à la treasury.
- Pour le travail : un PR mergé sur le repo Augure, ou un commit signé sur main, ou une review publique sur un PR. Ce qui n'est pas dans Git n'existe pas.

L'agent IA produit la valuation **strictement** à partir de ces artefacts (diff, fichiers touchés, tests, description du PR, commits, reviews). **Aucune déclaration, aucune submission, aucune heure auto-rapportée.**

Conséquences :
- PR non-mergé, fermé, abandonné → valeur = 0.
- Travail "invisible" (mentorat en DM, hours de support hors-thread) → non capté. Trade-off explicite et assumé.
- Pour intégrer un travail non-code (animation communauté, RFC, dataset), l'output doit être commité dans le repo (digest signé, doc, données curées).

## 4. Refusabilité symétrique

Tout apport est refusable par JS (phase 1) ou le panel (phase 2+) avec motivation écrite, pendant la fenêtre de challenge :

- **Refus d'un apport travail** : ne pas merger le PR → valeur = 0.
- **Refus d'un apport cash** : renvoyer les fonds depuis l'adresse multisig "subscription pending" → 0 mint.

Aucune contribution n'est imposée au projet. Raisons légitimes de refus : conflit d'intérêt, risque réputationnel, compliance, qualité insuffisante, cohérence stratégique.

## 5. Cycle mensuel

```
J0   (1er du mois)  : agent run automatisé sur les artefacts du mois M-1
J0-J1               : publication du valuation_report.md (PR sur le repo)
J1-J7               : fenêtre de challenge publique
J7                  : ratification (auto si non contesté ET non refusé, vote panel sinon) → mint multisig
                      Tokens libérés sur les wallets enregistrés
```

## 6. Contestation et vote du panel

- Tant que personne ne challenge formellement la PR de valuation, à J7 elle est mergée et le mint exécuté.
- Une **contestation formelle** se déclare par un commentaire structuré sur la PR (label `challenge`, signé par un wallet enregistré).
- Quand une contestation existe à J7, la décision passe au **panel des Top X holders** :
  - X = 5 en phase 1 (≤ 20 contributeurs), 7 en phase 2 (20-50), 11 en phase 3 (>50).
  - **Chaque membre du panel a 1 voix.** Pas de pondération par stake. Top X = ranking par solde de tokens AUG-POC à la clôture du round.
  - Majorité simple (≥ ⌈X/2⌉+1) tranche : valider la valuation telle quelle, ou exiger une révision (avec instructions écrites, retour à l'agent).

Évite la plutocratie pure tout en confiant la décision à ceux qui ont le plus à perdre/gagner.

## 7. Calcul de la NAV (en BTC)

```
NAV_BTC = solde_BTC_treasury
        + (positions_Kalshi_USD × USD/BTC_spot)
        + créances_settlement_en_attente_BTC
        - dettes_opérationnelles_BTC

NAV_par_token = NAV_BTC / supply_circulant
```

Le travail livré n'entre PAS dans la NAV (anti-circularité).

**Conséquence — dilution des cash investors :** quand du travail est minté à la NAV courante, le supply augmente sans que le numérateur (cash + positions) ne bouge immédiatement. Le pari : le code livré crée du P&L Kalshi futur qui ramènera la NAV au-dessus.

**Garde-fous :**
- Cap mensuel global : ≤ 10 % du supply circulant minté par fenêtre.
- Cap par apporteur : ≤ 30 % du mint mensuel.
- Valuations individuelles > 0,01 BTC : passent automatiquement en vote panel (même sans contestation).
- Slashing : tokens claw-back-ables sur 6 mois en cas de fraude établie par vote 67 %.

## 8. Subscription / Redemption

- **Subscription window mensuelle** (1er du mois). Apports cash (BTC ou USDC) et apports travail (PRs mergés du mois M-1) traités dans le même round.
- **Tout apport est refusable** (cf. §4).
- **Redemption window trimestrielle**, notice 30 jours, gate 20 % par window, pénalité 2 % avant 12 mois.
- **Calcul NAV** : signé multisig 2/3 (JS + 1 advisor + 1 holder représentatif). Publication mensuelle.

## 9. Gouvernance générale

Distincte du panel anti-contestation :

- **1 token = 1 vote**, cap 25 % par wallet, sur les sujets paramétriques (rubric, taux, cap dilution, conversion DAO, slashing).
- Seuils : 51 % courant, 67 % paramétrique majeur, quorum 15 % du supply circulant.

## 10. Trade-offs assumés

1. **Volatilité de la cap table.** Personne ne sait à quoi elle ressemblera dans 6 mois. Cohérent pour qui croit que ce qui compte est la part proportionnelle de la valeur réellement accumulée, pas un % "garanti".
2. **Dilution potentielle des cash investors.** À inscrire en clair dans la term sheet.
3. **Travail non-Git invisible.** Assumé. Pour intégrer ce travail, l'output doit être commité.
4. **Volatilité BTC.** Les taux horaires sont stables en BTC mais bougent en EUR/USD. Mécanisme de recalibration par vote si dérive > 25 % en un trimestre.
5. **Panel Top X holders peut se polariser.** Mitigation : X augmente avec la communauté ; vote du panel public et journalisé.
6. **Pas attractif pour gros VC traditionnels.** Choix philosophique. Le projet cherche des investisseurs alignés sur la valeur-travail.

## 11. Genesis

Au lancement, deux choses simultanées dans la même fenêtre :

1. **Valuation rétroactive du travail JS sur kalshi-poc** (intégré dans `predictor/`). L'agent passe sur tout l'historique Git, produit une valuation détaillée par phase. **Fenêtre de challenge étendue à 30 jours**, ouverte aux premiers prospects investisseurs avant qu'ils n'investissent.
2. **Premiers investisseurs cash** (s'il y en a). Apport BTC ou USDC, mint à NAV initiale 1 sat = 1 token.

Voir le dry-run dans `rounds/archives/2026-05-genesis/` pour la première itération du moteur sur l'historique pré-open-source.
