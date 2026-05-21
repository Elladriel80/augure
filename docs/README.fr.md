<!-- English version: README.md -->

# Documentation Aratea

Index des documents canoniques de `docs/`. Chaque entrée pointe vers le
fichier et en résume l'objet en une ligne. Les descriptions se limitent
strictement à ce que dit le document lui-même — aucune affirmation
nouvelle n'est introduite ici.

Le projet Aratea est bilingue FR/EN. La langue de chaque document est
indiquée à côté de son entrée. La version anglaise de cet index est en
[README.md](README.md).

## Architecture produit

| Document | Lang | Objet |
|---|---|---|
| [architecture.md](architecture.md) | FR | Vision Aratea (mutuelle paramétrique décentralisée + moteur prédictif + couche de données DePIN), boucle de renforcement entre les trois piliers, plan de phases. |

## Économie du token

| Document | Lang | Objet |
|---|---|---|
| [token_model.md](token_model.md) | FR | Spécification du token AUG-POC : ERC-20 sur Arbitrum, convention NAV 1 sat = 1 token, comptabilisation valeur-travail sans catégorie d'apporteur privilégiée. |

## Valuation

| Document | Lang | Objet |
|---|---|---|
| [value_engine.md](value_engine.md) | FR | Moteur de valuation fact-only en BTC, alimenté uniquement par les artefacts visibles dans Git ; le rubric opérationnel vit dans [`../rounds/RUBRIC.fr.md`](../rounds/RUBRIC.fr.md). |

## Sécurité

| Document | Lang | Objet |
|---|---|---|
| [SECURITY-audit-2026-05-11-handoff.md](SECURITY-audit-2026-05-11-handoff.md) | FR | Handoff de l'audit du 2026-05-11 : ce qui a été corrigé dans le code et les rotations manuelles restantes. |
| [SECURITY-rotation-procedure.md](SECURITY-rotation-procedure.md) | EN | Runbook pour les rotations de credentials routinières (90 jours) et déclenchées sur incident. |
| [SECURITY-rotation-log.md](SECURITY-rotation-log.md) | EN | Journal append-only de chaque rotation de secret (noms de credentials uniquement, jamais les valeurs). |

## Onboarding contributeurs

| Document | Lang | Objet |
|---|---|---|
| [contributor-starter-issues.md](contributor-starter-issues.md) | EN | Catalogue de tâches réelles et bornées, exploitables comme tickets `good-first-issue`. |
| [bounty-mechanism.md](bounty-mechanism.md) | EN | Placeholder décrivant le mécanisme de bounty *futur* (Phase 2) — précise explicitement qu'Aratea **ne** lance actuellement **pas** de programme de bounty cash. |

## Documents racine liés

- [../README.md](../README.md) — point d'entrée projet (EN).
- [../README.fr.md](../README.fr.md) — point d'entrée projet (FR).
- [../ROADMAP.md](../ROADMAP.md) — phases courantes et jalons.
- [../STATUS.md](../STATUS.md) — état live de chaque chantier.
- [../CONTRIBUTING.md](../CONTRIBUTING.md) / [../CONTRIBUTING.fr.md](../CONTRIBUTING.fr.md) — règles de contribution.
