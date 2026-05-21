**Run 009 — résolu NO · Multi-model A/B**

Event : Lowest temperature in New York City on May 19, 2026?
Bin cible : `KXLOWTNYC-26MAY19-B69.5` · Outcome : NO · Low observée (bin gagnant) : ≥72°F

Modèles en course (⭐ = best Brier sur ce run) :
- `vendor_ensemble` (champion) — p_yes=0.076, Brier=0.0058, P&L réel=$+1.74 ⭐
- `learned_v2` (challenger) — p_yes=0.172, Brier=0.0297, P&L théorique=$+1.74
- `kalshi_mid_baseline` (baseline) — p_yes=0.145, Brier=0.0210, P&L théorique=$+1.74

Verdict run 009 : Champion best ✓.

Champion actuel : `vendor_ensemble` (la ligne réelle du ledger paper_bets.csv = celle de ce modèle).
Challengers et baselines : positions shadow, P&L théorique, pas d'exposition réelle.

Compteur Phase 1 : voir `dashboard/public/predictor_manifest.json` après rebuild.

Règle de promotion : un challenger n'est pas promoté sur un seul win. Il faut N>=10 résolus avec rolling-mean Brier strictement inférieur ET sign test 1-sided p<0.10. Cf. `predictor/runs_learning/CHAMPION.json`.

Log complet : https://github.com/Elladriel80/aratea/blob/main/predictor/runs/009/report.json
