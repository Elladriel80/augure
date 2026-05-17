# External skills — extraits & analyse

Recherche menée le **2026-05-17** sur deux dépôts open-source de skills de trading,
dans le contexte du predictor Aratea (paper bets Kalshi NYC LOWT, payoffs binaires).

## Source

- `tradermonty/claude-trading-skills` — 82★, 32 forks, ~45 skills, README bilingue
  EN/JA, MIT, CI active. Mature. URL : <https://github.com/tradermonty/claude-trading-skills>
- `joinQuantish/skills` — 2★, 1 fork. **Plateforme en cours de fermeture**,
  contenu = wrappers MCP Polymarket/Kalshi sans logique d'edge. **Rien à
  extraire.** URL : <https://github.com/joinQuantish/skills>

## Trois skills extraits de tradermonty

| Skill | Fichier | Réutilisation Aratea |
|---|---|---|
| `position-sizer` | [position-sizer-extract.md](position-sizer-extract.md) | Formule Kelly canonique identique au code existant `sizing.py`. Gains : pattern *portfolio heat* + cap concentration. |
| `backtest-expert` | [backtest-expert-extract.md](backtest-expert-extract.md) | Méthodologie walk-forward, sample size, common failures — directement applicable au tournoi champion/challenger. |
| `edge-strategy-reviewer` | [edge-strategy-reviewer-extract.md](edge-strategy-reviewer-extract.md) | Gabarit 8 critères + verdict PASS/REVISE/REJECT, à adapter pour promouvoir un challenger en champion. |

## Ce qui n'a **pas** été extrait, et pourquoi

Tous les screeners equity (`vcp-screener`, `canslim-screener`, `pair-trade-screener`,
`value-dividend-screener`, `dividend-growth-pullback-screener`, `pead-screener`,
`finviz-screener`, `earnings-trade-analyzer`), les détecteurs de régime
(`market-top-detector`, `ftd-detector`, `us-market-bubble-detector`,
`ibd-distribution-day-monitor`), et tout l'options/Greek pricing
(`options-strategy-advisor`) sont hors-périmètre — payoffs equity
discrétionnaires, signal tape-reading, pas de transposition possible sur des
contrats binaires météo paramétriques.

## Critique du tweet viral à l'origine de cette recherche

Un post X viral (2026-05-17) prétend qu'un framework de prediction
market trading bot à **68.4 % win rate** vient d'être publié par un grand
fournisseur d'agents.

- **Faux sur la source.** Le screenshot vient d'un pitch tiers attaché au PDF
  d'origine pour le rendre viral. Le fournisseur n'a publié aucun bot.
- **Faux sur la plausibilité.** 68.4 % win rate / Sharpe 2.14 / max DD −4.2 %
  sur 312 trades est le profil d'un edge que les fonds quantitatifs cherchent
  depuis vingt ans. Si un tel système existait en open-source gratuit,
  l'arbitrage l'aurait neutralisé dans la semaine. Explications probables :
  backtest in-sample non-OOS, cherry-picking d'un sous-ensemble de marchés,
  survivorship bias sur les marchés effectivement résolus, ou fabrication
  marketing.
- **La recherche ci-dessus confirme** qu'aucun des skills open-source visibles
  ne contient un tel pipeline. Le repo `joinQuantish` est mort, le repo
  `tradermonty` est mature mais 100 % equity et ne touche aucun prediction
  market.

## RFC associé

[../rfc/RFC-portfolio-heat-and-correlation-caps.md](../rfc/RFC-portfolio-heat-and-correlation-caps.md)
— le seul changement actionnable identifié à l'issue de cette recherche.
