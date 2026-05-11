"""Client HTTP pour l'API publique Kalshi (lecture seule, sans authentification)."""
from __future__ import annotations
import json
import re
import time
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urlencode

import requests

from src.config import KALSHI_API_BASE, USER_AGENT, MARKETS_DIR
from .models import Series, Event, Market


WEATHER_CATEGORY_KEYWORDS = ("climate", "weather")
WEATHER_TITLE_KEYWORDS = ("snow", "rain", "temperature", "precip", "hurricane")

# Whitelist used to sanitise `event_ticker` before it joins a filesystem
# path. Kalshi tickers are documented as upper-case alphanumerics + `-`
# but the upstream API is not under our control, so we enforce it here.
_TICKER_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")


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

    # Cap the total time spent on retries+sleeps per _get call. Without
    # this, three 429 responses with a Retry-After of 60s each would
    # stall the daily run for 3+ minutes per market.
    _RETRY_BUDGET_SECONDS = 60
    _RETRY_AFTER_CAP_SECONDS = 30

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode({k: v for k, v in params.items() if v is not None})}"
        budget_start = time.monotonic()
        last_exc: Optional[BaseException] = None
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=20)
                if resp.status_code == 429:
                    sleep_for = self._parse_retry_after(resp) or (2 ** attempt)
                    sleep_for = min(sleep_for, self._RETRY_AFTER_CAP_SECONDS)
                    if (time.monotonic() - budget_start) + sleep_for > self._RETRY_BUDGET_SECONDS:
                        raise requests.HTTPError(
                            f"kalshi rate-limit budget exhausted "
                            f"after {time.monotonic() - budget_start:.1f}s "
                            f"(Retry-After suggested {sleep_for}s)"
                        )
                    time.sleep(sleep_for)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                last_exc = e
                if attempt == 2:
                    raise
                sleep_for = 1 + attempt
                if (time.monotonic() - budget_start) + sleep_for > self._RETRY_BUDGET_SECONDS:
                    raise
                time.sleep(sleep_for)
        if last_exc is not None:  # pragma: no cover — defensive
            raise last_exc
        return {}

    @staticmethod
    def _parse_retry_after(resp: requests.Response) -> Optional[float]:
        """Read a `Retry-After` header. Returns None if absent/invalid."""
        raw = resp.headers.get("Retry-After")
        if not raw:
            return None
        try:
            return max(0.0, float(raw))
        except ValueError:
            return None

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
        """Sauvegarde l'état brut d'un event sur disque pour reproductibilité.

        SECURITY: `event_ticker` comes from Kalshi (third-party). We
        collapse any character outside `[A-Za-z0-9._-]` to underscore
        and then refuse paths that escape `self.snapshot_dir`. A bogus
        upstream value cannot overwrite arbitrary files on disk.
        """
        safe_ticker = _TICKER_SAFE_RE.sub("_", event.event_ticker or "")
        if not safe_ticker:
            raise ValueError(
                f"refusing snapshot for empty/invalid ticker: {event.event_ticker!r}"
            )
        snapshot_root = self.snapshot_dir.resolve()
        path = (snapshot_root / f"{safe_ticker}.json").resolve()
        try:
            path.relative_to(snapshot_root)
        except ValueError as exc:
            raise ValueError(
                f"snapshot path escape attempt for ticker {event.event_ticker!r}"
            ) from exc
        path.write_text(json.dumps(event.raw, indent=2), encoding="utf-8")
        return path
