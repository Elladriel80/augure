"""Régression : deux bugs révélés par daily-trading run #13 du 2026-05-20.

Logs du run GH Actions : 26187320777 sur main au commit 9f7f9b8.

Bug 1 — collision bet_id (FATAL)
    Le suffixe `000000` était hardcodé dans `live_run._bet_id()`. Quand
    deux paris étaient capturés dans la même seconde par `_capture_one_bin`
    (cas typique : plusieurs bins qualifiés sur le même event), le second
    appel à `PortfolioHeat.register` plantait avec
    ``ValueError: bet_id déjà ouvert : '20260520T201419Z000000'``.

Bug 2 — NoneType.__format__ sur tail bins (rc=99, swallowé en exit 0
        avant la PR #fix/daily-auto-fail-hard, exit 1 après)
    `_render_post_run_v2` formattait ``observed_range[1]:.0f`` sans guard,
    plantait sur les tail bins Kalshi (préfixe ``T``, cap=None, signifie
    "≥ floor"). Runs 008/009 résolus sur ``KXLOWTNYC-26MAY19-T72``
    déclenchaient ``unsupported format string passed to NoneType.__format__``.

Les deux fixes sont indépendants mais regroupés dans la PR de remédiation
post-run #13.
"""
from __future__ import annotations

import re

# `scripts/` est ajouté au sys.path par predictor/tests/conftest.py.
from live_run import _bet_id
from finalize_run import _render_post_run_v2


# =====================================================================
# Bug 1 — collision bet_id
# =====================================================================


def test_bet_id_unique_within_same_second() -> None:
    """Deux appels successifs en moins d'une seconde doivent produire des
    bet_id distincts.

    Avant fix : ``strftime("%Y%m%dT%H%M%SZ000000")`` → suffix figé →
    collision garantie pour deux paris dans la même seconde.
    Après fix : ``strftime("%Y%m%dT%H%M%SZ%f")`` → microsecondes réelles →
    probabilité de collision quasi nulle sur du code séquentiel.
    """
    ids = [_bet_id() for _ in range(50)]
    duplicates = len(ids) - len(set(ids))
    assert duplicates == 0, (
        f"{duplicates} bet_id en double sur 50 appels successifs. "
        f"Échantillon : {ids[:5]}"
    )


def test_bet_id_format_compat() -> None:
    """Format figé : ``YYYYMMDDTHHMMSSZffffff`` (Z au caractère 15, 22 chars).

    Le slice ``bet_id[:16]`` reste utilisé par ``daily_auto`` pour
    l'affichage des bets ouverts : si quelqu'un change le format
    plus tard, ce test casse en premier et signale la rupture.
    """
    bid = _bet_id()
    assert re.fullmatch(r"\d{8}T\d{6}Z\d{6}", bid), f"format inattendu : {bid!r}"
    assert bid[15] == "Z", "Z doit rester au caractère 15 (compat bet_id[:16])"
    assert len(bid) == 22


# =====================================================================
# Bug 2 — render POST_RUN sur tail bins (cap=None)
# =====================================================================

_REPORT_STUB: dict = {
    "event": {"target_market_ticker": "STUB-MARKET", "title": "test event"},
    "champion_at_time_of_run": "vendor_ensemble",
}

_BY_MODEL_STUB: dict = {
    "vendor_ensemble": {
        "role": "champion",
        "p_yes": 0.20,
        "brier": 0.04,
        "pnl_usd": 12.34,
        "pnl_type": "actual",
    },
}

_RANKED_STUB: list = [("vendor_ensemble", 0.04)]


def test_render_post_run_v2_tail_bin_high() -> None:
    """Bin tail haut (Kalshi T*) : observed_range=(72.0, None) → '≥72°F'.

    Régression directe du run #13 : runs 008/009 résolus sur
    KXLOWTNYC-26MAY19-T72 plantaient sur cette branche avant fix.
    """
    md = _render_post_run_v2(
        _REPORT_STUB,
        run_id="008",
        outcome=0,
        observed_range=(72.0, None),
        by_model=_BY_MODEL_STUB,
        ranked=_RANKED_STUB,
    )
    assert "≥72°F" in md, f"format tail-haut manquant dans :\n{md}"
    assert "None" not in md, "aucun 'None' littéral ne doit fuir dans le rendu"


def test_render_post_run_v2_tail_bin_low() -> None:
    """Cas symétrique théorique : observed_range=(None, 50.0) → '≤50°F'.

    Pas observé sur les events Low/High Kalshi actuels mais inscrit
    défensivement pour ne pas reproduire le pattern Bug 2 côté
    floor=None si Kalshi introduit des bins tail-bas.
    """
    md = _render_post_run_v2(
        _REPORT_STUB,
        run_id="999",
        outcome=1,
        observed_range=(None, 50.0),
        by_model=_BY_MODEL_STUB,
        ranked=_RANKED_STUB,
    )
    assert "≤50°F" in md, f"format tail-bas manquant dans :\n{md}"
    assert "None" not in md


def test_render_post_run_v2_bounded_bin() -> None:
    """Bin borné (Kalshi B*) : observed_range=(57.0, 58.0) → '57-58°F'.

    Cas nominal — vérifie qu'on n'a pas régressé en gérant les tail bins.
    """
    md = _render_post_run_v2(
        _REPORT_STUB,
        run_id="010",
        outcome=1,
        observed_range=(57.0, 58.0),
        by_model=_BY_MODEL_STUB,
        ranked=_RANKED_STUB,
    )
    assert "57-58°F" in md, f"format bounded manquant dans :\n{md}"


def test_render_post_run_v2_unknown_range() -> None:
    """Cas dégénéré : observed_range=(None, None) → '?'.

    Maintient le comportement de fallback documenté avant fix
    (lo is None → "?") même si lo+hi sont None.
    """
    md = _render_post_run_v2(
        _REPORT_STUB,
        run_id="011",
        outcome=0,
        observed_range=(None, None),
        by_model=_BY_MODEL_STUB,
        ranked=_RANKED_STUB,
    )
    assert "Low observée (bin gagnant) : ?" in md
