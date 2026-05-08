# HOURLY_RATES — grille de taux Augure (BTC)

> [Read in English](HOURLY_RATES.md)

*Version 0.1 — modifiable par PR + ratification.*

## Principe

Un seul standard pour tout le projet. Pas de salaire individuel, pas de négociation, pas de différenciation géographique. Les taux ci-dessous sont **les seuls** utilisés par l'agent de valuation.

L'unité de compte est **BTC**. Les taux sont en **sats par heure** (1 BTC = 100 000 000 sats). Volontairement modestes vs marché : la promesse d'upside est dans les tokens, pas dans le taux.

Référence : TJM freelance Paris moyen divisé par 7 heures de travail, converti en BTC à la date de calibration.

## Grille

| Profil | sats / heure | sats / jour (×7) | mBTC / heure |
|---|---|---|---|
| Dev senior / smart contracts | 130 000 | 910 000 | 1,30 |
| Dev mid | 80 000 | 560 000 | 0,80 |
| Dev junior / apprenant | 40 000 | 280 000 | 0,40 |
| ML engineer / data scientist | 140 000 | 980 000 | 1,40 |
| Researcher / quant senior | 160 000 | 1 120 000 | 1,60 |
| Designer produit / UX | 90 000 | 630 000 | 0,90 |
| Tech writer / documentation | 70 000 | 490 000 | 0,70 |
| Community / ops / coordination | 60 000 | 420 000 | 0,60 |
| Audit sécurité smart contracts | 220 000 | 1 540 000 | 2,20 |

Date de calibration : 2026-05. Référence BTC/EUR ≈ 95 000 € (ancrage uniquement — n'entre pas dans les calculs).

## Choix du profil

L'agent choisit le profil selon **la nature de l'output**, pas selon qui l'a produit. Un junior qui livre du code senior level est rétribué au taux senior pour ce PR. Inversement, un senior qui produit du trivial est rétribué au profil correspondant.

Si plusieurs profils s'appliquent, décomposer en heures par nature et sommer.

## Junior produisant du senior

Le système valorise le **livrable**, pas l'effort. Un junior qui sort de la qualité senior touche le taux senior. Cohérent avec la théorie valeur-travail : ce qui compte est ce qui est produit, pas la peine prise.

Inverse : un senior qui produit lentement est borné par les **heures réellement nécessaires** au profil correspondant. Pas de prime au temps perdu.

## Recalibration

Les taux sont revus :
- **Trimestriellement** par benchmark vs TJM freelance Paris (sources : Malt, Comet, Crème de la Crème agrégées). Conversion au spot moyen BTC/EUR du trimestre.
- **Sur déclencheur** si BTC dérive > 25 % vs prix de référence en un trimestre.

Toute modification suit le process versioning du `RUBRIC.fr.md`.

## Devise

Comptabilité interne et mint exclusivement en BTC. Les références EUR/USD dans ce document sont des ancrages pour la recalibration, jamais utilisées dans la chaîne de valuation.

## Limites

- La grille reste arbitraire à un niveau fondamental — il n'existe pas de "vrai" taux unique. Mitigation : méthode transparente, recalibration régulière, vote des holders pour changements majeurs.
- Les profils ne couvrent pas toutes les contributions imaginables. Pour les cas non répertoriés, l'agent propose un profil et un taux par analogie à la grille, avec justification explicite, ratifié comme toute valuation.
- La volatilité BTC expose les apporteurs aux fluctuations BTC/fiat. Choix assumé : le projet est BTC-aligné. Vote des holders pour recalibrer si dérive matérielle.
