# predictor/runs/

Public, append-only record of every Kalshi POC run. Phase 1 of Augure
is about measuring a predictive edge before any decentralized
parametric mutual is built — every paper or live position has to leave
a trace here.

## Layout

```
predictor/runs/
├── CONVENTION.md            naming, schema, workflow, go/no-go
├── 001/
│   ├── REPORT.md            builder log
│   └── report.json          machine-readable record
└── NNN/                     one folder per run
    ├── REPORT.md
    ├── report.json
    └── templates/           pre/post-run posts (Discord + X)
```

## Workflow at a glance

```
   open       tag           announce CI                 resolve         update
  ──────►  run-NNN  ──────►  Discord+X    ──────►   wait market   ──────► report.json
                              auto fires             resolution            +REPORT.md
                                                                           commit
```

Ordered:

1. **Open** — fill the pre-run sections of `runs/NNN/REPORT.md` and
   `report.json`. Commit.
2. **Tag** — annotated `git tag run-NNN`. Push.
   `.github/workflows/announce-release.yml` auto-posts to Discord and X
   from the tag's annotated message.
3. **Manual posts** *(optional)* — `predictor/scripts/post_to_discord.py`
   sends a markdown file to any channel via webhook, for updates that
   don't warrant a tag (signal, P&L, mid-run note).
4. **Resolve** — once the market settles, fill the resolution fields
   in `report.json`, append a Resolution section to `REPORT.md`.
   Commit.

## Phase 1 success criterion

Validated *only* if, on N > 50 resolved runs, the meta-ensemble's
Brier score is strictly lower than **both** the best single model
**and** climatology, on the same N events. Failing either condition
is a no-go: the project pivots or stops.

The criterion is encoded in the union of `report.json` files — no
separate scoreboard needed.

## See also

- [`CONVENTION.md`](./CONVENTION.md) — full convention.
- [`../scripts/post_to_discord.py`](../scripts/post_to_discord.py) — manual webhook poster.
- [`../../.github/workflows/announce-release.yml`](../../.github/workflows/announce-release.yml) — tag-driven announce CI.
