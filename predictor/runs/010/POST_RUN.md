**Run 010 — résolu YES · Multi-model A/B**

Event : Lowest temperature in Los Angeles on May 19, 2026?
Bin cible : `KXLOWTLAX-26MAY19-B57.5` · Outcome : YES · Low observée (bin gagnant) : 57-58°F

Modèles en course (⭐ = best Brier sur ce run) :
- `vendor_ensemble` (champion) — p_yes=0.256, Brier=0.5537, P&L réel=$-40.88
- `learned_v2` (challenger) — p_yes=0.144, Brier=0.7320, P&L théorique=$-40.88
- `kalshi_mid_baseline` (baseline) — p_yes=0.455, Brier=0.2970, P&L théorique=$-40.88 ⭐

Verdict run 010 : Challenger `kalshi_mid_baseline` ahead this run.

Champion actuel : `vendor_ensemble` (la ligne réelle du ledger paper_bets.csv = celle de ce modèle).
Challengers et baselines : positions shadow, P&L théorique, pas d'exposition réelle.

Compteur Phase 1 : voir `dashboard/public/predictor_manifest.json` après rebuild.

Règle de promotion : un challenger n'est pas promoté sur un seul win. Il faut N>=10 résolus avec rolling-mean Brier strictement inférieur ET sign test 1-sided p<0.10. Cf. `predictor/runs_learning/CHAMPION.json`.

Log complet : https://github.com/Elladriel80/aratea/blob/main/predictor/runs/010/report.json
