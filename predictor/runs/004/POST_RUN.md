**Run 004 — résolu YES · Multi-model A/B**

Event : Lowest temperature in New York City on May 14, 2026?
Bin cible : `KXLOWTNYC-26MAY14-B52.5` · Outcome : YES · Low observée (bin gagnant) : 52-53°F

Modèles en course (⭐ = best Brier sur ce run) :
- `vendor_ensemble` (champion) — p_yes=0.141, Brier=0.7385, P&L réel=$-99.96
- `learned_v2` (challenger) — p_yes=0.171, Brier=0.6873, P&L théorique=$-99.96
- `kalshi_mid_baseline` (baseline) — p_yes=0.320, Brier=0.4624, P&L théorique=$-99.96 ⭐

Verdict run 004 : Challenger `kalshi_mid_baseline` ahead this run.

Champion actuel : `vendor_ensemble` (la ligne réelle du ledger paper_bets.csv = celle de ce modèle).
Challengers et baselines : positions shadow, P&L théorique, pas d'exposition réelle.

Compteur Phase 1 : voir `dashboard/public/predictor_manifest.json` après rebuild.

Règle de promotion : un challenger n'est pas promoté sur un seul win. Il faut N>=10 résolus avec rolling-mean Brier strictement inférieur ET sign test 1-sided p<0.10. Cf. `predictor/runs_learning/CHAMPION.json`.

Log complet : https://github.com/Elladriel80/aratea/blob/main/predictor/runs/004/report.json
