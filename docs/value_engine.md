# Moteur de valuation Augure — fact-only, BTC

*Date : 2026-05-08 — version 0.2, monorepo*

> Ce document est la version canonique du moteur de valuation, hébergée dans le repo public Augure. Voir aussi `rounds/RUBRIC.fr.md` pour les règles opérationnelles précises et `rounds/agent/PROMPT.fr.md` pour le prompt système.

## 1. Mission

Estimer en **BTC** la valeur de chaque apport observable au projet, sans aucune déclaration de l'apporteur. Sortie : un montant en BTC qui sert de numérateur au mint (`tokens = valeur_BTC / NAV`).

Contraintes inviolables :
- **Fact-only.** Source unique d'information : Git (PRs mergés, diffs, commits, reviews, descriptions). Aucun rapport d'heures, aucune submission texte, aucune affirmation non-vérifiable.
- **Push KO = 0.** Travail rejeté, non-mergé, abandonné → valeur nulle.
- **BTC.** Tous les calculs en BTC ou sats. Pas d'EUR/USD dans les paramètres (uniquement en référence pour recalibration trimestrielle).
- **Open-source du rubric et du prompt.** Versionnés, modifiables par PR + ratification.

## 2. Architecture

Trois couches mensuelles :

### Couche A — Collecte (jour 1)

GitHub Action automatisée. Pour chaque wallet enregistré dans `rounds/WALLETS.md`, agrège **uniquement** :

- PRs mergés du mois M-1 (titre, body, diff stats, fichiers touchés, reviewers, labels, commit messages, issues fermées par le PR)
- Reviews données sur PRs d'autres
- Commits signés directement sur `main` (rares)

Ce qui n'est PAS collecté :
- Issues ouvertes mais sans PR mergé associé
- Discussions Discord, forum, DM
- Time tracking déclaré
- Auto-rapports de quelque nature que ce soit

Sortie : `rounds/archives/YYYY-MM/raw.json`.

### Couche B — Valuation IA (jours 1-2)

L'agent reçoit `raw.json` + `RUBRIC.md` + `HOURLY_RATES.md` + état projet (`docs/architecture.md` + `docs/state.md` du round si présent).

Pour chaque artefact observable, il calcule :

```
valeur_BTC = heures_estimées × taux_BTC_par_heure × ajust_qualité × ajust_impact
```

- **heures_estimées** : temps qu'un pro mettrait pour produire le même output, déduit du diff et du contexte. Pas demandé à l'apporteur.
- **taux_BTC_par_heure** : selon profil requis par la nature de l'output, table publique versionnée (`rounds/HOURLY_RATES.md`).
- **ajust_qualité** ∈ [0,5 ; 1,3]. Lu sur les artefacts : tests présents, CI verte, reviewers, propreté du code.
- **ajust_impact** ∈ [0,8 ; 1,5]. Lu sur le rôle du module touché et l'avancement du roadmap.

Le profil est une **variable** (taux marché → BTC, recalibrée trimestriellement). Le **livrable** détermine la valeur (un junior qui produit du senior touche le rate senior pour ce livrable, et inversement).

Sortie : `rounds/archives/YYYY-MM/valuation_report.md` (PR ouverte sur le repo augure).

### Couche C — Challenge & ratification (jours 1-7)

Fenêtre de **7 jours**. Un commentaire structuré (label `challenge`, signé par wallet du registry) peut contester un point précis de la valuation.

À J+7 :
- **Aucun challenge formel** → la PR est mergée par GitHub Action. Mint multisig exécuté.
- **Au moins un challenge formel** → la décision passe au panel **Top X holders, 1 voix chacun**. X = 5 en phase 1. Majorité simple. Délai panel : 72 h. Le panel valide la valuation telle quelle ou demande une révision spécifique avec instruction écrite. Après révision, nouvelle PR, nouvelle fenêtre 72 h restreinte.

## 3. Le profil comme variable de marché

Les taux du `HOURLY_RATES.md` sont des **variables** liées au marché freelance, exprimées en BTC à un instant donné. Recalibration trimestrielle :

- Source : moyennes TJM Paris (Malt, Comet, Crème de la Crème) par profil.
- Conversion EUR/BTC au spot moyen du trimestre.
- Si dérive > 25 % vs valeurs courantes → vote token-weighted (51 %) pour ajuster.

Le rubric ne *choisit* pas le profil par individu. Il choisit le profil **selon l'output produit** : un PR d'optimisation de pipeline ML → profil ML/data, peu importe qui l'a écrit. Un PR de doc → profil tech writer.

## 4. Le rubric — résumé

Détail dans `rounds/RUBRIC.md`. Synthèse :

1. **Heures estimées** : déduites du diff (LoC ajustées par complexité, fichiers touchés, refactor vs greenfield, présence de tests).
2. **Profil** : déterminé par la nature du module et de l'output.
3. **Qualité** ∈ [0,5 ; 1,3] : tests, doc, CI, reviewers approving, dette technique.
4. **Impact** ∈ [0,8 ; 1,5] : core vs périphérique, débloque-t-il une étape, métrique mesurable améliorée.

Bornes dures, pas de bonus exceptionnel.

## 5. Cas du cash

Hors rubric côté valuation (1 sat = 1 sat, pas d'estimation), mais **soumis à ratification comme tout apport**.

- Apport BTC : envoyé à l'adresse multisig `subscription-pending` du round courant. Si accepté à J+7, mint à NAV. Si refusé par JS (phase 1) ou panel (phase 2+) avec motivation écrite, fonds renvoyés.
- Apport USDC ou EURC : converti au spot du jour de subscription en sats, même mécanique pending + ratification.

Le cash apparaît dans le rapport mensuel **sans valuation** (montant brut + adresse expéditeur), pour visibilité du ratificateur. Refus possible pour raison stratégique, réputationnelle, conflit d'intérêts ou compliance.

## 6. Genesis — valuation rétroactive

L'agent passe sur **tout l'historique Git du repo** (commits, PRs, code livré avant l'ouverture du projet). Découpage par phases logiques documentées.

Pour le round genesis :
- Fenêtre de challenge **étendue à 30 jours** (vs 7 standards).
- Notification explicite aux premiers prospects investisseurs **avant qu'ils n'investissent**.
- Pas de bonus "founder".

Voir le dry-run dans `rounds/archives/2026-05-genesis/` pour la première itération.

## 7. Garde-fous opérationnels

- **Cap mensuel global** : ≤ 10 % supply circulant.
- **Cap par apporteur** : ≤ 30 % du mint mensuel.
- **Vote auto pour grosses valuations** : tout apporteur valorisé > 0,01 BTC dans un round passe en vote panel même sans contestation.
- **Cooldown nouveaux entrants** : première contribution mergée > 30 jours avant éligibilité au mint.
- **Slashing** : claw-back sur 6 mois en cas de fraude établie par vote 67 %.
- **Audit annuel** : rubric, grille, valuations passées revus en assemblée holder.

## 8. Évolution du système

- **Phase 1 (≤ 20 contributeurs)** : panel 5 holders. Ratification par GitHub Action si non contesté, sinon panel.
- **Phase 2 (20-50)** : panel 7 holders. Ajout possible d'un module peer-feedback automatisé (signaux croisés review-de-PR, encore fact-based).
- **Phase 3 (DAO live, > 50)** : panel 11 holders. Vote token-weighted sur paramètres. Rounds rétroactifs trimestriels.

## 9. Risques honnêtes

1. **Coordination invisible non rétribuée.** Mitigation : encourager les digests publics signés. Si ce n'est pas Git, ce n'est pas valorisé.
2. **Gaming sur le diff.** Le rubric pénalise dette technique et ajustements impact "modestes/faibles". Le panel reste l'autorité ultime.
3. **Volatilité BTC.** Compensation : recalibration trimestrielle.
4. **Panel Top X polarisé.** Mitigation : transparence du vote, revue annuelle.
5. **Sous-estimation IA pour certaines catégories.** Audit annuel comparatif aux taux freelance réels.

## 10. Implémentation actuelle

Phase 1 MVP en GitHub Actions + multisig Safe. Pas de smart contract custom encore. Voir `rounds/scripts/` pour le squelette de la GitHub Action de collecte, `rounds/agent/PROMPT.md` pour le prompt système, et `contracts/README.md` pour la roadmap des contracts à venir.
