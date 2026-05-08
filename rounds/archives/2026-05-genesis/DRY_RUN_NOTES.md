# DRY_RUN_NOTES — round `2026-05-genesis`

*Ce document accompagne le `valuation_report.md` du round genesis. Il liste explicitement ce qui rend ce rapport un dry-run et ce qu'il faut faire avant ratification effective.*

## Pourquoi c'est un dry-run

1. **Pas d'accès direct à `kalshi-poc`.** L'agent (Claude) n'a pas pu lire l'arborescence ni les diffs réels du repo. Il a travaillé sur la base des descriptions consolidées dans la mémoire projet (`project_kalshi_poc.md`).
2. **Pas de pipeline GitHub Actions.** Le script `collect_github_activity.py` est un squelette ; il n'a pas tourné pour produire `raw.json`.
3. **Pas de panel Top-X holders.** À ce stade, supply = 0, donc pas de holders. Le round genesis utilise la fenêtre de challenge étendue 30 jours comme substitut, conformément au RUBRIC §10.

## Ce que ce rapport apporte malgré tout

- **Calibration du système** : les ordres de grandeur, les ratios entre phases, les choix d'ajustements qualité/impact donnent une référence pour les rounds suivants.
- **Test du prompt et du rubric** : exposer des cas concrets (résultat négatif Phase B-2, bugfix avec qualité positive Phase A.1-bugfix, décomposition multi-profils Phase A.1) montre comment l'agent applique les règles. Si ces décisions paraissent illégitimes à JS ou aux prospects investisseurs, c'est le prompt ou le rubric qu'il faut amender, pas la valuation au cas par cas.
- **Première cap-table de référence** : si `kalshi-poc` réel produit un total entre 0,22 et 0,33 BTC (±20 % autour de 0,273), la cap-table genesis est tractable sans grosse surprise.

## Ce qu'il faut faire avant ratification réelle

### Bloquants

1. **Accéder à `kalshi-poc`** :
   - Option A : ouvrir le repo en public (idéalement) avec licence Apache 2.0.
   - Option B : le rendre accessible à l'agent (token GitHub avec scope read sur le repo privé).
   - Option C : exporter localement l'arborescence + `git log --stat --all` et fournir comme input au prochain agent run.
2. **Faire tourner `collect_github_activity.py`** sur le vrai repo. À adapter pour un repo solo (pas de PRs mergées, commits directs sur main : il faut agréger par tag/branche/CHANGELOG).
3. **Re-lancer l'agent** avec le `raw.json` réel + `phases.md` ajusté + `state.md` ajusté. Comparer le résultat à ce dry-run : tout écart > 20 % sur une phase mérite explication.

### À trancher avant ratification

4. **NAV initiale**. 1000 sats/token (= 0,00001 BTC) est arbitraire. Trois alternatives :
   - **100 sats/token** : 27 299 400 / 100 = 272 994 tokens à @Elladriel80. Plus de granularité pour les futurs petits apports.
   - **1000 sats/token** *(retenu dans le rapport)* : 27 299 tokens. Lecture humaine OK.
   - **10 000 sats/token** : 2 730 tokens. Très peu de granularité — un investisseur de 0,001 BTC mint 10 tokens. Trop grossier.
   - Recommandation : trancher entre 100 et 1000 selon la NAV minimale d'investissement visée. Si premier ticket est 0,005 BTC (~475 €), à 100 sats/token = 5000 tokens, à 1000 sats/token = 500 tokens. 100 sats/token paraît préférable.
5. **Choix d'allocation des bugfixes (Phase A.1-bugfix)**. Coefficient qualité ×1,15 est défendable parce que tests régression ajoutés. À valider que le rubric n'incite pas à introduire des bugs pour ensuite les fixer "qualitativement" — risque de gaming. Mitigation : contre-pénalité explicite via Phase 4 si bug "shippé" est imputable à l'auteur (×0,8 sur la phase d'origine). Ce dry-run est neutre sur ce point — à débattre.
6. **Travail Augure-rounds & token model**. Les docs du repo `augure-rounds` et les drafts `token_model_augure_poc.md` / `value_engine.md` sont du travail visible (commités sur GitHub) mais ils relèvent d'un round différent. Décider :
   - Round séparé `2026-05-augure-rounds-genesis`, à valoriser distinctement.
   - OU intégrer au premier round mensuel régulier `2026-06`.
   - Impact estimatif : ~5-10 jours de travail R&D / design (rubric, prompt engineering, économie token), soit 0,05-0,1 BTC supplémentaires à @Elladriel80.

### Non bloquants — décisions parallèles

7. **Langue du round**. Ce dry-run est en français. Convention à figer : tous les rounds en français (cohérence projet) ? bilingue (cohérence repo augure-rounds) ? langue du PR ouvre-t-elle ratification dans la même langue uniquement ? À trancher avant le premier round régulier.
8. **Format de raw.json pour repo sans PRs**. Le script actuel suppose des PRs mergées. Pour un repo solo en commits directs, il faut adapter (segmentation par messages de commit, par CHANGELOG, par tags). Spec à écrire avant de coder.

## Engagement de transparence

Ce dry-run est volontairement publié dans le repo `augure-rounds` (sera commité après validation) pour que les premiers prospects investisseurs voient :
- comment l'agent décompose et valorise un travail réel,
- où sont les zones d'ambiguïté,
- ce qu'on a choisi conservativement vs où on aurait pu être généreux.

Si un prospect ne souscrit pas après lecture de ce document, le système a fonctionné : il a permis une décision informée. C'est l'objectif.
