**Run 008 — résolu NO · Multi-model A/B**

Event : Lowest temperature in New York City on May 19, 2026?
Bin cible : `KXLOWTNYC-26MAY19-B71.5` · Outcome : NO · Low observée (bin gagnant) : ≥72°F

Modèles en course (⭐ = best Brier sur ce run) :
- `vendor_ensemble` (champion) — p_yes=0.062, Brier=0.0039, P&L réel=$+34.00 ⭐
- `learned_v2` (challenger) — p_yes=0.170, Brier=0.0290, P&L théorique=$+34.00
- `kalshi_mid_baseline` (baseline) — p_yes=0.400, Brier=0.1600, P&L théorique=$+34.00

Verdict run 008 : Champion best ✓.

Champion actuel : `vendor_ensemble` (la ligne réelle du ledger paper_bets.csv = celle de ce modèle).
Challengers et baselines : positions shadow, P&L théorique, pas d'exposition réelle.

Compteur Phase 1 : voir `dashboard/public/predictor_manifest.json` après rebuild.

Règle de promotion : un challenger n'est pas promoté sur un seul win. Il faut N>=10 résolus avec rolling-mean Brier strictement inférieur ET sign test 1-sided p<0.10. Cf. `predictor/runs_learning/CHAMPION.json`.

Log complet : https://github.com/Elladriel80/aratea/blob/main/predictor/runs/008/report.json
