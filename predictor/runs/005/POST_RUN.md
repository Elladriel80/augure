**Run 005 — résolu YES · Multi-model A/B**

Event : Lowest temperature in New York City on May 15, 2026?
Bin cible : `KXLOWTNYC-26MAY15-B49.5` · Outcome : YES · Low observée (bin gagnant) : 49-50°F

Modèles en course (⭐ = best Brier sur ce run) :
- `vendor_ensemble` (champion) — p_yes=0.149, Brier=0.7240, P&L réel=$-99.56
- `learned_v2` (challenger) — p_yes=0.186, Brier=0.6626, P&L théorique=$-99.56
- `kalshi_mid_baseline` (baseline) — p_yes=0.345, Brier=0.4290, P&L théorique=$-99.56 ⭐

Verdict run 005 : Challenger `kalshi_mid_baseline` ahead this run.

Champion actuel : `vendor_ensemble` (la ligne réelle du ledger paper_bets.csv = celle de ce modèle).
Challengers et baselines : positions shadow, P&L théorique, pas d'exposition réelle.

Compteur Phase 1 : voir `dashboard/public/predictor_manifest.json` après rebuild.

Règle de promotion : un challenger n'est pas promoté sur un seul win. Il faut N>=10 résolus avec rolling-mean Brier strictement inférieur ET sign test 1-sided p<0.10. Cf. `predictor/runs_learning/CHAMPION.json`.

Log complet : https://github.com/Elladriel80/aratea/blob/main/predictor/runs/005/report.json
