"""Client HTTP pour l'API publique Kalshi (lecture seule, sans authentification)."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urlencode

import requests

from src.config import KALSHI_API_BASE, USER_AGENT, MARKETS_DIR
from .models import Series, Event, Market


WEATHER_CATEGORY_KEYWORDS = ("climate", "weather")
WEATHER_TITLE_KEYWORDS = ("snow", "rain", "temperature", "precip", "hurricane")


class KalshiClient:
    """Client de lecture pour l'API publique Kalshi.

    Pas d'authentification : on ne peut pas trader, on lit seulement.
    """

    def __init__(self, base_url: str = KALSHI_API_BASE, snapshot_dir: Path = MARKETS_DIR):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        })
        self.snapshot_dir = snapshot_dir
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    # -- HTTP --

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode({k: v for k, v in params.items() if v is not None})}"
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=20)
                if resp.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
        return {}

    def _paginate(self, path: str, params: dict, key: str, limit_per_page: int = 200) -> Iterator[dict]:
        cursor = None
        while True:
            page_params = dict(params)
            page_params["limit"] = limit_per_page
            if cursor:
                page_params["cursor"] = cursor
            data = self._get(path, page_params)
            items = data.get(key, []) or []
            for item in items:
                yield item
            cursor = data.get("cursor") or None
            if not cursor or not items:
                break

    # -- Série --

    def list_series(self) -> list[Series]:
        """Liste toutes les séries (pas de pagination — un seul gros payload)."""
        data = self._get("/series")
        return [Series.from_api(s) for s in data.get("series", [])]

    def list_weather_series(self) -> list[Series]:
        """Filtre les séries météo par catégorie + mots-clés titre."""
        all_series = self.list_series()
        out = []
        for s in all_series:
            cat = (s.category or "").lower()
            title = (s.title or "").lower()
            if any(k in cat for k in WEATHER_CATEGORY_KEYWORDS):
                if any(k in title for k in WEATHER_TITLE_KEYWORDS):
                    out.append(s)
        return out

    # -- Events --

    def list_events(
        self,
        series_ticker: Optional[str] = None,
        status: Optional[str] = None,
        with_nested_markets: bool = False,
    ) -> Iterator[Event]:
        """Itère les events, optionnellement filtrés par série et statut."""
        params = {
            "series_ticker": series_ticker,
            "status": status,
            "with_nested_markets": "true" if with_nested_markets else None,
        }
        for raw in self._paginate("/events", params, key="events"):
            yield Event.from_api(raw)

    def get_event(self, event_ticker: str, with_nested_markets: bool = True) -> Event:
        """Récupère un event avec ses marchés."""
        params = {"with_nested_markets": "true" if with_nested_markets else "false"}
        data = self._get(f"/events/{event_ticker}", params)
        return Event.from_api(data.get("event", {}))

    # -- Markets --

    def get_market(self, ticker: str) -> Market:
        data = self._get(f"/markets/{ticker}")
        return Market.from_api(data.get("market", {}))

    def get_orderbook(self, ticker: str) -> dict:
        return self._get(f"/markets/{ticker}/orderbook")

    # -- Snapshot disque --

    def snapshot_event(self, event: Event) -> Path:
        """Sauvegarde l'état brut d'un event sur disque pour reproductibilité."""
        path = self.snapshot_dir / f"{event.event_ticker}.json"
        path.write_text(json.dumps(event.raw, indent=2), encoding="utf-8")
        return path
