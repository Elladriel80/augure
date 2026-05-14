# Rapport — Correctif split temporel `train_learned.py`

**Projet :** Aratea — predictor / Phase A.3 (learned predictor)
**Date :** 2026-05-14
**Repo :** `github.com/Elladriel80/Aratea`
**Run de référence :** `predictor/runs_learning/20260514T141925Z/run.json` (feature set v2, post Run 002 + Run 003)
**Destinataire :** analyste dev

---

## 1. Contexte

Le predictor Phase A.3 entraîne un `LogisticRegression(L2)` sur des features extraites de captures `forward_*.json`, jointes aux résolutions Kalshi. Le critère de promotion d'un feature set est un seul : Brier test < Brier `kalshi_mid` sur le même test set.

Le run `v2` du 2026-05-14T14:19:25Z a renvoyé :

```
metric           train        test     kalshi_mid (test)
n                  268         116                   116
Brier           0.1250      0.1416                0.0752
LogLoss         0.3910      0.4624                0.2354

>> learned model LOSES to kalshi_mid by 0.0664 Brier on test.
```

L'écart à `kalshi_mid` est passé de **+0.0204** (memory Phase A.2, N=60) à **+0.0664** sur ce run. Avant de conclure que v2 régresse, audit du protocole d'évaluation.

---

## 2. Problème observé

Le `run.json` rapporte :

```json
"train_date_range": ["20260508T102045Z", "20260512T144111Z"],
"test_date_range":  ["20260512T144111Z", "20260512T144111Z"]
```

Les 116 lignes du test set partagent toutes la **même valeur de `capture_at`**. Le split n'est pas un découpage temporel — c'est une photo instantanée de ce qui a été fetché dans le dernier `forward_predict`.

Origine : `src/learning/dataset.py::keep_earliest_with_quote()` ne garde qu'une ligne par ticker (la première capture avec `yes_mid` non nul). Comme un gros batch `forward_predict` a tourné le 2026-05-12 et a inscrit la majorité des tickers résolus pour la première fois ce jour-là, le tri par `capture_at` puis le cut à 70 % envoie toutes ces lignes en bloc dans le test set.

Conséquences directes :

1. **Pas de mesure de généralisation.** Le test set est un instantané, pas un horizon futur. Le Brier obtenu ne dit rien sur la capacité du modèle à prédire des events à venir.
2. **Baseline `kalshi_mid` artificiellement bonne.** À T fixe, `yes_mid` capture déjà l'essentiel de l'information publique disponible — c'est de la quasi-tautologie. D'où le 0.0752, exceptionnellement bas et non comparable au 0.1234 de Phase A.2.
3. **Comparaisons inter-runs cassées.** Brier deltas leave-one-out (`p_climatology -0.0037`, etc.) sont des micro-variations sur un instantané, pas des signaux de feature exploitables.

---

## 3. Diagnostic — trois défauts cumulés

| # | Défaut | Effet |
|---|--------|-------|
| 1 | Split sur `capture_at` au lieu de `target_date` | Test set collapse sur un batch de fetch |
| 2 | Pas de garde-fou sur la cardinalité du test set | Un run dégénéré ressemble à un run valide |
| 3 | Cut numérique brut (`int(n * 0.7)`) | Possible leakage de bord si une journée d'events est à cheval |

Le défaut 1 est primaire. Les 2 et 3 sont secondaires mais doivent être corrigés en même temps pour ne pas se les reprendre à la prochaine itération.

---

## 4. Correctif appliqué

### 4.1 Fichiers modifiés

- `predictor/scripts/train_learned.py`
- `predictor/scripts/build_dashboard_manifest.py`

### 4.2 Changements `train_learned.py`

**a) Nouveau flag `--split-key`**

```python
parser.add_argument("--split-key",
                    choices=["target_date", "capture_at"],
                    default="target_date",
                    help="Field used to chronologically order rows before "
                         "the train/test split. target_date (default) "
                         "splits by the date each market resolves, "
                         "measuring forecast skill across distinct events. "
                         "capture_at splits by snapshot timestamp; with "
                         "the current dataset builder this typically "
                         "collapses test into a single batch (degenerate).")
```

Défaut explicite à `target_date`. `capture_at` reste accessible pour reproduire les runs historiques mais n'est plus le chemin nominal.

**b) `chronological_split()` réécrit en group-aware**

Cut snappé sur la frontière du `split_key` la plus proche du target, en préférant systématiquement réduire le train plutôt que créer du leakage de bord. Pseudo-algo :

```
1. Tri stable par split_key (None / "" → fin).
2. target = int(N * train_frac), borné [1, N-1].
3. Si meta[target-1][split_key] == meta[target][split_key] :
   - backward = premier index où la valeur change en remontant
   - forward  = premier index où la valeur change en descendant
   - Snap sur le plus proche du target ; égalité → backward.
4. Découpage.
```

Garantie : aucune valeur de `split_key` ne se retrouve dans les deux sous-ensembles.

**c) Deux warnings explicites en sortie**

```
!! WARNING: test set spans only N distinct {split_key} value(s).
   Brier deltas measured here are NOT generalization estimates
   — they describe a single point in time.
```

```
!! WARNING: K {split_key} value(s) appear in BOTH train and test: [...]
   Boundary leakage — train and test are not cleanly separated.
```

Ces warnings sont non bloquants (le run continue) pour permettre les diagnostics, mais visibles à la lecture du stdout.

**d) `run.json` schema v2 → v3**

Ajouts :

```json
"split_key": "target_date",
"train_frac": 0.7,
"train_split_range": ["2026-05-08", "2026-05-11"],
"test_split_range":  ["2026-05-12", "2026-05-12"],
"n_distinct_test_split_values": 1
```

Champs legacy `train_date_range` / `test_date_range` (sur `capture_at`) préservés pour compat ascendante avec le manifest builder et les anciens parsers.

### 4.3 Changement `build_dashboard_manifest.py`

Surface les nouveaux champs dans le manifest consommé par le dashboard :

```python
"split_key": run.get("split_key"),
"train_split_range": run.get("train_split_range"),
"test_split_range": run.get("test_split_range"),
"n_distinct_test_split_values": run.get("n_distinct_test_split_values"),
```

Permet au front d'afficher quel split a été utilisé et de marquer visuellement les runs dégénérés (n=1 valeur).

---

## 5. Validation attendue

À la prochaine exécution `python predictor/scripts/train_learned.py --feature-set v2` :

- La sortie doit afficher `>> split key: target_date (train_frac=0.7)`.
- `train target_date range` doit couvrir plusieurs jours antérieurs, `test target_date range` doit couvrir les jours les plus récents.
- Le warning "test set spans only 1 distinct target_date value" s'allumera tant que le dataset n'aura pas accumulé suffisamment de jours-events post-résolution. C'est attendu sur l'état actuel des données et n'est pas un bug.
- Aucun warning de leakage de bord ne doit apparaître (la snap garantit la séparation propre).
- Le `run.json` v3 doit contenir les nouveaux champs ; le manifest builder existant doit toujours fonctionner via les champs legacy.

Critère de succès méthodologique (pas modèle) : le Brier `kalshi_mid` sur test set doit remonter vers ~0.12-0.14 (valeurs typiques quand on prédit des résolutions futures et non un instantané), pas rester à 0.0752. Si `kalshi_mid` reste anormalement bas, refaire un audit — la baseline reste contaminée.

---

## 6. Suites recommandées (hors scope de ce correctif)

1. **Cardinalité du test set.** Tant que `n_distinct_test_split_values == 1`, on mesure un point, pas une généralisation. Solution : accumuler 5-10 jours supplémentaires de `forward_predict` + résolutions avant tout test d'ajout de feature.

2. **Multi-colinéarité des features de probabilité.** Le run v2 du 2026-05-14 montre `p_ensemble +1.216`, `p_forecast_blend -0.774`, `p_climatology -0.689`. Trois probabilités du même outcome, deux coefficients négatifs : signal classique de L2 qui compense par soustraction. À retester sous split propre. Si le pattern persiste, candidat à un set v3 où l'on remplace les trois par `p_consensus` (moyenne/médiane) + `forecast_spread`.

3. **Tests unitaires `chronological_split`.** Le repo n'a pas d'infra pytest formelle (les `test_*.py` sont des smoke scripts manuels). Un test ciblé sur la logique de snap (cas : cut au milieu d'un groupe, cut sur une frontière, tous identiques, tous distincts) coûterait peu et éviterait une régression future.

4. **Conformité PR flow.** Les deux commits du 2026-05-14 (`74bff71`, `6d8d6b1`) ont bypassé branch protection sur `main`. La règle interne du 2026-05-11 impose PR systématique même solo. Ce correctif doit être livré via PR sur une branche dédiée (suggérée : `fix/temporal-split-group-aware`).

---

## 7. Annexes

### 7.1 Commande de retest

```bash
python predictor/scripts/train_learned.py \
  --feature-set v2 \
  --notes "v2 sous split target_date group-aware, baseline méthodo propre"
python predictor/scripts/build_dashboard_manifest.py
```

### 7.2 Run de référence (avant correctif)

`predictor/runs_learning/20260514T141925Z/run.json` — schema v2, split `capture_at` implicite, test set dégénéré sur `20260512T144111Z`.

### 7.3 Compat ascendante

Le manifest builder lit `train_date_range` / `test_date_range` ; ces champs restent peuplés dans le schema v3. Aucun run.json historique (v1, v2) n'est cassé.
