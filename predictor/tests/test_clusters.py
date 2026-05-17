"""Tests du parser de ticker Kalshi et du mapping NOAA.

Couvre :
  - Parsing de tickers daily et monthly réels (tirés de data/markets/).
  - Le piège LV vs TLV (le 'T' de HIGHT/LOWT n'est PAS dans le code ville).
  - Le piège MIA vs MIAM (le 'M' n'est strippé qu'en monthly, jamais en
    daily ; la distinction se fait sur la longueur du segment date).
  - Bornes de la fenêtre de settlement (0 / 3 / 4 jours).
"""
from __future__ import annotations

from datetime import date

import pytest

from src.simulation.clusters import (
    CITY_TO_NOAA,
    parse_city_from_ticker,
    same_settlement_window,
    spatial_cluster_for_ticker,
)


# --- Parsing daily (tickers présents dans predictor/data/markets/) ---------
@pytest.mark.parametrize(
    "ticker, expected_city",
    [
        ("KXLOWTNYC-26MAY17", "NYC"),
        ("KXHIGHTSFO-26MAY08", "SFO"),
        ("KXHIGHCHI-26MAY08", "CHI"),       # HIGH (sans T) vs HIGHT
        ("KXLOWTDC-26MAY15", "DC"),         # code ville à 2 chars
        ("KXLOWTNOLA-26MAY15", "NOLA"),     # code ville à 4 chars
        ("KXHIGHTSATX-26MAY13", "SATX"),
    ],
)
def test_parse_city_from_ticker_daily(ticker: str, expected_city: str) -> None:
    assert parse_city_from_ticker(ticker) == expected_city


def test_parse_daily_lv_is_las_vegas_not_tlv() -> None:
    # KXLOWTLV = LOWT + LV : le 'T' appartient au market type, pas au code
    # ville. Il n'existe pas de code 'TLV' chez Kalshi.
    assert parse_city_from_ticker("KXLOWTLV-26MAY15") == "LV"
    assert parse_city_from_ticker("KXHIGHTLV-26MAY15") == "LV"


# --- Parsing monthly ------------------------------------------------------
@pytest.mark.parametrize(
    "ticker, expected_city",
    [
        ("KXRAINCHIM-26MAY", "CHI"),
        ("KXRAINMIAM-26MAY", "MIA"),   # gotcha : MIAM est RAIN + MIA + M
        ("KXRAINAUSM-26MAY", "AUS"),
        ("KXRAINNYCM-26MAY", "NYC"),
    ],
)
def test_parse_city_from_ticker_monthly(ticker: str, expected_city: str) -> None:
    assert parse_city_from_ticker(ticker) == expected_city


def test_daily_does_not_strip_trailing_m() -> None:
    # Stub : ticker daily hypothétique se terminant par 'M'. Doit garder le
    # M dans le code ville (la longueur du segment date = 7 chars indique
    # une cadence daily, pas monthly).
    assert parse_city_from_ticker("KXRAINMIA-26MAY08") == "MIA"


# --- Erreurs de parsing ----------------------------------------------------
def test_unknown_market_type_raises() -> None:
    with pytest.raises(ValueError, match="Type de marché inconnu"):
        parse_city_from_ticker("KXFOONYC-26MAY17")


def test_missing_kx_prefix_raises() -> None:
    with pytest.raises(ValueError, match="ne commence pas par 'KX'"):
        parse_city_from_ticker("LOWTNYC-26MAY17")


def test_malformed_date_raises() -> None:
    with pytest.raises(ValueError, match="Segment date non reconnu"):
        parse_city_from_ticker("KXLOWTNYC-2026-05-17")


def test_monthly_without_m_suffix_raises() -> None:
    # Segment date = 5 chars → monthly attendu → ville doit finir par M.
    with pytest.raises(ValueError, match="devrait se terminer par 'M'"):
        parse_city_from_ticker("KXRAINCHI-26MAY")


# --- Mapping NOAA ----------------------------------------------------------
def test_unknown_city_raises_on_spatial_cluster() -> None:
    # 'ZZZ' n'est dans aucun mapping NOAA réel.
    with pytest.raises(ValueError, match="absente du mapping NOAA"):
        spatial_cluster_for_ticker("KXLOWTZZZ-26MAY17")


def test_spatial_cluster_for_known_cities() -> None:
    assert spatial_cluster_for_ticker("KXLOWTNYC-26MAY17") == "NE"
    assert spatial_cluster_for_ticker("KXLOWTLV-26MAY17") == "SW"
    assert spatial_cluster_for_ticker("KXLOWTDEN-26MAY17") == "PLAINS"
    assert spatial_cluster_for_ticker("KXLOWTNOLA-26MAY17") == "SE"


def test_city_to_noaa_covers_every_city_in_data_markets() -> None:
    # Garde-fou : toute ville ajoutée au mapping est un Literal valide.
    valid_regions = {"NE", "SE", "MW", "NW", "SW", "PLAINS", "AK", "HI"}
    for city, region in CITY_TO_NOAA.items():
        assert region in valid_regions, (
            f"Région NOAA {region!r} (ville {city!r}) hors enum."
        )


# --- Fenêtre temporelle ----------------------------------------------------
def test_same_settlement_window_bounds() -> None:
    d = date(2026, 5, 17)
    # diff 0 → True
    assert same_settlement_window(d, d, window_days=3) is True
    # diff 3 → True (borne incluse)
    assert same_settlement_window(d, date(2026, 5, 20), window_days=3) is True
    assert same_settlement_window(d, date(2026, 5, 14), window_days=3) is True
    # diff 4 → False
    assert same_settlement_window(d, date(2026, 5, 21), window_days=3) is False
    assert same_settlement_window(d, date(2026, 5, 13), window_days=3) is False
