# RUBRIC — règles de valuation

> [Read in English](RUBRIC.md)

*Version 0.2 — fact-only, BTC. Toute modification passe par PR + 7 jours de discussion publique + ratification.*

## 1. Question unique

Pour chaque artefact observable, l'agent répond à **une seule question** :

> Combien le marché aurait-il payé un professionnel pour produire ce livrable, à cette qualité, dans ce contexte ?

La réponse est en **BTC** (ou sats). Pas d'EUR/USD dans la chaîne de calcul.

## 2. Contraintes dures

- **Faits seuls.** Inputs limités à : PRs mergés, diffs, fichiers, descriptions, reviews, commit messages, commits signés sur `main`. Pas d'heures auto-déclarées, pas de submissions, pas de narratif.
- **Push KO = 0.** PRs fermés sans merge / rejetés / abandonnés ont valeur nulle.
- **Pas de bonus.** Aucun multiplicateur "founder", "loyalty", "early-mover".
- **Caps durs.** Qualité ∈ [0,5 ; 1,3], Impact ∈ [0,8 ; 1,5]. L'agent ne sort jamais de ces bornes.

## 3. Calcul

```
valeur_BTC = heures_estimées × taux_horaire_BTC × ajust_qualité × ajust_impact
```

- **heures_estimées** : temps qu'un pro du profil requis mettrait pour produire le même output, en partant d'un état familier-avec-la-stack mais pas-avec-le-repo. Déduit du diff et du contexte.
- **taux_horaire_BTC** : selon `HOURLY_RATES.fr.md`, choisi selon le profil de l'output (pas selon qui l'a écrit).
- **ajust_qualité** : ∈ [0,5 ; 1,3], borne dure.
- **ajust_impact** : ∈ [0,8 ; 1,5], borne dure.
- Plancher : 0,4 ; plafond : 1,95 sur les ajustements combinés.

## 4. Estimation des heures

Dans l'ordre :

1. **Diff** — lignes ajoutées/supprimées, fichiers touchés, complexité apparente (densité if/loops/branching).
2. **Contexte** — module core ou périphérique, refactor ou greenfield, intégrations affectées.
3. **Artefacts associés** — tests ajoutés, doc mise à jour, issues référencées, RFC.

Heuristiques (baseline de calibration) :
- 100 lignes propres testées sur un module isolé ≈ 4-8 heures.
- Refactor architectural touchant 5+ fichiers ≈ 2-4 jours.
- RFC / spec 2-3 pages ≈ 4-8 heures.
- Bug fix ciblé avec test régression ≈ 1-3 heures.
- Notebook d'analyse / benchmark ≈ 1-2 jours.

Si une contribution mêle plusieurs natures, **décomposer** et sommer.

## 5. Choix du profil (détermine le taux)

Le profil est choisi selon **la nature de l'output**, pas selon qui l'a écrit. Un junior qui livre du code senior level sur un smart contract est rétribué au taux senior-SC pour ce PR.

Si plusieurs profils s'appliquent dans un même PR, décomposer en heures par nature :
```
exemple : PR mêlant 3h logique ML + 2h documentation
valeur_avant_ajust = 3 × taux_ML + 2 × taux_techwriter
```

## 6. Ajustement qualité — ×0,5 à ×1,3

| Signal | Effet |
|---|---|
| Tests présents et significatifs | +0,10 |
| Documentation à jour (docstrings, README, ADR) | +0,05 |
| Code lisible, conventions respectées | +0,05 |
| CI verte du premier coup | +0,05 |
| Plusieurs reviewers approving sans correction majeure | +0,05 |
| Introduit de la dette technique (TODO sans ticket, hack non documenté) | -0,10 |
| Bug shipping (régression repérée plus tard et imputable) | -0,20 |
| Travail incomplet / nécessite reprise immédiate | -0,30 |

Partir de 1,0, appliquer les modifs, clamp dur sur [0,5 ; 1,3].

## 7. Ajustement impact — ×0,8 à ×1,5

| Niveau | Critère | Coefficient |
|---|---|---|
| Bloquant | Débloque une étape majeure du roadmap, résout un risque critique | 1,4 - 1,5 |
| Élevé | Améliore mesurablement une métrique clé (P&L, qualité prédictive, robustesse) | 1,2 - 1,3 |
| Standard | Avancement normal sur tâche prévue | 1,0 |
| Modeste | Travail périphérique, polish, nice-to-have | 0,9 |
| Faible | Sera probablement jeté ou dupliqué | 0,8 |

L'agent justifie chaque niveau en référence au roadmap ou à un outcome mesuré.

## 8. Artefacts non-code (toujours fact-based)

### Datasets commités au repo
- Dataset public sous licence permissive : **valeur = 0** (heures de curation valorisées au taux profil pertinent si visibles dans l'historique commits).
- Dataset propriétaire acheté : valeur = coût d'acquisition documenté converti en BTC, plafonné au prix marché.
- Dataset construit (scraping, labeling, capteurs) : heures impliquées par le code qui l'a produit × profil correspondant.

### RFC, specs, design docs (commités en Markdown)
- Heures × profil researcher ou design.
- Ajust impact selon adoption (RFC adopté tel quel : ×1,3 ; modifié majoritairement : ×1,0 ; rejeté : ×0,8).

### Digest communauté (uniquement si commité)
- Un digest mensuel commité comme `community/digest-YYYY-MM.md`, signé par le wallet du contributeur, peut être valorisé comme travail community.
- Heures × profil community.
- Aucune valeur si non commité. L'historique Discord seul ne compte pas.

### Bugs disclosés (responsible disclosure)
- Critique (perte fonds, fuite clés) : 0,05 - 0,20 BTC
- Élevé (DoS, corruption d'état) : 0,015 - 0,05 BTC
- Moyen (incohérence non-bloquante) : 0,003 - 0,015 BTC
- Mineur (typo, edge case) : 0,0005 - 0,003 BTC

Inspiré du barème Immunefi, recalibré après premiers cas.

## 9. Apports cash

Hors rubric côté valuation (1 sat = 1 sat, pas d'estimation) mais **soumis à ratification comme tout autre apport**.

- Apport BTC : envoyé à l'adresse multisig `subscription-pending` du round. Accepté à J+7 → mint à NAV. Refusé par ratificateur(s) avec motivation écrite → fonds renvoyés à l'expéditeur.
- Apport USDC / EURC : converti en sats au spot du jour de subscription, même mécanique pending + ratification.

Les apports cash apparaissent dans le rapport mensuel de l'agent **sans valuation** (montant brut + adresse expéditeur) pour visibilité du ratificateur. Refus possible pour raison stratégique, réputationnelle, conflit d'intérêts, ou compliance. Symétrie avec le code : on "refuse" un apport travail en ne mergant pas son PR ; on refuse un apport cash en renvoyant les fonds.

## 10. Valuation rétroactive (genesis)

Une seule fois, à l'ouverture du projet :
1. L'agent scanne tout l'historique Git du repo principal.
2. Décompose en phases logiques (visibles dans branches/tags/CHANGELOG).
3. Applique la méthode standard par phase.
4. **Fenêtre de challenge étendue à 30 jours** (vs 7 standard).
5. Premiers prospects investisseurs invités explicitement à challenger avant d'investir.
6. Pas de bonus "founder". La justice du modèle dépend de l'absence de privilège catégoriel.

## 11. Règle de bris d'égalité

> Si l'agent hésite entre deux estimations, il retient la plus basse. Si un contributeur s'estime sous-valorisé, il dépose un challenge formel avec arguments.

## 12. Versioning

Ce rubric est versionné en Git. Toute modification :
1. PR ouvert avec justification.
2. 7 jours minimum de discussion publique.
3. Ratification (phase 1 : JS ; phase 2 : comité ; phase 3 : vote 51 %).
4. La nouvelle version s'applique au round suivant la merge, jamais rétroactivement.

## 13. Limitations connues

- Travail invisible hors-Git (mentorat synchrone, debug en DM, conversations) non capté. **Par design.** Trade-off objectivité contre inclusivité. Pour être valorisé, le travail doit produire un artefact Git visible.
- L'agent peut sous- ou sur-estimer certaines catégories. Audit annuel comparatif aux taux freelance réels du marché. Recalibrage si dérive > 20 %.
- Les ajustements qualité/impact reposent sur la lecture de l'agent. Le panel Top-X holders est le filet de sécurité.
